import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("cognitrace.concept_service")

# Common conversational filler words to ignore as concepts
FILLER_WORDS = {
  "today", "video", "see", "lecture", "now", "basically", "so", "welcome",
  "topic", "discussed", "already", "okay", "next", "going", "we", "in", "the",
  "this", "that", "there", "series", "dial", "with", "help", "of", "two", "examples"
}

# Educational topic keywords & mappings for clean concept extraction
CONCEPT_KEYWORD_MAP = [
    (r"\b(binary search tree|bst)\b", "Binary Search Tree", "Hard", "Binary Search"),
    (r"\b(time complexity|big o|logarithmic time|o\(n\)|o\(log n\))\b", "Time Complexity", "Medium", "Algorithm Properties"),
    (r"\b(space complexity|memory complexity)\b", "Space Complexity", "Medium", "Algorithm Properties"),
    (r"\b(binary search|halfing search|divide and conquer search)\b", "Binary Search", "Medium", "Arrays"),
    (r"\b(linear search|sequential search)\b", "Linear Search", "Easy", "Arrays"),
    (r"\b(array|arrays|elements|indexes)\b", "Arrays", "Easy", "None"),
    (r"\b(recursion|recursive|base case)\b", "Recursion", "Hard", "Functions"),
    (r"\b(algorithm|algorithms|step by step|pseudo code)\b", "Algorithm Definition & Properties", "Easy", "None"),
    (r"\b(data structure|data structures)\b", "Data Structures", "Easy", "None"),
    (r"\b(definition|introduction|overview|concept)\b", "Introduction & Concepts", "Easy", "None"),
]


class ConceptService:

    @staticmethod
    def extract_concepts_from_transcript(
        segments: List[Dict[str, Any]],
        subject_name: str = "",
        course_name: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Extract meaningful educational concept segments from stored Faster-Whisper transcript segments.
        Groups contiguous segments discussing the same educational topic, mapping precise timestamps.
        """
        if not segments:
            return []

        extracted_clusters: List[Dict[str, Any]] = []
        current_cluster: Dict[str, Any] = None

        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue

            text_lower = text.lower()
            start_fmt = seg.get("TranscriptStart", "00:00")
            end_fmt = seg.get("TranscriptEnd", "00:00")

            # Match text against educational topic keyword patterns
            matched_concept = None
            matched_difficulty = "Easy"
            matched_prereq = "None"

            for pattern, c_name, diff, prereq in CONCEPT_KEYWORD_MAP:
                if re.search(pattern, text_lower):
                    matched_concept = c_name
                    matched_difficulty = diff
                    matched_prereq = prereq
                    break

            # Fallback if no specific keyword matched: derive from course name or topic
            if not matched_concept:
                if "algorithm" in text_lower or "algorithm" in course_name.lower():
                    matched_concept = "Algorithm Execution & Examples"
                    matched_difficulty = "Easy"
                elif "search" in text_lower:
                    matched_concept = "Search Fundamentals"
                    matched_difficulty = "Easy"
                else:
                    matched_concept = f"{course_name.title() or 'Core'} Fundamentals"
                    matched_difficulty = "Easy"

            # Cluster adjacent segments with the same concept name
            if current_cluster is None:
                current_cluster = {
                    "Concept": matched_concept,
                    "ConceptStart": start_fmt,
                    "ConceptEnd": end_fmt,
                    "Prerequisite": matched_prereq,
                    "DifficultyLevel": matched_difficulty,
                    "text_count": 1
                }
            elif current_cluster["Concept"] == matched_concept:
                current_cluster["ConceptEnd"] = end_fmt
                current_cluster["text_count"] += 1
            else:
                extracted_clusters.append(current_cluster)
                current_cluster = {
                    "Concept": matched_concept,
                    "ConceptStart": start_fmt,
                    "ConceptEnd": end_fmt,
                    "Prerequisite": matched_prereq,
                    "DifficultyLevel": matched_difficulty,
                    "text_count": 1
                }

        if current_cluster:
            extracted_clusters.append(current_cluster)

        # Fix prerequisites in sequential order if prerequisite is "None" but a prior concept exists
        formatted_concepts: List[Dict[str, Any]] = []
        prior_concept_name = "None"

        for idx, cluster in enumerate(extracted_clusters):
            c_name = cluster["Concept"]
            prereq = cluster["Prerequisite"]

            if idx > 0 and (prereq == "None" or prereq == c_name):
                # Set prior distinct concept as prerequisite
                prereq = prior_concept_name if prior_concept_name != c_name else "None"

            item = {
                "Concept": c_name,
                "ConceptStart": cluster["ConceptStart"],
                "ConceptEnd": cluster["ConceptEnd"],
                "Prerequisite": prereq,
                "DifficultyLevel": cluster["DifficultyLevel"]
            }
            formatted_concepts.append(item)
            prior_concept_name = c_name

        logger.info("Extracted %d concept segment(s) from %d transcript segments for course '%s'.",
                    len(formatted_concepts), len(segments), course_name)

        return formatted_concepts
