/**
 * Ross-Macdonald Vectorial Capacity — Client-Side Implementation
 * ================================================================
 * Provides instant recalculation for the ITN governance slider preview.
 * Mirrors the Python backend equations exactly.
 */

export interface VectorialCapacityInput {
  temperature: number;
  humidity: number;
  precipitation: number;
  baselineBitingRate: number;
  itnCoverage: number;
}

export interface VectorialCapacityResult {
  C: number;
  n: number;
  p: number;
  m: number;
  aEff: number;
  riskLevel: string;
}

/**
 * Extrinsic Incubation Period (EIP) for Plasmodium falciparum.
 * n = 111 / (T - 16) for T > 16°C.
 */
export function calcExtrinsicIncubationPeriod(temperature: number): number {
  if (temperature <= 16) return 999.0;
  return 111.0 / (temperature - 16.0);
}

/**
 * Mosquito daily survival rate as a function of relative humidity.
 * p = 0.6 + 0.4 * (RH / 100), clamped to [0.01, 0.99].
 */
export function calcDailySurvivalRate(humidity: number): number {
  const p = 0.6 + 0.4 * (humidity / 100.0);
  return Math.max(0.01, Math.min(0.99, p));
}

/**
 * Mosquito density index from daily precipitation.
 * m = 0.5 + P * 0.3, clamped to [0.5, 15].
 */
export function calcMosquitoDensity(precipitation: number): number {
  const m = 0.5 + precipitation * 0.3;
  return Math.max(0.5, Math.min(15.0, m));
}

/**
 * Full Vectorial Capacity calculation.
 * C = m * a_eff² * p^n / (-ln(p))
 */
export function calcVectorialCapacity(
  input: VectorialCapacityInput
): VectorialCapacityResult {
  const n = calcExtrinsicIncubationPeriod(input.temperature);
  const p = calcDailySurvivalRate(input.humidity);
  const m = calcMosquitoDensity(input.precipitation);
  const aEff = input.baselineBitingRate * (1.0 - input.itnCoverage);

  let C = 0;
  if (p > 0 && p < 1) {
    const negLnP = -Math.log(p);
    if (negLnP > 0) {
      const pToN = Math.pow(p, n);
      C = (m * aEff * aEff * pToN) / negLnP;
    }
  }

  return {
    C: Math.round(C * 1e6) / 1e6,
    n: Math.round(n * 100) / 100,
    p: Math.round(p * 10000) / 10000,
    m: Math.round(m * 100) / 100,
    aEff: Math.round(aEff * 10000) / 10000,
    riskLevel: classifyRisk(C),
  };
}

/**
 * Classify transmission risk based on Vectorial Capacity.
 */
export function classifyRisk(C: number): string {
  if (C < 0.01) return "Negligible";
  if (C < 0.1) return "Low";
  if (C < 0.5) return "Moderate";
  if (C < 1.0) return "High";
  return "Critical";
}

/**
 * Recalculate an entire daily forecast array with a new ITN coverage value.
 * Used for the governance panel's client-side preview.
 */
export function recalculateWithITN(
  forecastDaily: Array<{
    date: string;
    temperature: number;
    humidity: number;
    precipitation: number;
  }>,
  baselineBitingRate: number,
  newItnCoverage: number
): Array<{ date: string; vectorial_capacity: number; risk_level: string }> {
  return forecastDaily.map((day) => {
    const result = calcVectorialCapacity({
      temperature: day.temperature,
      humidity: day.humidity,
      precipitation: day.precipitation,
      baselineBitingRate,
      itnCoverage: newItnCoverage,
    });
    return {
      date: day.date,
      vectorial_capacity: result.C,
      risk_level: result.riskLevel,
    };
  });
}

/**
 * Aggregate daily data to monthly averages.
 */
export function aggregateMonthly(
  dailyData: Array<{
    date: string;
    temperature: number;
    humidity: number;
    precipitation: number;
    vectorial_capacity: number;
  }>
): Array<{
  year_month: string;
  temperature: number;
  humidity: number;
  precipitation: number;
  vectorial_capacity: number;
}> {
  const monthMap = new Map<
    string,
    { temps: number[]; hums: number[]; precs: number[]; vcs: number[] }
  >();

  for (const day of dailyData) {
    const ym = day.date.slice(0, 7); // "YYYY-MM"
    if (!monthMap.has(ym)) {
      monthMap.set(ym, { temps: [], hums: [], precs: [], vcs: [] });
    }
    const bucket = monthMap.get(ym)!;
    bucket.temps.push(day.temperature);
    bucket.hums.push(day.humidity);
    bucket.precs.push(day.precipitation);
    bucket.vcs.push(day.vectorial_capacity);
  }

  const result: Array<{
    year_month: string;
    temperature: number;
    humidity: number;
    precipitation: number;
    vectorial_capacity: number;
  }> = [];

  for (const [ym, bucket] of monthMap.entries()) {
    const avg = (arr: number[]) =>
      Math.round((arr.reduce((a, b) => a + b, 0) / arr.length) * 10000) / 10000;
    result.push({
      year_month: ym,
      temperature: avg(bucket.temps),
      humidity: avg(bucket.hums),
      precipitation: avg(bucket.precs),
      vectorial_capacity: avg(bucket.vcs),
    });
  }

  return result.sort((a, b) => a.year_month.localeCompare(b.year_month));
}
