from db.mongodb import get_db
from fastapi import HTTPException

# layer → 컬렉션명 매핑
LAYER_COLLECTION = {
    "overall":  None,           # 전체 컬렉션에서 종합
    "health":   "health_scores",
    "comfort":  "comfort_scores",
    "safety":   "safety_scores",
    "stress":   "stress_scores",   # 서버팀 담당
    "hvac":     "hvac_scores",     # 서버팀 담당
}

VALID_LAYERS = set(LAYER_COLLECTION.keys())


# ── 히트맵 서비스 ─────────────────────────────────────────────
async def get_heatmap(layer: str, year: int, month: int) -> list:
    if layer not in VALID_LAYERS:
        raise HTTPException(status_code=400, detail=f"잘못된 layer 값: {layer}")

    db = get_db()

    if layer == "overall":
        return await get_heatmap_overall(db, year, month)

    col_name = LAYER_COLLECTION[layer]
    col = db[col_name]
    cursor = col.find(
        {"year": year, "month": month},
        {"_id": 0, "dong_code": 1, "dong": 1, "gu": 1, "score": 1, "grade": 1}
    )
    docs = await cursor.to_list(length=None)

    if not docs:
        raise HTTPException(status_code=400, detail="해당 연도/월 데이터가 없습니다")

    return [{
        "code":  d["dong_code"],
        "dong":  d["dong"],
        "gu":    d["gu"],
        "grade": d["grade"],
        "score": float(d["score"]),
    } for d in docs]


async def get_heatmap_overall(db, year: int, month: int) -> list:
    """overall: 각 컬렉션 점수 평균으로 종합 점수 계산"""
    layers = ["health", "comfort", "safety"]
    data = {}

    for layer in layers:
        col = db[LAYER_COLLECTION[layer]]
        cursor = col.find(
            {"year": year, "month": month},
            {"_id": 0, "dong_code": 1, "dong": 1, "gu": 1, "score": 1}
        )
        docs = await cursor.to_list(length=None)
        for d in docs:
            code = d["dong_code"]
            if code not in data:
                data[code] = {"dong": d["dong"], "gu": d["gu"], "scores": []}
            data[code]["scores"].append(d["score"])

    if not data:
        raise HTTPException(status_code=400, detail="해당 연도/월 데이터가 없습니다")

    result = []
    for code, info in data.items():
        avg = sum(info["scores"]) / len(info["scores"])
        # 점수 → 등급 (1=좋음, 5=나쁨 기준)
        if avg >= 80:   grade = 1
        elif avg >= 60: grade = 2
        elif avg >= 40: grade = 3
        elif avg >= 20: grade = 4
        else:           grade = 5
        result.append({
            "code":  code,
            "dong":  info["dong"],
            "gu":    info["gu"],
            "grade": grade,
            "score": round(avg, 2),
        })
    return result


# ── 상세보기 서비스 ───────────────────────────────────────────
async def get_detail(dong_code: int, year: int) -> dict:
    db = get_db()

    # health 기준으로 기본 정보 + 월별 점수 가져오기
    health_col = db["health_scores"]
    cursor = health_col.find(
        {"dong_code": dong_code, "year": year},
        {"_id": 0}
    ).sort("month", 1)
    health_docs = await cursor.to_list(length=None)

    if not health_docs:
        raise HTTPException(status_code=400, detail="해당 동/연도 데이터가 없습니다")

    latest     = health_docs[-1]
    dong_name  = latest.get("dong", "")
    gu_name    = latest.get("gu", "")

    # 각 모델 최신 월 점수 조회
    async def get_latest_score(col_name: str) -> tuple:
        col    = db[col_name]
        cursor = col.find(
            {"dong_code": dong_code, "year": year},
            {"_id": 0, "score": 1, "grade": 1}
        ).sort("month", -1).limit(1)
        docs = await cursor.to_list(length=1)
        if docs:
            return docs[0].get("score", 0), docs[0].get("grade", 3)
        return 0, 3

    health_score,  health_grade  = latest.get("score", 0), latest.get("grade", 3)
    comfort_score, comfort_grade = await get_latest_score("comfort_scores")
    safety_score,  safety_grade  = await get_latest_score("safety_scores")

    # 종합 점수 (3개 모델 평균)
    overall = int(round((health_score + comfort_score + safety_score) / 3))

    # 월별 health 점수 (최근 12개월)
    score_last_year = [int(d.get("score", 0)) for d in health_docs]
    average_score   = int(round(sum(score_last_year) / len(score_last_year)))

    # 최근 추세
    recent_trend = 0
    if len(score_last_year) >= 2:
        diff = score_last_year[-1] - score_last_year[-2]
        if diff > 1:   recent_trend = 1
        elif diff < -1: recent_trend = 2

    return {
        "status":          200,
        "code":            dong_code,
        "dong":            dong_name,
        "gu":              gu_name,
        "score":           overall,
        "health":          health_score,
        "comfort":         comfort_score,
        "safety":          safety_score,
        "hvac":            0,      # 서버팀 담당
        "stress":          0,      # 서버팀 담당
        "expenses":        0,      # 서버팀 담당
        "average_score":   average_score,
        "score_last_year": score_last_year,
        "recent_trend":    recent_trend,
    }
