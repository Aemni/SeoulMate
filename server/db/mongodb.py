# app/db/mongodb.py

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# .env 파일에서 환경변수 로드 (MONGO_URI, MONGO_DB)
load_dotenv()

# 전역 변수로 클라이언트와 DB 객체 관리
# 서버 시작할 때 connect_db()로 초기화, 종료할 때 close_db()로 해제
client: AsyncIOMotorClient = None
db = None


async def connect_db():
    """
    FastAPI 서버 시작 시 MongoDB에 연결
    main.py의 lifespan에서 호출됨
    """
    global client, db
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB  = os.getenv("MONGO_DB", "seoulmate")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]
    print(f"[DB] MongoDB 연결 완료 → {MONGO_DB}")


async def close_db():
    """
    FastAPI 서버 종료 시 MongoDB 연결 해제
    main.py의 lifespan에서 호출됨
    """
    global client
    if client:
        client.close()
        print("[DB] MongoDB 연결 종료")


def get_db():
    """
    라우터/서비스에서 DB 쿼리할 때 호출
    반환값: AsyncIOMotorDatabase 객체
    """
    return db