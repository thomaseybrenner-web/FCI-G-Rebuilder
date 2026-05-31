from __future__ import annotations

import numpy as np
import pandas as pd

from .core import DRIVERS


RATE_DRIVERS = ["FFR", "T10yr", "Mort30yr", "bbbCorpBond"]
DOLLAR_DRIVER = "dollarIndex"
LOG_LEVEL_DRIVERS = ["Stockmkt", "houseIndex"]


def _month_end(date: pd.Timestamp) -> pd.Timestamp:
    return date + pd.offsets.MonthEnd(0)


def _window_average(
    data: pd.DataFrame,
    column: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> float:
    values = data.loc[data["date"].between(start, end), column].dropna()
    if values.empty:
        return np.nan
    return float(values.mean())


def _last_level_on_or_before(
    data: pd.DataFrame,
    column: str,
    date: pd.Timestamp,
) -> float:
    values = data.loc[data["date"].le(date), ["date", column]].dropna()
    if values.empty:
        return np.nan
    return float(values.iloc[-1][column])


def _three_month_windows(month_end: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    current_start = pd.Timestamp(year=month_end.year, month=month_end.month, day=1) - pd.DateOffset(months=2)
    prior_end = current_start - pd.Timedelta(days=1)
    prior_start = current_start - pd.DateOffset(months=3)
    return current_start, month_end, prior_start, prior_end


def monthly_level_proxy_to_delta(levels: pd.DataFrame) -> pd.DataFrame:
    """Convert monthly levels into the Fed input shape.

    This helper is exact for monthly stock and house-price level changes, and a
    proxy for rate/dollar inputs when only monthly levels are available. Exact
    replication should use daily data for rate averages and dollar averages.
    """

    data = levels[["date", *DRIVERS]].copy()
    data["date"] = pd.to_datetime(data["date"]).map(lambda date: date + pd.offsets.MonthEnd(0))
    data = data.sort_values("date").reset_index(drop=True)

    out = pd.DataFrame({"date": data["date"]})
    for column in RATE_DRIVERS:
        out[column] = data[column] - data[column].shift(3)
    for column in LOG_LEVEL_DRIVERS + ["dollarIndex"]:
        out[column] = 100 * (np.log(data[column]) - np.log(data[column].shift(3)))

    return out.dropna().reset_index(drop=True)


def raw_primary_to_delta(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Build the FCI-G input table from the seven primary raw series.

    Expected columns are `date` plus the seven driver names in `DRIVERS`.
    Daily rows are preferred for rates, yields, stock prices, and the dollar.
    Monthly Zillow observations are fine for `houseIndex`.
    """

    missing = [column for column in ["date", *DRIVERS] if column not in raw_data.columns]
    if missing:
        raise ValueError(f"Raw primary data is missing columns: {missing}")

    data = raw_data[["date", *DRIVERS]].copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)

    month_ends = (
        data.loc[data["houseIndex"].notna(), "date"]
        .map(_month_end)
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    rows: list[dict[str, float | pd.Timestamp]] = []
    for month_end in month_ends:
        current_start, current_end, prior_start, prior_end = _three_month_windows(month_end)
        row: dict[str, float | pd.Timestamp] = {"date": month_end}

        for column in RATE_DRIVERS:
            current_avg = _window_average(data, column, current_start, current_end)
            prior_avg = _window_average(data, column, prior_start, prior_end)
            row[column] = current_avg - prior_avg

        stock_now = _last_level_on_or_before(data, "Stockmkt", month_end)
        stock_prior = _last_level_on_or_before(data, "Stockmkt", month_end - pd.DateOffset(months=3))
        row["Stockmkt"] = 100 * (np.log(stock_now) - np.log(stock_prior))

        house_now = _last_level_on_or_before(data, "houseIndex", month_end)
        house_prior = _last_level_on_or_before(data, "houseIndex", month_end - pd.DateOffset(months=3))
        row["houseIndex"] = 100 * (np.log(house_now) - np.log(house_prior))

        dollar_now = _window_average(data, DOLLAR_DRIVER, current_start, current_end)
        dollar_prior = _window_average(data, DOLLAR_DRIVER, prior_start, prior_end)
        row[DOLLAR_DRIVER] = 100 * (np.log(dollar_now) - np.log(dollar_prior))
        rows.append(row)

    return pd.DataFrame(rows).dropna().reset_index(drop=True)


def load_redfin_house_index(
    redfin_csv: str,
    date_column: str = "date",
    value_column: str = "houseIndex",
) -> pd.DataFrame:
    """Load a Redfin home-price index file as `date,houseIndex`.

    Use the Redfin Home Price Index national series where possible. If your
    download uses different column names, pass them through the CLI flags.
    """

    redfin = pd.read_csv(redfin_csv)
    missing = [column for column in [date_column, value_column] if column not in redfin.columns]
    if missing:
        raise ValueError(f"Redfin data is missing columns: {missing}")

    out = redfin[[date_column, value_column]].copy()
    out.columns = ["date", "houseIndex"]
    out["date"] = pd.to_datetime(out["date"]).map(_month_end)
    out = out.dropna().sort_values("date").drop_duplicates("date", keep="last")
    return out.reset_index(drop=True)


def replace_house_index_delta_with_redfin(
    primary_delta: pd.DataFrame,
    redfin_house_index: pd.DataFrame,
) -> pd.DataFrame:
    """Create the flash input by replacing only the house-price delta."""

    redfin = redfin_house_index.copy()
    redfin["date"] = pd.to_datetime(redfin["date"]).map(_month_end)
    redfin = redfin.sort_values("date").drop_duplicates("date", keep="last")
    redfin["houseIndex"] = 100 * (
        np.log(redfin["houseIndex"]) - np.log(redfin["houseIndex"].shift(3))
    )
    redfin_delta = redfin[["date", "houseIndex"]].dropna()

    flash = primary_delta.drop(columns=["houseIndex"]).merge(redfin_delta, on="date", how="inner")
    return flash[["date", *DRIVERS]].reset_index(drop=True)
