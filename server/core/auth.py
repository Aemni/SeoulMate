# app/core/auth.py

from fastapi import Header, HTTPException

# 유효한 API Key 상수로 관리
# 실제 운영 시 .env로 빼는 것을 권장
VALID_API_KEY = "v9WzP1xF7K8lQ2mR4sT6uY8aB0cD3eF9GhJkLmNo"


async def verify_api_key(x_api_key: str = Header(default=None)):
    """
    모든 엔드포인트에서 호출되는 API Key 인증 함수
    FastAPI의 Depends()로 주입해서 사용

    Header에 x-api-key가 없거나 틀리면 401 반환
    
    사용 예시:
        @router.get("/v1/heatmap")
        async def get_heatmap(auth=Depends(verify_api_key)):
            ...
    """
    if x_api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="인증 실패")