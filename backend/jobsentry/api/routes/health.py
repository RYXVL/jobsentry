from __future__ import annotations

from fastapi import APIRouter

from ... import __version__
from ..schemas import HealthOut

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthOut, summary="Check the API is running")
def health() -> HealthOut:
    return HealthOut(version=__version__)
