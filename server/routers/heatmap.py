# app/routers/heatmap.py

from fastapi import APIRouter, Depends, HTTPException, Query
from core.auth import verify_api_key
from services.score_service import get_layer_scores, get_overall_scores, get_safety_scores

router = APIRouter()

VALID_LAYERS = {"overall", "safety", "health", "stress", "hvac", "comfort", "expenses"}


@router.get("/v1/heatmap")
async def get_heatmap(
    layer: str = Query(..., description="조회 layer (overall, safety, health, stress, hvac, comfort, expenses)"),
    year:  int = Query(..., description="조회 연도"),
    month: int = Query(..., ge=1, le=12, description="조회 월 (1~12)"),
    auth=Depends(verify_api_key),
):
    """전체 행정동 히트맵 데이터 조회"""
    if layer not in VALID_LAYERS:
        raise HTTPException(status_code=400, detail="잘못된 layer입니다.")

    if layer == "overall":
        dong_list = await get_overall_scores(year, month)
    else:
        dong_list = await get_layer_scores(layer, year, month)

    return {"status": 200, "dong_list": dong_list}


@router.get("/v1/heatmap/safety")
async def get_heatmap_safety(
    year: int = Query(..., description="조회 연도 (예: 2026)"),
    auth=Depends(verify_api_key),
):
    """치안 레이어 연간 히트맵 데이터 조회"""
    dong_list = await get_safety_scores(year)

    return {"status": 200, "dong_list": dong_list}