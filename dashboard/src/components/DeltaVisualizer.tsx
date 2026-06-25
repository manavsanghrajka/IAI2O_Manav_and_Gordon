"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea
} from "recharts";
import { RegionData } from "@/lib/types";

export default function DeltaVisualizer({ region }: { region: RegionData }) {
  if (!region || !region.data) return null;

  // Filter out completely empty years if needed
  const chartData = region.data.filter(d => d.actual_prevalence !== null || d.predicted_prevalence !== null);

  return (
    <div className="glass-card p-6 animate-fade-in-up">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-[#e2e8f0]/90">Actual vs Predicted Prevalence</h3>
          <p className="text-xs text-[#e2e8f0]/50">Year-over-Year Delta Model Validation (2000-2024)</p>
        </div>
      </div>

      <div className="h-[400px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a2540" />
            <XAxis 
              dataKey="year" 
              stroke="#e2e8f0" 
              opacity={0.5} 
              tick={{ fontSize: 12 }} 
            />
            <YAxis 
              stroke="#e2e8f0" 
              opacity={0.5} 
              tick={{ fontSize: 12 }} 
              label={{ value: 'Infection Prevalence (%)', angle: -90, position: 'insideLeft', style: { fill: '#e2e8f0', opacity: 0.5, fontSize: 12 } }}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: "#0a0e1a", border: "1px solid rgba(45, 212, 191, 0.2)", borderRadius: "8px" }}
              itemStyle={{ fontSize: "14px" }}
            />
            <Legend verticalAlign="top" height={36} />
            
            <ReferenceArea x1={2020} x2={2024} strokeOpacity={0.3} fill="#9467bd" fillOpacity={0.1} />

            <Line 
              type="monotone" 
              dataKey="actual_prevalence" 
              name="Actual Prevalence" 
              stroke="#2ca02c" 
              strokeWidth={3} 
              dot={{ r: 4 }} 
              activeDot={{ r: 6 }} 
            />
            <Line 
              type="monotone" 
              dataKey="predicted_prevalence" 
              name="Predicted (Delta Method)" 
              stroke="#9467bd" 
              strokeWidth={3} 
              strokeDasharray="5 5" 
              dot={{ r: 4 }} 
              activeDot={{ r: 6 }} 
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-center mt-4 text-xs text-[#e2e8f0]/40">
        Shaded area represents the Temporal Holdout Test Set (2020-2024).
      </div>
    </div>
  );
}
