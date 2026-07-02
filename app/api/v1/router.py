from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.v1.endpoints.supplier_predictions import (
    router as supplier_predictions_router,
)
from app.infra.settings import settings


def verify_api_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


api_router = APIRouter(
    dependencies=[Depends(verify_api_key)]
)

api_router.include_router(
    supplier_predictions_router,
    tags=["Supplier Predictions"],
)