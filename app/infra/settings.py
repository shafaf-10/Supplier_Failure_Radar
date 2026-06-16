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

    MODEL_PATH: str = "app/ml/models/risk_model.pkl"
    FEATURE_PATH: str = "outputs/supplier_features.csv"

    class Config:
        env_file = ".env"


settings = Settings()