from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "supplier_failure_radar"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    APP_NAME: str = "Supplier Failure Radar"
    DEBUG: bool = False

    API_KEY: str = "dev-secret-key"

    # Training-data source
    TRAINING_DATA_PROVENANCE: str = "SYNTHETIC"
    ALLOW_SYNTHETIC_TRAINING: bool = True

    # Production validation must be explicitly enabled
    # only after testing on real supplier traffic.
    ENABLE_PRODUCTION_VALIDATION: bool = False

    # Minimum real temporal training rows required.
    MIN_PRODUCTION_TRAINING_ROWS: int = 1000

    # Minimum number of distinct temporal snapshots.
    MIN_PRODUCTION_SNAPSHOTS: int = 60

    # Minimum accepted future-model accuracy.
    MIN_PRODUCTION_ACCURACY_24H: float = 0.70
    MIN_PRODUCTION_ACCURACY_3D: float = 0.75
    MIN_PRODUCTION_ACCURACY_7D: float = 0.80

    # Minimum accepted severity-model accuracy.
    MIN_PRODUCTION_SEVERITY_ACCURACY: float = 0.60

    class Config:
        env_file = ".env"


settings = Settings()