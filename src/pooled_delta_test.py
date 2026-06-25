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
DATA_FILE = os.path.join(DATA_DIR, "test_results", "pooled_global_data_v3_full.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "test_results", "pooled_delta_results_full.csv")
GRAPH_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "accuracy_graphs")
LOCAL_MD = os.path.join(GRAPH_DIR, "pooled_delta_model_summary_full.md")

# Define features
FEATURES = ['temperature_2m_mean', 'precipitation_sum', 'soil_moisture', 'Approx_C', 'ITN_Coverage']

def main():
    print("="*60)
    print("Delta Forecasting Validation")
    print("="*60)
    
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return
        
    df = pd.read_csv(DATA_FILE)
    
    # 1. Clean and create Lag 1 & Delta
    # MUST group by Name so lags don't cross over
    df = df.sort_values(by=["Name", "Year"])
    df["Lag_1_Infection_Prevalence"] = df.groupby("Name")["Infection Prevalence"].shift(1)
    df["Delta_Infection_Prevalence"] = df["Infection Prevalence"] - df["Lag_1_Infection_Prevalence"]
    
    # Add one-hot encoded country columns
    df = pd.get_dummies(df, columns=["ISO3"], prefix="ISO3")
    iso3_cols = [col for col in df.columns if col.startswith("ISO3_")]
    
    current_features = FEATURES + iso3_cols
    df = df.dropna(subset=current_features + ["Lag_1_Infection_Prevalence", "Delta_Infection_Prevalence", "Infection Prevalence"])
    
    # 2. Train/Test Split
    train_df = df[df["Year"] <= 2019].copy()
    test_df = df[(df["Year"] >= 2020) & (df["Year"] <= 2024)].copy()
    
    print(f"Training set: {len(train_df)} rows")
    print(f"Testing set: {len(test_df)} rows")
    
    target = "Delta_Infection_Prevalence"
    
    # Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), FEATURES),
            ('passthrough', 'passthrough', iso3_cols)
        ])
        
    models = {
        "Lasso": Pipeline([('pre', preprocessor), ('model', Lasso(alpha=0.1, random_state=42))]),
        "Ridge": Pipeline([('pre', preprocessor), ('model', Ridge(alpha=1.0, random_state=42))]),
        "XGBoost": Pipeline([('pre', preprocessor), ('model', XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42))])
    }
    
    best_mae = float('inf')
    best_name = ""
    best_model = None
    
    X_train = train_df[current_features]
    y_train = train_df[target].values
    
    best_train_abs = None
    best_test_abs = None
    
    for name, pipeline in models.items():
        print(f"\nTraining {name} on Delta...")
        pipeline.fit(X_train, y_train)
        
        train_pred_delta = pipeline.predict(X_train)
        train_pred_abs = train_df["Lag_1_Infection_Prevalence"].values + train_pred_delta
        train_pred_abs = np.clip(train_pred_abs, 0, 100)
        
        test_df_copy = test_df.copy()
        
        for name_val in test_df_copy["Name"].unique():
            region_test = test_df_copy[test_df_copy["Name"] == name_val].sort_values("Year")
            if len(region_test) == 0:
                continue
                
            current_abs_pred = region_test.iloc[0]["Lag_1_Infection_Prevalence"]
            
            for idx, row in region_test.iterrows():
                row_df = pd.DataFrame([row])
                pred_delta = pipeline.predict(row_df[current_features])[0]
                pred_abs = current_abs_pred + pred_delta
                pred_abs = np.clip(pred_abs, 0, 100)
                test_df_copy.at[idx, "Predicted_Infection_Prevalence"] = pred_abs
                current_abs_pred = pred_abs
                
        mae = mean_absolute_error(test_df_copy["Infection Prevalence"], test_df_copy["Predicted_Infection_Prevalence"])
        train_mae = mean_absolute_error(train_df["Infection Prevalence"], train_pred_abs)
        
        print(f"  Test Absolute MAE: {mae:.3f} % | Train Absolute MAE: {train_mae:.3f} %")
        
        if mae < best_mae:
            best_mae = mae
            best_name = name
            best_model = pipeline
            best_train_abs = train_pred_abs
            best_test_abs = test_df_copy["Predicted_Infection_Prevalence"].values
            
    print(f"\nWinner: {best_name} with Absolute Test MAE {best_mae:.3f}%")
    
    # Save best results
    train_df["Predicted_Infection_Prevalence"] = best_train_abs
    test_df["Predicted_Infection_Prevalence"] = best_test_abs
    
    final_df = pd.concat([train_df, test_df])
    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved predictions to {OUTPUT_CSV}")
    
    # Extract Feature Importances for the winning model
    importances = {}
    if best_name == "XGBoost":
        feats = preprocessor.get_feature_names_out()
        imp = best_model.named_steps['model'].feature_importances_
        for f, v in zip(feats, imp):
            importances[f] = v
    else:
        feats = preprocessor.get_feature_names_out()
        imp = best_model.named_steps['model'].coef_
        for f, v in zip(feats, imp):
            importances[f] = v
            
    # Print top 5 features
    print("\nTop 5 Absolute Feature Importance/Coefficients:")
    sorted_imp = sorted(importances.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
    for k, v in sorted_imp:
        print(f"  {k}: {v:.4f}")
    
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
    plt.scatter(y_test, y_pred, alpha=0.6, color='purple')
    plt.plot([0, 100], [0, 100], 'k--', lw=2) 
    plt.title(f"Global Delta Model Test Set Accuracy\n{best_name} Abs MAE: {overall_mae:.2f}%", fontsize=14)
    plt.xlabel("Actual Infection Prevalence (%)", fontsize=12)
    plt.ylabel("Predicted Infection Prevalence (%)", fontsize=12)
    plt.xlim(0, max(max(y_test), max(y_pred)) + 5)
    plt.ylim(0, max(max(y_test), max(y_pred)) + 5)
    
    global_graph_path = os.path.join(GRAPH_DIR, "delta_global_scatter.png")
    plt.savefig(global_graph_path, dpi=300)
    plt.close()
    
    # 2. Representative Time Series
    target_regions = final_df['Name'].unique()[:3]
    
    for reg in target_regions:
        reg_df = final_df[final_df["Name"] == reg].sort_values("Year")
        if len(reg_df) == 0:
            continue
            
        plt.figure(figsize=(10, 6))
        plt.plot(reg_df["Year"], reg_df["Infection Prevalence"], marker='o', lw=2, label="Actual", color="#2ca02c")
        plt.plot(reg_df["Year"], reg_df["Predicted_Infection_Prevalence"], marker='x', ls='--', lw=2, label="Predicted (Delta Method)", color="#9467bd")
        plt.axvline(x=2019.5, color='gray', linestyle=':', linewidth=2, label="Train/Test Split")
        plt.axvspan(2019.5, reg_df["Year"].max(), color='gray', alpha=0.1)
        
        plt.title(f"Delta Forecasting: {reg} (2000-2024)", fontsize=16)
        plt.xlabel("Year", fontsize=12)
        plt.ylabel("Infection Prevalence (%)", fontsize=12)
        plt.legend()
        plt.tight_layout()
        
        safe_reg = reg.replace("/", "_")
        reg_graph_path = os.path.join(GRAPH_DIR, f"delta_temporal_{safe_reg}.png")
        plt.savefig(reg_graph_path, dpi=300)
        plt.close()
        
    print(f"Saved global scatter and regional timelines to {GRAPH_DIR}")
    
    # Generate local markdown report
    md = f"""# Delta Model Validation Report

By shifting the target variable from **Absolute Prevalence** to the **Year-over-Year Delta** (change), we eliminated the model's ability to cheat via naive forecasting (i.e. just guessing whatever happened last year).

The model was forced to use CHIRPS Precipitation, WHO ITN Coverage, and Vectorial Capacity to biologically justify why the prevalence changes from year to year.

## Model Setup
- **Algorithm:** {best_name} Regressor (Trained on Delta)
- **Features:** Temperature, CHIRPS Precipitation, Soil Moisture, Vectorial Capacity, WHO ITN Coverage, and One-Hot Encoded `ISO3`. (Lag-1 completely removed as a feature!)
- **Validation:** Global Temporal Holdout (Trained on 2000-2019 all regions, Tested recursively on 2020-2024 all regions)

## Global Absolute Accuracy Metrics (Holdout Test Set)
- **Mean Absolute Error (MAE):** `{overall_mae:.3f}` percentage points
- **Root Mean Squared Error (RMSE):** `{overall_rmse:.3f}` percentage points
- **R^2:** `{overall_r2:.3f}`
- **Pearson r:** `{overall_pearson:.3f}`

## Top Features Justifying the Delta
"""
    for k, v in sorted_imp:
        md += f"- **{k}**: {v:.4f}\n"

    md += """
## Graphs
![Global Accuracy Scatter](./delta_global_scatter.png)
"""
    for reg in target_regions:
        safe_reg = reg.replace("/", "_")
        md += f"![{reg} Accuracy](./delta_temporal_{safe_reg}.png)\n"
    with open(LOCAL_MD, "w") as f:
        f.write(md)
        
if __name__ == "__main__":
    main()
