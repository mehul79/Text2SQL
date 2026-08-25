import os

import requests
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/model/list")
def list_models():
    response = requests.get(
        "https://opencode.ai/zen/v1/models",
        headers={"Authorization": f"Bearer {os.getenv('OPENCODE_API_KEY')}"},
    )
    response.raise_for_status()
    return {"models": response.json()}
