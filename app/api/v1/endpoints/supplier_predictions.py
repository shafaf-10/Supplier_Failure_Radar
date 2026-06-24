from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, HTTPException, Query

from app.services.supplier_prediction_service import SupplierPredictionService


router = APIRouter()

VALID_PERIODS = ["24h", "7d", "30d", "1y", "all"]

@router.get("/supplier-predictions")
def get_supplier_predictions(
    period: str = Query("all"),
):
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail="Invalid period. Use 24h, 7d, 30d, 1y, or all.",
        )

    return SupplierPredictionService.get_predictions(period)


@router.post("/refresh-model")
async def refresh_model():
    try:
        SupplierPredictionService.clear_cache()

        result = await run_in_threadpool(
    SupplierPredictionService.get_predictions,
    "all",
)

        return {
            "status": "success",
            "message": "Supplier prediction pipeline refreshed successfully.",
            "summary": result.get("summary", {}),
            "total_suppliers": len(result.get("suppliers", [])),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )