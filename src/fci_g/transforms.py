from __future__ import annotations

import numpy as np
import pandas as pd

from .core import DRIVERS


RATE_DRIVERS = ["FFR", "T10yr", "Mort30yr", "bbbCorpBond"]
LOG_LEVEL_DRIVERS = ["Stockmkt", "houseIndex"]


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

