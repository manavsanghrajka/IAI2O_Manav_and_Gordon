/**
 * TypeScript types for the dashboard_data.json schema.
 */

export interface DashboardData {
  metadata: {
    title: string;
    authors: string[];
    institution: string;
    generated_at: string;
    model_type: string;
    framework: string;
  };
  global_mae: number;
  top_features: Array<{ feature: string; importance: number }>;
  regions: Record<string, RegionData>;
}

export interface RegionData {
  region_name: string;
  data: AnnualDataPoint[];
  mae: number;
}

export interface AnnualDataPoint {
  year: number;
  actual_prevalence: number | null;
  predicted_prevalence: number | null;
  delta: number | null;
  temp: number;
  precip: number;
  itn: number;
  approx_c: number;
}
