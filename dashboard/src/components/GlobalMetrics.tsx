"use client";

import { DashboardData } from "@/lib/types";
import { IconTarget, IconMosquito, IconAlert } from "./Icons";

export default function GlobalMetrics({ data }: { data: DashboardData }) {
  if (!data) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in-up">
      {/* Global Accuracy Card */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-bold text-[#e2e8f0]/90 flex items-center gap-2 mb-4">
          <IconTarget className="text-teal-400" size={20} />
          Global Delta Validation
        </h3>
        <p className="text-sm text-[#e2e8f0]/50 mb-6">
          Evaluated using Temporal Holdout (Trained 2000-2019, Tested 2020-2024).
        </p>
        
        <div className="bg-[#131b2e]/60 rounded-xl p-6 border border-teal-400/10">
          <p className="text-xs uppercase tracking-wider text-[#e2e8f0]/40 mb-2">Overall Test MAE</p>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold font-mono text-emerald-400">{data.global_mae.toFixed(2)}%</span>
            <span className="text-sm text-[#e2e8f0]/30">percentage points</span>
          </div>
          <p className="text-xs text-[#e2e8f0]/40 mt-4">
            The model predicted the year-over-year change in infection prevalence across all global regions with a very low error margin.
          </p>
        </div>
      </div>

      {/* Top Features Card */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-bold text-[#e2e8f0]/90 flex items-center gap-2 mb-4">
          <IconAlert className="text-teal-400" size={20} />
          Top Predictive Features
        </h3>
        <p className="text-sm text-[#e2e8f0]/50 mb-6">
          The most important variables justifying the year-over-year delta.
        </p>

        <div className="space-y-4">
          {data.top_features && data.top_features.length > 0 ? (
            data.top_features.map((feat, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm text-[#e2e8f0]/80">{feat.feature}</span>
                <span className="text-sm font-mono text-amber-400">{feat.importance.toFixed(4)}</span>
              </div>
            ))
          ) : (
            <div className="text-center p-4 bg-[#131b2e]/60 rounded-xl">
              <p className="text-sm text-[#e2e8f0]/40">Run the full pipeline to generate feature importances.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
