import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

SPATIAL_CSV = os.path.join(DATA_DIR, "test_results", "test_results.csv")
TEMPORAL_CSV = os.path.join(DATA_DIR, "test_results", "mongala_temporal_results.csv")

SPATIAL_OUT = os.path.join(os.path.dirname(DATA_DIR), "accuracy_graphs", "spatial_test_graph.png")
TEMPORAL_OUT = os.path.join(os.path.dirname(DATA_DIR), "accuracy_graphs", "temporal_test_graph.png")

# Set global aesthetic style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

def plot_spatial():
    if not os.path.exists(SPATIAL_CSV):
        print(f"File not found: {SPATIAL_CSV}")
        return
        
    df = pd.read_csv(SPATIAL_CSV)
    df = df.sort_values(by="Year")
    
    plt.figure(figsize=(10, 6))
    plt.plot(df["Year"], df["Infection Prevalence"], marker='o', linewidth=2, label="Actual (Ground Truth)", color="#1f77b4")
    plt.plot(df["Year"], df["Predicted_Infection_Prevalence"], marker='x', linewidth=2, linestyle="--", label="Predicted (Spatial Model)", color="#ff7f0e")
    
    plt.title("Spatial Holdout Test: Matabeleland (2000-2023)", fontsize=16, fontweight='bold')
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Infection Prevalence (%)", fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.5)
    plt.tight_layout()
    
    plt.savefig(SPATIAL_OUT, dpi=300)
    print(f"Saved spatial graph to {SPATIAL_OUT}")
    plt.close()

def plot_temporal():
    if not os.path.exists(TEMPORAL_CSV):
        print(f"File not found: {TEMPORAL_CSV}")
        return
        
    df = pd.read_csv(TEMPORAL_CSV)
    df = df.sort_values(by="Year")
    
    plt.figure(figsize=(10, 6))
    
    # Plot entire actual line
    plt.plot(df["Year"], df["Infection Prevalence"], marker='o', linewidth=2, label="Actual (Ground Truth)", color="#2ca02c")
    
    # Plot predicted line
    plt.plot(df["Year"], df["Predicted_Infection_Prevalence"], marker='x', linewidth=2, linestyle="--", label="Predicted (Temporal Model)", color="#d62728")
    
    # Draw vertical line for Train/Test split
    plt.axvline(x=2019.5, color='gray', linestyle=':', linewidth=2, label="Train/Test Split (2019/2020)")
    
    # Shade the test region
    plt.axvspan(2019.5, df["Year"].max(), color='gray', alpha=0.1, label="Holdout Test Set")
    
    plt.title("Temporal Holdout Test: Mongala (2000-2023)", fontsize=16, fontweight='bold')
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Infection Prevalence (%)", fontsize=12)
    plt.legend(fontsize=12, loc='upper right')
    plt.grid(True, alpha=0.5)
    plt.tight_layout()
    
    plt.savefig(TEMPORAL_OUT, dpi=300)
    print(f"Saved temporal graph to {TEMPORAL_OUT}")
    plt.close()

if __name__ == "__main__":
    plot_spatial()
    plot_temporal()
