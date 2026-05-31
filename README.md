# FCI-G Rebuilder

Rebuild the Federal Reserve's Financial Conditions Impulse on Growth (FCI-G)
from the public multiplier matrix and a monthly input table of seven
three-month financial-condition changes.

The repo supports two use cases:

1. **Exact replication**: provide the same seven driver series used by the Fed,
   either as a prepared `input_data.csv` or as raw levels/rates.
2. **Redfin flash estimate**: use the same six non-housing primary inputs, but
   replace only Zillow ZHVI with Redfin's home-price index.

## Why GitHub Helps

The local Python issue was only a missing dependency. GitHub Actions solves that
by installing the pinned dependencies in `requirements.txt` on every scheduled
run.

## Exact Input Format

Create a CSV with:

```text
date,FFR,T10yr,Mort30yr,bbbCorpBond,Stockmkt,houseIndex,dollarIndex
```

Each value should already be a three-month change:

| Driver | Exact source | Transformation |
| --- | --- | --- |
| `FFR` | Federal funds rate, FRED `DFF` or NY Fed `EFFR` | Difference between latest and prior three-month daily averages, percentage points |
| `T10yr` | Fed nominal yield curve `SVENPY10` | Difference between latest and prior three-month daily averages, percentage points |
| `Mort30yr` | Optimal Blue 30-year fixed conforming mortgage index from 2016 onward; Freddie Mac history before then | Difference between latest and prior three-month averages, percentage points |
| `bbbCorpBond` | ICE BofA BBB U.S. Corporate Index effective yield | Difference between latest and prior three-month daily averages, percentage points |
| `Stockmkt` | Dow Jones U.S. Total Stock Market Index | `100 * log(level_t / level_t-3m)` |
| `houseIndex` | Zillow ZHVI all homes | `100 * log(level_t / level_t-3m)` |
| `dollarIndex` | Fed H.10 nominal broad dollar index | `100 * log(avg_latest_3m / avg_prior_3m)` |

## Run

If you already have the Fed-style three-month changes:

```bash
python -m fci_g.cli \
  --input path/to/input_data.csv \
  --multipliers data/multipliers.csv \
  --out-dir output
```

Outputs:

```text
output/threeyearFCI_output.csv
output/oneyearFCI_output.csv
```

If you have raw input levels/rates and a Redfin home-price file:

```bash
python -m fci_g.build_series \
  --primary-raw path/to/primary_raw.csv \
  --redfin path/to/redfin_home_price_index.csv \
  --redfin-date-col date \
  --redfin-value-col houseIndex \
  --multipliers data/multipliers.csv \
  --out-dir output
```

This writes both primary and flash outputs:

```text
output/primary_input_data.csv
output/primary_threeyearFCI_output.csv
output/primary_oneyearFCI_output.csv
output/flash_redfin_input_data.csv
output/flash_redfin_threeyearFCI_output.csv
output/flash_redfin_oneyearFCI_output.csv
```

## Raw Input Format

For `primary_raw.csv`, use one wide file with these columns:

```text
date,FFR,T10yr,Mort30yr,bbbCorpBond,Stockmkt,houseIndex,dollarIndex
```

Daily rows are preferred for `FFR`, `T10yr`, `Mort30yr`, `bbbCorpBond`,
`Stockmkt`, and `dollarIndex`. Monthly rows are fine for Zillow `houseIndex`.
Missing cells are acceptable when a series is not observed on a given date.

For `redfin_home_price_index.csv`, use a national Redfin Home Price Index file.
The default expected columns are:

```text
date,houseIndex
```

If Redfin's download uses different names, pass them with `--redfin-date-col`
and `--redfin-value-col`.

The flash series is then built by taking the full primary transformed input and
replacing only the `houseIndex` three-month change with Redfin's equivalent
three-month log change.

## Scheduled Updates

The included GitHub Actions workflow runs monthly and can also be launched
manually. For production use, store any licensed-data credentials or private
download URLs as GitHub Actions secrets.

The workflow checks for `primary_raw.csv` and `redfin_home_price_index.csv` in
the repository first. If they are not present, it can download them from private
URLs stored as `PRIMARY_RAW_DATA_URL` and `REDFIN_HOME_PRICE_URL` repository
secrets.

## Earliest Exact Monthly Update

The bottleneck is Zillow ZHVI. As of the May 31, 2026 check, FRED showed April
2026 ZHVI released on May 21, 2026, with the next release scheduled for June 18,
2026. That implies a clean exact May 2026 FCI-G can first be updated when May
ZHVI is available, currently scheduled for June 18, 2026.

## Home Price Substitutes

| Substitute | Timeliness | Tradeoff |
| --- | --- | --- |
| Zillow ZHVI | Around the third week of the following month | Exact Fed-compatible choice |
| FHFA Purchase-Only HPI | Often end of following or later month | Public repeat-sales index, but slower |
| Case-Shiller National HPI | Roughly two-month lag | High-quality repeat-sales index, but slower |
| Redfin Home Price Index | Published monthly, before/around the Zillow release window | Used only for the flash series; all other primary inputs are unchanged |
