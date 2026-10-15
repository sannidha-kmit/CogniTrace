import asyncio
from app.db.mongodb import get_database

async def main():
    db = await get_database()
    qs = await db.questions.find({}).to_list(100)
    print(f"Total questions in DB: {len(qs)}")
    for q in qs[:15]:
        print(f"[{q.get('concept_name')}] {q.get('question')}")
        opts = q.get("options", [])
        for o in opts:
            print(f"   - {o}")
        print()

if __name__ == '__main__':
    asyncio.run(main())
