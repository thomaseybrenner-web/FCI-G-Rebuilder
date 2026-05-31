from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


DRIVERS = [
    "FFR",
    "T10yr",
    "Mort30yr",
    "bbbCorpBond",
    "Stockmkt",
    "houseIndex",
    "dollarIndex",
]

OUTPUT_NAMES = [
    "ffr",
    "t10yr",
    "mortrate",
    "bbbrate",
    "stockmkt",
    "houseprices",
    "dollarval",
]


def load_multipliers(path: str | Path) -> pd.DataFrame:
    multipliers = pd.read_csv(path)
    multipliers = multipliers.iloc[:, :7].copy()
    multipliers.columns = DRIVERS
    return multipliers.astype(float)


def prepare_delta_input(path: str | Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    missing = [column for column in ["date", *DRIVERS] if column not in data.columns]
    if missing:
        raise ValueError(f"Input data is missing columns: {missing}")

    data = data[["date", *DRIVERS]].copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)

    if len(data) > 1:
        month_steps = data["date"].dt.to_period("M").diff().dropna().astype(int)
        if month_steps.eq(1).all():
            data["date"] = data["date"].map(lambda date: date + pd.offsets.MonthEnd(0))

    if data[DRIVERS].isna().any().any():
        raise ValueError("Input data contains missing driver changes.")

    return data


def _lag_dates(date: pd.Timestamp, lookback_quarters: int) -> list[pd.Timestamp]:
    return [date - pd.DateOffset(months=3 * lag) for lag in range(lookback_quarters)]


def compute_fci(
    delta_data: pd.DataFrame,
    multipliers: pd.DataFrame,
    start_date: str = "1990-01-01",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows_3y: list[dict[str, float | pd.Timestamp]] = []
    rows_1y: list[dict[str, float | pd.Timestamp]] = []

    indexed = delta_data.set_index("date")
    for date in delta_data["date"]:
        lag_dates = _lag_dates(date, 12)
        if any(lag not in indexed.index for lag in lag_dates):
            continue

        history = indexed.loc[lag_dates, DRIVERS].to_numpy(dtype=float)
        weights = multipliers[DRIVERS].to_numpy(dtype=float)
        contrib_3y = -np.sum(history * weights[:12], axis=0)
        contrib_1y = -np.sum(history[:4] * weights[:4], axis=0)

        row_3y = {"date": date, "fci3val": float(contrib_3y.sum())}
        row_1y = {"date": date, "fci1val": float(contrib_1y.sum())}
        row_3y.update(dict(zip(OUTPUT_NAMES, contrib_3y)))
        row_1y.update(dict(zip(OUTPUT_NAMES, contrib_1y)))
        rows_3y.append(row_3y)
        rows_1y.append(row_1y)

    start = pd.Timestamp(start_date)
    out_3y = pd.DataFrame(rows_3y)
    out_1y = pd.DataFrame(rows_1y)
    return (
        out_3y[out_3y["date"] >= start].reset_index(drop=True),
        out_1y[out_1y["date"] >= start].reset_index(drop=True),
    )

