from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .core import compute_fci, load_multipliers
from .transforms import (
    load_redfin_house_index,
    raw_primary_to_delta,
    replace_house_index_delta_with_redfin,
)


def _write_series(prefix: str, delta_data: pd.DataFrame, multipliers_path: str, out_dir: Path) -> None:
    multipliers = load_multipliers(multipliers_path)
    out_3y, out_1y = compute_fci(delta_data, multipliers)
    delta_data.to_csv(out_dir / f"{prefix}_input_data.csv", index=False)
    out_3y.to_csv(out_dir / f"{prefix}_threeyearFCI_output.csv", index=False)
    out_1y.to_csv(out_dir / f"{prefix}_oneyearFCI_output.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build primary FCI-G from raw primary inputs, plus a flash series "
            "that only replaces Zillow house prices with Redfin."
        )
    )
    parser.add_argument("--primary-raw", required=True, help="CSV with date plus all seven raw primary input levels/rates")
    parser.add_argument("--redfin", required=True, help="CSV containing the Redfin home price index")
    parser.add_argument("--redfin-date-col", default="date", help="Date column in the Redfin CSV")
    parser.add_argument("--redfin-value-col", default="houseIndex", help="Index value column in the Redfin CSV")
    parser.add_argument("--multipliers", default="data/multipliers.csv", help="Fed multiplier CSV")
    parser.add_argument("--out-dir", default="output", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    primary_raw = pd.read_csv(args.primary_raw)
    primary_delta = raw_primary_to_delta(primary_raw)
    _write_series("primary", primary_delta, args.multipliers, out_dir)

    redfin_index = load_redfin_house_index(
        args.redfin,
        date_column=args.redfin_date_col,
        value_column=args.redfin_value_col,
    )
    flash_delta = replace_house_index_delta_with_redfin(primary_delta, redfin_index)
    _write_series("flash_redfin", flash_delta, args.multipliers, out_dir)


if __name__ == "__main__":
    main()
