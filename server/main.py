# main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from db.mongodb import connect_db, close_db
from routers import heatmap, overview


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 MongoDB 연결
    await connect_db()
    yield
    # 서버 종료 시 MongoDB 연결 해제
    await close_db()


app = FastAPI(
    title="SeoulMate API",
    description="서울시 동네 점수 조회 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 라우터 등록
app.include_router(heatmap.router)   # /v1/heatmap, /v1/heatmap/safety
app.include_router(overview.router)  # /v1/overview/{code}


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "ok"}