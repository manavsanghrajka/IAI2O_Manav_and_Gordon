"""
Hybrid AI-Mechanistic Malaria Risk Predictor
=============================================
Authors: Manav Sanghrajka & Gordon Li, The Woodlands School

Pipeline:
  1. Ingest 10 years of daily climate data from Open-Meteo Archive API
  2. Load historical yearly MAP data (Infection Prevalence)
  3. Estimate historical ITN coverage inversely from Prevalence
  4. Train 3 XGBoost models per city (temperature, humidity, precipitation) + 1 for ITN coverage (yearly)
  5. Iteratively forecast 5 years of daily climate + 5 years of yearly ITN
  6. Apply Ross-Macdonald Vectorial Capacity equations (Daily climate + Locked yearly MAP baseline)
  7. Compute historical validation (Pearson r) between historical C and actual Infection Prevalence
  8. Export dashboard_data.json
"""

import json
import os
import time
import traceback
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from vectorial_capacity import (
    calc_vectorial_capacity,
    classify_risk,
    vectorised_daily_C,
)


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "exports", "dashboard_data.json")
COMBINED_DIR = os.path.join(DATA_DIR, "combined_datasets")

HISTORICAL_YEARS = 10
FORECAST_YEARS = 5

# Open-Meteo API
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean"


# ---------------------------------------------------------------------------
# PHASE A: DATA INGESTION
# ---------------------------------------------------------------------------

def fetch_historical_climate(lat: float, lon: float, city_name: str) -> pd.DataFrame:
    """Fetch 10 years of daily climate data from Open-Meteo Archive API."""
    end_date = datetime.now() - timedelta(days=5)  # Archive has ~5 day lag
    try:
        start_date = end_date.replace(year=end_date.year - HISTORICAL_YEARS)
    except ValueError:
        start_date = end_date.replace(year=end_date.year - HISTORICAL_YEARS, month=2, day=28)

    print(f"  [Ingest] Fetching {HISTORICAL_YEARS} years daily climate for {city_name}...")

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": DAILY_VARS,
        "timezone": "UTC",
    }

    retries = 3
    for attempt in range(retries):
        try:
            resp = requests.get(ARCHIVE_API, params=params, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            break
        except (requests.RequestException, ValueError) as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
            else:
                raise RuntimeError(f"Failed to fetch data for {city_name}: {e}")

    daily = data["daily"]
    df = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "temperature": daily["temperature_2m_mean"],
        "precipitation": daily["precipitation_sum"],
        "humidity": daily["relative_humidity_2m_mean"],
    })

    # Handle missing values with interpolation
    df = df.set_index("date").asfreq("D")
    df = df.interpolate(method="linear", limit=7).ffill().bfill()
    df = df.reset_index()

    return df


def load_yearly_map_data(city_name: str) -> pd.DataFrame:
    """Load the yearly combined CSV which contains historical Infection Prevalence."""
    safe_name = city_name.split(',')[0].strip()
    filepath = os.path.join(COMBINED_DIR, f"combined_{safe_name}.csv")
    
    if not os.path.exists(filepath):
        print(f"  [Warning] Yearly MAP data not found for {city_name} at {filepath}")
        return pd.DataFrame(columns=["Year", "Infection Prevalence", "Mortality Rate"])
        
    df = pd.read_csv(filepath)
    return df


# ---------------------------------------------------------------------------
# PHASE B: INVERSE ITN ESTIMATION
# ---------------------------------------------------------------------------

def estimate_historical_itn(map_df: pd.DataFrame, anchor_itn: float) -> dict:
    """
    Inversely estimate historical ITN coverage from Infection Prevalence.
    Formula: ITN_year = anchor_itn * ((PR_max - PR_year) / (PR_max - PR_latest))
    If PR_max == PR_latest (no variance), ITN stays constant.
    Returns a dict mapping Year -> ITN Coverage.
    """
    if map_df.empty or "Infection Prevalence" not in map_df.columns:
        return {}
        
    # Drop rows where prevalence is NaN
    valid_df = map_df.dropna(subset=["Infection Prevalence"]).sort_values("Year")
    if valid_df.empty:
        return {}
        
    pr_array = valid_df["Infection Prevalence"].values
    years = valid_df["Year"].values
    
    pr_latest = pr_array[-1]
    pr_max = np.max(pr_array)
    
    itn_map = {}
    for y, pr in zip(years, pr_array):
        if pr_max == pr_latest or pr_max == 0:
            itn = anchor_itn  # No variance or 0 prevalence -> constant ITN
        else:
            # Scale inversely
            itn = anchor_itn * ((pr_max - pr) / (pr_max - pr_latest))
            itn = np.clip(itn, 0.0, 1.0)
        itn_map[int(y)] = float(itn)
        
    return itn_map


# ---------------------------------------------------------------------------
# PHASE C: FEATURE ENGINEERING
# ---------------------------------------------------------------------------

def create_features(df: pd.DataFrame, target_col: str, fill_last_row: bool = False) -> pd.DataFrame:
    """Create time-series features for XGBoost training and prediction.
    
    Args:
        df: DataFrame with 'date' and target_col columns.
        target_col: Name of the target variable column.
        fill_last_row: If True, fill NaN values in the last row with medians
                       (used during iterative forecasting).
    """
    feat = df[["date", target_col]].copy()

    day_of_year = feat["date"].dt.dayofyear
    feat["sin_doy"] = np.sin(2 * np.pi * day_of_year / 365.25)
    feat["cos_doy"] = np.cos(2 * np.pi * day_of_year / 365.25)

    month = feat["date"].dt.month
    feat["sin_month"] = np.sin(2 * np.pi * month / 12)
    feat["cos_month"] = np.cos(2 * np.pi * month / 12)

    min_year = feat["date"].dt.year.min()
    feat["year_trend"] = (feat["date"].dt.year - min_year) / max(1, HISTORICAL_YEARS)

    for lag in [1, 3, 7, 14, 30, 60, 90, 365]:
        feat[f"lag_{lag}"] = feat[target_col].shift(lag)

    for window in [7, 14, 30, 90]:
        feat[f"roll_mean_{window}"] = feat[target_col].rolling(window, min_periods=1).mean()
        feat[f"roll_std_{window}"] = feat[target_col].rolling(window, min_periods=1).std().fillna(0)

    if fill_last_row and feat.iloc[-1:].isna().any(axis=1).iloc[0]:
        for col in feat.columns:
            if feat[col].isna().iloc[-1]:
                median_val = feat[col].dropna().median()
                feat.iloc[-1, feat.columns.get_loc(col)] = median_val if not np.isnan(median_val) else 0

    if not fill_last_row:
        feat = feat.dropna().reset_index(drop=True)

    return feat


# ---------------------------------------------------------------------------
# PHASE D: XGBOOST TRAINING (CLIMATE + ITN)
# ---------------------------------------------------------------------------

def train_xgboost_climate(df: pd.DataFrame, target_col: str, city_name: str):
    feat_df = create_features(df, target_col)

    feature_cols = [c for c in feat_df.columns if c not in ["date", target_col]]
    X = feat_df[feature_cols].values
    y = feat_df[target_col].values

    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    model = XGBRegressor(n_estimators=500, max_depth=6, learning_rate=0.05, 
                         subsample=0.8, colsample_bytree=0.8, min_child_weight=5, 
                         reg_alpha=0.1, reg_lambda=1.0, random_state=42, verbosity=0)

    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    y_pred = model.predict(X_val)
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    print(f"  [Train] {city_name} / {target_col}: MAE={mae:.3f}, R²={r2:.3f}")

    return model, feature_cols, {"mae": round(mae, 4), "r2": round(r2, 4)}


def forecast_climate_iterative(model, feature_cols: list, historical_df: pd.DataFrame, target_col: str, forecast_days: int) -> list:
    """Iteratively forecast daily climate values.
    Pre-allocates the DataFrame to avoid O(n²) pd.concat in a loop.
    """
    last_date = historical_df["date"].iloc[-1]
    
    # Pre-allocate: create all future dates at once
    future_dates = [last_date + timedelta(days=i + 1) for i in range(forecast_days)]
    future_df = pd.DataFrame({"date": future_dates, target_col: np.nan})
    work = pd.concat([historical_df[["date", target_col]], future_df], ignore_index=True)
    
    predictions = []
    hist_len = len(historical_df)

    for day_i in range(forecast_days):
        idx = hist_len + day_i
        # Only pass rows up to and including the current prediction row
        feat_df = create_features(work.iloc[:idx + 1], target_col, fill_last_row=True)
        
        last_feat = feat_df[feature_cols].iloc[-1:].values
        pred_val = float(model.predict(last_feat)[0])

        if target_col == "temperature":
            pred_val = np.clip(pred_val, -50, 55)
        elif target_col == "humidity":
            pred_val = np.clip(pred_val, 0, 100)
        elif target_col == "precipitation":
            pred_val = max(0, pred_val)

        work.iloc[idx, work.columns.get_loc(target_col)] = pred_val
        predictions.append({"date": future_dates[day_i], "value": round(pred_val, 2)})

    return predictions


def train_and_forecast_itn(itn_map: dict, anchor_year: int, forecast_years: int):
    """Simple linear regression on year to forecast ITN coverage (slow variable)."""
    if not itn_map:
        return {}
        
    years = np.array(list(itn_map.keys())).reshape(-1, 1)
    values = np.array(list(itn_map.values()))
    
    # Simple linear fit for the trend
    if len(years) > 1:
        coeffs = np.polyfit(years.flatten(), values, 1)
        trend = np.poly1d(coeffs)
    else:
        constant_val = values[0]
        trend = lambda _: constant_val
        
    forecast_itn = {}
    for i in range(1, forecast_years + 1):
        fy = anchor_year + i
        val = trend(fy)
        forecast_itn[fy] = float(np.clip(val, 0.0, 1.0))
        
    return forecast_itn


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def process_city(city_name: str, city_config: dict) -> dict:
    print(f"\n{'='*60}")
    print(f"Processing: {city_name}")
    print(f"{'='*60}")

    lat = city_config["lat"]
    lon = city_config["lon"]
    map_params = city_config["map_parameters"]
    anchor_itn = map_params["itn_coverage_percentage"]
    baseline_a = map_params["baseline_biting_rate_a"]

    # 1. Fetch daily climate data
    hist_climate = fetch_historical_climate(lat, lon, city_name)
    last_hist_date = hist_climate["date"].iloc[-1]
    anchor_year = last_hist_date.year

    # 2. Load Yearly MAP Data & Estimate ITN
    yearly_map_df = load_yearly_map_data(city_name)
    historical_itn_map = estimate_historical_itn(yearly_map_df, anchor_itn)
    
    # 3. Forecast Future ITN
    future_itn_map = train_and_forecast_itn(historical_itn_map, anchor_year, FORECAST_YEARS)
    
    # Combine ITN maps
    full_itn_map = {**historical_itn_map, **future_itn_map}
    
    def get_itn_for_year(y: int) -> float:
        return full_itn_map.get(y, anchor_itn) # Fallback to anchor if missing

    # 4. Historical Biological Validation (vectorised)
    validation_r = None
    c_df = None
    if not yearly_map_df.empty and "Infection Prevalence" in yearly_map_df.columns:
        print(f"  [Biology] Validating historical model (fast daily weather + locked yearly MAP)...")
        hist_c_yearly = []
        hist_years = []
        
        hist_climate["year"] = hist_climate["date"].dt.year
        for year, group in hist_climate.groupby("year"):
            itn_cov = get_itn_for_year(year)
            # Vectorised computation instead of row-by-row
            c_values = vectorised_daily_C(
                group["temperature"].values,
                group["humidity"].values,
                group["precipitation"].values,
                baseline_a,
                itn_cov,
            )
            hist_c_yearly.append(np.mean(c_values))
            hist_years.append(year)
            
        c_df = pd.DataFrame({"Year": hist_years, "Hist_C": hist_c_yearly})
        val_df = pd.merge(c_df, yearly_map_df, on="Year", how="inner").dropna()
        if len(val_df) > 2:
            validation_r = val_df["Hist_C"].corr(val_df["Infection Prevalence"])
            print(f"  [Validation] Pearson r (C vs Infection Prevalence): {validation_r:.3f}")

    # 5. Train XGBoost Climate Models
    target_cols = ["temperature", "humidity", "precipitation"]
    models, feature_cols_map, metrics = {}, {}, {}

    for col in target_cols:
        model, feat_cols, met = train_xgboost_climate(hist_climate, col, city_name)
        models[col] = model
        feature_cols_map[col] = feat_cols
        metrics[col] = met

    # 6. Forecast 5 Years Climate (leap-year aware)
    try:
        forecast_end = last_hist_date.replace(year=last_hist_date.year + FORECAST_YEARS)
    except ValueError:
        forecast_end = last_hist_date.replace(year=last_hist_date.year + FORECAST_YEARS, month=2, day=28)
    forecast_days = (forecast_end - last_hist_date).days
    forecasts = {}

    for col in target_cols:
        print(f"  [Forecast] Predicting {FORECAST_YEARS}-year {col} for {city_name}...")
        preds = forecast_climate_iterative(models[col], feature_cols_map[col], hist_climate, col, forecast_days)
        forecasts[col] = preds

    # 7. Apply Ross-Macdonald (Daily Weather + Locked Yearly ITN)
    print(f"  [Biology] Computing Future Vectorial Capacity...")
    risk_data = []

    for i in range(forecast_days):
        date_obj = forecasts["temperature"][i]["date"]
        date_str = date_obj.strftime("%Y-%m-%d")
        year = date_obj.year
        
        temp_val = forecasts["temperature"][i]["value"]
        hum_val = forecasts["humidity"][i]["value"]
        prec_val = forecasts["precipitation"][i]["value"]
        
        # LOCKED YEARLY MAP BASELINE
        locked_itn = get_itn_for_year(year)

        vc = calc_vectorial_capacity(temp_val, hum_val, prec_val, baseline_a, locked_itn)

        risk_data.append({
            "date": date_str,
            "temperature": temp_val,
            "humidity": hum_val,
            "precipitation": prec_val,
            "vectorial_capacity": vc["C"],
            "eip": vc["n"],
            "survival_rate": vc["p"],
            "mosquito_density": vc["m"],
            "effective_biting_rate": vc["a_eff"],
            "locked_yearly_itn": round(locked_itn, 4),
            "risk_level": classify_risk(vc["C"]),
        })

    # 8. Train & Forecast Epidemic Risk (Infection Prevalence)
    forecast_prevalence_data = []
    if not yearly_map_df.empty and "Infection Prevalence" in yearly_map_df.columns and c_df is not None:
        print(f"  [Epidemiology] Training XGBoost Disease Regressor & Forecasting True Prevalence...")
        
        try:
            # We need historical yearly climate averages to train the model
            hist_yearly = hist_climate.groupby("year").agg({
                "temperature": "mean", "precipitation": "sum", "humidity": "mean"
            }).reset_index()
            
            # Merge with historical C
            hist_yearly = pd.merge(hist_yearly, c_df, left_on="year", right_on="Year")
            
            # Merge with Infection Prevalence
            hist_yearly = pd.merge(hist_yearly, yearly_map_df[["Year", "Infection Prevalence"]], on="Year").sort_values("Year")
            
            # Create Lag_1
            hist_yearly["Lag_1_Infection_Prevalence"] = hist_yearly["Infection Prevalence"].shift(1)
            train_df = hist_yearly.dropna()
            
            if not train_df.empty:
                features = ["temperature", "precipitation", "humidity", "Hist_C", "Lag_1_Infection_Prevalence"]
                target = "Infection Prevalence"
                
                X_train = train_df[features].values
                y_train = train_df[target].values
                
                disease_model = XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1, random_state=42)
                disease_model.fit(X_train, y_train)
                
                # Forecast recursive 5 years
                risk_df_future = pd.DataFrame(risk_data)
                risk_df_future["year"] = pd.to_datetime(risk_df_future["date"]).dt.year
                future_yearly = risk_df_future.groupby("year").agg({
                    "temperature": "mean", "precipitation": "sum", "humidity": "mean", "vectorial_capacity": "mean"
                }).reset_index()
                
                current_lag = train_df.iloc[-1]["Infection Prevalence"]
                
                for _, row in future_yearly.iterrows():
                    x_input = np.array([
                        row["temperature"],
                        row["precipitation"],
                        row["humidity"],
                        row["vectorial_capacity"],
                        current_lag
                    ]).reshape(1, -1)
                    
                    pred_val = float(disease_model.predict(x_input)[0])
                    pred_val = float(np.clip(pred_val, 0, 100))
                    
                    forecast_prevalence_data.append({
                        "year": int(row["year"]),
                        "prevalence": round(pred_val, 2)
                    })
                    current_lag = pred_val
        except (KeyError, ValueError) as e:
            print(f"  [Warning] Failed to generate epidemic forecast: {e}")
            traceback.print_exc()

    # 9. Summary Statistics
    c_values = [d["vectorial_capacity"] for d in risk_data]
    risk_df = pd.DataFrame(risk_data)
    risk_df["date_parsed"] = pd.to_datetime(risk_df["date"])

    risk_df["year_month"] = risk_df["date_parsed"].dt.to_period("M").astype(str)
    monthly = risk_df.groupby("year_month").agg({
        "temperature": "mean", "humidity": "mean", "precipitation": "mean",
        "vectorial_capacity": "mean", "eip": "mean", "survival_rate": "mean",
        "mosquito_density": "mean",
    }).round(4).reset_index()

    monthly_data = monthly.to_dict(orient="records")
    peak_month_label = max(monthly_data, key=lambda x: x["vectorial_capacity"])["year_month"] if monthly_data else "N/A"

    hist_climate["year_month"] = hist_climate["date"].dt.to_period("M").astype(str)
    hist_monthly = hist_climate.groupby("year_month").agg({
        "temperature": "mean", "humidity": "mean", "precipitation": "mean",
    }).round(2).reset_index()

    summary = {
        "mean_annual_C": round(np.mean(c_values), 4),
        "max_C": round(np.max(c_values), 4),
        "min_C": round(np.min(c_values), 6),
        "peak_risk_month": peak_month_label,
        "overall_risk": classify_risk(np.mean(c_values)),
        "days_high_risk": int(sum(1 for c in c_values if c >= 0.5)),
        "days_critical": int(sum(1 for c in c_values if c >= 1.0)),
        "historical_validation_r": round(validation_r, 3) if validation_r is not None else None
    }

    return {
        "city_name": city_name,
        "lat": lat,
        "lon": lon,
        "map_parameters": map_params,
        "model_metrics": metrics,
        "summary": summary,
        "historical_monthly": hist_monthly.to_dict(orient="records"),
        "forecast_daily": risk_data,
        "forecast_monthly": monthly_data,
        "forecast_prevalence": forecast_prevalence_data,
    }


def main():
    print("=" * 60)
    print("Hybrid AI-Mechanistic Malaria Risk Predictor")
    print("Manav Sanghrajka & Gordon Li — The Woodlands School")
    print("=" * 60)

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    cities = config["cities"]
    print(f"\nLoaded {len(cities)} cities from config.json")
    os.makedirs(DATA_DIR, exist_ok=True)

    results = {}
    for city_name, city_config in cities.items():
        city_result = process_city(city_name, city_config)
        results[city_name] = city_result

    output = {
        "metadata": {
            "title": "Hybrid AI-Mechanistic Malaria Risk Predictor",
            "authors": ["Manav Sanghrajka", "Gordon Li"],
            "institution": "The Woodlands School",
            "generated_at": datetime.now().isoformat(),
            "historical_years": HISTORICAL_YEARS,
            "forecast_years": FORECAST_YEARS,
            "model_type": "XGBoost",
            "framework": "Ross-Macdonald Vectorial Capacity",
        },
        "cities": results,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    file_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"Pipeline complete! Output: {OUTPUT_PATH}")
    print(f"File size: {file_size_mb:.2f} MB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
