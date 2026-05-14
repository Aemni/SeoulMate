from fastapi import APIRouter, Depends, Query
from core.auth import verify_api_key
from services.score_service import get_detail
from models.schemas import DetailResponse

router = APIRouter()


@router.get("/detail", response_model=DetailResponse)
async def detail(
    id:   int = Query(..., description="행정동 코드"),
    year: int = Query(..., description="조회 연도"),
    _: str = Depends(verify_api_key),
):
    return await get_detail(dong_code=id, year=year)
