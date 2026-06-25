"use client";

import { RegionData } from "@/lib/types";
import { IconChart, IconAlert } from "@/components/Icons";

interface StatsBarProps {
  region: RegionData;
}

export default function StatsBar({ region }: StatsBarProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3" id="stats-bar">
      <div className="glass-card px-4 py-3 animate-fade-in-up">
        <div className="flex items-center gap-2 mb-2">
          <IconChart className="text-teal-400/60" size={16} />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[#e2e8f0]/40 truncate">
            Region MAE
          </p>
        </div>
        <p className="text-xl font-bold bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
          {region.mae.toFixed(3)}
        </p>
        <p className="text-[10px] text-[#e2e8f0]/30 mt-1 truncate">
          Absolute Error (%)
        </p>
      </div>

      <div className="glass-card px-4 py-3 animate-fade-in-up" style={{ animationDelay: '60ms' }}>
        <div className="flex items-center gap-2 mb-2">
          <IconAlert className="text-amber-400/60" size={16} />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[#e2e8f0]/40 truncate">
            Years Tracked
          </p>
        </div>
        <p className="text-xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
          {region.data.length}
        </p>
        <p className="text-[10px] text-[#e2e8f0]/30 mt-1 truncate">
          2000-2024
        </p>
      </div>
    </div>
  );
}
