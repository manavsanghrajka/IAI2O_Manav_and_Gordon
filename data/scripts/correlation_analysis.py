"""
Correlation Matrix: Annual Average Climate Features vs Malaria Metrics
======================================================================
Authors: Manav Sanghrajka & Gordon Li, The Woodlands School

Generates:
  1. Pooled correlation matrices (all regions) — CSV + heatmap PNG
  2. Per-region correlation matrices — CSV + heatmap PNG
  
For each of 3 malaria metrics:
  - Incidence Rate (Cases per Thousand)
  - Infection Prevalence (per 100 Children)
  - Mortality Rate (Deaths per 100 Thousand)

Climate features from Annual_Average_Climate_Per_Region.csv:
  - temperature_2m_mean, precipitation_sum, rain_sum, snowfall_sum,
    relative_humidity_2m_mean, surface_pressure_mean, soil_moisture_mean,
    soil_temperature_mean
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CLIMATE_CSV = os.path.join(DATA_DIR, "Annual_Average_Climate_Per_Region.csv")
OUTPUT_DIR = os.path.join(DATA_DIR, "correlation_output")

CITY_FILES = {
    "Beni, DRC": os.path.join(DATA_DIR, "Beni.csv"),
    "Delhi, India": os.path.join(DATA_DIR, "Delhi.csv"),
    "Heilongjiang, China": os.path.join(DATA_DIR, "Heilongjiang.csv"),
    "Nairobi, Kenya": os.path.join(DATA_DIR, "Nairobi.csv"),
    "Zinder, Niger": os.path.join(DATA_DIR, "Zinder.csv"),
}

METRICS = [
    "Incidence Rate",
    "Infection Prevalence",
    "Mortality Rate",
]

CLIMATE_FEATURES = [
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "relative_humidity_2m_mean",
    "surface_pressure_mean",
    "soil_moisture_mean",
    "soil_temperature_mean",
]

# Shortened labels for heatmap readability
FEATURE_SHORT = {
    "temperature_2m_mean": "Temp (2m)",
    "precipitation_sum": "Precipitation",
    "rain_sum": "Rain",
    "snowfall_sum": "Snowfall",
    "relative_humidity_2m_mean": "Rel. Humidity",
    "surface_pressure_mean": "Surface Pressure",
    "soil_moisture_mean": "Soil Moisture",
    "soil_temperature_mean": "Soil Temp",
}


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_climate_data() -> pd.DataFrame:
    """Load and clean the annual average climate data."""
    df = pd.read_csv(CLIMATE_CSV)
    # Exclude 2024 (incomplete/anomalous data)
    df = df[df["Year"] < 2024].copy()
    # Standardize region names to match city files
    df["Region"] = df["Region"].str.strip()
    print(f"Loaded climate data: {len(df)} rows, years {df['Year'].min()}-{df['Year'].max()}")
    return df


def load_incidence_data() -> pd.DataFrame:
    """Load and merge all city incidence/prevalence/mortality CSVs.
    
    Maps local region names from city CSVs to the standardized Region names
    used in the climate CSV.
    """
    all_dfs = []

    for region_key, filepath in CITY_FILES.items():
        if not os.path.exists(filepath):
            print(f"  Warning: {filepath} not found, skipping.")
            continue

        df = pd.read_csv(filepath)
        # Exclude 2024
        df = df[df["Year"] < 2024].copy()

        # Pivot: one row per year with columns for each metric
        pivoted = df.pivot_table(
            index="Year", columns="Metric", values="Value", aggfunc="first"
        ).reset_index()
        pivoted["Region"] = region_key  # Use the standardized region key
        all_dfs.append(pivoted)

    if not all_dfs:
        raise RuntimeError("No incidence data loaded!")

    combined = pd.concat(all_dfs, ignore_index=True)

    # Ensure metric columns exist
    for metric in METRICS:
        if metric not in combined.columns:
            combined[metric] = np.nan

    print(f"Loaded incidence data: {len(combined)} rows across {combined['Region'].nunique()} regions")
    return combined


def merge_data(climate_df: pd.DataFrame, incidence_df: pd.DataFrame) -> pd.DataFrame:
    """Merge climate and incidence data on Year + Region."""
    # Map climate region names to match incidence region keys
    region_map = {
        "Beni, DRC": "Beni, DRC",
        "Delhi, India": "Delhi, India",
        "Heilongjiang, China": "Heilongjiang, China",
        "Nairobi, Kenya": "Nairobi, Kenya",
        "Zinder, Niger": "Zinder, Niger",
    }

    # Ensure matching
    climate_df = climate_df.copy()
    incidence_df = incidence_df.copy()

    merged = climate_df.merge(
        incidence_df,
        on=["Year", "Region"],
        how="inner",
    )

    print(f"Merged dataset: {len(merged)} rows, {merged['Region'].nunique()} regions")
    return merged


# ---------------------------------------------------------------------------
# CORRELATION COMPUTATION
# ---------------------------------------------------------------------------

def compute_correlation(df: pd.DataFrame, metric: str) -> pd.Series:
    """Compute Pearson correlation of each climate feature with a metric."""
    correlations = {}
    for feat in CLIMATE_FEATURES:
        if feat in df.columns and metric in df.columns:
            valid = df[[feat, metric]].dropna()
            if len(valid) >= 3:
                correlations[feat] = valid[feat].corr(valid[metric])
            else:
                correlations[feat] = np.nan
        else:
            correlations[feat] = np.nan
    return pd.Series(correlations)


# ---------------------------------------------------------------------------
# HEATMAP PLOTTING
# ---------------------------------------------------------------------------

def plot_heatmap(
    corr_matrix: pd.DataFrame,
    title: str,
    output_path: str,
    figsize: tuple = (12, 6),
):
    """Generate a publication-quality correlation heatmap."""
    fig, ax = plt.subplots(figsize=figsize)

    # Dark theme
    fig.patch.set_facecolor("#0a0e1a")
    ax.set_facecolor("#0a0e1a")

    # Custom diverging colormap: Red (negative) → Dark (zero) → Teal (positive)
    colors_list = ["#ef4444", "#dc2626", "#1a2540", "#14b8a6", "#2dd4bf"]
    cmap = mcolors.LinearSegmentedColormap.from_list("epi_diverge", colors_list, N=256)

    n_rows, n_cols = corr_matrix.shape
    im = ax.imshow(corr_matrix.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")

    # Axis labels
    short_cols = [FEATURE_SHORT.get(c, c) for c in corr_matrix.columns]
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(short_cols, rotation=45, ha="right", fontsize=9, color="#e2e8f0")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(corr_matrix.index, fontsize=9, color="#e2e8f0")

    # Annotate cells with correlation values
    for i in range(n_rows):
        for j in range(n_cols):
            val = corr_matrix.iloc[i, j]
            if np.isnan(val):
                text = "—"
                color = "#555"
            else:
                text = f"{val:.2f}"
                color = "#0a0e1a" if abs(val) > 0.5 else "#e2e8f0"
            ax.text(j, i, text, ha="center", va="center", fontsize=8,
                    fontweight="bold" if abs(val) > 0.5 else "normal", color=color)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("Pearson r", color="#e2e8f0", fontsize=10)
    cbar.ax.yaxis.set_tick_params(color="#e2e8f0")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#e2e8f0", fontsize=8)

    # Title
    ax.set_title(title, fontsize=13, fontweight="bold", color="#2dd4bf", pad=15)

    # Grid lines
    ax.set_xticks([x - 0.5 for x in range(1, n_cols)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, n_rows)], minor=True)
    ax.grid(which="minor", color="#1a2540", linewidth=0.5)
    ax.tick_params(which="minor", size=0)

    # Remove outer spines
    for spine in ax.spines.values():
        spine.set_color("#1a2540")

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, facecolor="#0a0e1a", bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Correlation Analysis: Climate Features vs Malaria Metrics")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load data
    climate_df = load_climate_data()
    incidence_df = load_incidence_data()
    merged_df = merge_data(climate_df, incidence_df)

    # =====================
    # 1. POOLED MATRICES
    # =====================
    print("\n--- Pooled Correlation (All Regions) ---")

    for metric in METRICS:
        metric_safe = metric.replace(" ", "_").lower()
        corr_series = compute_correlation(merged_df, metric)

        # Build matrix: single row for pooled
        corr_matrix = pd.DataFrame(
            [corr_series.values],
            index=["All Regions (Pooled)"],
            columns=corr_series.index,
        )

        # Also compute per-region rows for the combined view
        rows = [corr_series.values]
        row_labels = ["All Regions (Pooled)"]

        for region in sorted(merged_df["Region"].unique()):
            region_df = merged_df[merged_df["Region"] == region]
            r_corr = compute_correlation(region_df, metric)
            rows.append(r_corr.values)
            row_labels.append(region)

        combined_matrix = pd.DataFrame(rows, index=row_labels, columns=CLIMATE_FEATURES)

        # Save CSV
        csv_path = os.path.join(OUTPUT_DIR, f"correlation_{metric_safe}_all.csv")
        combined_matrix.to_csv(csv_path, float_format="%.4f")
        print(f"  CSV: {csv_path}")

        # Plot heatmap
        png_path = os.path.join(OUTPUT_DIR, f"correlation_{metric_safe}_all.png")
        plot_heatmap(
            combined_matrix,
            f"Climate Features vs {metric}\n(Pearson Correlation · 2001–2023)",
            png_path,
            figsize=(13, 5 + len(row_labels) * 0.3),
        )

        # Print to console
        print(f"\n  {metric}:")
        print(combined_matrix.round(3).to_string())
        print()

    # ============================
    # 2. PER-REGION MATRICES
    # ============================
    print("\n--- Per-Region Correlation Matrices ---")

    for region in sorted(merged_df["Region"].unique()):
        region_df = merged_df[merged_df["Region"] == region]
        region_safe = region.split(",")[0].strip().lower()

        rows = []
        row_labels = []
        for metric in METRICS:
            corr = compute_correlation(region_df, metric)
            rows.append(corr.values)
            row_labels.append(metric)

        region_matrix = pd.DataFrame(rows, index=row_labels, columns=CLIMATE_FEATURES)

        # Save CSV
        csv_path = os.path.join(OUTPUT_DIR, f"correlation_{region_safe}_per_metric.csv")
        region_matrix.to_csv(csv_path, float_format="%.4f")

        # Plot heatmap
        png_path = os.path.join(OUTPUT_DIR, f"correlation_{region_safe}_per_metric.png")
        plot_heatmap(
            region_matrix,
            f"{region}\nClimate Features vs Malaria Metrics (r · 2001–2023)",
            png_path,
            figsize=(12, 4),
        )

        print(f"\n  {region}:")
        print(region_matrix.round(3).to_string())
        print()

    print("=" * 60)
    print(f"All outputs saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
