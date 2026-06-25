# Hybrid AI-Mechanistic Malaria Risk Predictor

**Authors:** Manav Sanghrajka & Gordon Li

A hybrid epidemiological forecasting system that combines XGBoost climate prediction with Ross-Macdonald vectorial capacity modeling to forecast malaria transmission risk across multiple regions.

## Project Structure

```
├── src/                        # Python ML pipeline
│   ├── main.py                 # Main pipeline (ingest → train → forecast → export)
│   ├── vectorial_capacity.py   # Shared Ross-Macdonald equations
│   ├── config.json             # City configurations & MAP parameters
│   ├── test_accuracy.py        # Spatial holdout validation (Matabeleland)
│   ├── temporal_accuracy_test.py  # Temporal holdout validation (Mongala)
│   └── plot_results.py         # Accuracy visualization
├── dashboard/                  # Next.js interactive dashboard
│   └── src/
│       ├── app/                # Pages & API routes
│       ├── components/         # React components
│       └── lib/                # Shared types & client-side VC calculations
├── data/                       # Data directory
│   ├── combined_datasets/      # Merged climate + disease CSVs per region
│   ├── exports/                # Pipeline output (dashboard_data.json)
│   ├── raw_climate_malaria/    # Source disease data CSVs
│   └── scripts/                # Data preparation scripts
├── accuracy_graphs/            # Validation result visualizations
├── Dockerfile                  # Multi-stage Python container
├── docker-compose.yml          # Docker Compose for pipeline
└── requirements.txt            # Python dependencies
```

## Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Docker** (optional, for containerized pipeline execution)

## Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the AI Pipeline

```bash
python src/main.py
```

This fetches 10 years of climate data, trains XGBoost models, and produces `data/exports/dashboard_data.json`.

### 3. Start the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the interactive dashboard.

### Alternative: Run via Docker

```bash
docker compose run --rm ai-mechanistic-model
```

## How It Works

1. **Climate Ingestion** — Fetches daily temperature, humidity, and precipitation from Open-Meteo Archive API
2. **XGBoost Forecasting** — Trains 3 models per city to iteratively forecast 5 years of daily climate
3. **Ross-Macdonald Model** — Applies mechanistic vectorial capacity equations: `C = m · a² · pⁿ / (-ln p)`
4. **ITN Estimation** — Inversely estimates historical insecticide-treated net coverage from infection prevalence
5. **Epidemic Forecasting** — XGBoost regressor predicts future infection prevalence from climate + VC features
6. **Dashboard** — Next.js app with interactive governance simulator (ITN slider) and multi-view charts

## Accuracy Validation

| Test Type | Region | MAE | Pearson r |
|-----------|--------|-----|-----------|
| Spatial Holdout | Matabeleland, Zimbabwe | — | — |
| Temporal Holdout | Mongala, DRC | 5.9 pp | 0.892 |

See `accuracy_graphs/accuracy_graphs_summary.md` for detailed results.

## License

This project was created for the International Artificial Intelligence Olympiad (IAI2O).
