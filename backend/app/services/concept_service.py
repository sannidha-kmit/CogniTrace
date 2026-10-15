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

# Educational topic keywords & mappings for clean concept extraction across CS curriculum
CONCEPT_KEYWORD_MAP = [
    # ── Computer Organization and Architecture (COA) ──
    (r"\b(computer architecture|functional behavior|architectural specification|design implementation|tony stark|iron man)\b", "Computer Architecture & Functional Behavior", "Easy", "None"),
    (r"\b(computer organization|structural relationship|operational attributes|functional units|functional components)\b", "Computer Organization & Structure", "Easy", "Computer Architecture & Functional Behavior"),
    (r"\b(processor|arithmetic and logic unit|alu|timing and control|control unit|registers|register section)\b", "Processor Organization & ALU", "Medium", "Computer Organization & Structure"),
    (r"\b(system bus|data bus|address bus|control bus|intercommunication)\b", "System Bus & Intercommunication", "Easy", "Processor Organization & ALU"),
    (r"\b(memory hierarchy|memory interfacing|memory mapping|secondary memory|cache|ram|rom)\b", "Memory Hierarchy & Interfacing", "Medium", "System Bus & Intercommunication"),
    (r"\b(instruction pipelining|pipelining|pipeline hazards|processor efficiency|throughput)\b", "Instruction Pipelining & Optimization", "Hard", "Processor Organization & ALU"),
    (r"\b(io interfacing|input output|io peripherals|data transmission modes|peripherals)\b", "I/O Interfacing & Peripherals", "Medium", "System Bus & Intercommunication"),
    (r"\b(machine instructions|addressing modes|instruction format|data path)\b", "Machine Instructions & Addressing Modes", "Hard", "Processor Organization & ALU"),
    (r"\b(number systems?|binary|two's complement|booth's|floating point|ieee 754)\b", "Number Systems & Data Representation", "Easy", "None"),
    (r"\b(half adder|full adder|digital logic|logic design|gates|flip flop)\b", "Digital Logic & Circuit Design", "Easy", "None"),

    # ── Operating Systems (OS) ──
    (r"\b(process scheduling|cpu scheduling|round robin|fcfs|sjf|priority scheduling)\b", "CPU Scheduling Algorithms", "Medium", "Process Management"),
    (r"\b(deadlock|deadlocks|banker's algorithm|resource allocation graph)\b", "Deadlock Detection & Prevention", "Hard", "Process Synchronization"),
    (r"\b(semaphore|mutex|critical section|race condition|synchronization)\b", "Process Synchronization", "Hard", "Process Management"),
    (r"\b(virtual memory|paging|page fault|segmentation|tlb|page replacement)\b", "Virtual Memory & Paging", "Hard", "Memory Management"),

    # ── Database Management Systems (DBMS) ──
    (r"\b(normalization|1nf|2nf|3nf|bcnf|functional dependency)\b", "Database Normalization", "Hard", "Relational Model"),
    (r"\b(acid properties|transaction|concurrency control|serializability)\b", "Transactions & ACID Properties", "Hard", "Database Fundamentals"),
    (r"\b(sql|query optimization|joins|indexing|b-tree|b\+ tree)\b", "SQL & Query Indexing", "Medium", "Relational Model"),

    # ── Computer Networks (CN) ──
    (r"\b(osi model|tcp/ip|network layers|transport layer|application layer|data link)\b", "Network Models & Protocols", "Easy", "None"),
    (r"\b(routing|dijkstra|distance vector|link state|bgp|ospf)\b", "Routing Algorithms & Protocols", "Hard", "Network Models & Protocols"),
    (r"\b(tcp|udp|flow control|congestion control|sliding window|three-way handshake)\b", "Transport Layer & Flow Control", "Medium", "Network Models & Protocols"),

    # ── Data Structures & Algorithms (DAA) ──
    (r"\b(binary search tree|bst|avl tree|red black tree)\b", "Binary Search Tree", "Hard", "Binary Search"),
    (r"\b(time complexity|big o|logarithmic time|o\(n\)|o\(log n\))\b", "Time Complexity", "Medium", "Algorithm Properties"),
    (r"\b(space complexity|memory complexity)\b", "Space Complexity", "Medium", "Algorithm Properties"),
    (r"\b(binary search|halfing search|divide and conquer search)\b", "Binary Search", "Medium", "Arrays"),
    (r"\b(linear search|sequential search)\b", "Linear Search", "Easy", "Arrays"),
    (r"\b(array|arrays|elements|indexes)\b", "Arrays", "Easy", "None"),
    (r"\b(recursion|recursive|base case)\b", "Recursion", "Hard", "Functions"),
    (r"\b(algorithm|algorithms|step by step|pseudo code)\b", "Algorithm Definition & Properties", "Easy", "None"),
    (r"\b(data structure|data structures)\b", "Data Structures", "Easy", "None"),
    (r"\b(definition|introduction|overview|concept)\b", "Introduction & Overview", "Easy", "None"),
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

        # Pass 1: Merge identical adjacent clusters
        merged: List[Dict[str, Any]] = []
        for c in extracted_clusters:
            if not merged:
                merged.append(dict(c))
            elif merged[-1]["Concept"] == c["Concept"]:
                merged[-1]["ConceptEnd"] = c["ConceptEnd"]
                merged[-1]["text_count"] += c.get("text_count", 1)
            else:
                merged.append(dict(c))

        # Pass 2: Merge transient fallback fragments into dominant neighboring educational concepts
        smoothed: List[Dict[str, Any]] = []
        for c in merged:
            if not smoothed:
                smoothed.append(c)
                continue
            if "Fundamentals" in c["Concept"] and c.get("text_count", 1) <= 3 and "Fundamentals" not in smoothed[-1]["Concept"]:
                smoothed[-1]["ConceptEnd"] = c["ConceptEnd"]
                smoothed[-1]["text_count"] += c.get("text_count", 1)
            elif smoothed[-1]["Concept"] == c["Concept"]:
                smoothed[-1]["ConceptEnd"] = c["ConceptEnd"]
                smoothed[-1]["text_count"] += c.get("text_count", 1)
            else:
                smoothed.append(c)

        # Pass 3: Final adjacent merge
        final_clusters: List[Dict[str, Any]] = []
        for c in smoothed:
            if not final_clusters:
                final_clusters.append(c)
            elif final_clusters[-1]["Concept"] == c["Concept"]:
                final_clusters[-1]["ConceptEnd"] = c["ConceptEnd"]
                final_clusters[-1]["text_count"] += c.get("text_count", 1)
            else:
                final_clusters.append(c)

        # Fix prerequisites in sequential order if prerequisite is "None" but a prior concept exists
        formatted_concepts: List[Dict[str, Any]] = []
        prior_concept_name = "None"

        for idx, cluster in enumerate(final_clusters):
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

