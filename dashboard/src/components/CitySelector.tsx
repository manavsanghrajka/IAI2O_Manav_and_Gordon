"use client";

import { CityData } from "@/lib/types";

interface CitySelectorProps {
  cities: Record<string, CityData>;
  selectedCity: string;
  onSelectCity: (cityName: string) => void;
}

const RISK_COLORS: Record<string, string> = {
  Negligible: "risk-negligible",
  Low: "risk-low",
  Moderate: "risk-moderate",
  High: "risk-high",
  Critical: "risk-critical",
};

export default function CitySelector({
  cities,
  selectedCity,
  onSelectCity,
}: CitySelectorProps) {
  const cityEntries = Object.entries(cities);

  return (
    <aside className="w-full lg:w-72 xl:w-80 shrink-0" id="city-selector">
      <div className="sticky top-6">
        <div className="mb-4 px-1">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-teal-400/70 mb-1">
            Study Regions
          </h2>
          <p className="text-[11px] text-[#e2e8f0]/40">
            {cityEntries.length} cities · MAP-seeded parameters
          </p>
        </div>

        <nav className="flex flex-col gap-2" aria-label="City selection">
          {cityEntries.map(([name, data], index) => {
            const isSelected = name === selectedCity;
            const riskClass = RISK_COLORS[data.summary.overall_risk] || "risk-low";

            return (
              <button
                key={name}
                id={`city-btn-${index}`}
                onClick={() => onSelectCity(name)}
                className={`
                  group glass-card text-left px-4 py-3 cursor-pointer
                  animate-fade-in-up transition-all duration-300
                  ${
                    isSelected
                      ? "!border-teal-400/50 !bg-teal-400/5 ring-1 ring-teal-400/20"
                      : "hover:!border-teal-400/20"
                  }
                `}
                style={{ animationDelay: `${index * 80}ms` }}
                aria-current={isSelected ? "true" : undefined}
              >
                {/* City name & vector */}
                <div className="flex items-start justify-between mb-2">
                  <div className="min-w-0">
                    <h3 className={`text-sm font-semibold truncate ${isSelected ? "text-teal-300" : "text-[#e2e8f0]/90 group-hover:text-teal-300"} transition-colors`}>
                      {name}
                    </h3>
                    <p className="text-[10px] text-[#e2e8f0]/40 mt-0.5 italic truncate">
                      {data.map_parameters.dominant_vector}
                    </p>
                  </div>
                  <span className={`risk-badge ${riskClass} shrink-0 ml-2`}>
                    {data.summary.overall_risk}
                  </span>
                </div>

                {/* Mini stats */}
                <div className="grid grid-cols-3 gap-2 mt-2">
                  <div>
                    <p className="text-[9px] uppercase tracking-wider text-[#e2e8f0]/30">
                      Mean C
                    </p>
                    <p className="text-xs font-mono font-medium text-[#e2e8f0]/70">
                      {data.summary.mean_annual_C.toFixed(3)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[9px] uppercase tracking-wider text-[#e2e8f0]/30">
                      Peak
                    </p>
                    <p className="text-xs font-mono font-medium text-[#e2e8f0]/70">
                      {data.summary.max_C.toFixed(3)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[9px] uppercase tracking-wider text-[#e2e8f0]/30">
                      ITN
                    </p>
                    <p className="text-xs font-mono font-medium text-[#e2e8f0]/70">
                      {(data.map_parameters.itn_coverage_percentage * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                {/* Coordinates */}
                <p className="text-[9px] text-[#e2e8f0]/25 mt-2 font-mono">
                  {data.lat.toFixed(4)}°{data.lat >= 0 ? "N" : "S"},{" "}
                  {data.lon.toFixed(4)}°{data.lon >= 0 ? "E" : "W"}
                </p>
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
