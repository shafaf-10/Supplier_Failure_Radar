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
def refresh_model():
    try:
        from app.ml.pipeline import run_prediction_pipeline

        result = run_prediction_pipeline()
        SupplierPredictionService.clear_cache()

        return {
            "status": "success",
            "message": "Supplier prediction pipeline refreshed successfully.",
            "pipeline": result,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )