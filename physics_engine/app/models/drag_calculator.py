"""
Aerodynamic drag force calculator for low Earth orbit satellites.

Implements the standard drag equation:
    F_d = 0.5 * rho * v^2 * C_d * A

where:
    rho  - atmospheric mass density (kg/m³)
    v    - orbital velocity (m/s)
    C_d  - dimensionless drag coefficient (typically 2.2 for LEO satellites)
    A    - effective cross-sectional area (m²)
"""
from __future__ import annotations


def calculate_drag_force(rho: float, v: float, cd: float, area: float) -> float:
    """
    Calculate aerodynamic drag force acting on a satellite.

    Parameters
    ----------
    rho : float
        Atmospheric mass density in kg/m³.
    v : float
        Satellite velocity relative to the atmosphere in m/s.
    cd : float
        Drag coefficient (dimensionless). Typical value: 2.2.
    area : float
        Effective cross-sectional area in m².

    Returns
    -------
    float
        Drag force in Newtons (N).

    Raises
    ------
    ValueError
        If any input value is negative.
    """
    if rho < 0:
        raise ValueError(f"Atmospheric density must be non-negative, got {rho}")
    if v < 0:
        raise ValueError(f"Velocity must be non-negative, got {v}")
    if cd <= 0:
        raise ValueError(f"Drag coefficient must be positive, got {cd}")
    if area <= 0:
        raise ValueError(f"Cross-sectional area must be positive, got {area}")

    return 0.5 * rho * v**2 * cd * area


def calculate_ballistic_coefficient(mass: float, cd: float, area: float) -> float:
    """
    Calculate the ballistic coefficient B* for a satellite.

    B* = mass / (C_d * A)

    A higher ballistic coefficient means less drag deceleration per unit mass.

    Parameters
    ----------
    mass : float
        Satellite mass in kilograms.
    cd : float
        Drag coefficient (dimensionless).
    area : float
        Effective cross-sectional area in m².

    Returns
    -------
    float
        Ballistic coefficient in kg/m².

    Raises
    ------
    ValueError
        If mass, cd, or area are not positive.
    """
    if mass <= 0:
        raise ValueError(f"Mass must be positive, got {mass}")
    if cd <= 0:
        raise ValueError(f"Drag coefficient must be positive, got {cd}")
    if area <= 0:
        raise ValueError(f"Cross-sectional area must be positive, got {area}")

    return mass / (cd * area)


def calculate_drag_acceleration(rho: float, v: float, cd: float, area: float, mass: float) -> float:
    """
    Calculate drag deceleration magnitude acting on a satellite.

    a_d = F_d / m = (0.5 * rho * v^2 * C_d * A) / m

    Parameters
    ----------
    rho : float
        Atmospheric mass density in kg/m³.
    v : float
        Satellite velocity relative to the atmosphere in m/s.
    cd : float
        Drag coefficient (dimensionless).
    area : float
        Effective cross-sectional area in m².
    mass : float
        Satellite mass in kg.

    Returns
    -------
    float
        Drag deceleration in m/s².
    """
    if mass <= 0:
        raise ValueError(f"Mass must be positive, got {mass}")
    return calculate_drag_force(rho, v, cd, area) / mass
