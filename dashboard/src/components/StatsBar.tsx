"use client";

import { CityData } from "@/lib/types";
import { IconChart, IconCalendar, IconAlert, IconFlame, IconShield, IconDna } from "@/components/Icons";

interface StatsBarProps {
  city: CityData;
}

interface StatCardData {
  label: string;
  value: string;
  sub?: string;
  color: string;
  icon: React.ReactNode;
  /** Optional: color-code the value for negative Bio Validation r */
  valueClassName?: string;
}

export default function StatsBar({ city }: StatsBarProps) {
  const s = city.summary;
  const p = city.map_parameters;

  const validationR = s.historical_validation_r;
  const validationColor =
    validationR === null || validationR === undefined
      ? ""
      : validationR >= 0.5
      ? "text-emerald-400"
      : validationR >= 0
      ? "text-amber-400"
      : "text-red-400";

  const validationSub =
    validationR !== null && validationR !== undefined && validationR < 0
      ? "Weak/negative — limited fit"
      : "C vs Infection Prev";

  const stats: StatCardData[] = [
    {
      label: "Mean Annual C",
      value: s.mean_annual_C.toFixed(4),
      sub: "Vectorial Capacity",
      color: "from-teal-400 to-cyan-400",
      icon: <IconChart className="text-teal-400/60" size={16} />,
    },
    {
      label: "Peak Risk Month",
      value: s.peak_risk_month,
      sub: "Highest transmission",
      color: "from-amber-400 to-orange-400",
      icon: <IconCalendar className="text-amber-400/60" size={16} />,
    },
    {
      label: "Max C Value",
      value: s.max_C.toFixed(4),
      sub: `${s.days_critical} critical days`,
      color: "from-red-400 to-rose-500",
      icon: <IconAlert className="text-red-400/60" size={16} />,
    },
    {
      label: "High Risk Days",
      value: s.days_high_risk.toString(),
      sub: `of ${city.forecast_daily.length} forecast days`,
      color: "from-orange-400 to-amber-400",
      icon: <IconFlame className="text-orange-400/60" size={16} />,
    },
    {
      label: "ITN Coverage",
      value: `${(p.itn_coverage_percentage * 100).toFixed(0)}%`,
      sub: p.dominant_vector,
      color: "from-emerald-400 to-teal-400",
      icon: <IconShield className="text-emerald-400/60" size={16} />,
    },
    {
      label: "Bio Validation r",
      value: validationR !== null && validationR !== undefined
        ? validationR.toFixed(3)
        : "N/A",
      sub: validationSub,
      color: "from-violet-400 to-purple-400",
      icon: <IconDna className="text-violet-400/60" size={16} />,
      valueClassName: validationColor,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3" id="stats-bar">
      {stats.map((stat, i) => (
        <div
          key={stat.label}
          className="glass-card px-4 py-3 animate-fade-in-up"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <div className="flex items-center gap-2 mb-2">
            {stat.icon}
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[#e2e8f0]/40 truncate">
              {stat.label}
            </p>
          </div>
          <p
            className={
              stat.valueClassName
                ? `text-xl font-bold ${stat.valueClassName}`
                : `text-xl font-bold bg-gradient-to-r ${stat.color} bg-clip-text text-transparent`
            }
          >
            {stat.value}
          </p>
          {stat.sub && (
            <p className="text-[10px] text-[#e2e8f0]/30 mt-1 truncate">
              {stat.sub}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
