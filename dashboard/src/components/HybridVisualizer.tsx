"use client";

import { useMemo, useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import { MonthlyForecast } from "@/lib/types";
import { IconChart, IconVirus, IconThermometer, IconDroplet, IconCloud } from "@/components/Icons";

interface HybridVisualizerProps {
  forecastMonthly: MonthlyForecast[];
  cityName: string;
  /** Optional override monthly data from ITN slider */
  overrideMonthly?: Array<{
    year_month: string;
    vectorial_capacity: number;
  }> | null;
  forecastPrevalence?: { year: number; prevalence: number }[];
}

type ViewMode = "climate_vc" | "epidemic" | "temperature" | "humidity" | "precipitation";

const VIEW_OPTIONS: { key: ViewMode; label: string; icon: React.ReactNode }[] = [
  { key: "climate_vc", label: "Climate + Risk", icon: <IconChart size={14} /> },
  { key: "epidemic", label: "Epidemic Forecast", icon: <IconVirus size={14} /> },
  { key: "temperature", label: "Temperature", icon: <IconThermometer size={14} /> },
  { key: "humidity", label: "Humidity", icon: <IconDroplet size={14} /> },
  { key: "precipitation", label: "Rainfall", icon: <IconCloud size={14} /> },
];

export default function HybridVisualizer({
  forecastMonthly,
  cityName,
  overrideMonthly,
  forecastPrevalence,
}: HybridVisualizerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("climate_vc");

  const chartData = useMemo(() => {
    return forecastMonthly.map((month) => {
      const override = overrideMonthly?.find(
        (o) => o.year_month === month.year_month
      );
      return {
        ...month,
        // Format month label nicely
        label: formatMonthLabel(month.year_month),
        shortLabel: formatShortLabel(month.year_month),
        // Override VC if governance panel provides one
        vc_override: override ? override.vectorial_capacity : undefined,
        // Original VC for comparison
        vc_original: month.vectorial_capacity,
      };
    });
  }, [forecastMonthly, overrideMonthly]);

  return (
    <div className="glass-card p-5 animate-fade-in-up" id="hybrid-visualizer">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div>
          <h3 className="text-lg font-semibold text-[#e2e8f0]/90">
            Hybrid AI-Mechanistic Forecast
          </h3>
          <p className="text-xs text-[#e2e8f0]/40 mt-0.5">
            {cityName} · {forecastMonthly.length} months · XGBoost →
            Ross-Macdonald
          </p>
        </div>

        {/* View mode toggle */}
        <div className="flex gap-1 p-1 rounded-xl bg-[#131b2e]/80 border border-teal-400/10">
          {VIEW_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setViewMode(opt.key)}
              className={`
                px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer flex items-center gap-1.5
                ${
                  viewMode === opt.key
                    ? "bg-teal-400/15 text-teal-300 border border-teal-400/30"
                    : "text-[#e2e8f0]/40 hover:text-[#e2e8f0]/70 border border-transparent"
                }
              `}
            >
              {opt.icon}
              <span className="hidden sm:inline">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="chart-container">
        <ResponsiveContainer width="100%" height={420}>
          {viewMode === "epidemic" && forecastPrevalence ? (
            <ComposedChart
              data={forecastPrevalence}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="gradPrev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(45, 212, 191, 0.06)" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: "rgba(226, 232, 240, 0.4)", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "rgba(45, 212, 191, 0.1)" }} />
              <YAxis tick={{ fill: "rgba(226, 232, 240, 0.4)", fontSize: 10 }} tickLine={false} axisLine={false} domain={[0, 'auto']} label={{ value: "Infection Prevalence (%)", angle: -90, position: "insideLeft", fill: "rgba(226, 232, 240, 0.3)", fontSize: 10 }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="prevalence" name="Infection Prevalence (%)" stroke="#a855f7" fill="url(#gradPrev)" strokeWidth={3} activeDot={{ r: 6, fill: "#a855f7", stroke: "#fff", strokeWidth: 2 }} />
            </ComposedChart>
          ) : viewMode === "climate_vc" ? (
            <ComposedChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="gradTemp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradHumid" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradVC" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(45, 212, 191, 0.06)"
                vertical={false}
              />
              <XAxis
                dataKey="shortLabel"
                tick={{ fill: "rgba(226, 232, 240, 0.4)", fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: "rgba(45, 212, 191, 0.1)" }}
                interval={2}
              />
              <YAxis
                yAxisId="climate"
                orientation="left"
                tick={{ fill: "rgba(226, 232, 240, 0.4)", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                label={{
                  value: "°C / %",
                  angle: -90,
                  position: "insideLeft",
                  fill: "rgba(226, 232, 240, 0.3)",
                  fontSize: 10,
                }}
              />
              <YAxis
                yAxisId="vc"
                orientation="right"
                tick={{ fill: "rgba(239, 68, 68, 0.6)", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                label={{
                  value: "Vectorial Capacity (C)",
                  angle: 90,
                  position: "insideRight",
                  fill: "rgba(239, 68, 68, 0.4)",
                  fontSize: 10,
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 11, paddingTop: 10 }}
                iconType="plainline"
              />

              {/* Climate areas */}
              <Area
                yAxisId="climate"
                type="monotone"
                dataKey="temperature"
                name="Temperature (°C)"
                stroke="#f97316"
                fill="url(#gradTemp)"
                strokeWidth={1.5}
                dot={false}
              />
              <Area
                yAxisId="climate"
                type="monotone"
                dataKey="humidity"
                name="Humidity (%)"
                stroke="#22d3ee"
                fill="url(#gradHumid)"
                strokeWidth={1.5}
                dot={false}
              />

              {/* Vectorial Capacity line */}
              <Line
                yAxisId="vc"
                type="monotone"
                dataKey="vc_original"
                name="Vectorial Capacity (C)"
                stroke="#ef4444"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5, fill: "#ef4444", stroke: "#fff", strokeWidth: 2 }}
              />

              {/* Override line (from governance panel) */}
              {overrideMonthly && (
                <Line
                  yAxisId="vc"
                  type="monotone"
                  dataKey="vc_override"
                  name="C (Adjusted ITN)"
                  stroke="#10b981"
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  dot={false}
                  activeDot={{ r: 4, fill: "#10b981" }}
                />
              )}

              {/* High risk threshold */}
              <ReferenceLine
                yAxisId="vc"
                y={0.5}
                stroke="rgba(251, 191, 36, 0.4)"
                strokeDasharray="8 4"
                label={{
                  value: "High Risk",
                  fill: "rgba(251, 191, 36, 0.5)",
                  fontSize: 9,
                  position: "right",
                }}
              />
            </ComposedChart>
          ) : (
            <ComposedChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient
                  id="gradSingle"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="5%"
                    stopColor={getSingleColor(viewMode)}
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="95%"
                    stopColor={getSingleColor(viewMode)}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(45, 212, 191, 0.06)"
                vertical={false}
              />
              <XAxis
                dataKey="shortLabel"
                tick={{ fill: "rgba(226, 232, 240, 0.4)", fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: "rgba(45, 212, 191, 0.1)" }}
                interval={2}
              />
              <YAxis
                tick={{ fill: "rgba(226, 232, 240, 0.4)", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                label={{
                  value: getSingleUnit(viewMode),
                  angle: -90,
                  position: "insideLeft",
                  fill: "rgba(226, 232, 240, 0.3)",
                  fontSize: 10,
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey={viewMode}
                name={getSingleLabel(viewMode)}
                stroke={getSingleColor(viewMode)}
                fill="url(#gradSingle)"
                strokeWidth={2}
                dot={false}
                activeDot={{
                  r: 5,
                  fill: getSingleColor(viewMode),
                  stroke: "#fff",
                  strokeWidth: 2,
                }}
              />
            </ComposedChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ============================================
   CUSTOM TOOLTIP
   ============================================ */

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="bg-[#0d1321]/95 border border-teal-400/20 rounded-xl p-3 backdrop-blur-md shadow-2xl min-w-[180px]">
      <p className="text-xs font-semibold text-teal-300 mb-2">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex justify-between gap-4 py-0.5">
          <span className="text-[11px] text-[#e2e8f0]/50 flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{ background: entry.color }}
            />
            {entry.name}
          </span>
          <span className="text-[11px] font-mono font-medium text-[#e2e8f0]/80">
            {typeof entry.value === "number" ? entry.value.toFixed(3) : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ============================================
   HELPERS
   ============================================ */

function formatMonthLabel(ym: string): string {
  const [year, month] = ym.split("-");
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  return `${months[parseInt(month, 10) - 1]} ${year}`;
}

function formatShortLabel(ym: string): string {
  const [year, month] = ym.split("-");
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  return `${months[parseInt(month, 10) - 1]}'${year.slice(2)}`;
}

function getSingleColor(mode: ViewMode): string {
  switch (mode) {
    case "temperature":
      return "#f97316";
    case "humidity":
      return "#22d3ee";
    case "precipitation":
      return "#3b82f6";
    default:
      return "#2dd4bf";
  }
}

function getSingleUnit(mode: ViewMode): string {
  switch (mode) {
    case "temperature":
      return "°C";
    case "humidity":
      return "%";
    case "precipitation":
      return "mm";
    default:
      return "";
  }
}

function getSingleLabel(mode: ViewMode): string {
  switch (mode) {
    case "temperature":
      return "Temperature (°C)";
    case "humidity":
      return "Relative Humidity (%)";
    case "precipitation":
      return "Precipitation (mm)";
    default:
      return "";
  }
}
