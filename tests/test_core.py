import numpy as np
import pandas as pd

from fci_g.core import DRIVERS, compute_fci, load_multipliers


def test_compute_fci_uses_four_and_twelve_lags(tmp_path):
    dates = pd.date_range("1987-01-31", "1991-12-31", freq="ME")
    delta_data = pd.DataFrame({"date": dates})
    for idx, column in enumerate(DRIVERS, start=1):
        delta_data[column] = idx * 0.1

    multipliers = load_multipliers("data/multipliers.csv")
    out_3y, out_1y = compute_fci(delta_data, multipliers)

    history = delta_data.iloc[36:0:-3][DRIVERS].head(12).to_numpy(dtype=float)
    weights = multipliers[DRIVERS].to_numpy(dtype=float)
    expected_3y = -np.sum(history * weights[:12], axis=0).sum()
    expected_1y = -np.sum(history[:4] * weights[:4], axis=0).sum()

    assert out_3y.iloc[0]["date"] == pd.Timestamp("1990-01-31")
    assert np.isclose(out_3y.iloc[0]["fci3val"], expected_3y)
    assert np.isclose(out_1y.iloc[0]["fci1val"], expected_1y)

