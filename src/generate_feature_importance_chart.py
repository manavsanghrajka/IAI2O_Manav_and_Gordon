import json
import matplotlib.pyplot as plt
import seaborn as sns
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "exports", "dashboard_data.json")
OUTPUT_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "accuracy_graphs", "feature_importance_publication.png")

def main():
    if not os.path.exists(JSON_FILE):
        print(f"Error: {JSON_FILE} not found.")
        return

    with open(JSON_FILE, "r") as f:
        data = json.load(f)

    features = data.get("top_features", [])
    if not features:
        print("No top features found in JSON.")
        return

    # Sort features by absolute importance
    features = sorted(features, key=lambda x: abs(x["importance"]), reverse=True)[:15] # top 15
    
    names = [f["feature"].replace("num__", "").replace("passthrough__ISO3_", "Country: ") for f in features]
    importances = [f["importance"] for f in features]

    # Use a clean, modern style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create a horizontal bar chart
    bars = ax.barh(names, importances, color="#4c72b0", edgecolor="none")
    
    ax.invert_yaxis()  # Labels read top-to-bottom
    ax.set_xlabel("Feature Importance (Model Weight)", fontsize=12, fontweight='bold')
    ax.set_title("Top Predictive Features for Malaria Delta Infection Prevalence", fontsize=14, fontweight='bold', pad=15)
    
    # Add values on the bars
    for bar in bars:
        width = bar.get_width()
        # Position label based on whether it's positive or negative
        x_offset = 0.05 * max(abs(min(importances)), max(importances))
        if width >= 0:
            label_x_pos = width + x_offset
            ha = 'left'
        else:
            label_x_pos = width - x_offset
            ha = 'right'
        
        ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.3f}', 
                va='center', ha=ha, fontsize=10, color='black')

    # Add a vertical line at 0
    ax.axvline(0, color='black', linewidth=1, linestyle='--')

    plt.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Saved feature importance chart to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
