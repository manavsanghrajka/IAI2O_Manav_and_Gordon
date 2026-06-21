"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { CityData } from "@/lib/types";
import {
  recalculateWithITN,
  aggregateMonthly,
  classifyRisk,
} from "@/lib/vectorial-capacity";
import { IconShield } from "@/components/Icons";

interface GovernancePanelProps {
  city: CityData;
  onOverrideMonthly: (
    data: Array<{ year_month: string; vectorial_capacity: number }> | null
  ) => void;
}

export default function GovernancePanel({
  city,
  onOverrideMonthly,
}: GovernancePanelProps) {
  const originalITN = city.map_parameters.itn_coverage_percentage;
  const [sliderValue, setSliderValue] = useState(originalITN * 100);
  const [isAdjusted, setIsAdjusted] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset when city changes
  useEffect(() => {
    setSliderValue(originalITN * 100);
    setIsAdjusted(false);
    onOverrideMonthly(null);
  }, [city.city_name, originalITN, onOverrideMonthly]);

  // Compute preview stats (client-side, instant)
  const previewStats = useMemo(() => {
    const newCoverage = sliderValue / 100;
    if (Math.abs(newCoverage - originalITN) < 0.001) return null;

    const recalculated = recalculateWithITN(
      city.forecast_daily,
      city.map_parameters.baseline_biting_rate_a,
      newCoverage
    );

    const newMeanC =
      recalculated.reduce((sum, d) => sum + d.vectorial_capacity, 0) /
      recalculated.length;
    const originalMeanC = city.summary.mean_annual_C;
    const reduction =
      originalMeanC > 0
        ? ((originalMeanC - newMeanC) / originalMeanC) * 100
        : 0;

    const newHighRiskDays = recalculated.filter(
      (d) => d.vectorial_capacity >= 0.5
    ).length;
    const newCriticalDays = recalculated.filter(
      (d) => d.vectorial_capacity >= 1.0
    ).length;

    return {
      newMeanC,
      reduction,
      newRiskLevel: classifyRisk(newMeanC),
      newHighRiskDays,
      newCriticalDays,
      originalMeanC,
    };
  }, [sliderValue, city, originalITN]);

  // Handle slider drag — debounced recalculation for performance
  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseFloat(e.target.value);
      setSliderValue(val);
      setIsAdjusted(Math.abs(val / 100 - originalITN) > 0.001);

      // Debounce the expensive recalculation (~50ms for smooth feel)
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => {
        const newCoverage = val / 100;
        const recalculated = recalculateWithITN(
          city.forecast_daily,
          city.map_parameters.baseline_biting_rate_a,
          newCoverage
        );

        const dailyWithClimate = city.forecast_daily.map((d, i) => ({
          ...d,
          vectorial_capacity: recalculated[i].vectorial_capacity,
        }));
        const monthly = aggregateMonthly(dailyWithClimate);
        onOverrideMonthly(monthly);
      }, 50);
    },
    [city, originalITN, onOverrideMonthly]
  );

  // Reset to original — clears debounce timer to prevent stale updates
  const handleReset = useCallback(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    setSliderValue(originalITN * 100);
    setIsAdjusted(false);
    onOverrideMonthly(null);
  }, [originalITN, onOverrideMonthly]);

  const RISK_COLORS: Record<string, string> = {
    Negligible: "text-emerald-400",
    Low: "text-emerald-300",
    Moderate: "text-amber-400",
    High: "text-orange-400",
    Critical: "text-red-400",
  };

  return (
    <div className="glass-card p-5 animate-fade-in-up" id="governance-panel">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[#e2e8f0]/90 flex items-center gap-2">
            <IconShield className="text-teal-400/70" size={16} />
            Governance Intervention Panel
          </h3>
          <p className="text-[10px] text-[#e2e8f0]/40 mt-0.5">
            Simulate ITN (bed net) coverage changes
          </p>
        </div>
        {isAdjusted && (
          <button
            onClick={handleReset}
            className="text-[10px] font-medium text-teal-400 hover:text-teal-300 px-3 py-1 rounded-full border border-teal-400/20 hover:border-teal-400/40 transition-all cursor-pointer"
          >
            Reset
          </button>
        )}
      </div>

      {/* Slider */}
      <div className="mb-5">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-[#e2e8f0]/50">ITN Coverage</span>
          <span className="text-lg font-bold font-mono text-teal-300">
            {sliderValue.toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          value={sliderValue}
          onChange={handleSliderChange}
          className="itn-slider"
          aria-label="ITN Coverage Percentage"
          id="itn-slider"
        />
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-red-400/60">0% (No nets)</span>
          <span className="text-[9px] text-[#e2e8f0]/30">
            Baseline: {(originalITN * 100).toFixed(0)}%
          </span>
          <span className="text-[9px] text-emerald-400/60">100% (Full)</span>
        </div>
      </div>

      {/* Impact Preview */}
      {previewStats && (
        <div className="space-y-3 pt-3 border-t border-teal-400/10">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[#e2e8f0]/30">
            Projected Impact
          </p>

          <div className="grid grid-cols-2 gap-3">
            {/* Risk Reduction */}
            <div className="bg-[#131b2e]/60 rounded-xl p-3">
              <p className="text-[9px] text-[#e2e8f0]/40 mb-1">
                Risk Reduction
              </p>
              <p
                className={`text-xl font-bold ${
                  previewStats.reduction > 0
                    ? "text-emerald-400"
                    : "text-red-400"
                }`}
              >
                {previewStats.reduction > 0 ? "↓" : "↑"}
                {Math.abs(previewStats.reduction).toFixed(1)}%
              </p>
            </div>

            {/* New Risk Level */}
            <div className="bg-[#131b2e]/60 rounded-xl p-3">
              <p className="text-[9px] text-[#e2e8f0]/40 mb-1">New Risk Level</p>
              <p
                className={`text-xl font-bold ${
                  RISK_COLORS[previewStats.newRiskLevel] || "text-[#e2e8f0]"
                }`}
              >
                {previewStats.newRiskLevel}
              </p>
            </div>

            {/* New Mean C */}
            <div className="bg-[#131b2e]/60 rounded-xl p-3">
              <p className="text-[9px] text-[#e2e8f0]/40 mb-1">
                Adjusted Mean C
              </p>
              <p className="text-sm font-mono font-bold text-[#e2e8f0]/80">
                {previewStats.newMeanC.toFixed(4)}
              </p>
              <p className="text-[9px] text-[#e2e8f0]/30 mt-0.5">
                was {previewStats.originalMeanC.toFixed(4)}
              </p>
            </div>

            {/* High Risk Days */}
            <div className="bg-[#131b2e]/60 rounded-xl p-3">
              <p className="text-[9px] text-[#e2e8f0]/40 mb-1">
                High Risk Days
              </p>
              <p className="text-sm font-mono font-bold text-[#e2e8f0]/80">
                {previewStats.newHighRiskDays}
              </p>
              <p className="text-[9px] text-[#e2e8f0]/30 mt-0.5">
                was {city.summary.days_high_risk}
              </p>
            </div>
          </div>
        </div>
      )}

      {!isAdjusted && (
        <div className="text-center py-4">
          <p className="text-xs text-[#e2e8f0]/30">
            Drag the slider to simulate intervention scenarios
          </p>
        </div>
      )}
    </div>
  );
}
