import asyncio
from app.db.mongodb import get_database

async def main():
    db = await get_database()
    # 1. Well Posed Problem
    tx = await db.course_transcripts.find_one({'course_id': '6a895f063ec3b1b93c69597a'})
    if tx:
        segs = tx.get('segments', [])
        print("=== Well Posed Problem Segments 20 to 50 ===")
        for s in segs[20:50]:
            t_start = s.get('TranscriptStart') or s.get('start')
            t_end = s.get('TranscriptEnd') or s.get('end')
            print(f"[{t_start} - {t_end}]: {s.get('text')}")

    # 2. Intoduction to ML
    tx_ml = await db.course_transcripts.find_one({'course_id': '6a7f29a87959ed0a44852fc7'})
    if tx_ml:
        segs_ml = tx_ml.get('segments', [])
        print("\n=== Intoduction to ML Segments 0 to 30 ===")
        for s in segs_ml[:30]:
            t_start = s.get('TranscriptStart') or s.get('start')
            t_end = s.get('TranscriptEnd') or s.get('end')
            print(f"[{t_start} - {t_end}]: {s.get('text')}")

if __name__ == '__main__':
    asyncio.run(main())
