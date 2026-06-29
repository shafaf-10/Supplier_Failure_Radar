from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

from app.observability.audit_logger import log_prediction_view
from app.services.supplier_prediction_service import SupplierPredictionService


router = APIRouter()

VALID_PERIODS = ["24h", "7d", "30d", "1y", "all"]


@router.get("/supplier-predictions")
async def get_supplier_predictions(
    request: Request,
    period: str = Query("all"),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail="Invalid period. Use 24h, 7d, 30d, 1y, or all.",
        )

    log_prediction_view(
        request_id=request.headers.get("X-Request-ID"),
        period=period,
        limit=limit,
        offset=offset,
    )

    predictions = await run_in_threadpool(
    SupplierPredictionService.get_predictions,
    period,
)

    suppliers = predictions.get("suppliers", [])

    return {
        **predictions,
        "suppliers": suppliers[offset : offset + limit],
        "limit": limit,
        "offset": offset,
    }


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