import asyncio
import joblib
import numpy as np
from app.db.mongodb import get_database
from app.services.mapping_service import parse_timestamp_to_seconds

FEATURES = [
    "backward_count",
    "replay_count",
    "study_pause_count",
    "other_work_pause_count",
    "forward_count",
    "speed_increase_count"
]

def normalize_pause_reason(reason):
    if not reason:
        return None
    r = str(reason).strip().lower()
    if r == "study":
        return "study"
    if r == "other_work":
        return "other_work"
    return None

async def main():
    db = await get_database()
    course_id = "6a7f29a87959ed0a44852fc7"
    student_id = "S24A003"
    
    # 1. Get concept segments
    cs_doc = await db.concept_segments.find_one({"course_id": course_id})
    segments = cs_doc.get("segments", []) if cs_doc else []
    print(f"Course: {cs_doc.get('CourseName')} with {len(segments)} concept segments:")
    for s in segments:
        print(f"  Concept: '{s.get('Concept')}', Start: {s.get('ConceptStart')}, End: {s.get('ConceptEnd')}")
        
    # 2. Get events
    events = await db.interaction_events.find({
        "CourseID": course_id,
        "StudentID": student_id
    }).sort("created_at", 1).to_list(length=500)
    print(f"\nTotal events for {student_id}: {len(events)}")
    
    # 3. Map events to concepts
    # Using the boundary rule: ConceptStart <= event_secs < ConceptEnd (or <=)
    from app.services.mapping_service import MappingService
    
    concept_events = {s.get("Concept"): [] for s in segments}
    
    for ev in events:
        ts_sec = parse_timestamp_to_seconds(ev.get("EventTimestamp", "00:00"))
        matched = MappingService.find_matching_concept_segment(segments, ts_sec)
        c_name = matched.get("Concept")
        if c_name in concept_events:
            concept_events[c_name].append(ev)
        else:
            concept_events[c_name] = [ev]
            
    # 4. Load ML model
    loaded_dict = joblib.load("models/adaptive_quiz_model.pkl")
    model = loaded_dict["model"]
    print("\nLoaded model classes:", model.classes_)
    
    print("\nAggregated Features per Concept:")
    for c_name, ev_list in concept_events.items():
        backward_count = sum(1 for e in ev_list if e.get("EventType") == "SEEK_BACKWARD")
        replay_count = sum(1 for e in ev_list if e.get("EventType") == "REPLAY")
        study_pause_count = sum(1 for e in ev_list if e.get("EventType") == "PAUSE" and normalize_pause_reason(e.get("PauseReason")) == "study")
        other_work_pause_count = sum(1 for e in ev_list if e.get("EventType") == "PAUSE" and normalize_pause_reason(e.get("PauseReason")) == "other_work")
        forward_count = sum(1 for e in ev_list if e.get("EventType") == "SEEK_FORWARD")
        speed_increase_count = sum(1 for e in ev_list if e.get("EventType") == "SPEED_CHANGE" and float(e.get("PlaybackSpeed") or 1.0) > 1.0)
        
        feature_vector = [
            backward_count,
            replay_count,
            study_pause_count,
            other_work_pause_count,
            forward_count,
            speed_increase_count
        ]
        
        pred = model.predict([feature_vector])[0]
        proba = model.predict_proba([feature_vector])[0]
        confidence = float(np.max(proba))
        
        q_count = 5 if pred == "HIGH" else (3 if pred == "MEDIUM" else 1)
        
        print(f"\nConcept: '{c_name}'")
        print(f"  Features: {dict(zip(FEATURES, feature_vector))}")
        print(f"  Prediction: {pred}")
        print(f"  Confidence: {confidence:.6f}")
        print(f"  Question Count: {q_count}")

if __name__ == "__main__":
    asyncio.run(main())
