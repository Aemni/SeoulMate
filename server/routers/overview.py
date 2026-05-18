# app/routers/overview.py

from fastapi import APIRouter, Depends, HTTPException, Query
from core.auth import verify_api_key
from services.score_service import (
    get_dong_detail,
    get_dong_trend,
    get_dong_overall_trend,  # 추가
    LAYER_COLLECTION,
)

router = APIRouter()


def calculate_trend(scores: list) -> int:
    """
    최근 2개월 점수 비교로 추세 계산
    
    Returns:
        0: 유지
        1: 상승
        2: 하강
    """
    if len(scores) < 2:
        return 0
    before  = scores[-2]
    current = scores[-1]
    if current > before:
        return 1
    elif current < before:
        return 2
    else:
        return 0


@router.get("/v1/overview/{code}")
async def get_overview(
    code:  str,
    year:  int = Query(..., description="조회 연도 (예: 2026)"),
    month: int = Query(..., ge=1, le=12, description="조회 월 (1~12)"),
    layer: str = Query(default=None, description="레이어 지정 시 해당 레이어 트렌드 반환"),
    auth=Depends(verify_api_key),
):
    """
    특정 행정동 상세 조회

    - layer 없음: 종합 요약 (3번 엔드포인트)
      → 종합점수 + 6개 레이어 점수 + score_last_year(health기준) + recent_trend
    
    - layer 있음: 특정 레이어 트렌드 (4번 엔드포인트)
      → 해당 레이어의 전년 1월 ~ 현재 월 월별 점수 배열
    """
    # layer 있으면 트렌드 조회 (4번 엔드포인트)
    if layer is not None:
        if layer not in LAYER_COLLECTION:
            raise HTTPException(status_code=400, detail="잘못된 layer입니다.")

        scores = await get_dong_trend(code, layer, year, month)

        return {
            "status":       200,
            "code":         code,
            "layer":        layer,
            "score_trend":  scores,
            "recent_trend": calculate_trend(scores),
        }

    # layer 없으면 종합 요약 (3번 엔드포인트)
    detail = await get_dong_detail(code, year, month)

    if not detail["dong"]:
        raise HTTPException(status_code=400, detail="해당 행정동 코드를 찾을 수 없습니다.")

    # 종합 점수 = 6개 레이어 평균
    layer_scores = [
        detail.get("health",   0),
        detail.get("comfort",  0),
        detail.get("safety",   0),
        detail.get("hvac",     0),
        detail.get("expenses", 0),
    ]
    valid_scores  = [s for s in layer_scores if s != 0]
    average_score = round(sum(valid_scores) / len(valid_scores)) if valid_scores else 0

    # score_last_year: health 기준 전년 1월 ~ 현재 월
    score_last_year = await get_dong_overall_trend(code, year, month)

    return {
        "status":          200,
        "code":            code,
        "dong":            detail["dong"],
        "gu":              detail["gu"],
        "score":           average_score,
        "health":          detail.get("health",   0),
        "comfort":         detail.get("comfort",  0),
        "safety":          detail.get("safety",   0),
        "hvac":            detail.get("hvac",     0),
        "expenses":        detail.get("expenses", 0),
        "average_score":   average_score,
        "score_last_year": score_last_year,
        "recent_trend":    calculate_trend(score_last_year),
    }