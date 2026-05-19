"""
CSV 데이터 → MongoDB 적재 스크립트
실행: python load_data.py

컬렉션 구조:
- health_scores   ← health_safety_model.csv  (행정동별 월별, 건강안전도)
- comfort_scores  ← comfort_model.csv         (행정동별 월별, 쾌적도)
- safety_scores   ← safety_model.csv          (구별 → 동별 확장, 치안)
- expenses_scores ← expenses_model.csv        (행정동별 월별, 생활비용)

추후 추가:
- hvac_scores    ← pkl 모델 결과 CSV
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

# CSV 파일 경로 → load_data.py 기준 data/ 폴더
BASE_PATH = os.path.join(os.path.dirname(__file__), "data")


# ── 1. health_scores 적재 ────────────────────────────────────────
async def load_health(db):
    print("\n[health] health_safety_model.csv 로드 중...")
    df = pd.read_csv(os.path.join(BASE_PATH, "health_safety_model.csv"), encoding="utf-8-sig")

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
    print("\n[comfort] comfort.csv 로드 중...")
    df = pd.read_csv(os.path.join(BASE_PATH, "comfort_model.csv"), encoding="utf-8-sig")

    df = df[["행정동코드", "년도", "월", "쾌적도점수", "쾌적도등급", "행정동", "자치구"]].copy()
    df = df.rename(columns={
        "행정동코드": "dong_code",
        "년도":       "year",
        "월":         "month",
        "쾌적도점수": "score",
        "쾌적도등급": "grade",
        "행정동":     "dong",
        "자치구":     "gu",
    })
    df["dong_code"] = df["dong_code"].astype(int)
    df["score"]     = df["score"].round().astype(int)
    df["grade"]     = df["grade"].astype(int)

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
    print("\n[safety] safety_model.csv 로드 중...")
    safety = pd.read_csv(os.path.join(BASE_PATH, "safety_model.csv"), encoding="utf-8-sig")

    # 행정동 목록 health에서 가져오기
    health_ref = pd.read_csv(os.path.join(BASE_PATH, "health_safety_model.csv"), encoding="utf-8-sig")
    dong_info  = health_ref[["행정동_코드", "행정동_한글", "자치구명"]]\
        .drop_duplicates(subset=["행정동_코드"])\
        .rename(columns={"행정동_코드": "dong_code", "행정동_한글": "dong", "자치구명": "gu"})
    dong_info["dong_code"] = dong_info["dong_code"].astype(int)

    col = db["safety_scores"]
    ops = []

    # 2017~2024년 각 연도별로 적재
    for year in range(2017, 2025):
        score_col = f"{year}_점수"
        grade_col = f"{year}_등급"

        if score_col not in safety.columns:
            continue

        # 구별 점수를 모든 동에 적용
        safety_year = safety[["자치구", score_col, grade_col]].copy()
        safety_year.columns = ["gu", "score", "grade"]
        safety_year["score"] = safety_year["score"].round().astype(int)
        safety_year["grade"] = safety_year["grade"].astype(int)

        df = dong_info.merge(safety_year, on="gu", how="left")

        for _, row in df.iterrows():
            doc = {
                "dong_code": int(row["dong_code"]),
                "dong":      row["dong"],
                "gu":        row["gu"],
                "year":      year,
                "month":     1,  # 치안은 연간 데이터라 month=1 고정
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
    print(f"safety_scores 완료 — {len(ops):,}건 (upserted: {result.upserted_count})")


# ── 4. expenses_scores 적재 ─────────────────────────────────────
async def load_expenses(db):
    print("\n[expenses] expenses_model.csv 로드 중...")
    df = pd.read_csv(os.path.join(BASE_PATH, "expenses_model.csv"), encoding="utf-8-sig")

    df = df[["행정동코드", "년도", "월", "생활비용지수", "생활비용지수_등급"]].copy()
    df = df.rename(columns={
        "행정동코드":     "dong_code",
        "년도":           "year",
        "월":             "month",
        "생활비용지수":   "score",
        "생활비용지수_등급": "grade",
    })
    df["dong_code"] = df["dong_code"].astype(int)
    df["score"]     = df["score"].round().astype(int)
    df["grade"]     = df["grade"].astype(int)

    # dong, gu 정보 health에서 가져오기
    health_ref = pd.read_csv(os.path.join(BASE_PATH, "health_safety_model.csv"), encoding="utf-8-sig")
    dong_info  = health_ref[["행정동_코드", "행정동_한글", "자치구명"]]\
        .drop_duplicates(subset=["행정동_코드"])\
        .rename(columns={"행정동_코드": "dong_code", "행정동_한글": "dong", "자치구명": "gu"})
    dong_info["dong_code"] = dong_info["dong_code"].astype(int)
    df = df.merge(dong_info, on="dong_code", how="left")

    col = db["expenses_scores"]
    ops = []
    for _, row in df.iterrows():
        doc = {
            "dong_code": int(row["dong_code"]),
            "dong":      row.get("dong", ""),
            "gu":        row.get("gu", ""),
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
    print(f"expenses_scores 완료 — {len(df):,}건 (upserted: {result.upserted_count})")


# ── 메인 ────────────────────────────────────────────────────────
async def run():
    client = AsyncIOMotorClient(MONGO_URI)
    db     = client[MONGO_DB]

    await load_health(db)
    await load_comfort(db)
    await load_safety(db)
    await load_expenses(db)

    client.close()
    print("\n전체 적재 완료!")


if __name__ == "__main__":
    asyncio.run(run())