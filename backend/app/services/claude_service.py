import os
import json
import logging
from typing import List, Optional

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.question import GeneratedMCQ

logger = logging.getLogger(__name__)


class ClaudeService:
    @staticmethod
    async def generate_mcqs_from_transcript(
        transcript_text: str,
        concept_name: str,
        count: int = 3,
        target_difficulty: Optional[str] = None,
        course_name: Optional[str] = None,
        pause_count: Optional[int] = None,
        pause_timestamps: Optional[List[str]] = None
    ) -> List[GeneratedMCQ]:

        """
        Generate MCQs using Google Gemini API.

        The method name/class is kept as ClaudeService so the rest of
        the existing Cognitrace application does not need to change.
        """

        # ---------------------------------------------------------
        # 1. Get Gemini API key
        # ---------------------------------------------------------
        api_key = settings.GEMINI_API_KEY

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is missing. "
                "Please configure GEMINI_API_KEY in backend/.env"
            )

        # ---------------------------------------------------------
        # 2. Get Gemini model
        # ---------------------------------------------------------
        model_name = (
            settings.GEMINI_MODEL
            or "gemini-2.5-flash"
        )

        logger.info(
            "[GEMINI SERVICE] Using Gemini model: %s",
            model_name
        )

        # ---------------------------------------------------------
        # 3. Difficulty instruction
        # ---------------------------------------------------------
        diff_instruction = (
            f"All questions should be at "
            f"{target_difficulty.upper()} difficulty level."
            if target_difficulty
            else
            "Distribute difficulties appropriately across "
            "EASY, MEDIUM, and HARD."
        )

        # ---------------------------------------------------------
        # 4. Telemetry information
        # ---------------------------------------------------------
        telemetry_info = ""

        if course_name:
            telemetry_info += (
                f"Course Title: {course_name}\n"
            )

        if pause_count is not None:
            telemetry_info += (
                f"Student Pause Count on Video: {pause_count}\n"
            )

        if pause_timestamps:
            telemetry_info += (
                "Student Video Pause Timestamps: "
                f"{', '.join(pause_timestamps)}\n"
            )

        # ---------------------------------------------------------
        # 5. System instruction
        # ---------------------------------------------------------
        system_prompt = """
You are an expert academic assessment generator.

Generate high-quality Multiple Choice Questions (MCQs) based
STRICTLY AND EXCLUSIVELY on the provided lecture transcript.

IMPORTANT:
- Do NOT use outside general knowledge.
- Do NOT invent facts.
- Every question must be answerable directly from the transcript.
- Generate exactly the requested number of questions.
- Each question must have exactly 4 options.
- The correct_answer must be VERBATIM IDENTICAL to one of the 4 options.
- difficulty must be exactly one of:
  EASY, MEDIUM, HARD
- explanation must explain why the correct answer is correct
  using information from the transcript.
- Do not create duplicate questions.

Return ONLY a valid JSON array.

Each object must contain:
{
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "correct_answer": "...",
    "difficulty": "EASY",
    "explanation": "...",
    "concept": "..."
}

Do not include markdown.
Do not include ```json.
Do not include any text outside the JSON array.
"""

        # ---------------------------------------------------------
        # 6. User prompt
        # ---------------------------------------------------------
        user_prompt = (
            f"Course & Student Interaction Context:\n"
            f"{telemetry_info}\n"

            f"Target Concept Name: {concept_name}\n"
            f"Requested Question Count: {count}\n"
            f"{diff_instruction}\n\n"

            f"Lecture Transcript Content:\n"
            f'"""\n'
            f"{transcript_text}\n"
            f'"""\n\n'

            f"Generate exactly {count} MCQs."
        )

        # ---------------------------------------------------------
        # 7. Create Gemini client
        # ---------------------------------------------------------
        client = genai.Client(api_key=api_key)

        try:
            # -----------------------------------------------------
            # 8. Call Gemini
            # -----------------------------------------------------
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )

            # -----------------------------------------------------
            # 9. Read response
            # -----------------------------------------------------
            response_text = response.text

            if not response_text:
                raise ValueError(
                    "Gemini returned an empty response."
                )

            response_text = response_text.strip()

            # Safety cleanup in case Gemini adds markdown fences
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.rfind("```")
                response_text = response_text[start:end]
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.rfind("```")
                response_text = response_text[start:end]
            
            response_text = response_text.strip()
            
            import re
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if match:
                response_text = match.group(0)

            # -----------------------------------------------------
            # 10. Parse JSON
            # -----------------------------------------------------
            raw_list = json.loads(response_text)

            if not isinstance(raw_list, list):
                raise ValueError(
                    "Gemini output is not a JSON array."
                )

            # -----------------------------------------------------
            # 11. Validate MCQs using existing schema
            # -----------------------------------------------------
            validated_mcqs: List[GeneratedMCQ] = []

            for item in raw_list:
                mcq = GeneratedMCQ(**item)
                validated_mcqs.append(mcq)

            logger.info(
                "[GEMINI SERVICE] Successfully generated "
                "and validated %d MCQs.",
                len(validated_mcqs)
            )

            return validated_mcqs

        except json.JSONDecodeError as e:
            logger.error(
                "[GEMINI SERVICE] JSON parsing failed: %s",
                str(e)
            )

            raise ValueError(
                f"Gemini API returned invalid JSON: {str(e)}"
            )

        except Exception as e:
            logger.error(
                "[GEMINI SERVICE] API call failed: %s",
                str(e)
            )

            raise ValueError(
                f"Gemini API Call Error: {str(e)}"
            )

        finally:
            # Close the async client connection
            try:
                await client.aio.aclose()
            except Exception:
                pass