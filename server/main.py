from fastapi import FastAPI
from contextlib import asynccontextmanager
from db.mongodb import connect_db, close_db
from routers import heatmap, detail


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="SeoulMate API",
    description="서울시 동네 점수 조회 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(heatmap.router)
app.include_router(detail.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
