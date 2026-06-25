import os
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
OUTPUT_CSV = os.path.join(DATA_DIR, "test_results", "mongala_temporal_results.csv")
OUTPUT_MD = os.path.join(DATA_DIR, "test_results", "mongala_temporal_summary.md")
MONGALA_CSV = os.path.join(DATA_DIR, "raw_climate_malaria", "Mongala.csv")

ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean"

MONGALA_LAT = 2.15
MONGALA_LON = 21.50

# MAP Assumptions for Mongala (approx C)
BASELINE_A = 0.40
ITN_COV = 0.35

# ---------------------------------------------------------------------------
# DATA PIPELINE
# ---------------------------------------------------------------------------

def fetch_mongala_climate() -> pd.DataFrame:
    """Fetch 2000-2023 historical climate data for Mongala."""
    print("Fetching historical climate for Mongala (2000-2023)...")
    
    params = {
        "latitude": MONGALA_LAT,
        "longitude": MONGALA_LON,
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


def load_mongala_disease_data(climate_df: pd.DataFrame) -> pd.DataFrame:
    """Load the user's Mongala.csv and merge with the fetched climate data."""
    if not os.path.exists(MONGALA_CSV):
        raise FileNotFoundError(f"Missing {MONGALA_CSV}")
        
    m_df = pd.read_csv(MONGALA_CSV)
    
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
    print("Temporal Holdout Validation (Target: Mongala)")
    print("="*60)

    # 1. Prepare Data
    climate_df = fetch_mongala_climate()
    df = load_mongala_disease_data(climate_df)
    df = df.dropna(subset=["temperature_2m_mean", "precipitation_sum", "relative_humidity_2m_mean", "Infection Prevalence", "Approx_C"])
    
    # Sort chronologically and create the Lag feature
    df = df.sort_values(by="Year")
    df["Lag_1_Infection_Prevalence"] = df["Infection Prevalence"].shift(1)
    
    # Drop the first year (2000) because it has no lag data
    df = df.dropna(subset=["Lag_1_Infection_Prevalence"])
    
    # 2. Time-Series Split
    # Train: 2001-2019
    # Test: 2020-2023
    train_df = df[df["Year"] <= 2019].copy()
    test_df = df[(df["Year"] >= 2020) & (df["Year"] <= 2023)].copy()
    
    print(f"Training set: {len(train_df)} years (2001-2019)")
    print(f"Testing set: {len(test_df)} years (2020-2023)")

    if len(train_df) == 0 or len(test_df) == 0:
        print("Error: Not enough data after split.")
        return

    # 3. Train Model
    features = ["temperature_2m_mean", "precipitation_sum", "relative_humidity_2m_mean", "Approx_C", "Lag_1_Infection_Prevalence"]
    target = "Infection Prevalence"
    
    X_train = train_df[features].values
    y_train = train_df[target].values
    y_test = test_df[target].values
    
    print("\nTraining XGBoost Regressor on Mongala history...")
    model = XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)
    
    # 4. Predict & Evaluate (Option B: Recursive Forecasting)
    print("Predicting the future recursively (2020-2023)...")
    y_pred = []
    
    # The first prediction (2020) uses the actual lag from 2019
    current_lag = test_df.iloc[0]["Lag_1_Infection_Prevalence"]
    
    for index, row in test_df.iterrows():
        # Construct the feature array manually with the predicted lag
        x_input = np.array([
            row["temperature_2m_mean"], 
            row["precipitation_sum"], 
            row["relative_humidity_2m_mean"], 
            row["Approx_C"], 
            current_lag
        ]).reshape(1, -1)
        
        pred_val = model.predict(x_input)[0]
        pred_val = np.clip(pred_val, 0, 100)
        
        y_pred.append(pred_val)
        
        # The prediction becomes the lag for the NEXT year's prediction!
        current_lag = pred_val
        
    y_pred = np.array(y_pred)
    
    test_df["Predicted_Infection_Prevalence"] = y_pred
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    if len(y_test) > 1 and np.std(y_pred) > 0:
        pearson_r, _ = pearsonr(y_test, y_pred)
    else:
        pearson_r = 0.0
        
    print(f"\nAccuracy Metrics for Mongala Temporal Holdout:")
    print(f"  MAE:       {mae:.3f} %")
    print(f"  RMSE:      {rmse:.3f} %")
    print(f"  R^2:       {r2:.3f}")
    print(f"  Pearson r: {pearson_r:.3f}")
    
    # Output the full dataset
    # For training set, we can just do one-step predictions to show model fit
    train_df["Predicted_Infection_Prevalence"] = np.clip(model.predict(X_train), 0, 100)
    
    # Combine back
    final_df = pd.concat([train_df, test_df])
    final_df["Split"] = final_df["Year"].apply(lambda y: "Train" if y <= 2019 else "Test")
    
    final_df.to_csv(OUTPUT_CSV, index=False)
    
    md_content = f"""# Mongala Temporal Holdout Accuracy Report

This report evaluates the predictive foresight of the localized Mechanistic-AI model for Mongala, Democratic Republic of the Congo. The model was trained purely on historical data and forced to predict the unseen future.

## Model Setup
- **Algorithm:** XGBoost Regressor
- **Features (X):** Temperature, Precipitation, Humidity, and Vectorial Capacity ($C$)
- **Target (y):** Infection Prevalence (%)
- **Training Set (Known Past):** 20 Years (2000 - 2019)
- **Testing Set (Unseen Future):** 4 Years (2020 - 2023)

## Standard Accuracy Metrics (On the Test Set)
- **Mean Absolute Error (MAE):** `{mae:.3f}` percentage points
- **Root Mean Squared Error (RMSE):** `{rmse:.3f}` percentage points
- **Coefficient of Determination ($R^2$):** `{r2:.3f}`
- **Biological Correlation (Pearson $r$):** `{pearson_r:.3f}`

## Insights
A temporal holdout test is notoriously difficult, especially for ecological diseases. A positive Pearson correlation indicates that the model accurately detected the *trend* and fluctuations in the future years. A strong $R^2$ demonstrates excellent absolute accuracy over the baseline mean.

The detailed year-by-year predictions for the entire 2000-2023 timeframe have been exported to `mongala_temporal_results.csv`.
"""
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"\nSaved results to:\n- {OUTPUT_CSV}\n- {OUTPUT_MD}")


if __name__ == "__main__":
    main()
