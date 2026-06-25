"use client";

import { RegionData } from "@/lib/types";

interface CitySelectorProps {
  cities: Record<string, RegionData>;
  selectedCity: string;
  onSelectCity: (cityName: string) => void;
}

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
            {cityEntries.length} regions
          </p>
        </div>

        <nav className="flex flex-col gap-2 max-h-[80vh] overflow-y-auto pr-2" aria-label="City selection">
          {cityEntries.map(([name, data], index) => {
            const isSelected = name === selectedCity;

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
                style={{ animationDelay: `${Math.min(index * 20, 500)}ms` }}
                aria-current={isSelected ? "true" : undefined}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="min-w-0">
                    <h3 className={`text-sm font-semibold truncate ${isSelected ? "text-teal-300" : "text-[#e2e8f0]/90 group-hover:text-teal-300"} transition-colors`}>
                      {name}
                    </h3>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div>
                    <p className="text-[9px] uppercase tracking-wider text-[#e2e8f0]/30">
                      MAE
                    </p>
                    <p className="text-xs font-mono font-medium text-emerald-400">
                      {data.mae.toFixed(3)}%
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
