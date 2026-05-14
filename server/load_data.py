"""
CSV 데이터 → MongoDB 적재 스크립트
실행: python load_data.py

컬렉션 구조:
- health_scores  ← monthly_risk.csv  (행정동별 월별, 건강안전도)
- comfort_scores ← comfort.csv       (행정동별 월별, 쾌적도)
- safety_scores  ← safety_model.csv  (구별 → 동별 확장, 치안)

훈섭님 담당 (추후 추가):
- stress_scores  ← 서버팀 pkl 모델
- hvac_scores    ← 서버팀 pkl 모델
"""

import asyncio
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "seoulmate")
BASE_PATH = r"C:\Users\T\Desktop\SeoulMate"


# ── 1. health_scores 적재 ────────────────────────────────────────
async def load_health(db):
    print("\n[health] monthly_risk.csv 로드 중...")
    df = pd.read_csv(f"{BASE_PATH}\\monthly_risk.csv", encoding="utf-8-sig")

    df = df[["행정동_코드", "행정동_한글", "자치구명", "year", "month",
             "건강안전도_점수", "건강안전도_등급"]].copy()
    df = df.rename(columns={
        "행정동_코드":    "dong_code",
        "행정동_한글":    "dong",
        "자치구명":       "gu",
        "건강안전도_점수": "score",
        "건강안전도_등급": "grade",
    })
    df["dong_code"] = df["dong_code"].astype(int)
    df["score"]     = df["score"].astype(int)
    df["grade"]     = df["grade"].astype(int)

    col = db["health_scores"]
    ops = []
    for _, row in df.iterrows():
        doc = {
            "dong_code": int(row["dong_code"]),
            "dong":      row["dong"],
            "gu":        row["gu"],
            "year":      int(row["year"]),
            "month":     int(row["month"]),
            "score":     int(row["score"]),
            "grade":     int(row["grade"]),
        }
        ops.append(UpdateOne(
            {"dong_code": doc["dong_code"], "year": doc["year"], "month": doc["month"]},
            {"$set": doc},
            upsert=True,
        ))

    result = await col.bulk_write(ops)
    await col.create_index([("dong_code", 1), ("year", 1), ("month", 1)])
    print(f"health_scores 완료 — {len(df):,}건 (upserted: {result.upserted_count})")


# ── 2. comfort_scores 적재 ───────────────────────────────────────
async def load_comfort(db):
    print("\n [comfort] comfort.csv 로드 중...")
    df = pd.read_csv(f"{BASE_PATH}\\comfort.csv", encoding="utf-8-sig")

    df = df[["행정동코드", "년도", "월", "쾌적도점수", "쾌적도등급"]].copy()
    df = df.rename(columns={
        "행정동코드": "dong_code",
        "년도":       "year",
        "월":         "month",
        "쾌적도점수": "score",
        "쾌적도등급": "grade",
    })
    df["dong_code"] = df["dong_code"].astype(str).str[:8].astype(int)
    df["score"]     = df["score"].round().astype(int)
    df["grade"]     = df["grade"].astype(int)

    # dong, gu 정보 health에서 가져오기
    health_ref = pd.read_csv(f"{BASE_PATH}\\monthly_risk.csv", encoding="utf-8-sig")
    dong_info  = health_ref[["행정동_코드", "행정동_한글", "자치구명"]]\
        .drop_duplicates(subset=["행정동_코드"])\
        .rename(columns={"행정동_코드": "dong_code", "행정동_한글": "dong", "자치구명": "gu"})
    dong_info["dong_code"] = dong_info["dong_code"].astype(int)
    df = df.merge(dong_info, on="dong_code", how="left")

    col = db["comfort_scores"]
    ops = []
    for _, row in df.iterrows():
        doc = {
            "dong_code": int(row["dong_code"]),
            "dong":      row.get("dong", ""),
            "gu":        row.get("gu", ""),
            "year":      int(row["year"]),
            "month":     int(row["month"]),
            "score":     int(row["score"]),
            "grade":     int(row["grade"]),
        }
        ops.append(UpdateOne(
            {"dong_code": doc["dong_code"], "year": doc["year"], "month": doc["month"]},
            {"$set": doc},
            upsert=True,
        ))

    result = await col.bulk_write(ops)
    await col.create_index([("dong_code", 1), ("year", 1), ("month", 1)])
    print(f"comfort_scores 완료 — {len(df):,}건 (upserted: {result.upserted_count})")


# ── 3. safety_scores 적재 ───────────────────────────────────────
async def load_safety(db):
    print("\n [safety] safety_model.csv 로드 중...")
    safety = pd.read_csv(f"{BASE_PATH}\\safety_model.csv", encoding="utf-8-sig")

    # 2024년 점수/등급만 사용
    safety = safety[["자치구", "2024_점수", "2024_등급"]].copy()
    safety.columns = ["gu", "score", "grade"]
    safety["score"] = safety["score"].round().astype(int)
    safety["grade"] = safety["grade"].astype(int)

    # 행정동 목록 health에서 가져오기
    health_ref = pd.read_csv(f"{BASE_PATH}\\monthly_risk.csv", encoding="utf-8-sig")
    dong_info  = health_ref[["행정동_코드", "행정동_한글", "자치구명", "year", "month"]]\
        .rename(columns={"행정동_코드": "dong_code", "행정동_한글": "dong", "자치구명": "gu"})
    dong_info["dong_code"] = dong_info["dong_code"].astype(int)

    # 구별 점수를 모든 동에 적용
    df = dong_info.merge(safety, on="gu", how="left")

    col = db["safety_scores"]
    ops = []
    for _, row in df.iterrows():
        doc = {
            "dong_code": int(row["dong_code"]),
            "dong":      row["dong"],
            "gu":        row["gu"],
            "year":      int(row["year"]),
            "month":     int(row["month"]),
            "score":     int(row["score"]) if pd.notna(row["score"]) else 0,
            "grade":     int(row["grade"]) if pd.notna(row["grade"]) else 3,
        }
        ops.append(UpdateOne(
            {"dong_code": doc["dong_code"], "year": doc["year"], "month": doc["month"]},
            {"$set": doc},
            upsert=True,
        ))

    result = await col.bulk_write(ops)
    await col.create_index([("dong_code", 1), ("year", 1), ("month", 1)])
    print(f"safety_scores 완료 — {len(df):,}건 (upserted: {result.upserted_count})")


# ── 메인 ────────────────────────────────────────────────────────
async def run():
    client = AsyncIOMotorClient(MONGO_URI)
    db     = client[MONGO_DB]

    await load_health(db)
    await load_comfort(db)
    await load_safety(db)

    client.close()
    print("\n 전체 적재 완료!")


if __name__ == "__main__":
    asyncio.run(run())
