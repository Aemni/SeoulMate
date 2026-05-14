from fastapi import APIRouter, Depends, Query
from core.auth import verify_api_key
from services.score_service import get_heatmap
from models.schemas import HeatmapResponse

router = APIRouter()

VALID_LAYERS = {"overall", "safety", "health", "stress", "hvac", "comfort", "expenses"}


@router.get("/heatmap", response_model=HeatmapResponse)
async def heatmap(
    layer: str = Query(..., description="조회 layer (overall, safety, health, stress, hvac, comfort, expenses)"),
    year:  int  = Query(..., description="조회 연도"),
    month: int  = Query(..., ge=1, le=12, description="조회 월 (1~12)"),
    _: str = Depends(verify_api_key),
):
    if layer not in VALID_LAYERS:
        return {"status": 400, "dong_list": []}

    dong_list = await get_heatmap(layer, year, month)
    return {"status": 200, "dong_list": dong_list}
