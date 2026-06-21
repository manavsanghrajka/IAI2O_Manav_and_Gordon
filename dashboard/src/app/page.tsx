"use client";

import { useState, useCallback, useEffect } from "react";
import { DashboardData } from "@/lib/types";
import CitySelector from "@/components/CitySelector";
import HybridVisualizer from "@/components/HybridVisualizer";
import GovernancePanel from "@/components/GovernancePanel";
import StatsBar from "@/components/StatsBar";
import {
  IconMosquito,
  IconAlert,
  IconRocket,
  IconTarget,
  IconSpinner,
  IconRefresh,
} from "@/components/Icons";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [selectedCity, setSelectedCity] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<string>("");
  const [overrideMonthly, setOverrideMonthly] = useState<Array<{
    year_month: string;
    vectorial_capacity: number;
  }> | null>(null);

  // Load dashboard data
  useEffect(() => {
    loadData();
  }, []);

  // Dynamic document title per city
  useEffect(() => {
    if (selectedCity) {
      document.title = `${selectedCity} | Malaria Risk Predictor`;
    } else {
      document.title = "Malaria Risk Predictor";
    }
  }, [selectedCity]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/data");
      if (!resp.ok) {
        if (resp.status === 404) {
          setError("NO_DATA");
          setLoading(false);
          return;
        }
        throw new Error(`Failed to load data: ${resp.status}`);
      }
      const json: DashboardData = await resp.json();
      setData(json);
      // Auto-select first city
      const cities = Object.keys(json.cities);
      if (cities.length > 0 && !selectedCity) {
        setSelectedCity(cities[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleRunPipeline = async () => {
    setPipelineRunning(true);
    setPipelineStatus("Starting pipeline...");
    try {
      const resp = await fetch("/api/run-pipeline", { method: "POST" });
      const result = await resp.json();
      if (result.success) {
        setPipelineStatus("Pipeline complete! Loading data...");
        await loadData();
        setPipelineStatus("");
      } else {
        setPipelineStatus(`Error: ${result.error}`);
      }
    } catch (err) {
      setPipelineStatus(
        `Error: ${err instanceof Error ? err.message : "Unknown"}`
      );
    } finally {
      setPipelineRunning(false);
    }
  };

  const handleCityChange = useCallback((city: string) => {
    setSelectedCity(city);
    setOverrideMonthly(null); // Reset governance override
  }, []);

  const handleOverrideMonthly = useCallback(
    (
      monthlyData: Array<{
        year_month: string;
        vectorial_capacity: number;
      }> | null
    ) => {
      setOverrideMonthly(monthlyData);
    },
    []
  );

  const currentCity = data?.cities[selectedCity];

  // ============================================
  // NO DATA STATE
  // ============================================
  if (error === "NO_DATA" || (!loading && !data)) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="glass-card p-10 max-w-lg text-center animate-fade-in-up">
          <IconMosquito className="mx-auto text-teal-400/80 mb-6" size={64} />
          <h1 className="text-2xl font-bold bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent mb-3">
            Malaria Risk Predictor
          </h1>
          <p className="text-sm text-[#e2e8f0]/50 mb-6">
            No forecast data found. Run the AI pipeline to generate predictions
            for all study regions.
          </p>
          <button
            onClick={handleRunPipeline}
            disabled={pipelineRunning}
            className={`
              px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-300 cursor-pointer
              ${
                pipelineRunning
                  ? "bg-teal-400/20 text-teal-300/50 cursor-wait"
                  : "bg-gradient-to-r from-teal-500 to-cyan-500 text-white hover:from-teal-400 hover:to-cyan-400 hover:shadow-lg hover:shadow-teal-500/20"
              }
            `}
            id="run-pipeline-btn"
          >
            {pipelineRunning ? (
              <span className="flex items-center gap-2 justify-center">
                <IconSpinner className="h-4 w-4" />
                Running Pipeline...
              </span>
            ) : (
              <span className="flex items-center gap-2 justify-center">
                <IconRocket size={16} />
                Run AI Pipeline
              </span>
            )}
          </button>
          {pipelineStatus && (
            <p className="text-xs text-[#e2e8f0]/40 mt-4 animate-pulse">
              {pipelineStatus}
            </p>
          )}
          <div className="mt-8 text-[10px] text-[#e2e8f0]/20">
            <p>
              Or run manually:{" "}
              <code className="text-teal-400/50">
                docker compose run ai-mechanistic-model
              </code>
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ============================================
  // LOADING STATE
  // ============================================
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center animate-fade-in-up">
          <IconMosquito className="mx-auto text-teal-400/60 mb-4 animate-bounce" size={48} />
          <p className="text-sm text-teal-400/60">Loading forecast data...</p>
        </div>
      </div>
    );
  }

  // ============================================
  // ERROR STATE
  // ============================================
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="glass-card p-8 max-w-md text-center">
          <IconAlert className="mx-auto text-red-400 mb-4" size={40} />
          <h2 className="text-lg font-bold text-red-400 mb-2">Error</h2>
          <p className="text-sm text-[#e2e8f0]/50">{error}</p>
          <button
            onClick={loadData}
            className="mt-4 px-4 py-2 text-xs text-teal-400 border border-teal-400/30 rounded-lg hover:bg-teal-400/10 transition-all cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data || !currentCity) return null;

  // ============================================
  // MAIN DASHBOARD
  // ============================================
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-teal-400/10 bg-[#0a0e1a]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <IconMosquito className="text-teal-400" size={24} />
            <div>
              <h1 className="text-base font-bold bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
                Malaria Risk Predictor
              </h1>
              <p className="text-[10px] text-[#e2e8f0]/30">
                AI-Mechanistic Hybrid Model · {data.metadata.authors.join(" & ")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-[10px] text-[#e2e8f0]/30">
              <span className="px-2 py-1 rounded-md bg-teal-400/10 text-teal-400/60 font-mono">
                {data.metadata.model_type}
              </span>
              <span className="px-2 py-1 rounded-md bg-teal-400/10 text-teal-400/60 font-mono">
                Ross-Macdonald
              </span>
            </div>
            <button
              onClick={handleRunPipeline}
              disabled={pipelineRunning}
              className="px-3 py-1.5 text-[11px] font-medium text-teal-400 border border-teal-400/20 rounded-lg hover:bg-teal-400/10 transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              id="header-run-btn"
            >
              {pipelineRunning ? (
                <>
                  <IconSpinner className="h-3.5 w-3.5" />
                  Running...
                </>
              ) : (
                <>
                  <IconRefresh className="h-3.5 w-3.5" />
                  Re-run Pipeline
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-[1800px] mx-auto w-full px-6 py-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar */}
          <CitySelector
            cities={data.cities}
            selectedCity={selectedCity}
            onSelectCity={handleCityChange}
          />

          {/* Content Area */}
          <div className="flex-1 min-w-0 space-y-6">
            {/* City Title */}
            <div className="animate-fade-in-up">
              <h2 className="text-2xl font-bold text-[#e2e8f0]/90">
                {currentCity.city_name}
              </h2>
              <p className="text-xs text-[#e2e8f0]/40 mt-1">
                {currentCity.lat.toFixed(4)}°
                {currentCity.lat >= 0 ? "N" : "S"},{" "}
                {currentCity.lon.toFixed(4)}°
                {currentCity.lon >= 0 ? "E" : "W"} ·{" "}
                <span className="italic">
                  {currentCity.map_parameters.dominant_vector}
                </span>{" "}
                · {data.metadata.forecast_years}-year forecast
              </p>
            </div>

            {/* Stats Bar */}
            <StatsBar city={currentCity} />

            {/* Hybrid Visualizer */}
            <HybridVisualizer
              forecastMonthly={currentCity.forecast_monthly}
              cityName={currentCity.city_name}
              overrideMonthly={overrideMonthly}
              forecastPrevalence={currentCity.forecast_prevalence}
            />

            {/* Bottom Row: Governance + Model Info */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <div className="xl:col-span-2">
                <GovernancePanel
                  city={currentCity}
                  onOverrideMonthly={handleOverrideMonthly}
                />
              </div>

              {/* Model Performance Card */}
              <div className="glass-card p-5 animate-fade-in-up">
                <h3 className="text-sm font-semibold text-[#e2e8f0]/90 flex items-center gap-2 mb-4">
                  <IconTarget className="text-teal-400" size={16} />
                  XGBoost Model Metrics
                </h3>
                <div className="space-y-3">
                  {Object.entries(currentCity.model_metrics).map(
                    ([variable, metrics]) => (
                      <div
                        key={variable}
                        className="bg-[#131b2e]/60 rounded-xl p-3"
                      >
                        <p className="text-[10px] uppercase tracking-wider text-[#e2e8f0]/40 mb-2">
                          {variable}
                        </p>
                        <div className="flex gap-4">
                          <div>
                            <p className="text-[9px] text-[#e2e8f0]/30">MAE</p>
                            <p className="text-sm font-mono font-bold text-amber-400">
                              {metrics.mae.toFixed(3)}
                            </p>
                          </div>
                          <div>
                            <p className="text-[9px] text-[#e2e8f0]/30">R²</p>
                            <p
                              className={`text-sm font-mono font-bold ${
                                metrics.r2 > 0.8
                                  ? "text-emerald-400"
                                  : metrics.r2 > 0.5
                                  ? "text-amber-400"
                                  : "text-red-400"
                              }`}
                            >
                              {metrics.r2.toFixed(3)}
                            </p>
                          </div>
                          {/* R² quality bar */}
                          <div className="flex-1 flex items-end">
                            <div className="w-full h-1.5 bg-[#0a0e1a] rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                  metrics.r2 > 0.8
                                    ? "bg-emerald-400"
                                    : metrics.r2 > 0.5
                                    ? "bg-amber-400"
                                    : "bg-red-400"
                                }`}
                                style={{ width: `${Math.max(0, metrics.r2 * 100)}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  )}
                </div>

                {/* Framework badge */}
                <div className="mt-4 pt-3 border-t border-teal-400/10">
                  <p className="text-[9px] text-[#e2e8f0]/25 text-center">
                    Ross-Macdonald Vectorial Capacity Framework
                    <br />C = m · a² · p
                    <sup>n</sup> / (-ln p)
                  </p>
                </div>
              </div>
            </div>

            {/* Footer */}
            <footer className="text-center py-6 text-[10px] text-[#e2e8f0]/20">
              <p>
                Hybrid AI-Mechanistic Malaria Risk Predictor ·{" "}
                {data.metadata.authors.join(" & ")} ·{" "}
                {data.metadata.institution}
              </p>
              <p className="mt-1">
                Generated {new Date(data.metadata.generated_at).toLocaleDateString()}{" "}
                · {data.metadata.historical_years}yr training →{" "}
                {data.metadata.forecast_years}yr forecast
              </p>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}
