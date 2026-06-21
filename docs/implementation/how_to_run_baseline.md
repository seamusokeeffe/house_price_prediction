# How to Run the Baseline

## Expected input

Provide a processed modelling CSV with at least these columns:

- `transaction_date`
- `sale_price_eur`
- `canonical_area`
- `property_type`

Optional columns used by later feature/report code include:

- `geo_scope`
- `beds`
- `baths`
- `floor_area_sqm`
- `ber_rating`
- `exclude_from_training`

## Train baseline

```powershell
python scripts/train_baseline.py --dataset data/processed/dataset_version=YYYYMMDD/processed_transactions.csv
```

This writes:

```text
artifacts/grouped_median_baseline.pkl
```

## Run validation

```powershell
python scripts/run_validation.py --dataset data/processed/dataset_version=YYYYMMDD/processed_transactions.csv --holdout-months 12
```

The command prints JSON with:

- train row count
- validation row count
- MAE in euro
- median absolute percentage-style error
- log MAE
- baseline backoff counts

## Notes

This is intentionally a baseline skeleton. It should be replaced or extended after the first real processed dataset exists.

