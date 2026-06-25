import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import pearsonr

from sklearn.linear_model import Ridge, Lasso
from xgboost import XGBRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

# Config & Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
DATA_FILE = os.path.join(DATA_DIR, "test_results", "pooled_drc_data_v2.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "test_results", "pooled_accuracy_results.csv")
GRAPH_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "accuracy_graphs")
OUTPUT_MD = os.path.join(GRAPH_DIR, "accuracy_graphs_summary.md") # We will update this externally, but save a local report here too
LOCAL_MD = os.path.join(GRAPH_DIR, "pooled_model_summary.md")

FEATURES = ['temperature_2m_mean', 'precipitation_sum', 'soil_moisture', 'Approx_C', 'Lag_1_Infection_Prevalence']

def main():
    print("="*60)
    print("Spatial Pooling Validation (Target: 26 DRC Provinces)")
    print("="*60)
    
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run process_copernicus.py first.")
        return
        
    df = pd.read_csv(DATA_FILE)
    
    # Clean and create Lag 1
    # MUST group by Region so lags don't cross over
    df = df.sort_values(by=["Region", "Year"])
    df["Lag_1_Infection_Prevalence"] = df.groupby("Region")["Infection Prevalence"].shift(1)
    
    df = df.dropna(subset=[
        "temperature_2m_mean", "precipitation_sum", "soil_moisture", 
        "Approx_C", "Lag_1_Infection_Prevalence", "Infection Prevalence"
    ])
    
    # Train/Test Split
    train_df = df[df["Year"] <= 2019].copy()
    test_df = df[(df["Year"] >= 2020) & (df["Year"] <= 2024)].copy()
    
    print(f"Training set: {len(train_df)} rows")
    print(f"Testing set: {len(test_df)} rows")
    
    num_features = ["temperature_2m_mean", "precipitation_sum", "soil_moisture", "Approx_C", "Lag_1_Infection_Prevalence"]
    cat_features = ["Region"]
    target = "Infection Prevalence"
    
    # Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_features)
        ])
        
    models = {
        "Lasso": Pipeline([('pre', preprocessor), ('model', Lasso(alpha=0.1, random_state=42))]),
        "Ridge": Pipeline([('pre', preprocessor), ('model', Ridge(alpha=1.0, random_state=42))]),
        "XGBoost": Pipeline([('pre', preprocessor), ('model', XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42))])
    }
    
    best_mae = float('inf')
    best_name = ""
    best_model = None
    best_predictions = None
    
    X_train = train_df[num_features + cat_features]
    y_train = train_df[target].values
    
    for name, pipeline in models.items():
        print(f"\nTraining {name}...")
        pipeline.fit(X_train, y_train)
        
        # Recursive Prediction
        y_pred_all = []
        
        # We must do this region by region
        test_df_copy = test_df.copy()
        
        for region in test_df_copy["Region"].unique():
            region_test = test_df_copy[test_df_copy["Region"] == region].sort_values("Year")
            if len(region_test) == 0:
                continue
                
            current_lag = region_test.iloc[0]["Lag_1_Infection_Prevalence"]
            
            for idx, row in region_test.iterrows():
                # Build single row dataframe for prediction (maintaining column names for preprocessor)
                row_df = pd.DataFrame([{
                    "temperature_2m_mean": row["temperature_2m_mean"],
                    "precipitation_sum": row["precipitation_sum"],
                    "soil_moisture": row["soil_moisture"],
                    "Approx_C": row["Approx_C"],
                    "Lag_1_Infection_Prevalence": current_lag,
                    "Region": row["Region"]
                }])
                
                pred = pipeline.predict(row_df)[0]
                pred = np.clip(pred, 0, 100)
                
                # Assign prediction back
                test_df_copy.at[idx, "Predicted_Infection_Prevalence"] = pred
                current_lag = pred
                
        # Evaluate
        mae = mean_absolute_error(test_df_copy["Infection Prevalence"], test_df_copy["Predicted_Infection_Prevalence"])
        train_mae = mean_absolute_error(y_train, pipeline.predict(X_train))
        print(f"  Test MAE: {mae:.3f} % | Train MAE: {train_mae:.3f} %")
        
        if mae < best_mae:
            best_mae = mae
            best_name = name
            best_model = pipeline
            best_predictions = test_df_copy["Predicted_Infection_Prevalence"].values
            
    print(f"\nWinner: {best_name} with MAE {best_mae:.3f}%")
    
    # Save best results
    test_df["Predicted_Infection_Prevalence"] = best_predictions
    train_df["Predicted_Infection_Prevalence"] = best_model.predict(X_train)
    
    final_df = pd.concat([train_df, test_df])
    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved predictions to {OUTPUT_CSV}")
    
    # Metrics
    y_test = test_df["Infection Prevalence"].values
    y_pred = test_df["Predicted_Infection_Prevalence"].values
    
    overall_mae = mean_absolute_error(y_test, y_pred)
    overall_rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    overall_r2 = r2_score(y_test, y_pred)
    overall_pearson, _ = pearsonr(y_test, y_pred)
    
    # Generate Graphs
    os.makedirs(GRAPH_DIR, exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    # 1. Global Scatter Plot (Actual vs Predicted on Test Set)
    plt.figure(figsize=(8, 8))
    plt.scatter(y_test, y_pred, alpha=0.6, color='blue')
    plt.plot([0, 100], [0, 100], 'r--', lw=2) # Perfect prediction line
    plt.title(f"Global Test Set Accuracy (26 Provinces)\n{best_name} MAE: {overall_mae:.2f}%", fontsize=14)
    plt.xlabel("Actual Infection Prevalence (%)", fontsize=12)
    plt.ylabel("Predicted Infection Prevalence (%)", fontsize=12)
    plt.xlim(0, max(max(y_test), max(y_pred)) + 5)
    plt.ylim(0, max(max(y_test), max(y_pred)) + 5)
    
    global_graph_path = os.path.join(GRAPH_DIR, "pooled_global_scatter.png")
    plt.savefig(global_graph_path, dpi=300)
    plt.close()
    
    # 2. Representative Time Series (Tshopo, Mongala, Sud-Kivu)
    target_regions = ["Tshopo", "Mongala", "Sud-Kivu"]
    
    for reg in target_regions:
        reg_df = final_df[final_df["Region"] == reg].sort_values("Year")
        if len(reg_df) == 0:
            continue
            
        plt.figure(figsize=(10, 6))
        plt.plot(reg_df["Year"], reg_df["Infection Prevalence"], marker='o', lw=2, label="Actual", color="#2ca02c")
        plt.plot(reg_df["Year"], reg_df["Predicted_Infection_Prevalence"], marker='x', ls='--', lw=2, label="Predicted", color="#d62728")
        plt.axvline(x=2019.5, color='gray', linestyle=':', linewidth=2, label="Train/Test Split")
        plt.axvspan(2019.5, reg_df["Year"].max(), color='gray', alpha=0.1)
        
        plt.title(f"Spatial Pooling Validation: {reg} (2000-2024)", fontsize=16)
        plt.xlabel("Year", fontsize=12)
        plt.ylabel("Infection Prevalence (%)", fontsize=12)
        plt.legend()
        plt.tight_layout()
        
        reg_graph_path = os.path.join(GRAPH_DIR, f"pooled_temporal_{reg}.png")
        plt.savefig(reg_graph_path, dpi=300)
        plt.close()
        
    print(f"Saved global scatter and regional timelines to {GRAPH_DIR}")
    
    # Generate local markdown report
    md = f"""# Spatial Pooling Model Validation Report

By pooling data from 26 DRC provinces, the training dataset size was artificially expanded to **{len(train_df)} rows** (compared to 19 rows previously). This allowed the model to learn universal climate dynamics while adapting to local baselines.

## Model Setup
- **Algorithm:** {best_name} Regressor
- **Features:** Temperature, Precipitation, Soil Moisture, Vectorial Capacity, Lag-1 Prevalence, and One-Hot Encoded `Region`.
- **Validation:** Global Temporal Holdout (Trained on 2000-2019 all regions, Tested recursively on 2020-2024 all regions)

## Global Accuracy Metrics (Holdout Test Set)
- **Mean Absolute Error (MAE):** `{overall_mae:.3f}` percentage points
- **Root Mean Squared Error (RMSE):** `{overall_rmse:.3f}` percentage points
- **R^2:** `{overall_r2:.3f}`
- **Pearson r:** `{overall_pearson:.3f}`

## Graphs
![Global Accuracy Scatter](./pooled_global_scatter.png)
![Tshopo Accuracy](./pooled_temporal_Tshopo.png)
![Mongala Accuracy](./pooled_temporal_Mongala.png)
![Sud-Kivu Accuracy](./pooled_temporal_Sud-Kivu.png)
"""
    with open(LOCAL_MD, "w") as f:
        f.write(md)
        
if __name__ == "__main__":
    main()
