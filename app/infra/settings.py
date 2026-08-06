from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "supplier_failure_radar"
    DATABASE_URL: str | None = None

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    APP_NAME: str = "Supplier Failure Radar"
    DEBUG: bool = False

    API_KEY: str
    WEBHOOK_URL: str | None = None

    TRAINING_DATA_PROVENANCE: str = "SYNTHETIC"
    ALLOW_SYNTHETIC_TRAINING: bool = True

    ENABLE_PRODUCTION_VALIDATION: bool = False

    MIN_PRODUCTION_TRAINING_ROWS: int = 1000
    MIN_PRODUCTION_SNAPSHOTS: int = 60

    MIN_PRODUCTION_ACCURACY_24H: float = 0.70
    MIN_PRODUCTION_ACCURACY_3D: float = 0.75
    MIN_PRODUCTION_ACCURACY_7D: float = 0.80

    MIN_PRODUCTION_SEVERITY_ACCURACY: float = 0.60

    model_config = ConfigDict(
    env_file=".env",
    extra="ignore",
)
    FAILURE_ATTRIBUTION_ENABLED: bool = True
    INCIDENT_RATE_MULTIPLIER: float = 3.0
    INCIDENT_MIN_ABS_RATE_DELTA: float = 0.05
    INCIDENT_MIN_AFFECTED_FRACTION: float = 0.5
    INCIDENT_MIN_EVENTS: int = 20
    INCIDENT_BASELINE_DAYS: int = 30
    PLATFORM_WEBHOOK_URL: str | None = None


settings = Settings()