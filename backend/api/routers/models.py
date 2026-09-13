import os

import requests
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/model/list")
def list_models():
    response = requests.get(
        f"{os.environ['BASE_URL'].rstrip('/')}/models",
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
    )
    response.raise_for_status()
    return {"models": response.json()}
