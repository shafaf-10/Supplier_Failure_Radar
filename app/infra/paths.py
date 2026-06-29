from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = ROOT_DIR / "app"
ML_DIR = APP_DIR / "ml"
MODEL_DIR = ML_DIR / "models"