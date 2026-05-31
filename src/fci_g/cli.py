from __future__ import annotations

import argparse
from pathlib import Path

from .core import compute_fci, load_multipliers, prepare_delta_input


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild Fed FCI-G outputs.")
    parser.add_argument("--input", required=True, help="CSV of three-month driver changes")
    parser.add_argument("--multipliers", required=True, help="Fed multiplier CSV")
    parser.add_argument("--out-dir", default="output", help="Output directory")
    args = parser.parse_args()

    delta_data = prepare_delta_input(args.input)
    multipliers = load_multipliers(args.multipliers)
    out_3y, out_1y = compute_fci(delta_data, multipliers)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_3y.to_csv(out_dir / "threeyearFCI_output.csv", index=False)
    out_1y.to_csv(out_dir / "oneyearFCI_output.csv", index=False)


if __name__ == "__main__":
    main()

