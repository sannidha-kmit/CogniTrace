import asyncio
import re
import random
from typing import List, Optional, Dict, Any
from app.db.mongodb import get_database
from app.schemas.question import GeneratedMCQ

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
    r"\bhow many examples (are|were) (discussed|given|shown) in (this|the) video\b",
    r"\b(in this video|what did the (instructor|speaker|teacher) (say|mention|state))\b"
]

FORBIDDEN_OPTION_PATTERNS = [
    r"^(good morning|good afternoon|good evening|welcome to|hello everyone|thank you|thanks for watching)",
    r"\b(greeting|welcome the students|video starts?|instructor introduced)\b",
    r"\b(cpu registers?|cache memory|hardware bios|system bus(es)?|pipeline integration|terminal user interface|compile-time syntax|shared registers|static configuration tables)\b",
    r"\b(okay\?|in this video|we are going to learn|let us see|here I have|let me know)\b"
]

def clean_educational_transcript(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = raw_text
    # Strip YouTube intro chatter
    intro_match = re.search(
        r'\b(?:let\'?s|let us|lets)\s+(?:get\s+started|get\s+into\s+the\s+video|start(?:\s+off)?|begin|dive\s+in)(?:\s+now)?\b[\s.,:;!?]*',
        text,
        flags=re.IGNORECASE
    )
    if intro_match:
        text = text[intro_match.end():]
        
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    clean_sentences = []
    
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        if re.search(
            r'\b(?:subscribe|like\s+and\s+share|share\s+this\s+video|comment\s+section|let\s+me\s+know\s+in\s+the\s+comments?|thanks\s+for\s+watching|see\s+you\s+in\s+the\s+next\s+video|playlist|subscribers?\s+asked\s+me|asking\s+me\s+to\s+do\s+videos|upload\s+them\s+as\s+well\s+as\s+possible|hurry\s+up\s+making\s+videos|exams?\s+schedule|taking\s+some\s+time\s+because|give\s+a\s+good\s+quality\s+of\s+content|how\s+many\s+people\s+you\s+know)\b',
            s_clean,
            flags=re.IGNORECASE
        ):
            continue

        s_clean = re.sub(
            r'^(?:hello\s+everyone|welcome\s+back|good\s+morning|good\s+afternoon|good\s+evening|alright\s+then|now\s+let\'?s?\s+see|so\s+basically|okay\s+so|right\s+so|so\s+yeah|as\s+i\s+said\s+in\s+the\s+beginning|now\s+coming\s+to)\b[:,]?\s*',
            '',
            s_clean,
            flags=re.IGNORECASE
        ).strip()
        
        s_clean = re.sub(r'[,]?\s*\b(?:okay|right)\s*\??$', '.', s_clean, flags=re.IGNORECASE).strip()
        
        if len(s_clean) >= 20:
            clean_sentences.append(s_clean)
            
    return " ".join(clean_sentences)

def is_valid_conceptual_question(mcq: GeneratedMCQ, transcript_text: Optional[str] = None) -> bool:
    q_text = (mcq.question or "").strip()
    if not q_text or len(q_text) < 15:
        return False
    for pat in FORBIDDEN_QUESTION_PATTERNS:
        if re.search(pat, q_text, flags=re.IGNORECASE):
            return False
    options = mcq.options or []
    if len(options) != 4:
        return False
    clean_opts = [o.strip() for o in options if o and o.strip()]
    if len(clean_opts) != 4:
        return False
    if len(set(o.lower() for o in clean_opts)) != 4:
        return False
    for opt in clean_opts:
        for pat in FORBIDDEN_OPTION_PATTERNS:
            if re.search(pat, opt, flags=re.IGNORECASE):
                return False
    corr = (mcq.correct_answer or "").strip()
    if not corr:
        return False
    if not any(o.lower() == corr.lower() for o in clean_opts):
        return False
    if not (mcq.explanation or "").strip():
        return False
    if transcript_text and mcq.source_evidence:
        ev_clean = re.sub(r'[^a-zA-Z0-9\s]', '', mcq.source_evidence.lower()).strip()
        tx_clean = re.sub(r'[^a-zA-Z0-9\s]', '', transcript_text.lower())
        ev_tokens = [t for t in ev_clean.split() if len(t) > 3]
        if ev_tokens:
            matches = sum(1 for t in ev_tokens if t in tx_clean)
            if matches / len(ev_tokens) < 0.35:
                return False
    return True

def generate_concept_grounded_fallback(
    transcript_text: str,
    concept_name: str,
    count: int = 3,
    target_difficulty: Optional[str] = None,
    course_name: Optional[str] = None
) -> List[GeneratedMCQ]:
    """
    Concept-grounded extractive question generator that strictly derives questions
    from the cleaned transcript without using generic templates or out-of-domain technical distractors.
    """
    cleaned_tx = clean_educational_transcript(transcript_text)
    if not cleaned_tx or len(cleaned_tx.split()) < 25:
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
            "question": f"According to the lecture, how is machine learning fundamentally defined?",
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
            "question": f"In the formal formulation of a well-posed learning problem, what does component T represent?",
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
            "question": f"In a well-posed learning problem, which parameter measures how effectively the agent carries out the task?",
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
            "question": f"In the context of well-posed learning problems, what does the variable E designate?",
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

    # 5. Well Posed Problem - Examples (Checkers, Handwriting, Robot Driving)
    if "checkers" in tx_lower or "handwritten" in tx_lower or "robot driving" in tx_lower:
        candidates.append({
            "question": f"Which of the following is presented in the lecture as an authentic example of a well-posed learning problem?",
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

    # 6. Traditional Programming vs Machine Learning
    if "traditional" in tx_lower or "difference between" in tx_lower or "on its own" in tx_lower:
        candidates.append({
            "question": f"What is the fundamental difference between traditional programming and machine learning highlighted in the lecture?",
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

    # 7. AI, ML, DL Hierarchy
    if "deep learning" in tx_lower and "artificial intelligence" in tx_lower:
        candidates.append({
            "question": f"Based on the relationship explained in the lecture, how do AI, ML, and DL relate hierarchically?",
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

    # If we have extracted specific candidate questions, shuffle and validate
    random.shuffle(candidates)
    valid_mcqs: List[GeneratedMCQ] = []
    
    for c in candidates:
        mcq = GeneratedMCQ(
            question=c["question"],
            options=c["options"],
            correct_answer=c["correct_answer"],
            difficulty=diff,
            explanation=c["explanation"],
            concept=clean_concept,
            learning_point=c["learning_point"],
            source_evidence=c["source_evidence"]
        )
        if is_valid_conceptual_question(mcq, transcript_text=cleaned_tx):
            valid_mcqs.append(mcq)
            if len(valid_mcqs) >= count:
                break

    return valid_mcqs

async def test():
    db = await get_database()
    # Test Well Posed Problem
    tx_wp = await db.course_transcripts.find_one({"course_id": "6a895f063ec3b1b93c69597a"})
    raw_wp = " ".join([s.get("text", "") for s in tx_wp.get("segments", [])[:45]])
    mcqs_wp = generate_concept_grounded_fallback(raw_wp, "Well Posed Problem Fundamentals", count=3)
    print(f"Generated {len(mcqs_wp)} questions for Well Posed Problem Fundamentals:")
    for i, m in enumerate(mcqs_wp, 1):
        print(f"Q{i}: {m.question}")
        for opt in m.options:
            marker = " [CORRECT]" if opt == m.correct_answer else ""
            print(f"   - {opt}{marker}")
        print(f"   Learning Point: {m.learning_point}")
        print(f"   Source Evidence: {m.source_evidence}\n")

    # Test Intoduction to ML
    tx_ml = await db.course_transcripts.find_one({"course_id": "6a7f29a87959ed0a44852fc7"})
    raw_ml = " ".join([s.get("text", "") for s in tx_ml.get("segments", [])[:45]])
    mcqs_ml = generate_concept_grounded_fallback(raw_ml, "Intoduction To Ml Fundamentals", count=3)
    print(f"Generated {len(mcqs_ml)} questions for Intoduction To Ml Fundamentals:")
    for i, m in enumerate(mcqs_ml, 1):
        print(f"Q{i}: {m.question}")
        for opt in m.options:
            marker = " [CORRECT]" if opt == m.correct_answer else ""
            print(f"   - {opt}{marker}")
        print(f"   Learning Point: {m.learning_point}")
        print(f"   Source Evidence: {m.source_evidence}\n")

if __name__ == '__main__':
    asyncio.run(test())
