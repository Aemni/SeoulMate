# app/services/score_service.py

from db.mongodb import get_db

# 조회 가능한 레이어 목록
# 각 레이어는 MongoDB 컬렉션 이름과 매핑됨
LAYER_COLLECTION = {
    "health":   "health_scores",
    "comfort":  "comfort_scores",
    "safety":   "safety_scores",
    "hvac":     "hvac_scores",
    "expenses": "expenses_scores",
}


async def get_layer_scores(layer: str, year: int, month: int) -> list:
    """
    특정 레이어의 전체 동 점수 조회 (히트맵용)
    
    Args:
        layer: 조회할 레이어명 (health, comfort, safety 등)
        year:  조회 연도
        month: 조회 월
    
    Returns:
        [{"code": "1132069000", "dong": "청구동", "gu": "중구", "score": 73, "grade": 2}, ...]
    """
    db = get_db()
    collection = LAYER_COLLECTION.get(layer)

    if collection is None:
        return []

    cursor = db[collection].find(
        {"year": year, "month": month},
        {"_id": 0, "dong_code": 1, "dong": 1, "gu": 1, "score": 1, "grade": 1}
    )

    result = []
    async for doc in cursor:
        result.append({
            "code":  str(doc["dong_code"]),
            "dong":  doc.get("dong", ""),
            "gu":    doc.get("gu", ""),
            "score": doc.get("score", 0),
            "grade": doc.get("grade", 0),
        })

    return result


async def get_dong_overall_trend(code: str, year: int, month: int) -> list:
    """
    특정 동의 전체 레이어 월별 평균 트렌드 조회 (score_last_year용)
    조회 범위: 전년 1월 ~ 현재 월

    Args:
        code:  행정동 코드 (10자리 문자열)
        year:  조회 연도
        month: 조회 월

    Returns:
        [61, 63, 65, 68, 70, 72, 69, 67, 65, 63, 60, 58, 61, 64, 66, 68, 68]
    """
    db = get_db()
    dong_code = int(code)

    # 조회 범위 계산: 전년 1월 ~ 현재 월
    date_range = []
    for y in [year - 1, year]:
        start_month = 1
        end_month   = 12 if y == year - 1 else month
        for m in range(start_month, end_month + 1):
            date_range.append((y, m))

    scores = []
    for y, m in date_range:
        month_scores = []

        # 해당 월의 6개 레이어 점수 조회
        for layer, collection in LAYER_COLLECTION.items():
            doc = await db[collection].find_one(
                {"dong_code": dong_code, "year": y, "month": m},
                {"_id": 0, "score": 1}
            )
            if doc and doc.get("score", 0) != 0:
                month_scores.append(doc["score"])

        # 해당 월 평균
        avg = round(sum(month_scores) / len(month_scores)) if month_scores else 0
        scores.append(avg)

    return scores

async def get_overall_scores(year: int, month: int) -> list:
    """
    overall 레이어 조회 - 6개 레이어 점수 평균을 종합 점수로 반환 (히트맵용)

    Args:
        year:  조회 연도
        month: 조회 월

    Returns:
        [{"code": "1132069000", "dong": "청구동", "gu": "중구", "score": 68, "grade": 2}, ...]
    """
    db = get_db()

    # 전체 동 목록 health 기준으로 가져오기
    cursor = db["health_scores"].find(
        {"year": year, "month": month},
        {"_id": 0, "dong_code": 1, "dong": 1, "gu": 1}
    )

    dong_list = []
    async for doc in cursor:
        dong_list.append(doc)

    result = []
    for dong in dong_list:
        code = dong["dong_code"]
        scores = []

        # 6개 레이어에서 해당 동의 점수 조회
        for layer, collection in LAYER_COLLECTION.items():
            doc = await db[collection].find_one(
                {"dong_code": code, "year": year, "month": month},
                {"_id": 0, "score": 1}
            )
            if doc and doc.get("score", 0) != 0:
                scores.append(doc["score"])

        avg = round(sum(scores) / len(scores)) if scores else 0

        result.append({
            "code":  str(code),
            "dong":  dong.get("dong", ""),
            "gu":    dong.get("gu", ""),
            "score": avg,
            "grade": 0,  # overall은 등급 없음
        })

    return result

async def get_safety_scores(year: int) -> list:
    """
    치안 레이어 연간 평균 점수 조회 (heatmap/safety용)
    
    치안은 UI에서 월별 없이 연간으로만 보여주므로
    해당 연도 전체 월 평균을 내서 반환

    Args:
        year: 조회 연도

    Returns:
        [{"code": "1132069000", "dong": "청구동", "gu": "중구", "score": 73, "grade": 2}, ...]
    """
    db = get_db()

    # 해당 연도 전체 월 데이터 조회
    cursor = db["safety_scores"].find(
        {"year": year},
        {"_id": 0, "dong_code": 1, "dong": 1, "gu": 1, "score": 1, "grade": 1}
    )

    # 동별로 점수 모으기
    dong_scores: dict = {}
    async for doc in cursor:
        code = str(doc["dong_code"])
        if code not in dong_scores:
            dong_scores[code] = {
                "dong":   doc.get("dong", ""),
                "gu":     doc.get("gu", ""),
                "scores": [],
                "grade":  doc.get("grade", 0),
            }
        dong_scores[code]["scores"].append(doc.get("score", 0))

    # 동별 평균 계산
    result = []
    for code, data in dong_scores.items():
        scores = [s for s in data["scores"] if s != 0]
        avg = round(sum(scores) / len(scores)) if scores else 0
        result.append({
            "code":  code,
            "dong":  data["dong"],
            "gu":    data["gu"],
            "score": avg,
            "grade": data["grade"],
        })

    return result

async def get_dong_detail(code: str, year: int, month: int) -> dict:
    """
    특정 동의 전체 레이어 점수 조회 (overview 종합용)

    Args:
        code:  행정동 코드 (10자리 문자열)
        year:  조회 연도
        month: 조회 월

    Returns:
        {"dong": "청구동", "gu": "중구", "health": 72, "comfort": 65, ...}
    """
    db = get_db()
    dong_code = int(code)

    result = {"dong": "", "gu": ""}

    for layer, collection in LAYER_COLLECTION.items():
        doc = await db[collection].find_one(
            {"dong_code": dong_code, "year": year, "month": month},
            {"_id": 0, "dong": 1, "gu": 1, "score": 1}
        )
        if doc:
            result[layer] = doc.get("score", 0)
            if not result["dong"]:
                result["dong"] = doc.get("dong", "")
                result["gu"]   = doc.get("gu", "")
        else:
            result[layer] = 0

    return result

async def get_safety_trend(code: str) -> list:
    """
    치안 연도별 트렌드 조회 (2017~2024)
    월별이 아닌 연도별로 반환
    
    Returns:
        [{"year": 2017, "score": 49}, {"year": 2018, "score": 52}, ...]
    """
    db = get_db()
    dong_code = int(code)

    result = []
    for year in range(2017, 2025):
        doc = await db["safety_scores"].find_one(
            {"dong_code": dong_code, "year": year, "month": 1},
            {"_id": 0, "score": 1}
        )
        result.append({
            "year":  year,
            "score": doc["score"] if doc else 0
        })

    return result

async def get_dong_trend(code: str, layer: str, year: int, month: int) -> list:
    """
    특정 동의 특정 레이어 월별 트렌드 조회
    조회 범위: 전년 1월 ~ 현재 월
    
    예: year=2026, month=5 → 2025년 1월 ~ 2026년 5월 (총 17개월)

    Args:
        code:  행정동 코드 (10자리 문자열)
        layer: 조회할 레이어명
        year:  조회 연도
        month: 조회 월

    Returns:
        [61, 63, 65, 68, 70, 72, 69, 67, 65, 63, 60, 58, 61, 64, 66, 68, 68]
    """
    db = get_db()
    collection = LAYER_COLLECTION.get(layer)

    if collection is None:
        return []

    dong_code = int(code)

    # 조회 범위 계산: 전년 1월 ~ 현재 월
    # 예: 2026년 5월 → (2025, 1) ~ (2026, 5)
    date_range = []
    for y in [year - 1, year]:
        start_month = 1
        end_month   = 12 if y == year - 1 else month
        for m in range(start_month, end_month + 1):
            date_range.append((y, m))

    scores = []
    for y, m in date_range:
        doc = await db[collection].find_one(
            {"dong_code": dong_code, "year": y, "month": m},
            {"_id": 0, "score": 1}
        )
        scores.append(doc["score"] if doc else 0)

    return scores