from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.propagation.sgp4_integrator import propagate_with_drag, OrbitPoint

router = APIRouter()


class TLEInput(BaseModel):
    line1: str = Field(..., description="TLE line 1")
    line2: str = Field(..., description="TLE line 2")


class SpaceWeatherParams(BaseModel):
    f107: float = Field(150.0, ge=65.0, le=300.0, description="F10.7 solar flux index")
    f107a: float = Field(150.0, ge=65.0, le=300.0, description="81-day average F10.7")
    kp: float = Field(2.0, ge=0.0, le=9.0, description="Planetary Kp geomagnetic index")
    ap: float = Field(7.0, ge=0.0, le=400.0, description="Ap geomagnetic activity index")


class SatelliteParams(BaseModel):
    mass_kg: float = Field(500.0, gt=0, description="Satellite mass in kilograms")
    drag_coefficient: float = Field(2.2, gt=0, description="Drag coefficient (Cd)")
    cross_section_m2: float = Field(4.0, gt=0, description="Cross-sectional area in m²")


class DecayPredictionRequest(BaseModel):
    tle: TLEInput
    space_weather: SpaceWeatherParams = SpaceWeatherParams()
    satellite: SatelliteParams = SatelliteParams()


class DecayPoint(BaseModel):
    time_hours: float
    altitude_km: float
    velocity_ms: float


class DecayPredictionResponse(BaseModel):
    initial_altitude_km: float
    final_altitude_km: float
    total_altitude_loss_km: float
    decay_points: List[DecayPoint]
    ballistic_coefficient: float


@router.post("/predict-decay", response_model=DecayPredictionResponse)
async def predict_decay(request: DecayPredictionRequest) -> DecayPredictionResponse:
    """
    Calculate the 7-day orbital decay for a satellite given its TLE and current space weather.
    """
    try:
        orbit_points: List[OrbitPoint] = propagate_with_drag(
            tle_line1=request.tle.line1,
            tle_line2=request.tle.line2,
            mass_kg=request.satellite.mass_kg,
            cd=request.satellite.drag_coefficient,
            area_m2=request.satellite.cross_section_m2,
            f107=request.space_weather.f107,
            f107a=request.space_weather.f107a,
            ap=request.space_weather.ap,
            days=7,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Propagation error: {exc}") from exc

    if not orbit_points:
        raise HTTPException(status_code=500, detail="No propagation data returned")

    from app.models.drag_calculator import calculate_ballistic_coefficient

    bc = calculate_ballistic_coefficient(
        mass=request.satellite.mass_kg,
        cd=request.satellite.drag_coefficient,
        area=request.satellite.cross_section_m2,
    )

    initial_alt = orbit_points[0].altitude_km
    final_alt = orbit_points[-1].altitude_km

    return DecayPredictionResponse(
        initial_altitude_km=initial_alt,
        final_altitude_km=final_alt,
        total_altitude_loss_km=initial_alt - final_alt,
        decay_points=[
            DecayPoint(
                time_hours=p.time_hours,
                altitude_km=p.altitude_km,
                velocity_ms=p.velocity_ms,
            )
            for p in orbit_points
        ],
        ballistic_coefficient=bc,
    )
