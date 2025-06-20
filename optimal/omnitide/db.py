import motor.motor_asyncio
import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = os.environ.get("DB_NAME", "omnitide")
COLLECTION = os.environ.get("COLLECTION", "data")

client = None
db = None
collection = None


async def ensure_db_connection():
    global client, db, collection
    if client is None:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION]


async def store_data(data: dict, meta: dict):
    await ensure_db_connection()
    await collection.insert_one({"data": data, "meta": meta})


async def query_data(item_id: str = None, param: str = None, value: str = None):
    await ensure_db_connection()
    if item_id:
        return await collection.find_one({"_id": item_id})
    elif param and value:
        return [doc async for doc in collection.find({f"data.{param}": value})]
    else:
        return [doc async for doc in collection.find({})]
