"""End-to-end cleaning pipeline for the Zomato delivery dataset."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

# Define canonical file locations to keep CLI usage simple.
RAW_DATA_PATH = Path("data/raw/zomato_dataset.csv")
PROCESSED_DATA_PATH = Path("data/processed/zomato_deliveries_clean.csv")

# Known spelling fixes for categorical values discovered during profiling.
CITY_REMAP = {"Metropolitian": "Metropolitan"}


def load_raw_dataset(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Load the raw CSV into a DataFrame without applying any coercion."""
    # Use pandas defaults so that profile statistics match earlier explorations.
    return pd.read_csv(path)


def tidy_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and normalise obvious categorical quirks."""
    cleaned = df.copy()

    # Strip leading/trailing spaces for every object column so comparisons are reliable.
    string_cols = cleaned.select_dtypes(include="object").columns
    for col in string_cols:
        cleaned[col] = cleaned[col].astype(str).str.strip()
        cleaned.loc[cleaned[col].isin({"", "nan", "None"}), col] = pd.NA

    # Apply spelling corrections to categorical columns that were flagged during profiling.
    if "City" in cleaned.columns:
        cleaned["City"] = cleaned["City"].replace(CITY_REMAP)

    return cleaned


def convert_excel_fraction_to_time_string(fraction: pd.Series) -> pd.Series:
    """Convert Excel day-fraction numbers to HH:MM formatted strings."""
    # Drop missing entries so that we only transform genuinely numeric values.
    valid = fraction.dropna()
    if valid.empty:
        return pd.Series([], dtype="object")

    # Translate numeric fractions into minutes within a 24-hour window.
    minutes = (valid * 24 * 60).round()
    # Guard against values equal to or exceeding 24 hours by capping at 23:59.
    minutes = minutes.clip(lower=0, upper=(24 * 60) - 1)
    hours = (minutes // 60).astype(int)
    mins = (minutes % 60).astype(int)
    return hours.astype(str).str.zfill(2) + ":" + mins.astype(str).str.zfill(2)


def standardise_time_column(df: pd.DataFrame, column: str) -> Tuple[pd.DataFrame, pd.Series]:
    """Return DataFrame with a cleaned HH:MM time column and the corresponding minutes."""
    cleaned = df.copy()

    # Prepare a working copy that keeps the original values untouched for auditing.
    raw_series = cleaned[column]
    series = raw_series.astype(str).str.strip()
    series.loc[series.isin({"", "nan", "None"})] = pd.NA

    # Capture Excel-style fractions such as 0.458333333 that represent time of day.
    fraction_mask = series.str.fullmatch(r"\d+(\.\d+)?", na=False)
    fractions = pd.to_numeric(series.where(fraction_mask), errors="coerce")
    converted_fraction_times = convert_excel_fraction_to_time_string(fractions)
    series.loc[converted_fraction_times.index] = converted_fraction_times

    # Handle HH:MM:SS values by truncating to HH:MM.
    hhmmss_mask = series.str.fullmatch(r"\d{1,2}:\d{2}:\d{2}", na=False)
    series.loc[hhmmss_mask] = series.where(hhmmss_mask).str.slice(0, 5)

    # For entries exactly equal to "24:00" or other >23h times, clip down to 23:59.
    overflow_mask = series.str.fullmatch(r"24:\d{2}", na=False)
    series.loc[overflow_mask] = "23:59"

    # Attempt parsing remaining values as HH:MM and record failures as missing.
    parsed = pd.to_datetime(series, format="%H:%M", errors="coerce")
    series.loc[parsed.isna()] = pd.NA

    # Derive total minutes to simplify interval computations later on.
    minutes = parsed.dt.hour * 60 + parsed.dt.minute

    cleaned[column + "_clean"] = series
    cleaned[column + "_minutes"] = minutes

    return cleaned, minutes


def parse_order_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convert the Order_Date column into a proper datetime series."""
    cleaned = df.copy()

    if "Order_Date" in cleaned.columns:
        # Use DD-MM-YYYY format and mark unparseable entries for downstream handling.
        parsed_dates = pd.to_datetime(cleaned["Order_Date"], format="%d-%m-%Y", errors="coerce")
        cleaned["Order_Date_clean"] = parsed_dates
    return cleaned


def enforce_numeric_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the numeric validation rules defined during data profiling."""
    cleaned = df.copy()

    # Flag implausible courier ages and ratings by converting them to missing values.
    if "Delivery_person_Age" in cleaned.columns:
        mask_age = (cleaned["Delivery_person_Age"] < 18) | (cleaned["Delivery_person_Age"] > 60)
        cleaned.loc[mask_age, "Delivery_person_Age"] = pd.NA

    if "Delivery_person_Ratings" in cleaned.columns:
        mask_rating = (cleaned["Delivery_person_Ratings"] < 1) | (cleaned["Delivery_person_Ratings"] > 5)
        cleaned.loc[mask_rating, "Delivery_person_Ratings"] = pd.NA

    if "multiple_deliveries" in cleaned.columns:
        mask_multi = ~cleaned["multiple_deliveries"].isin([0, 1, 2, 3])
        cleaned.loc[mask_multi, "multiple_deliveries"] = pd.NA

    return cleaned


def scrub_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Replace zero latitude/longitude pairs with missing values."""
    cleaned = df.copy()
    coord_cols = [
        "Restaurant_latitude",
        "Restaurant_longitude",
        "Delivery_location_latitude",
        "Delivery_location_longitude",
    ]
    for col in coord_cols:
        if col in cleaned.columns:
            cleaned.loc[cleaned[col] == 0, col] = pd.NA
    return cleaned


def compute_time_intervals(df: pd.DataFrame) -> pd.DataFrame:
    """Derive order-to-pickup and pickup-to-delivery intervals in minutes."""
    cleaned = df.copy()

    # Ensure prerequisite columns exist before attempting interval calculations.
    required_cols = {"Order_Date_clean", "Time_Orderd_minutes", "Time_Order_picked_minutes", "Time_taken (min)"}
    if not required_cols.issubset(cleaned.columns):
        return cleaned

    # Build order and pickup timestamps from the parsed day plus time-of-day minutes.
    order_datetime = cleaned["Order_Date_clean"] + pd.to_timedelta(cleaned["Time_Orderd_minutes"], unit="m")
    pickup_datetime = cleaned["Order_Date_clean"] + pd.to_timedelta(cleaned["Time_Order_picked_minutes"], unit="m")

    # Adjust pickups that appear before the order time by assuming the dispatch happened after midnight.
    negative_mask = pickup_datetime < order_datetime
    pickup_datetime.loc[negative_mask] += pd.Timedelta(days=1)

    # Compute the interval in minutes; invalid or missing inputs propagate as NA automatically.
    order_to_pick = (pickup_datetime - order_datetime).dt.total_seconds() / 60
    cleaned["order_to_pick_minutes"] = order_to_pick

    # Derive pickup-to-delivery by subtracting the measured order-to-delivery time.
    cleaned["pickup_to_delivery_minutes"] = cleaned["Time_taken (min)"] - order_to_pick

    # Negative results indicate inconsistent source data, so mark them as missing for now.
    inconsistency_mask = cleaned["pickup_to_delivery_minutes"] < 0
    cleaned.loc[inconsistency_mask, "pickup_to_delivery_minutes"] = pd.NA

    return cleaned


def convert_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Cast high-cardinality string columns to categorical dtypes for efficiency."""
    cleaned = df.copy()
    categorical_columns = [
        "Weather_conditions",
        "Road_traffic_density",
        "Type_of_order",
        "Type_of_vehicle",
        "Festival",
        "City",
    ]
    for col in categorical_columns:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].astype("category")
    return cleaned


def standardize_units(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Ensure time-related columns are expressed in minutes and distances in kilometres."""
    cleaned = df.copy()
    adjustments: Dict[str, int] = {"time_unit_conversions": 0, "distance_standardised": 0}

    # Time columns expected to be in minutes; detect second-based entries heuristically.
    time_columns: List[str] = [
        "Time_taken (min)",
        "order_to_pick_minutes",
        "pickup_to_delivery_minutes",
        "Time_Orderd_minutes",
        "Time_Order_picked_minutes",
    ]
    for col in time_columns:
        if col not in cleaned.columns:
            continue
        series = pd.to_numeric(cleaned[col], errors="coerce")
        if series.dropna().empty:
            cleaned[col] = series
            continue

        # Treat values larger than 3 hours that are neatly divisible by 60 as seconds.
        suspect_mask = (series > 180) & (series % 60 == 0)
        if suspect_mask.any() and suspect_mask.mean() > 0.8:
            series = series / 60
            adjustments["time_unit_conversions"] += int(suspect_mask.sum())

        # Cap extreme values at 24 hours to avoid downstream skew.
        series = series.clip(upper=24 * 60)
        cleaned[col] = series

    distance_columns: List[str] = [
        "haversine_km",
        "Distance_km",
        "Delivery_distance",
    ]
    for col in distance_columns:
        if col not in cleaned.columns:
            continue
        series = pd.to_numeric(cleaned[col], errors="coerce")
        if series.dropna().empty:
            cleaned[col] = series
            continue

        # Detect metre-based measurements by looking for values > 1000.
        if series.max() and series.max() > 1000:
            series = series / 1000
            adjustments["distance_standardised"] += int(series.notna().sum())
        cleaned[col] = series

    return cleaned, adjustments


def detect_outliers(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Clip extreme values using the IQR rule for key numeric columns."""
    cleaned = df.copy()
    outlier_counts: Dict[str, int] = {"outliers_capped": 0}

    columns_to_check = [
        "Delivery_person_Age",
        "Delivery_person_Ratings",
        "Time_taken (min)",
        "order_to_pick_minutes",
        "pickup_to_delivery_minutes",
    ]

    for col in columns_to_check:
        if col not in cleaned.columns:
            continue
        series = pd.to_numeric(cleaned[col], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            cleaned[col] = series
            continue

        q1, q3 = valid.quantile([0.25, 0.75])
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            cleaned[col] = series
            continue

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        mask = (series < lower_bound) | (series > upper_bound)
        outlier_counts["outliers_capped"] += int(mask.sum())
        series = series.clip(lower=lower_bound, upper=upper_bound)
        cleaned[col] = series

    return cleaned, outlier_counts


def fill_missing_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Impute missing values using data-type aware strategies."""
    cleaned = df.copy()
    fill_stats: Dict[str, int] = {
        "numeric_missing_filled": 0,
        "time_missing_filled": 0,
        "categorical_missing_filled": 0,
    }

    time_columns = [col for col in cleaned.columns if col.endswith("_minutes")]
    if "Time_taken (min)" in cleaned.columns:
        time_columns.append("Time_taken (min)")
    time_columns = list(dict.fromkeys(time_columns))

    for col in time_columns:
        if col not in cleaned.columns:
            continue
        series = pd.to_numeric(cleaned[col], errors="coerce")
        if series.isna().any():
            valid = series.dropna()
            if not valid.empty:
                median_value = valid.median()
                missing_count = int(series.isna().sum())
                cleaned[col] = series.fillna(median_value)
                fill_stats["time_missing_filled"] += missing_count

    numeric_cols = cleaned.select_dtypes(include=["number", "Float64", "Int64"]).columns.difference(time_columns)
    for col in numeric_cols:
        series = pd.to_numeric(cleaned[col], errors="coerce")
        if series.isna().any():
            valid = series.dropna()
            if not valid.empty:
                mean_value = valid.mean()
                missing_count = int(series.isna().sum())
                cleaned[col] = series.fillna(mean_value)
                fill_stats["numeric_missing_filled"] += missing_count

    categorical_cols = cleaned.select_dtypes(include=["object", "category"]).columns
    for col in categorical_cols:
        series = cleaned[col]
        if series.isna().any():
            mode_series = series.mode(dropna=True)
            if not mode_series.empty:
                mode_value = mode_series.iloc[0]
                missing_count = int(series.isna().sum())
                cleaned[col] = series.fillna(mode_value)
                fill_stats["categorical_missing_filled"] += missing_count

    return cleaned, fill_stats


def remove_duplicates(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Drop exact duplicates and resolve clashes on critical identifier combinations."""
    cleaned = df.copy()
    duplicate_stats: Dict[str, int] = {
        "duplicates_removed_exact": 0,
        "duplicates_removed_key": 0,
    }

    before = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    duplicate_stats["duplicates_removed_exact"] = before - len(cleaned)

    key_candidates: List[str] = []
    if "Order_ID" in cleaned.columns:
        key_candidates.append("Order_ID")
    elif "ID" in cleaned.columns:
        key_candidates.append("ID")

    for candidate in ["Delivery_person_ID", "Order_Date_clean"]:
        if candidate in cleaned.columns:
            key_candidates.append(candidate)

    if len(key_candidates) >= 2:
        sort_cols = [col for col in ["Order_Date_clean", "Time_Orderd_minutes", "Time_Order_picked_minutes"] if col in cleaned.columns]
        if sort_cols:
            cleaned = cleaned.sort_values(sort_cols)
        before_key = len(cleaned)
        cleaned = cleaned.drop_duplicates(subset=key_candidates, keep="first")
        duplicate_stats["duplicates_removed_key"] = before_key - len(cleaned)

    cleaned = cleaned.reset_index(drop=True)
    return cleaned, duplicate_stats


def normalize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df where numeric columns are min-max scaled."""
    normalized = df.copy()
    numeric_cols = normalized.select_dtypes(include=["number", "Float64", "Int64"]).columns
    for col in numeric_cols:
        series = pd.to_numeric(normalized[col], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            normalized[col] = series
            continue
        min_val = valid.min()
        max_val = valid.max()
        if max_val == min_val:
            normalized[col] = series.where(series.isna(), 0.0)
            continue
        scaled = (series - min_val) / (max_val - min_val)
        normalized[col] = scaled
    return normalized


def clean_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    """Run the full cleaning pipeline and collect simple issue counters."""
    issues: Dict[str, int] = {}

    cleaned = tidy_string_columns(df)

    cleaned, order_minutes = standardise_time_column(cleaned, "Time_Orderd")
    issues["Time_Orderd_clean_missing"] = cleaned["Time_Orderd_clean"].isna().sum()

    cleaned, pickup_minutes = standardise_time_column(cleaned, "Time_Order_picked")
    issues["Time_Order_picked_clean_missing"] = cleaned["Time_Order_picked_clean"].isna().sum()

    cleaned = parse_order_dates(cleaned)
    issues["Order_Date_parse_missing"] = cleaned["Order_Date_clean"].isna().sum()

    cleaned = enforce_numeric_ranges(cleaned)

    cleaned = scrub_coordinates(cleaned)

    cleaned = compute_time_intervals(cleaned)

    cleaned, unit_stats = standardize_units(cleaned)
    issues.update({k: v for k, v in unit_stats.items() if v})

    cleaned, outlier_stats = detect_outliers(cleaned)
    issues.update({k: v for k, v in outlier_stats.items() if v})

    cleaned, fill_stats = fill_missing_values(cleaned)
    issues.update({k: v for k, v in fill_stats.items() if v})

    cleaned = convert_categoricals(cleaned)

    cleaned, duplicate_stats = remove_duplicates(cleaned)
    issues.update({k: v for k, v in duplicate_stats.items() if v})

    normalized = normalize_numeric_columns(cleaned)

    return cleaned, normalized, issues


def save_processed_dataset(df: pd.DataFrame, path: Path = PROCESSED_DATA_PATH) -> None:
    """Persist the cleaned dataset to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def main() -> None:
    """Execute the cleaning workflow and output a simple quality summary."""
    # Step 1: Load the raw data from the canonical location.
    raw_df = load_raw_dataset()

    # Step 2: Apply the cleaning pipeline to standardise fields and engineer features.
    cleaned_df, normalized_df, issues = clean_dataset(raw_df)

    # Step 3: Write the processed output for downstream analysis bundles.
    save_processed_dataset(cleaned_df)

    # Optionally persist the normalised view alongside the primary dataset for modelling experiments.
    normalized_path = PROCESSED_DATA_PATH.with_name("zomato_deliveries_normalized.csv")
    save_processed_dataset(normalized_df, normalized_path)

    # Step 4: Emit a concise diagnostic summary to assist manual review.
    summary_lines = ["Cleaning summary:"]
    for key, count in issues.items():
        summary_lines.append(f"  - {key}: {count}")
    print("\n".join(summary_lines))
    print(f"Processed dataset saved to {PROCESSED_DATA_PATH}")
    print(f"Normalized dataset saved to {normalized_path}")


if __name__ == "__main__":
    main()
