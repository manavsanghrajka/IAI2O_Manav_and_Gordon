/**
 * TypeScript types for the dashboard_data.json schema.
 */

export interface DashboardData {
  metadata: {
    title: string;
    authors: string[];
    institution: string;
    generated_at: string;
    historical_years: number;
    forecast_years: number;
    model_type: string;
    framework: string;
  };
  cities: Record<string, CityData>;
}

export interface CityData {
  city_name: string;
  lat: number;
  lon: number;
  map_parameters: MapParameters;
  model_metrics: Record<string, { mae: number; r2: number }>;
  summary: CitySummary;
  historical_monthly: MonthlyClimate[];
  forecast_daily: DailyForecast[];
  forecast_monthly: MonthlyForecast[];
  forecast_prevalence?: { year: number; prevalence: number }[];
}

export interface MapParameters {
  dominant_vector: string;
  baseline_biting_rate_a: number;
  itn_coverage_percentage: number;
}

export interface CitySummary {
  mean_annual_C: number;
  max_C: number;
  min_C: number;
  peak_risk_month: string;
  overall_risk: string;
  days_high_risk: number;
  days_critical: number;
  historical_validation_r?: number | null;
}

export interface MonthlyClimate {
  year_month: string;
  temperature: number;
  humidity: number;
  precipitation: number;
}

export interface DailyForecast {
  date: string;
  temperature: number;
  humidity: number;
  precipitation: number;
  vectorial_capacity: number;
  eip: number;
  survival_rate: number;
  mosquito_density: number;
  effective_biting_rate: number;
  locked_yearly_itn?: number;
  risk_level: string;
}

export interface MonthlyForecast {
  year_month: string;
  temperature: number;
  humidity: number;
  precipitation: number;
  vectorial_capacity: number;
  eip: number;
  survival_rate: number;
  mosquito_density: number;
}
