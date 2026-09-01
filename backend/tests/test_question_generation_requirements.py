import pytest
from unittest.mock import patch, MagicMock
from app.services.question_service import QuestionService
from app.schemas.question import GeneratedMCQ
from pymongo.errors import DuplicateKeyError

@pytest.fixture
def mock_db():
    class MockCollection:
        def __init__(self, data=None):
            self.data = data or {}
        
        async def find_one(self, query):
            course_id = query.get("course_id")
            if course_id in self.data:
                return self.data[course_id]
            # Handling hash queries
            if "question_hash" in query:
                return None
            return None
            
        async def insert_one(self, doc):
            class InsertResult:
                inserted_id = "test_id"
            return InsertResult()

    class MockDatabase:
        def __init__(self):
            # course_transcripts and concept_segments
            self.course_transcripts = MockCollection({
                "course_1": {
                    "course_id": "course_1",
                    "status": "COMPLETED",
                    "segments": [
                        {"start": "00:00", "end": "00:30", "text": "This is concept A content."},
                        {"start": "00:31", "end": "01:00", "text": "This is concept B content."}
                    ]
                },
                "course_2": {
                    "course_id": "course_2",
                    "status": "COMPLETED",
                    "segments": [
                        {"start": "00:00", "end": "00:30", "text": "Operating Systems memory management."},
                        {"start": "00:31", "end": "01:00", "text": "Empty text here."}
                    ]
                },
                "course_3": {
                    "course_id": "course_3",
                    "status": "COMPLETED",
                    "segments": [
                        {"start": "00:00", "end": "00:30", "text": "Different OS content."}
                    ]
                }
            })
            self.concept_segments = MockCollection({
                "course_1": {
                    "course_id": "course_1",
                    "status": "COMPLETED",
                    "segments": [
                        {"Concept": "Concept A", "ConceptStart": "00:00", "ConceptEnd": "00:30"},
                        {"Concept": "Concept B", "ConceptStart": "00:31", "ConceptEnd": "01:00"},
                        {"Concept": "Empty Concept", "ConceptStart": "02:00", "ConceptEnd": "03:00"}
                    ]
                },
                "course_2": {
                    "course_id": "course_2",
                    "CourseName": "Operating Systems",
                    "status": "COMPLETED",
                    "segments": [
                        {"Concept": "Memory", "ConceptStart": "00:00", "ConceptEnd": "00:30"}
                    ]
                },
                "course_3": {
                    "course_id": "course_3",
                    "CourseName": "Operating Systems",
                    "status": "COMPLETED",
                    "segments": [
                        {"Concept": "CPU", "ConceptStart": "00:00", "ConceptEnd": "00:30"}
                    ]
                }
            })
            self.questions = MockCollection()
    
    return MockDatabase()

@pytest.mark.asyncio
@patch("app.services.question_service.get_database")
async def test_extract_transcript_for_concept_normal(mock_get_db, mock_db):
    mock_get_db.return_value = mock_db
    
    # Requirement 9: Multiple Concept Test
    # Test Concept A
    ref_a, name_a, text_a = await QuestionService.extract_transcript_for_concept("course_1", "Concept A")
    assert name_a == "Concept A"
    assert "concept a content" in text_a.lower()
    assert "concept b content" not in text_a.lower()

    # Test Concept B
    ref_b, name_b, text_b = await QuestionService.extract_transcript_for_concept("course_1", "Concept B")
    assert name_b == "Concept B"
    assert "concept b content" in text_b.lower()
    assert "concept a content" not in text_b.lower()

@pytest.mark.asyncio
@patch("app.services.question_service.get_database")
async def test_empty_transcript_handling(mock_get_db, mock_db):
    mock_get_db.return_value = mock_db
    
    # Requirement 7: Empty Transcript Handling
    with pytest.raises(ValueError, match="No transcript content available for this concept."):
        await QuestionService.extract_transcript_for_concept("course_1", "Empty Concept")

@pytest.mark.asyncio
@patch("app.services.question_service.get_database")
async def test_missing_concept_handling(mock_get_db, mock_db):
    mock_get_db.return_value = mock_db
    
    # Requirement 8: Missing Concept Handling
    with pytest.raises(ValueError, match="Concept 'Missing Concept' not found in course concepts."):
        await QuestionService.extract_transcript_for_concept("course_1", "Missing Concept")

@pytest.mark.asyncio
@patch("app.services.question_service.get_database")
async def test_same_course_name_different_ids(mock_get_db, mock_db):
    mock_get_db.return_value = mock_db
    
    # Requirement 11: Same Course Name Test (and Req 10: Multiple Course/Video Test)
    # course_2 and course_3 both have CourseName="Operating Systems"
    ref_2, name_2, text_2 = await QuestionService.extract_transcript_for_concept("course_2", "Memory")
    assert "memory management" in text_2.lower()
    
    ref_3, name_3, text_3 = await QuestionService.extract_transcript_for_concept("course_3", "CPU")
    assert "different os content" in text_3.lower()

@pytest.mark.asyncio
@patch("app.services.question_service.get_database")
@patch("app.services.question_service.ClaudeService.generate_mcqs_from_transcript")
async def test_generate_and_store_questions_counts_and_duplicates(mock_claude, mock_get_db, mock_db):
    mock_get_db.return_value = mock_db
    
    # Simulate Claude returning 3 questions, with 2 being duplicates
    mock_mcq_1 = GeneratedMCQ(
        question="What is 1+1?", options=["1", "2", "3", "4"], correct_answer="2",
        difficulty="EASY", explanation="Basic math", concept="Math"
    )
    mock_mcq_2 = GeneratedMCQ( # duplicate
        question="What is 1+1?", options=["1", "2", "3", "4"], correct_answer="2",
        difficulty="EASY", explanation="Basic math", concept="Math"
    )
    mock_mcq_3 = GeneratedMCQ(
        question="What is 2+2?", options=["2", "3", "4", "5"], correct_answer="4",
        difficulty="EASY", explanation="Basic math", concept="Math"
    )
    
    mock_claude.return_value = [mock_mcq_1, mock_mcq_2, mock_mcq_3]
    
    # We requested 3, Claude gives 3, but one is a duplicate
    questions = await QuestionService.generate_and_store_questions(
        course_id="course_1", concept_identifier="Concept A", count=3
    )
    
    # Requirement 6: Duplicate Question Prevention (intra-request)
    assert len(questions) == 2
    assert questions[0].question == "What is 1+1?"
    assert questions[1].question == "What is 2+2?"

    # Verify count passed to Claude (Requirement 12: Different Question Counts)
    mock_claude.assert_called_with(
        transcript_text="This is concept A content.",
        concept_name="Concept A",
        count=3,
        target_difficulty=None,
        course_name=None,
        pause_count=None,
        pause_timestamps=None
    )
