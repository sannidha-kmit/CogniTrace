import asyncio
from app.db.mongodb import get_database, connect_to_mongo, close_mongo_connection
from app.core.security import get_password_hash

async def inspect():
    await connect_to_mongo()
    db = await get_database()
    
    # Check users
    users = await db.users.find().to_list(100)
    print("USERS:", [(u.get("identifier"), u.get("role")) for u in users])
    
    # Reset passwords to 'password' for easy testing
    for u in users:
        new_hash = get_password_hash("password")
        await db.users.update_one({"_id": u["_id"]}, {"$set": {"hashed_password": new_hash}})
        print(f"Reset password for {u.get('identifier')} to 'password'")
        
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(inspect())
