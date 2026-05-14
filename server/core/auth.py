from fastapi import Header, HTTPException
from dotenv import load_dotenv
import os

load_dotenv()

VALID_API_KEY = os.getenv("API_KEY", "v9WzP1xF7K8lQ2mR4sT6uY8aB0cD3eF9GhJkLmNo")


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="인증 실패: 유효하지 않은 API Key")
    return x_api_key
