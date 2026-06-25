import os
import pandas as pd
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
RESULTS_FILE = os.path.join(DATA_DIR, "test_results", "pooled_delta_results_full.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "exports", "dashboard_data.json")
MD_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "accuracy_graphs", "pooled_delta_model_summary_full.md")

def main():
    if not os.path.exists(RESULTS_FILE):
        print(f"Error: {RESULTS_FILE} not found. Run pipeline first.")
        return

    df = pd.read_csv(RESULTS_FILE)
    
    test_df = df[df["Year"] >= 2020]
    if len(test_df) > 0:
        global_mae = (test_df["Infection Prevalence"] - test_df["Predicted_Infection_Prevalence"]).abs().mean()
    else:
        global_mae = 0.0

    # Parse top features from Markdown if exists
    top_features = []
    if os.path.exists(MD_FILE):
        with open(MD_FILE, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("- **"):
                    parts = line.split("**:")
                    if len(parts) == 2:
                        top_features.append({
                            "feature": parts[0].replace("- **", "").strip(),
                            "importance": float(parts[1].strip())
                        })

    regions_data = {}
    for name, group in df.groupby("Name"):
        group = group.sort_values("Year")
        annual_data = []
        for _, row in group.iterrows():
            annual_data.append({
                "year": int(row["Year"]),
                "actual_prevalence": round(float(row["Infection Prevalence"]), 2) if pd.notna(row["Infection Prevalence"]) else None,
                "predicted_prevalence": round(float(row["Predicted_Infection_Prevalence"]), 2) if pd.notna(row["Predicted_Infection_Prevalence"]) else None,
                "delta": round(float(row.get("Delta_Infection_Prevalence", 0)), 2) if pd.notna(row.get("Delta_Infection_Prevalence", 0)) else None,
                "temp": round(float(row.get("temperature_2m_mean", 0)), 2),
                "precip": round(float(row.get("precipitation_sum", 0)), 2),
                "itn": round(float(row.get("ITN_Coverage", 0)), 2),
                "approx_c": round(float(row.get("Approx_C", 0)), 2)
            })
            
        region_test = test_df[test_df["Name"] == name]
        mae = 0.0
        if len(region_test) > 0:
            mae = (region_test["Infection Prevalence"] - region_test["Predicted_Infection_Prevalence"]).abs().mean()
            
        regions_data[name] = {
            "region_name": name,
            "data": annual_data,
            "mae": round(mae, 3)
        }

    dashboard_json = {
        "metadata": {
            "title": "Hybrid AI-Mechanistic Malaria Risk Predictor",
            "authors": ["Manav Sanghrajka", "Gordon Li"],
            "institution": "The Woodlands School",
            "generated_at": datetime.now().isoformat(),
            "model_type": "XGBoost Delta Model",
            "framework": "Ross-Macdonald Vectorial Capacity"
        },
        "global_mae": round(global_mae, 3),
        "top_features": top_features,
        "regions": regions_data
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(dashboard_json, f, indent=2)

    print(f"Exported dashboard data to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
