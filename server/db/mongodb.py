from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "seoulmate")

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    # 자주 쓰는 쿼리 인덱스
    await db["dong_scores"].create_index([("dong_code", 1), ("year", 1), ("month", 1)])
    print(f"✅ MongoDB 연결 완료: {MONGO_DB}")


async def close_db():
    global client
    if client:
        client.close()
        print("🔌 MongoDB 연결 종료")


def get_db():
    return db
