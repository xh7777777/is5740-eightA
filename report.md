# Raw Data Assessment Report

## Overview
Dataset: `data/raw/zomato_dataset.csv`
- 45,584 records; 20 fields describing delivery personnel, order timings, traffic, weather, and outcomes.
- Current notebook work resides in `notebooks/exploratory_zomato.ipynb` within a freshly provisioned virtual environment (`.venv/`) sourced from `requirements.txt` (pandas, seaborn, jupyterlab, nbconvert, pytest, black, isort).

## Profiling Highlights
- All IDs are unique; no duplicates detected.
- Numeric ranges: `Delivery_person_Age` spans 15–50 (mean 29.6); `Delivery_person_Ratings` 1.0–5.0, though 53 values exceed 5; `Time_taken (min)` median 26 with max 54.
- Categorical coverage: `City` carries `Metropolitian`, `Urban`, `Semi-Urban` (+1.2k null); traffic and weather columns list 4–6 distinct labels.

## Data Quality Issues
1. **Missing Values**
   - Ages (1.8k), ratings (1.9k), `Time_Orderd` (1.7k), multiple deliveries (993), festival flag (228), city (1.2k).
2. **Timestamps**
   - 4,068 `Time_Orderd` and 5,007 `Time_Order_picked` entries stored as Excel fractions (e.g., `0.458333333`).
   - Additional invalid forms (`24:05:00`, full integers `1`).
3. **Geospatial Gaps**
   - 3,640 rows contain zero latitude/longitude values.
4. **Outliers & Integrity**
   - Ages <18 (38 instances), ratings >5.0, misspelt `Metropolitian`.

## Proposed Data Preparation Steps
- **Schema Normalization**: strip strings, standardize casing, correct city spelling, convert categoricals.
- **Timestamp Repair**: convert fractional times with `pd.to_timedelta(frac, unit='D')`, cap invalid `24:xx` entries, parse `Order_Date` using `dayfirst=True`.
- **Missing Data Strategy**: evaluate column-specific imputation—drop/flag implausible ages, impute ratings within [1,5], backfill `Festival`/`City` via restaurant context, infer order times from pickup when plausible.
- **Numeric Validation**: enforce ranges (`18≤Age≤60`, `1≤Rating≤5`, `0≤multiple_deliveries≤3`), set anomalies to null before imputation.
- **Geospatial Cleanup**: mark zero coordinates as null, consider enrichment from restaurant/location lookup tables, ensure coordinates fall within expected city boundaries.
- **Feature Engineering**: compute order-to-pickup and pickup-to-delivery intervals post-cleaning, create delivery speed KPIs, categorize traffic/weather if needed.
- **Quality Assurance**: re-run descriptive stats after cleaning, confirm null handling, and export curated output to `data/processed/zomato_deliveries_clean.csv` with a companion notebook detailing the transformations.

## Next Actions
1. Implement the cleanup pipeline inside a dedicated notebook or `src/` module, adhering to the steps above.
2. Validate notebook execution end-to-end using `.venv/bin/python -m nbconvert --to notebook --execute notebooks/<file>.ipynb` prior to committing results.
