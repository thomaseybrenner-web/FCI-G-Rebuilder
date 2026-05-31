import numpy as np
import pandas as pd

from fci_g.core import DRIVERS
from fci_g.transforms import raw_primary_to_delta, replace_house_index_delta_with_redfin


def test_flash_replaces_only_house_index():
    dates = pd.date_range("2020-01-31", "2021-12-31", freq="ME")
    raw = pd.DataFrame({"date": dates})
    for column in DRIVERS:
        raw[column] = np.linspace(100, 125, len(dates))

    primary = raw_primary_to_delta(raw)
    redfin = pd.DataFrame(
        {
            "date": dates,
            "houseIndex": np.linspace(200, 260, len(dates)),
        }
    )
    flash = replace_house_index_delta_with_redfin(primary, redfin)

    merged = primary.merge(flash, on="date", suffixes=("_primary", "_flash"))
    for column in [driver for driver in DRIVERS if driver != "houseIndex"]:
        assert np.allclose(merged[f"{column}_primary"], merged[f"{column}_flash"])

    assert not np.allclose(merged["houseIndex_primary"], merged["houseIndex_flash"])

