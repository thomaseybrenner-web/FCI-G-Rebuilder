# FCI-G Rebuilder

Rebuild the Federal Reserve's Financial Conditions Impulse on Growth (FCI-G)
from the public multiplier matrix and a monthly input table of seven
three-month financial-condition changes.

The repo supports two use cases:

1. **Exact replication**: provide the same seven driver series used by the Fed,
   transformed into the `input_data.csv` format described below.
2. **Flash/proxy estimate**: use public/free data where possible, with any
   substitutions clearly documented. This is useful before Zillow ZHVI is
   released, but it is not the official-equivalent series.

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

## Scheduled Updates

The included GitHub Actions workflow runs monthly and can also be launched
manually. For exact replication, upload or generate `input_data.csv` before the
calculation step. For production use, store any licensed-data credentials as
GitHub Actions secrets.

The workflow checks for `input_data.csv` in the repository first. If that is not
present, it can download one from a private URL stored as the
`EXACT_INPUT_DATA_URL` repository secret.

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
| Redfin Home Price Index or Redfin weekly price data | Faster | Best for a flash estimate, not exact replication |
