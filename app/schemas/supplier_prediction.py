from pydantic import BaseModel


class ModelValidationInfo(BaseModel):
    training_data_provenance: str
    production_validated: bool
    prediction_status: str
    prediction_notice: str


class SupplierRecord(BaseModel):
    supplier_code: str | None = None
    supplier_name: str | None = None
    total_bookings: int
    risk_score: float
    risk_level: str | None = None
    predicted_risk: str | None = None
    prediction_probability: float
    current_anomaly_status: str | None = None
    current_anomaly_score: float
    recommendation: str | None = None
    future_probability_24h: float
    future_probability_3d: float
    future_probability_7d: float
    future_unavailability_severity: str | None = None
    future_instability_probability: float
    future_risk_window: str | None = None
    early_warning_status: str | None = None
    lead_signal: str | None = None
    prediction_confidence: str | None = None
    future_recommendation: str | None = None
    failure_rate: float
    pending_rate: float
    cancellation_rate: float
    process_error_rate: float
    refund_rate: float
    credit_rejection_rate: float
    search_failure_rate: float
    wallet_risk_rate: float
    created_at: str


class PredictionSummary(BaseModel):
    total_suppliers: int
    high_risk_suppliers: int
    medium_risk_suppliers: int
    low_risk_suppliers: int
    current_anomaly_suppliers: int
    critical_future_warnings: int
    warning_suppliers: int
    high_severity_suppliers: int
    medium_severity_suppliers: int
    low_severity_suppliers: int
    average_risk_score: float
    average_future_instability_probability: float
    average_future_probability_24h: float
    average_future_probability_3d: float
    average_future_probability_7d: float


class SupplierPredictionsResponse(BaseModel):
    period: str
    latest_date: str | None = None
    model_validation: ModelValidationInfo
    summary: PredictionSummary
    suppliers: list[SupplierRecord]
    limit: int | None = None
    offset: int | None = None
    warning: str | None = None


class RefreshModelResponse(BaseModel):
    status: str
    message: str
    summary: dict
    total_suppliers: int