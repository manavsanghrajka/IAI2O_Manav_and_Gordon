import { NextRequest, NextResponse } from "next/server";
import {
  calcExtrinsicIncubationPeriod,
  calcDailySurvivalRate,
  calcMosquitoDensity,
  classifyRisk,
} from "@/lib/vectorial-capacity";

/**
 * POST /api/recalculate
 * Server-side recalculation of Vectorial Capacity with modified ITN parameters.
 * Uses the shared vectorial-capacity module instead of duplicating equations.
 */

interface RecalculateRequest {
  forecastDaily: Array<{
    date: string;
    temperature: number;
    humidity: number;
    precipitation: number;
  }>;
  baselineBitingRate: number;
  itnCoverage: number;
}

export async function POST(request: NextRequest) {
  try {
    const body: RecalculateRequest = await request.json();
    const { forecastDaily, baselineBitingRate, itnCoverage } = body;

    if (!forecastDaily || !Array.isArray(forecastDaily)) {
      return NextResponse.json(
        { error: "forecastDaily array is required" },
        { status: 400 }
      );
    }

    // Recalculate vectorial capacity for each day
    const results = forecastDaily.map((day) => {
      const n = calcExtrinsicIncubationPeriod(day.temperature);
      const p = calcDailySurvivalRate(day.humidity);
      const m = calcMosquitoDensity(day.precipitation);
      const aEff = baselineBitingRate * (1.0 - itnCoverage);

      let C = 0;
      if (p > 0 && p < 1) {
        const negLnP = -Math.log(p);
        if (negLnP > 0) {
          C = (m * aEff * aEff * Math.pow(p, n)) / negLnP;
        }
      }

      return {
        date: day.date,
        vectorial_capacity: Math.round(C * 1e6) / 1e6,
        risk_level: classifyRisk(C),
      };
    });

    // Monthly aggregation
    const monthMap = new Map<string, number[]>();
    for (const r of results) {
      const ym = r.date.slice(0, 7);
      if (!monthMap.has(ym)) monthMap.set(ym, []);
      monthMap.get(ym)!.push(r.vectorial_capacity);
    }

    const monthly = Array.from(monthMap.entries())
      .map(([ym, values]) => ({
        year_month: ym,
        vectorial_capacity:
          Math.round(
            (values.reduce((a, b) => a + b, 0) / values.length) * 10000
          ) / 10000,
      }))
      .sort((a, b) => a.year_month.localeCompare(b.year_month));

    // Summary
    const allC = results.map((r) => r.vectorial_capacity);
    const meanC = allC.reduce((a, b) => a + b, 0) / allC.length;

    return NextResponse.json({
      success: true,
      monthly,
      summary: {
        mean_C: Math.round(meanC * 10000) / 10000,
        max_C: Math.round(Math.max(...allC) * 10000) / 10000,
        risk_level: classifyRisk(meanC),
        days_high_risk: allC.filter((c) => c >= 0.5).length,
        days_critical: allC.filter((c) => c >= 1.0).length,
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: `Recalculation failed: ${
          error instanceof Error ? error.message : "Unknown"
        }`,
      },
      { status: 500 }
    );
  }
}
