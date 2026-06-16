from fastapi import APIRouter

from app.api.v1.endpoints.supplier_predictions import (
    router as supplier_predictions_router,
)


api_router = APIRouter()

api_router.include_router(
    supplier_predictions_router,
    tags=["Supplier Predictions"],
)