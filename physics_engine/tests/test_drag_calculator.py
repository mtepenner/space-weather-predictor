"""
Unit tests for drag_calculator module.
"""
import pytest
from app.models.drag_calculator import (
    calculate_drag_force,
    calculate_ballistic_coefficient,
    calculate_drag_acceleration,
)


class TestCalculateDragForce:
    def test_basic_drag_force(self):
        # F_d = 0.5 * 1.225 * 100^2 * 2.2 * 4.0 = 53900 N
        rho = 1.225      # kg/m³ (sea level approx)
        v = 100.0        # m/s
        cd = 2.2
        area = 4.0       # m²
        result = calculate_drag_force(rho, v, cd, area)
        expected = 0.5 * rho * v**2 * cd * area
        assert result == pytest.approx(expected, rel=1e-9)

    def test_zero_density_gives_zero_force(self):
        assert calculate_drag_force(0.0, 7800.0, 2.2, 4.0) == pytest.approx(0.0)

    def test_zero_velocity_gives_zero_force(self):
        assert calculate_drag_force(1e-12, 0.0, 2.2, 4.0) == pytest.approx(0.0)

    def test_typical_leo_conditions(self):
        # At ~400 km altitude, density ≈ 2.8e-10 kg/m³, ISS orbital speed ≈ 7660 m/s
        rho = 2.8e-10
        v = 7660.0
        cd = 2.2
        area = 2500.0  # ISS-like cross-section m²
        result = calculate_drag_force(rho, v, cd, area)
        assert result > 0
        expected = 0.5 * rho * v**2 * cd * area
        assert result == pytest.approx(expected, rel=1e-6)

    def test_scales_quadratically_with_velocity(self):
        rho, cd, area = 1e-10, 2.2, 4.0
        f1 = calculate_drag_force(rho, 1000.0, cd, area)
        f2 = calculate_drag_force(rho, 2000.0, cd, area)
        assert f2 == pytest.approx(4.0 * f1, rel=1e-9)

    def test_scales_linearly_with_density(self):
        v, cd, area = 7800.0, 2.2, 4.0
        f1 = calculate_drag_force(1e-10, v, cd, area)
        f2 = calculate_drag_force(2e-10, v, cd, area)
        assert f2 == pytest.approx(2.0 * f1, rel=1e-9)

    def test_negative_density_raises(self):
        with pytest.raises(ValueError, match="density"):
            calculate_drag_force(-1.0, 7800.0, 2.2, 4.0)

    def test_negative_velocity_raises(self):
        with pytest.raises(ValueError, match="[Vv]elocity"):
            calculate_drag_force(1e-10, -7800.0, 2.2, 4.0)

    def test_zero_cd_raises(self):
        with pytest.raises(ValueError, match="[Dd]rag coefficient"):
            calculate_drag_force(1e-10, 7800.0, 0.0, 4.0)

    def test_zero_area_raises(self):
        with pytest.raises(ValueError, match="[Aa]rea"):
            calculate_drag_force(1e-10, 7800.0, 2.2, 0.0)


class TestCalculateBallisticCoefficient:
    def test_standard_satellite(self):
        # B* = 500 / (2.2 * 4.0) = 56.818...
        result = calculate_ballistic_coefficient(500.0, 2.2, 4.0)
        assert result == pytest.approx(500.0 / (2.2 * 4.0), rel=1e-9)

    def test_heavy_dense_satellite_high_bc(self):
        bc = calculate_ballistic_coefficient(5000.0, 2.2, 1.0)
        assert bc > 1000  # large mass, small area = high BC

    def test_light_large_satellite_low_bc(self):
        bc = calculate_ballistic_coefficient(10.0, 2.2, 50.0)
        assert bc < 1  # small mass, large area = low BC

    def test_zero_mass_raises(self):
        with pytest.raises(ValueError, match="[Mm]ass"):
            calculate_ballistic_coefficient(0.0, 2.2, 4.0)

    def test_negative_mass_raises(self):
        with pytest.raises(ValueError, match="[Mm]ass"):
            calculate_ballistic_coefficient(-100.0, 2.2, 4.0)


class TestCalculateDragAcceleration:
    def test_basic_acceleration(self):
        rho, v, cd, area, mass = 1e-10, 7800.0, 2.2, 4.0, 500.0
        a = calculate_drag_acceleration(rho, v, cd, area, mass)
        expected = (0.5 * rho * v**2 * cd * area) / mass
        assert a == pytest.approx(expected, rel=1e-9)

    def test_heavier_satellite_less_deceleration(self):
        rho, v, cd, area = 1e-10, 7800.0, 2.2, 4.0
        a1 = calculate_drag_acceleration(rho, v, cd, area, 500.0)
        a2 = calculate_drag_acceleration(rho, v, cd, area, 1000.0)
        assert a1 == pytest.approx(2 * a2, rel=1e-9)

    def test_zero_mass_raises(self):
        with pytest.raises(ValueError, match="[Mm]ass"):
            calculate_drag_acceleration(1e-10, 7800.0, 2.2, 4.0, 0.0)
