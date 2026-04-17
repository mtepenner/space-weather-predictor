"""
SGP4-based orbital propagator with atmospheric drag integration.

Propagates a satellite's orbit over a specified number of days by
combining TLE-based SGP4 propagation with NRLMSISE-00 atmospheric
drag calculations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import numpy as np
from sgp4.api import Satrec, WGS84

from app.models.drag_calculator import calculate_drag_acceleration
from app.models.nrlmsise00_wrapper import get_density

# Earth's gravitational parameter (m³/s²)
GM = 3.986004418e14
# Earth's mean radius (m)
R_EARTH_M = 6.371e6


@dataclass
class OrbitPoint:
    time_hours: float
    altitude_km: float
    velocity_ms: float


def propagate_with_drag(
    tle_line1: str,
    tle_line2: str,
    mass_kg: float,
    cd: float,
    area_m2: float,
    f107: float = 150.0,
    f107a: float = 150.0,
    ap: float = 7.0,
    days: int = 7,
    time_step_minutes: int = 30,
) -> List[OrbitPoint]:
    """
    Propagate a satellite orbit and compute altitude decay over time.

    Uses SGP4 for initial state vectors and numerically integrates drag
    perturbations between steps.

    Parameters
    ----------
    tle_line1, tle_line2 : str
        Two-line element set strings.
    mass_kg : float
        Satellite mass in kg.
    cd : float
        Drag coefficient.
    area_m2 : float
        Cross-sectional area in m².
    f107 : float
        F10.7 solar flux index.
    f107a : float
        81-day average F10.7.
    ap : float
        Daily Ap geomagnetic index.
    days : int
        Propagation duration in days.
    time_step_minutes : int
        Integration time step in minutes.

    Returns
    -------
    List[OrbitPoint]
        Time-series of altitude and velocity.

    Raises
    ------
    ValueError
        If TLE parsing fails.
    """
    satellite = Satrec.twoline2rv(tle_line1, tle_line2, WGS84)

    # Validate TLE parsed successfully
    if satellite.error != 0:
        raise ValueError(f"TLE parsing failed with error code {satellite.error}")

    total_minutes = days * 24 * 60
    steps = total_minutes // time_step_minutes

    # Extract epoch year/day for NRLMSISE input
    epoch_year = int(satellite.epochyr)
    if epoch_year < 57:
        epoch_year += 2000
    else:
        epoch_year += 1900
    epoch_day = satellite.epochdays  # fractional day of year

    orbit_points: List[OrbitPoint] = []

    # Cumulative velocity delta from drag (m/s); starts at zero
    delta_v_accumulated = 0.0

    for step in range(steps + 1):
        minutes_since_epoch = step * time_step_minutes
        hours_since_start = minutes_since_epoch / 60.0

        # SGP4 propagation: returns position (km) and velocity (km/s) in TEME frame
        e, r, v = satellite.sgp4(0.0, minutes_since_epoch / 1440.0)

        if e != 0:
            # Propagation error (e.g., satellite decayed)
            break

        r_vec = np.array(r) * 1000.0  # convert to metres
        v_vec = np.array(v) * 1000.0  # convert to m/s

        r_mag = float(np.linalg.norm(r_vec))
        v_mag = float(np.linalg.norm(v_vec))

        altitude_km = (r_mag - R_EARTH_M) / 1000.0

        if altitude_km < 100.0:
            # Satellite has re-entered
            orbit_points.append(OrbitPoint(
                time_hours=hours_since_start,
                altitude_km=max(altitude_km, 0.0),
                velocity_ms=v_mag,
            ))
            break

        # Get atmospheric density at this altitude/position
        lat = math.degrees(math.asin(r_vec[2] / r_mag))
        lon = math.degrees(math.atan2(r_vec[1], r_vec[0]))

        current_day = int(epoch_day) + int(minutes_since_epoch / 1440)
        seconds_of_day = ((epoch_day % 1.0) * 86400.0 + minutes_since_epoch * 60.0) % 86400.0

        rho = get_density(
            altitude_km=altitude_km,
            latitude=lat,
            longitude=lon,
            year=epoch_year,
            day_of_year=current_day,
            seconds=seconds_of_day,
            f107=f107,
            f107a=f107a,
            ap=ap,
        )

        # Compute drag deceleration over this step
        dt_seconds = time_step_minutes * 60.0
        a_drag = calculate_drag_acceleration(rho, v_mag, cd, area_m2, mass_kg)
        delta_v_step = a_drag * dt_seconds
        delta_v_accumulated += delta_v_step

        # Estimate altitude loss using energy conservation:
        # delta_h ≈ -2 * r^2 * delta_v / (v * T) derived from vis-viva
        # Simplified: altitude loss per step from vis-viva perturbation
        v_circular = math.sqrt(GM / r_mag)
        if v_circular > 0:
            alt_loss_m = (2.0 * r_mag * delta_v_step) / v_circular
        else:
            alt_loss_m = 0.0

        adjusted_altitude_km = altitude_km - (alt_loss_m / 1000.0)

        orbit_points.append(OrbitPoint(
            time_hours=hours_since_start,
            altitude_km=max(adjusted_altitude_km, 0.0),
            velocity_ms=v_mag,
        ))

    return orbit_points
