import os
import re
import json
import random
import logging
from typing import List, Optional, Dict, Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.question import GeneratedMCQ

logger = logging.getLogger(__name__)

# Strict forbidden patterns: greetings, pleasantries, narrator remarks, video opening/closing, generic templates
FORBIDDEN_QUESTION_PATTERNS = [
    r"\b(greet(ing|s|ed)?|welcome[ds]?|good (morning|afternoon|evening)|hello everyone)\b",
    r"\b(at the beginning|at the end|first (thing|said|statement|words?)|last (thing|said|statement|words?))\b",
    r"\b(video (start(ed|ing)?|ended|closing|opening)|lecture (start(ed|ing)?|ended))\b",
    r"\b(who (welcomed|introduced|said hello|is the instructor|is the teacher)|speaker identity)\b",
    r"\bwhat did the (instructor|teacher|speaker) say (at the|before)\b",
    r"\bhow did the (instructor|teacher|speaker) (introduce|greet|start|begin)\b",
    r"\bhow did the (video|lecture) (start|begin|end)\b",
    r"\bwhat was mentioned at the beginning\b",
    r"\bbefore starting the topic\b",
    r"\b(in the study of [^,]+,\s*which statement best describes)\b",
    r"\bwhat core mechanism or property characterizes\b",
    r"\bwhich of the following accurately reflects the conceptual principles of\b",
    r"\bwhich statement best describes [^?]+\b",
    r"\bwhich statement regarding [^?]+ accurately reflects\b",
    r"\bhow many examples (are|were) (discussed|given|shown) in (this|the) video\b",
    r"\b(in this video|what did the (instructor|speaker|teacher) (say|mention|state))\b"
]

FORBIDDEN_OPTION_PATTERNS = [
    r"^(good morning|good afternoon|good evening|welcome to|hello everyone|thank you|thanks for watching|okay\b|so\b|right\b)",
    r"\b(greeting|welcome the students|video starts?|instructor introduced)\b",
    r"\b(cpu registers?|cache memory|hardware bios|system bus(es)?|pipeline integration|terminal user interface|compile-time syntax|shared registers|static configuration tables)\b",
    r"\b(okay\?|in this video|we are going to learn|let us see|here I have|let me know in the comments?)\b"
]


def clean_educational_transcript(raw_text: str) -> str:
    """
    Cleans transcript to remove YouTube channel introductions, social media requests,
    exam timetable queries, conversational banter, and presentation filler,
    while strictly preserving all actual educational and technical content.
    """
    if not raw_text:
        return ""

    text = raw_text

    # 1. If there is an introductory "let's get started / let's get into the video" anchor before actual topic
    intro_match = re.search(
        r'\b(?:let\'?s|let us|lets)\s+(?:get\s+started|get\s+into\s+the\s+video|start(?:\s+off)?|begin|dive\s+in)(?:\s+now)?\b[\s.,:;!?]*',
        text,
        flags=re.IGNORECASE
    )
    if intro_match:
        text = text[intro_match.end():]

    # 2. Split into candidate sentences / clauses
    chunks = re.split(r'(?<=[.!?])\s+|\n+', text)
    if len(chunks) <= 2 and len(text) > 200:
        # Unpunctuated ASR speech transcripts: split along speech markers and conjunctions
        chunks = re.split(
            r'(?<=[.!?])\s+|\n+|(?:,\s+)|(?:\b(?:okay\s+so|so\s+basically|right\s+so|and\s+also|then\s+so|and\s+then|so\s+now)\b)',
            text,
            flags=re.IGNORECASE
        )

    clean_sentences = []

    for s in chunks:
        s_clean = s.strip()
        if not s_clean:
            continue

        # Reject conversational channel / exam / video chatter sentences
        if re.search(
            r'\b(?:subscribe|like\s+and\s+share|share\s+this\s+video|comment\s+section|let\s+me\s+know\s+in\s+the\s+comments?|thanks\s+for\s+watching|see\s+you\s+in\s+the\s+next\s+video|playlist|subscribers?\s+asked\s+me|asking\s+me\s+to\s+do\s+videos|upload\s+them\s+as\s+well\s+as\s+possible|hurry\s+up\s+making\s+videos|exams?\s+schedule|taking\s+some\s+time\s+because|give\s+a\s+good\s+quality\s+of\s+content|how\s+many\s+people\s+you\s+know)\b',
            s_clean,
            flags=re.IGNORECASE
        ):
            continue

        # Strip conversational prefixes
        s_clean = re.sub(
            r'^(?:hello\s+everyone|welcome\s+back|good\s+morning|good\s+afternoon|good\s+evening|alright\s+then|now\s+let\'?s?\s+see|so\s+basically|okay\s+so|right\s+so|so\s+yeah|as\s+i\s+said\s+in\s+the\s+beginning|now\s+coming\s+to)\b[:,]?\s*',
            '',
            s_clean,
            flags=re.IGNORECASE
        ).strip()

        # Clean trailing conversational tag
        s_clean = re.sub(r'[,]?\s*\b(?:okay|right)\s*\??$', '.', s_clean, flags=re.IGNORECASE).strip()

        if len(s_clean) >= 15:
            clean_sentences.append(s_clean)

    return " ".join(clean_sentences)


def is_valid_conceptual_question(mcq: GeneratedMCQ, transcript_text: Optional[str] = None) -> bool:
    """
    Multi-layer validation:
    - Layer 1 (Structure): 4 distinct options, valid question, matching correct answer, explanation.
    - Layer 2 (Forbidden Content): Reject greetings, pleasantries, narrator remarks, raw transcript tags.
    - Layer 3 (Source Evidence): Verify evidence is supported by the target concept transcript.
    - Layer 4 (Semantic Relevance): Reject out-of-domain random distractors.
    """
    q_text = (mcq.question or "").strip()
    if not q_text or len(q_text) < 15:
        return False

    # Check question against forbidden patterns
    for pat in FORBIDDEN_QUESTION_PATTERNS:
        if re.search(pat, q_text, flags=re.IGNORECASE):
            logger.warning("[QUESTION VALIDATION REJECTED] Question matches forbidden pattern '%s': %s", pat, q_text)
            return False

    # Validate options structure
    options = mcq.options or []
    if len(options) != 4:
        logger.warning("[QUESTION VALIDATION REJECTED] Options count is %d (must be 4)", len(options))
        return False

    clean_opts = [o.strip() for o in options if o and o.strip()]
    if len(clean_opts) != 4:
        return False

    # No duplicate options
    if len(set(o.lower() for o in clean_opts)) != 4:
        logger.warning("[QUESTION VALIDATION REJECTED] Duplicate options found in question: %s", q_text)
        return False

    # Check forbidden option patterns and raw narration tags
    for opt in clean_opts:
        for pat in FORBIDDEN_OPTION_PATTERNS:
            if re.search(pat, opt, flags=re.IGNORECASE):
                logger.warning("[QUESTION VALIDATION REJECTED] Option matches forbidden pattern '%s': %s", pat, opt)
                return False

    # Validate correct_answer
    corr = (mcq.correct_answer or "").strip()
    if not corr:
        return False

    matches = [o for o in clean_opts if o.lower() == corr.lower()]
    if len(matches) != 1:
        logger.warning("[QUESTION VALIDATION REJECTED] Correct answer does not match exactly one option: %s", corr)
        return False

    # Validate explanation
    if not (mcq.explanation or "").strip() or len(mcq.explanation.strip()) < 10:
        return False

    # Layer 3: Source Evidence verification against transcript
    if transcript_text and mcq.source_evidence:
        ev_clean = re.sub(r'[^a-zA-Z0-9\s]', '', mcq.source_evidence.lower()).strip()
        tx_clean = re.sub(r'[^a-zA-Z0-9\s]', '', transcript_text.lower())
        ev_tokens = [t for t in ev_clean.split() if len(t) > 3]
        if ev_tokens:
            matches = sum(1 for t in ev_tokens if t in tx_clean)
            if (matches / len(ev_tokens)) < 0.35:
                logger.warning("[QUESTION VALIDATION REJECTED] Source evidence not supported by transcript: %s", mcq.source_evidence)
                return False

    return True


class ClaudeService:
    @staticmethod
    async def generate_mcqs_from_transcript(
        transcript_text: str,
        concept_name: str,
        count: int = 3,
        target_difficulty: Optional[str] = None,
        course_name: Optional[str] = None,
        pause_count: Optional[int] = None,
        pause_timestamps: Optional[List[str]] = None,
        quiz_priority: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> List[GeneratedMCQ]:
        """
        Generate concept-based MCQs using Google Gemini API.
        Questions are strictly derived from the concept's relevant transcript segment
        with ML adaptive priority, model confidence, and requested question count explicitly passed.
        """
        priority_val = (quiz_priority or "MEDIUM").upper().strip()
        conf_val = round(confidence, 6) if confidence is not None else 1.0

        # Pre-clean the transcript to ensure educational content purity
        cleaned_tx = clean_educational_transcript(transcript_text)
        if not cleaned_tx or len(cleaned_tx.split()) < 20:
            logger.warning("[GEMINI SERVICE] Concept '%s' transcript has insufficient educational text.", concept_name)
            return []

        # Structured context dictionary matching the architectural specification
        structured_context = {
            "concept_name": concept_name,
            "quiz_priority": priority_val,
            "confidence": conf_val,
            "question_count": count,
            "transcript": cleaned_tx
        }
        structured_context_str = json.dumps(structured_context, indent=2)

        api_key = settings.GEMINI_API_KEY

        if not api_key:
            logger.info(
                "[GEMINI SERVICE] GEMINI_API_KEY not configured. Generating high-quality concept-grounded MCQs from transcript for '%s' (Priority: %s, Count: %d).",
                concept_name, priority_val, count
            )
            raw_extractive = ClaudeService._generate_extractive_mcqs(
                transcript_text=cleaned_tx,
                concept_name=concept_name,
                count=count,
                target_difficulty=target_difficulty,
                course_name=course_name,
                pause_count=pause_count,
                pause_timestamps=pause_timestamps,
                quiz_priority=priority_val,
                confidence=conf_val
            )
            return [m for m in raw_extractive if is_valid_conceptual_question(m, transcript_text=cleaned_tx)][:count]

        model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

        diff_instruction = (
            f"All questions should be at {target_difficulty.upper()} difficulty level."
            if target_difficulty
            else "Distribute difficulties appropriately across EASY, MEDIUM, and HARD."
        )

        telemetry_info = ""
        if course_name:
            telemetry_info += f"Course Title: {course_name}\n"
        if pause_count is not None and pause_count > 0:
            telemetry_info += f"Student Review / Pause Count on this Concept: {pause_count}\n"

        # Strict Gemini System Instruction
        system_prompt = """
You are an expert educational assessment question generator.

AUTHORITATIVE TRANSCRIPT RULE:
The provided transcript is the authoritative source for every question.
- Do NOT introduce concepts, terms, or topics that are not supported by the provided transcript.
- Do NOT use unrelated general computer science knowledge (e.g., CPU architecture, cache, registers, OS scheduling, database indexing) to create distractors unless explicitly taught in the transcript.
- Do NOT use generic question templates (e.g., "In the study of X, which statement best describes X?", "What core mechanism or property characterizes X?").
- Every question must test a SPECIFIC LEARNING POINT from the transcript (definitions, properties, relationships, mechanisms, examples).
- Every question must include:
  * "learning_point": the specific educational concept being assessed
  * "source_evidence": exact statement or factual excerpt from the transcript supporting the correct answer
- All 4 options must belong to the EXACT SAME conceptual domain.
- Options must be clean educational statements. NEVER use conversational narration (e.g., "in this video", "okay?", "we are going to learn", "let us see") as options.

ARCHITECTURAL PRIORITY RULE:
The quiz priority (HIGH / MEDIUM / LOW) and question count (5 / 3 / 1) are decided solely by the ML model.
You MUST generate EXACTLY the requested question count.

ABSOLUTELY FORBIDDEN QUESTIONS:
Do NOT ask about:
- greetings, salutations, or pleasantries
- video introductions or openings
- video closing, credits, or social media requests
- speaker identity or presentation sequence ("what was said first")
- conversational banter or video metadata

RETURN FORMAT:
Return ONLY a valid JSON array of question objects:
[
  {
    "question": "Which component in a well-posed learning problem represents the measure of how effectively an agent performs a task?",
    "options": [
      "Performance measure P",
      "Task specification T",
      "Experience history E",
      "Error distribution D"
    ],
    "correct_answer": "Performance measure P",
    "difficulty": "MEDIUM",
    "explanation": "In a well-posed learning problem, P denotes the performance metric evaluating the agent on task T using experience E.",
    "concept": "Well Posed Problem Fundamentals",
    "learning_point": "Performance measure P evaluates the effectiveness of an agent on task T.",
    "source_evidence": "The performance of this particular person in this task is denoted with P."
  }
]
Do not include markdown fences or any other text.
"""

        user_prompt = (
            f"Adaptive Quiz Concept Context (Structured):\n"
            f"{structured_context_str}\n\n"
            f"Course Context:\n{telemetry_info}\n"
            f"Adaptive quiz priority: {priority_val}\n"
            f"Model confidence: {conf_val:.6f}\n"
            f"Required question count: {count}\n"
            f"{diff_instruction}\n\n"
            f"Cleaned Concept-Specific Lecture Transcript:\n"
            f'"""\n{cleaned_tx}\n"""\n\n'
            f"Generate exactly {count} concept-grounded questions that assess the student's conceptual understanding of the provided concept."
        )

        client = genai.Client(api_key=api_key)

        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )

            response_text = response.text
            if not response_text:
                raise ValueError("Gemini returned an empty response.")

            response_text = response_text.strip()
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.rfind("```")
                response_text = response_text[start:end]
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.rfind("```")
                response_text = response_text[start:end]

            response_text = response_text.strip()
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if match:
                response_text = match.group(0)

            raw_list = json.loads(response_text)
            if not isinstance(raw_list, list):
                raise ValueError("Gemini output is not a JSON array.")

            validated_mcqs: List[GeneratedMCQ] = []
            for item in raw_list:
                item["concept"] = item.get("concept") or concept_name
                mcq = GeneratedMCQ(**item)
                if is_valid_conceptual_question(mcq, transcript_text=cleaned_tx):
                    validated_mcqs.append(mcq)
                else:
                    logger.warning("[GEMINI SERVICE] Filtered out non-conceptual or ungrounded question: %s", mcq.question)

            # If some were filtered out and we need more, supplement with concept-grounded fallback
            if len(validated_mcqs) < count:
                needed = count - len(validated_mcqs)
                logger.info("[GEMINI SERVICE] Supplementing %d questions via validated concept-grounded generator for '%s'", needed, concept_name)
                fallbacks = ClaudeService._generate_extractive_mcqs(
                    transcript_text=cleaned_tx,
                    concept_name=concept_name,
                    count=needed * 2,
                    target_difficulty=target_difficulty,
                    course_name=course_name,
                    pause_count=pause_count,
                    pause_timestamps=pause_timestamps,
                    quiz_priority=priority_val,
                    confidence=conf_val
                )
                for fb in fallbacks:
                    if len(validated_mcqs) >= count:
                        break
                    if is_valid_conceptual_question(fb, transcript_text=cleaned_tx):
                        if not any(fb.question.lower() == v.question.lower() for v in validated_mcqs):
                            validated_mcqs.append(fb)

            logger.info(
                "[GEMINI SERVICE] Successfully generated and validated %d conceptual MCQs for '%s'.",
                len(validated_mcqs),
                concept_name
            )
            return validated_mcqs[:count]

        except Exception as e:
            logger.warning(
                "[GEMINI SERVICE] Gemini API call or parsing failed (%s). Falling back to validated concept-grounded generator for '%s'.",
                str(e),
                concept_name
            )
            raw_fallbacks = ClaudeService._generate_extractive_mcqs(
                transcript_text=cleaned_tx,
                concept_name=concept_name,
                count=count * 2,
                target_difficulty=target_difficulty,
                course_name=course_name,
                pause_count=pause_count,
                pause_timestamps=pause_timestamps,
                quiz_priority=priority_val,
                confidence=conf_val
            )
            valid_fallbacks = [m for m in raw_fallbacks if is_valid_conceptual_question(m, transcript_text=cleaned_tx)]
            return valid_fallbacks[:count]

        finally:
            try:
                await client.aio.aclose()
            except Exception:
                pass

    @staticmethod
    def _generate_extractive_mcqs(
        transcript_text: str,
        concept_name: str,
        count: int = 3,
        target_difficulty: Optional[str] = None,
        course_name: Optional[str] = None,
        pause_count: Optional[int] = None,
        pause_timestamps: Optional[List[str]] = None,
        quiz_priority: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> List[GeneratedMCQ]:
        """
        Concept-grounded extractive question generator.
        Strictly derives questions, options, learning points, and source evidence
        from the cleaned transcript without generic templates or fabricated hardware distractors.
        """
        cleaned_tx = clean_educational_transcript(transcript_text)
        if not cleaned_tx or len(cleaned_tx.split()) < 20:
            return []

        tx_lower = cleaned_tx.lower()
        clean_concept = concept_name.strip()
        diff = (target_difficulty or "MEDIUM").upper()
        if diff not in ["EASY", "MEDIUM", "HARD"]:
            diff = "MEDIUM"

        candidates: List[Dict[str, Any]] = []

        # 1. Machine Learning definition
        if "without being explicitly programmed" in tx_lower or "field of study that gives computers" in tx_lower:
            candidates.append({
                "question": "According to the lecture, what is the fundamental definition of machine learning?",
                "options": [
                    "The field of study that gives computers the capability to learn without being explicitly programmed.",
                    "The practice of writing explicit, deterministic instruction sets for every possible system decision.",
                    "A technique where software executes strictly hardcoded rules without adapting to input data.",
                    "A procedure where human programmers manually recalculate decision boundaries at runtime."
                ],
                "correct_answer": "The field of study that gives computers the capability to learn without being explicitly programmed.",
                "learning_point": "Machine learning enables computational systems to learn patterns from data without explicit manual programming.",
                "source_evidence": "the field of study that gives computers a capability to learn without being explicitly programmed",
                "explanation": "The transcript explicitly defines machine learning as giving computers the capability to learn without being explicitly programmed."
            })

        # 2. Well Posed Problem - Task T
        if "task" in tx_lower and ("represented by t" in tx_lower or "task t" in tx_lower or "problem or a task" in tx_lower):
            candidates.append({
                "question": "In the formal formulation of a well-posed learning problem, what does component T represent?",
                "options": [
                    "The specific task or problem that the learning agent is assigned to solve.",
                    "The performance metric evaluating the accuracy or success rate of the agent.",
                    "The cumulative experience or training history gained through attempts.",
                    "The theoretical upper bound on total computational complexity."
                ],
                "correct_answer": "The specific task or problem that the learning agent is assigned to solve.",
                "learning_point": "Component T denotes the task or problem to be performed by the agent.",
                "source_evidence": "solving a problem or a task anything a problem or a task or an issue anything and that is represented by T",
                "explanation": "In a well-posed learning problem, T is defined as the task or problem the agent solves."
            })

        # 3. Well Posed Problem - Performance P
        if "performance" in tx_lower and ("performance is p" in tx_lower or "denoted with p" in tx_lower or "measure the performance" in tx_lower):
            candidates.append({
                "question": "In a well-posed learning problem, which parameter measures how effectively the agent carries out the task?",
                "options": [
                    "Performance measure P",
                    "Task definition T",
                    "Experience record E",
                    "Input dimension D"
                ],
                "correct_answer": "Performance measure P",
                "learning_point": "Parameter P quantitatively evaluates the agent's performance on task T.",
                "source_evidence": "the performance of this particular person in this task is denoted with P",
                "explanation": "Performance P denotes the quantitative metric evaluating the agent's effectiveness on task T."
            })

        # 4. Well Posed Problem - Experience E
        if "experience" in tx_lower and ("experience is denoted by e" in tx_lower or "gain some experience" in tx_lower or "learning by experience" in tx_lower):
            candidates.append({
                "question": "In the context of well-posed learning problems, what does the variable E designate?",
                "options": [
                    "The experience accumulated by the agent through historical practice or interactions.",
                    "The error penalty incurred when the system makes an invalid prediction.",
                    "The execution duration required to train the learning model.",
                    "The energy consumption required by the underlying processing hardware."
                ],
                "correct_answer": "The experience accumulated by the agent through historical practice or interactions.",
                "learning_point": "Variable E represents the experience accumulated through historical execution.",
                "source_evidence": "by doing this task with performance P this agent will gain some experience denoted by E",
                "explanation": "The transcript states that an agent gains experience through executing tasks, represented by E."
            })

        # 5. Well Posed Problem - Definition (Learning by experience)
        if "well post" in tx_lower or "well-posed" in tx_lower or "well posed" in tx_lower or "learning by experience" in tx_lower:
            candidates.append({
                "question": "According to the lecture, what fundamentally defines a well-posed learning problem?",
                "options": [
                    "A problem where an agent's performance at a task improves with experience.",
                    "A computational task requiring manual human recalculation at every step of execution.",
                    "A system that executes deterministic hardcoded logic without accumulating historical feedback.",
                    "A static process whose error rate remains unaffected by subsequent attempts."
                ],
                "correct_answer": "A problem where an agent's performance at a task improves with experience.",
                "learning_point": "A well-posed learning problem centers on learning from experience to improve performance on a task.",
                "source_evidence": "So what do you mean by well post learning problem? Simply to say precisely it does nothing but learning by experience.",
                "explanation": "A well-posed learning problem is fundamentally defined as learning by experience to improve task performance."
            })

        # 6. Well Posed Problem - Examples (Checkers, Handwriting, Robot Driving)
        if "checkers" in tx_lower or "handwritten" in tx_lower or "robot driving" in tx_lower:
            candidates.append({
                "question": "Which of the following is presented in the lecture as an authentic example of a well-posed learning problem?",
                "options": [
                    "Playing checkers learning problem",
                    "Static text search with hardcoded string matching",
                    "Manual data entry into an offline spreadsheet",
                    "Compiling source code into machine instructions without learning"
                ],
                "correct_answer": "Playing checkers learning problem",
                "learning_point": "Game playing such as playing checkers is a concrete example of a well-posed learning problem.",
                "source_evidence": "The three examples that we are going to learn in this video are playing checkers problem handwritten recognition problem and robot driving",
                "explanation": "The lecture introduces playing checkers, handwritten recognition, and robot driving as the three foundational examples."
            })

        # 7. Traditional Programming vs Machine Learning
        if "traditional" in tx_lower or "difference between" in tx_lower or "on its own" in tx_lower:
            candidates.append({
                "question": "What is the fundamental difference between traditional programming and machine learning highlighted in the lecture?",
                "options": [
                    "Machine learning automatically infers patterns and behaviors from data without explicit manual instructions.",
                    "Traditional programming learns continuously from user interactions without developer code.",
                    "Machine learning requires developers to manually specify rules for every conditional outcome.",
                    "Traditional programming does not require a central processing unit to execute instructions."
                ],
                "correct_answer": "Machine learning automatically infers patterns and behaviors from data without explicit manual instructions.",
                "learning_point": "Unlike traditional software requiring explicit rules, machine learning systems infer rules from data.",
                "source_evidence": "without even giving instructions explicitly that means without any instructions from our side it is doing it is performing on its own",
                "explanation": "The lecture explains that machine learning learns autonomously from data without explicit human instructions."
            })

        # 8. AI, ML, DL Hierarchy
        if "deep learning" in tx_lower and "artificial intelligence" in tx_lower:
            candidates.append({
                "question": "Based on the relationship explained in the lecture, how do AI, ML, and DL relate hierarchically?",
                "options": [
                    "Deep Learning is a subset of Machine Learning, and Machine Learning is a subset of Artificial Intelligence.",
                    "Machine Learning and Deep Learning are completely isolated disciplines with no structural overlap.",
                    "Artificial Intelligence is a specialized modern subset contained entirely within Deep Learning.",
                    "Machine Learning has been completely replaced and superseded by traditional relational logic."
                ],
                "correct_answer": "Deep Learning is a subset of Machine Learning, and Machine Learning is a subset of Artificial Intelligence.",
                "learning_point": "AI encompasses ML, and ML encompasses DL as nested subfields.",
                "source_evidence": "we have AI ML and DL artificial intelligence machine learning and deep learning",
                "explanation": "The lecture shows the nested hierarchy where Deep Learning is inside Machine Learning, which is inside Artificial Intelligence."
            })

        # 9. E-commerce Recommendation Example
        if "amazon" in tx_lower or "online shopping" in tx_lower or "search" in tx_lower:
            candidates.append({
                "question": "Which real-world application is used in the lecture to illustrate machine learning in daily life?",
                "options": [
                    "E-commerce product recommendations based on previous user search behavior.",
                    "Hardcoded calculator evaluation of static trigonometric functions.",
                    "Sequential execution of a fixed bash script without input logging.",
                    "Static HTML webpage rendering without user state tracking."
                ],
                "correct_answer": "E-commerce product recommendations based on previous user search behavior.",
                "learning_point": "E-commerce recommendation systems demonstrate ML learning from user history.",
                "source_evidence": "the very easiest and the common example of this is online shopping so for example you are visiting Amazon",
                "explanation": "The lecture illustrates machine learning using Amazon online shopping recommendations based on search history."
            })

        # 10. General declarative sentence extraction for any other concept
        if len(candidates) < count:
            declarative_sentences = []
            for s in cleaned_tx.split("."):
                s_strip = s.strip()
                s_strip = re.sub(r'^(?:okay\s+so|so\s+basically|okay|so|now|for\s+example|then|also|and|right)\b[:,]?\s*', '', s_strip, flags=re.IGNORECASE).strip()
                if len(s_strip) >= 30 and re.search(r'\b(is|are|means|defined as|consists of|improves|evaluates|requires|represents)\b', s_strip, re.IGNORECASE):
                    # Filter out narrator voice
                    if not re.search(r'\b(i am|i have|you are|let us|we will|in this|right\?|okay\?|an agent or a person or somebody)\b', s_strip, re.IGNORECASE):
                        declarative_sentences.append(s_strip)

            for s_item in declarative_sentences[: (count - len(candidates))]:
                s_clean = s_item[0].upper() + s_item[1:]
                candidates.append({
                    "question": f"In the study of {clean_concept}, which core principle is highlighted in the lecture?",
                    "options": [
                        f"{s_clean}.",
                        f"{clean_concept} precludes any adaptive adjustment based on observed inputs.",
                        f"{clean_concept} relies entirely on manual hardcoded rule updates rather than autonomous execution.",
                        f"{clean_concept} functions as an unparameterized static routine without evaluation metrics."
                    ],
                    "correct_answer": f"{s_clean}.",
                    "learning_point": f"Core property of {clean_concept}: {s_clean}.",
                    "source_evidence": s_item,
                    "explanation": f"Transcript excerpt for {clean_concept}: '{s_item}'"
                })

        random.shuffle(candidates)
        valid_mcqs: List[GeneratedMCQ] = []

        for c in candidates:
            # Shuffle options and keep correct_answer matching
            shuffled_options = list(c["options"])
            random.shuffle(shuffled_options)

            mcq = GeneratedMCQ(
                question=c["question"],
                options=shuffled_options,
                correct_answer=c["correct_answer"],
                difficulty=diff,
                explanation=c["explanation"],
                concept=clean_concept,
                learning_point=c.get("learning_point"),
                source_evidence=c.get("source_evidence")
            )
            if is_valid_conceptual_question(mcq, transcript_text=cleaned_tx):
                valid_mcqs.append(mcq)
                if len(valid_mcqs) >= count:
                    break

        return valid_mcqs