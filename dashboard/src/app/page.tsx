"use client";

import { useState, useCallback, useEffect } from "react";
import { DashboardData } from "@/lib/types";
import CitySelector from "@/components/CitySelector";
import DeltaVisualizer from "@/components/DeltaVisualizer";
import GlobalMetrics from "@/components/GlobalMetrics";
import StatsBar from "@/components/StatsBar";
import {
  IconMosquito,
  IconAlert,
  IconRocket,
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

  useEffect(() => {
    loadData();
  }, []);

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
      const cities = Object.keys(json.regions);
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
  }, []);

  const currentCity = data?.regions[selectedCity];

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
            className="px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-300 cursor-pointer bg-gradient-to-r from-teal-500 to-cyan-500 text-white hover:from-teal-400 hover:to-cyan-400"
          >
            {pipelineRunning ? "Running Pipeline..." : "Run AI Pipeline"}
          </button>
        </div>
      </div>
    );
  }

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

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="glass-card p-8 max-w-md text-center">
          <IconAlert className="mx-auto text-red-400 mb-4" size={40} />
          <h2 className="text-lg font-bold text-red-400 mb-2">Error</h2>
          <p className="text-sm text-[#e2e8f0]/50">{error}</p>
          <button onClick={loadData} className="mt-4 px-4 py-2 text-xs text-teal-400 border border-teal-400/30 rounded-lg hover:bg-teal-400/10 transition-all cursor-pointer">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data || !currentCity) return null;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-teal-400/10 bg-[#0a0e1a]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <IconMosquito className="text-teal-400" size={24} />
            <div>
              <h1 className="text-base font-bold bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
                Malaria Risk Predictor
              </h1>
              <p className="text-[10px] text-[#e2e8f0]/30">
                {data.metadata.model_type} · {data.metadata.authors.join(" & ")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleRunPipeline}
              disabled={pipelineRunning}
              className="px-3 py-1.5 text-[11px] font-medium text-teal-400 border border-teal-400/20 rounded-lg hover:bg-teal-400/10 cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
            >
              {pipelineRunning ? <><IconSpinner className="h-3.5 w-3.5" />Running...</> : <><IconRefresh className="h-3.5 w-3.5" />Re-run Pipeline</>}
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-[1800px] mx-auto w-full px-6 py-6">
        <GlobalMetrics data={data} />
        
        <div className="flex flex-col lg:flex-row gap-6 mt-6">
          <CitySelector
            cities={data.regions}
            selectedCity={selectedCity}
            onSelectCity={handleCityChange}
          />

          <div className="flex-1 min-w-0 space-y-6">
            <div className="animate-fade-in-up">
              <h2 className="text-2xl font-bold text-[#e2e8f0]/90">
                {currentCity.region_name}
              </h2>
            </div>

            <StatsBar region={currentCity} />
            <DeltaVisualizer region={currentCity} />

          </div>
        </div>
      </main>
    </div>
  );
}
