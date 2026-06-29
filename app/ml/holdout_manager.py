from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd


def save_holdout_set(
    X_test: pd.DataFrame,
    y_test: pd.Series,
    file_path: Path,
) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    holdout_data = {
        "X_test": X_test,
        "y_test": y_test,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    joblib.dump(holdout_data, file_path)