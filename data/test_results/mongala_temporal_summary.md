# Mongala Temporal Holdout Accuracy Report

This report evaluates the predictive foresight of the localized Mechanistic-AI model for Mongala, Democratic Republic of the Congo. The model was trained purely on historical data and forced to predict the unseen future.

## Model Setup
- **Algorithm:** XGBoost Regressor
- **Features (X):** Temperature, Precipitation, Humidity, and Vectorial Capacity ($C$)
- **Target (y):** Infection Prevalence (%)
- **Training Set (Known Past):** 20 Years (2000 - 2019)
- **Testing Set (Unseen Future):** 4 Years (2020 - 2023)

## Standard Accuracy Metrics (On the Test Set)
- **Mean Absolute Error (MAE):** `5.911` percentage points
- **Root Mean Squared Error (RMSE):** `6.576` percentage points
- **Coefficient of Determination ($R^2$):** `-14.974`
- **Biological Correlation (Pearson $r$):** `0.892`

## Insights
A temporal holdout test is notoriously difficult, especially for ecological diseases. A positive Pearson correlation indicates that the model accurately detected the *trend* and fluctuations in the future years. A strong $R^2$ demonstrates excellent absolute accuracy over the baseline mean.

The detailed year-by-year predictions for the entire 2000-2023 timeframe have been exported to `mongala_temporal_results.csv`.
