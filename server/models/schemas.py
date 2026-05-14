from pydantic import BaseModel
from typing import List, Optional


# ── 히트맵 응답 ──────────────────────────────────────────────
class DongHeatmap(BaseModel):
    code: int
    dong: str
    gu: str
    grade: int      # 1(하) / 2(중) / 3(상)
    score: float


class HeatmapResponse(BaseModel):
    status: int
    dong_list: List[DongHeatmap]


# ── 상세보기 응답 ─────────────────────────────────────────────
class DetailResponse(BaseModel):
    status: int
    code: int
    dong: str
    gu: str
    score: int                      # 종합 점수
    safety: int
    comfort: int
    hvac: int
    expenses: int
    health: int
    stress: int
    average_score: int              # 해당 연도 월별 평균
    score_last_year: List[int]      # 최근 12개월 점수 배열
    recent_trend: int               # 0=유지 / 1=상승 / 2=하강
