import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import pearsonr
from xgboost import XGBRegressor

from vectorial_capacity import calc_approx_yearly_C

# ---------------------------------------------------------------------------
# CONFIG & PATHS
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
COMBINED_DIR = os.path.join(DATA_DIR, "combined_datasets")
OUTPUT_CSV = os.path.join(DATA_DIR, "test_results", "test_results.csv")
OUTPUT_MD = os.path.join(DATA_DIR, "test_results", "test_results_summary.md")
MATABELELAND_CSV = os.path.join(DATA_DIR, "raw_climate_malaria", "Matabeleland - Test.csv")

ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean"

MATABELELAND_LAT = -18.53
MATABELELAND_LON = 27.53

# MAP Assumptions for Matabeleland (used to approx C)
BASELINE_A = 0.40
ITN_COV = 0.35

# ---------------------------------------------------------------------------
# DATA PIPELINE
# ---------------------------------------------------------------------------

def load_training_data() -> pd.DataFrame:
    """Load the 5 existing combined datasets to form the training corpus."""
    all_dfs = []
    for file in os.listdir(COMBINED_DIR):
        if file.endswith(".csv"):
            path = os.path.join(COMBINED_DIR, file)
            df = pd.read_csv(path)
            
            # Approximate C feature
            if "temperature_2m_mean" in df.columns:
                df["Approx_C"] = df.apply(lambda row: calc_approx_yearly_C(
                    row["temperature_2m_mean"],
                    row["relative_humidity_2m_mean"],
                    row["precipitation_sum"],
                    0.40, 0.35  # Generic baseline for training approx
                ), axis=1)
            all_dfs.append(df)
            
    if not all_dfs:
        raise FileNotFoundError("No combined datasets found for training!")
        
    return pd.concat(all_dfs, ignore_index=True)


def fetch_matabeleland_climate() -> pd.DataFrame:
    """Fetch 2000-2023 historical climate data for Matabeleland."""
    print("Fetching historical climate for Matabeleland (2000-2023)...")
    
    params = {
        "latitude": MATABELELAND_LAT,
        "longitude": MATABELELAND_LON,
        "start_date": "2000-01-01",
        "end_date": "2023-12-31",
        "daily": DAILY_VARS,
        "timezone": "UTC",
    }
    
    resp = requests.get(ARCHIVE_API, params=params, timeout=120)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    
    df = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "temperature_2m_mean": daily["temperature_2m_mean"],
        "precipitation_sum": daily["precipitation_sum"],
        "relative_humidity_2m_mean": daily["relative_humidity_2m_mean"],
    })
    
    # Drop NaNs
    df = df.dropna()
    
    # Aggregate to yearly
    df["Year"] = df["date"].dt.year
    yearly = df.groupby("Year").agg({
        "temperature_2m_mean": "mean",
        "precipitation_sum": "sum",
        "relative_humidity_2m_mean": "mean"
    }).reset_index()
    
    # Calculate Approx C
    yearly["Approx_C"] = yearly.apply(lambda row: calc_approx_yearly_C(
        row["temperature_2m_mean"],
        row["relative_humidity_2m_mean"],
        row["precipitation_sum"],
        BASELINE_A, ITN_COV
    ), axis=1)
    
    return yearly


def load_matabeleland_test_data(climate_df: pd.DataFrame) -> pd.DataFrame:
    """Load the user's Matabeleland - Test.csv and merge with the fetched climate data."""
    if not os.path.exists(MATABELELAND_CSV):
        raise FileNotFoundError(f"Missing {MATABELELAND_CSV}")
        
    m_df = pd.read_csv(MATABELELAND_CSV)
    
    # Filter to Infection Prevalence
    prev_df = m_df[m_df["Metric"] == "Infection Prevalence"][["Year", "Value"]].copy()
    prev_df = prev_df.rename(columns={"Value": "Infection Prevalence"})
    
    # Filter out 2024 since we only fetched climate up to 2023
    prev_df = prev_df[prev_df["Year"] <= 2023]
    
    # Merge
    merged = pd.merge(climate_df, prev_df, on="Year", how="inner")
    return merged


# ---------------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------------

def main():
    print("="*60)
    print("Spatial Holdout Validation (Target: Matabeleland)")
    print("="*60)

    # 1. Prepare Data
    train_df = load_training_data()
    train_df = train_df.dropna(subset=["temperature_2m_mean", "precipitation_sum", "relative_humidity_2m_mean", "Infection Prevalence", "Approx_C"])
    
    print(f"Training set: {len(train_df)} yearly records across 5 baseline cities.")
    
    test_climate = fetch_matabeleland_climate()
    test_df = load_matabeleland_test_data(test_climate)
    test_df = test_df.dropna(subset=["temperature_2m_mean", "precipitation_sum", "relative_humidity_2m_mean", "Infection Prevalence", "Approx_C"])
    
    print(f"Testing set: {len(test_df)} yearly records for Matabeleland.")

    # 2. Train Model
    features = ["temperature_2m_mean", "precipitation_sum", "relative_humidity_2m_mean", "Approx_C"]
    target = "Infection Prevalence"
    
    X_train = train_df[features].values
    y_train = train_df[target].values
    X_test = test_df[features].values
    y_test = test_df[target].values
    
    print("\nTraining generalized XGBoost Regressor...")
    model = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)
    
    # 3. Predict & Evaluate
    print("Evaluating on Matabeleland...")
    y_pred = model.predict(X_test)
    
    # Prevent negative prevalence
    y_pred = np.clip(y_pred, 0, 100)
    
    test_df["Predicted_Infection_Prevalence"] = y_pred
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    if len(y_test) > 1 and np.std(y_pred) > 0:
        pearson_r, _ = pearsonr(y_test, y_pred)
    else:
        pearson_r = 0.0
        
    print(f"\nAccuracy Metrics for Matabeleland Holdout:")
    print(f"  MAE:       {mae:.3f} %")
    print(f"  RMSE:      {rmse:.3f} %")
    print(f"  R^2:       {r2:.3f}")
    print(f"  Pearson r: {pearson_r:.3f}")
    
    # 4. Output Results
    test_df.to_csv(OUTPUT_CSV, index=False)
    
    md_content = f"""# Matabeleland Spatial Holdout Accuracy Report

This report evaluates the Hybrid AI-Mechanistic pipeline's ability to predict disease burden in a completely unseen geography (Matabeleland, Zimbabwe) by training exclusively on the other 5 baseline regions.

## Model
- **Algorithm:** XGBoost Regressor
- **Features (X):** Temperature, Precipitation, Humidity, and Mechanistic Vectorial Capacity Approximation
- **Target (y):** Infection Prevalence (%)
- **Training Set:** 5 Regions (Beni, Delhi, Zinder, Nairobi, Heilongjiang)
- **Testing Set:** Matabeleland North (2000-2023)

## Standard Accuracy Metrics
- **Mean Absolute Error (MAE):** `{mae:.3f}` percentage points
- **Root Mean Squared Error (RMSE):** `{rmse:.3f}` percentage points
- **Coefficient of Determination ($R^2$):** `{r2:.3f}`
- **Biological Correlation (Pearson $r$):** `{pearson_r:.3f}`

## Raw Predictions vs Ground Truth
The detailed year-by-year predictions have been exported to `test_results.csv`.
"""
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"\nSaved results to:\n- {OUTPUT_CSV}\n- {OUTPUT_MD}")


if __name__ == "__main__":
    main()
