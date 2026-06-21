"""
Ross-Macdonald Vectorial Capacity — Shared Module
===================================================
Centralised biological equations used by the main pipeline,
accuracy tests, and any future tooling.

Equation:  C = m · a_eff² · p^n / (-ln p)

Where:
  m     = mosquito density index (f(precipitation))
  a_eff = effective biting rate = a · (1 - ITN_coverage)
  p     = daily mosquito survival probability (f(humidity))
  n     = extrinsic incubation period (f(temperature))
"""

import math
from typing import Dict

import numpy as np

# ---------------------------------------------------------------------------
# BIOLOGICAL CONSTANTS
# ---------------------------------------------------------------------------

EIP_NUMERATOR = 111.0          # Degree-days for Plasmodium falciparum
EIP_TEMP_THRESHOLD = 16.0      # Minimum temperature for parasite development (°C)

SURVIVAL_BASE = 0.6            # Baseline daily survival at 0% RH
SURVIVAL_HUMIDITY_COEFF = 0.4  # Humidity contribution coefficient
SURVIVAL_MIN = 0.01
SURVIVAL_MAX = 0.99

DENSITY_BASE = 0.5             # Baseline mosquito density index
DENSITY_PRECIP_COEFF = 0.3     # Precipitation contribution coefficient
DENSITY_MIN = 0.5
DENSITY_MAX = 15.0


# ---------------------------------------------------------------------------
# CORE EQUATIONS
# ---------------------------------------------------------------------------

def calc_extrinsic_incubation_period(temperature: float) -> float:
    """Extrinsic Incubation Period (EIP) for Plasmodium falciparum.
    n = 111 / (T - 16) for T > 16°C.
    """
    if temperature <= EIP_TEMP_THRESHOLD:
        return 999.0
    return EIP_NUMERATOR / (temperature - EIP_TEMP_THRESHOLD)


def calc_daily_survival_rate(humidity: float) -> float:
    """Mosquito daily survival rate as a function of relative humidity.
    p = 0.6 + 0.4 * (RH / 100), clamped to [0.01, 0.99].
    """
    p = SURVIVAL_BASE + SURVIVAL_HUMIDITY_COEFF * (humidity / 100.0)
    return max(SURVIVAL_MIN, min(SURVIVAL_MAX, p))


def calc_mosquito_density(precipitation: float) -> float:
    """Mosquito density index from daily precipitation.
    m = 0.5 + P * 0.3, clamped to [0.5, 15].
    """
    m = DENSITY_BASE + precipitation * DENSITY_PRECIP_COEFF
    return max(DENSITY_MIN, min(DENSITY_MAX, m))


def calc_vectorial_capacity(
    temperature: float,
    humidity: float,
    precipitation: float,
    baseline_biting_rate: float,
    itn_coverage: float,
) -> Dict[str, float]:
    """Full Vectorial Capacity calculation.
    C = m · a_eff² · p^n / (-ln p)
    """
    n = calc_extrinsic_incubation_period(temperature)
    p = calc_daily_survival_rate(humidity)
    m = calc_mosquito_density(precipitation)
    a_eff = baseline_biting_rate * (1.0 - itn_coverage)

    if p <= 0 or p >= 1:
        C = 0.0
    else:
        neg_ln_p = -math.log(p)
        if neg_ln_p == 0:
            C = 0.0
        else:
            C = (m * (a_eff ** 2) * (p ** n)) / neg_ln_p

    return {
        "C": round(C, 6),
        "n": round(n, 2),
        "p": round(p, 4),
        "m": round(m, 2),
        "a_eff": round(a_eff, 4),
    }


def classify_risk(C: float) -> str:
    """Classify transmission risk based on Vectorial Capacity."""
    if C < 0.01:
        return "Negligible"
    elif C < 0.1:
        return "Low"
    elif C < 0.5:
        return "Moderate"
    elif C < 1.0:
        return "High"
    else:
        return "Critical"


def calc_approx_yearly_C(
    temp: float, hum: float, prec: float, a: float, itn: float
) -> float:
    """Approximate C using yearly climate averages as an engineered ML feature.
    Precipitation is divided by 365 to get average daily precipitation.
    """
    n = calc_extrinsic_incubation_period(temp)
    p = calc_daily_survival_rate(hum)
    m = calc_mosquito_density(prec / 365.0)
    a_eff = a * (1.0 - itn)

    if p <= 0 or p >= 1:
        return 0.0
    neg_ln_p = -math.log(p)
    if neg_ln_p == 0:
        return 0.0

    try:
        C = (m * (a_eff ** 2) * (p ** n)) / neg_ln_p
        return min(C, 100.0)
    except OverflowError:
        return 0.0


# ---------------------------------------------------------------------------
# VECTORISED HELPERS (for performance on large arrays)
# ---------------------------------------------------------------------------

def vectorised_daily_C(
    temps: np.ndarray,
    hums: np.ndarray,
    precs: np.ndarray,
    baseline_a: float,
    itn_cov: float,
) -> np.ndarray:
    """Compute Vectorial Capacity for arrays of daily climate data.
    50-100× faster than row-by-row Python loops.
    """
    a_eff = baseline_a * (1.0 - itn_cov)

    # EIP
    n = np.where(temps > EIP_TEMP_THRESHOLD,
                 EIP_NUMERATOR / (temps - EIP_TEMP_THRESHOLD),
                 999.0)
    # Survival
    p = np.clip(SURVIVAL_BASE + SURVIVAL_HUMIDITY_COEFF * (hums / 100.0),
                SURVIVAL_MIN, SURVIVAL_MAX)
    # Density
    m = np.clip(DENSITY_BASE + precs * DENSITY_PRECIP_COEFF,
                DENSITY_MIN, DENSITY_MAX)

    neg_ln_p = -np.log(p)
    # Avoid division by zero (shouldn't happen with clipped p, but safety)
    neg_ln_p = np.where(neg_ln_p == 0, 1e-10, neg_ln_p)

    C = (m * (a_eff ** 2) * np.power(p, n)) / neg_ln_p
    return C
