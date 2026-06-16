import numpy as np
import pandas as pd


def to_dt(df, cols):
    df = df.copy()

    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

    return df


def safe_rate(num, den):
    try:
        return num / den.replace(0, np.nan)
    except AttributeError:
        if den == 0:
            return 0
        return num / den


def normalise(series):
    mn = series.min()
    mx = series.max()

    return (series - mn) / (mx - mn + 1e-9)


def left_merge(base, right, on="supplier_code"):
    if right is None or right.empty:
        return base

    return base.merge(
        right,
        on=on,
        how="left"
    )