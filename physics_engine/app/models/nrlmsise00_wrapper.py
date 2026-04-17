"""
NRLMSISE-00 atmospheric density model wrapper.

Interfaces with the pymsis library to provide atmospheric density
at a given altitude, location, and solar/geomagnetic conditions.
"""
from __future__ import annotations

import datetime
import numpy as np

try:
    import pymsis
    _PYMSIS_AVAILABLE = True
except ImportError:
    _PYMSIS_AVAILABLE = False


def get_density(
    altitude_km: float,
    latitude: float,
    longitude: float,
    year: int,
    day_of_year: int,
    seconds: float,
    f107: float,
    f107a: float,
    ap: float,
) -> float:
    """
    Return atmospheric mass density (kg/m³) using the NRLMSISE-00 model.

    Parameters
    ----------
    altitude_km : float
        Altitude above WGS-84 ellipsoid in kilometres.
    latitude : float
        Geodetic latitude in degrees (-90 to 90).
    longitude : float
        Geodetic longitude in degrees (-180 to 180).
    year : int
        Calendar year (e.g. 2024).
    day_of_year : int
        Day of year (1-366).
    seconds : float
        Seconds elapsed since midnight UTC.
    f107 : float
        Previous day's F10.7 cm solar radio flux.
    f107a : float
        81-day average of F10.7 cm solar radio flux.
    ap : float
        Daily magnetic index Ap (0-400).

    Returns
    -------
    float
        Total mass density in kg/m³.
    """
    if not _PYMSIS_AVAILABLE:
        return _simple_exponential_density(altitude_km)

    # pymsis expects a datetime object and ap as a float or array
    dt = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(
        days=day_of_year - 1, seconds=seconds
    )

    # pymsis.calculate returns an ndarray of shape (..., 11) with densities
    # Index 5 = total mass density (kg/m³)
    result = pymsis.calculate(
        date=dt,
        lon=longitude,
        lat=latitude,
        alts=altitude_km,
        f107=f107,
        f107a=f107a,
        ap=[[ap] * 7],
    )

    # result shape: (1, 11) or (11,); index 5 is total mass density
    result = np.asarray(result)
    if result.ndim > 1:
        rho = float(result.flat[5])
    else:
        rho = float(result[5])

    # Guard against NaN/negative values with exponential fallback
    if not np.isfinite(rho) or rho <= 0:
        return _simple_exponential_density(altitude_km)

    return rho


def _simple_exponential_density(altitude_km: float) -> float:
    """
    Exponential atmospheric density model fallback.

    Uses a simple scale-height model valid from 100 to 1000 km.
    """
    # Reference density at 100 km in kg/m³ and scale height in km
    rho_0 = 5.6e-7  # kg/m³ at 100 km
    H = 8.5         # scale height in km
    alt_ref = 100.0

    if altitude_km < alt_ref:
        altitude_km = alt_ref

    return rho_0 * np.exp(-(altitude_km - alt_ref) / H)
