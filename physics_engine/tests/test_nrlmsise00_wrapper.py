"""
Unit tests for the NRLMSISE-00 wrapper module.

Uses mocking to avoid requiring pymsis to be available in all environments
and to ensure deterministic test results.
"""
import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import app.models.nrlmsise00_wrapper as wrapper_module
from app.models.nrlmsise00_wrapper import get_density, _simple_exponential_density


class TestSimpleExponentialDensity:
    def test_density_at_200km_is_positive(self):
        rho = _simple_exponential_density(200.0)
        assert rho > 0

    def test_density_decreases_with_altitude(self):
        rho_200 = _simple_exponential_density(200.0)
        rho_400 = _simple_exponential_density(400.0)
        rho_600 = _simple_exponential_density(600.0)
        assert rho_200 > rho_400 > rho_600

    def test_density_at_100km_reference(self):
        rho = _simple_exponential_density(100.0)
        assert rho == pytest.approx(5.6e-7, rel=1e-6)

    def test_density_below_100km_clamped(self):
        # Below 100 km should be clamped to 100 km value
        rho_80 = _simple_exponential_density(80.0)
        rho_100 = _simple_exponential_density(100.0)
        assert rho_80 == pytest.approx(rho_100)

    def test_scale_height_decay(self):
        # Verify exponential decay rate matches scale height H=8.5 km
        H = 8.5
        rho_0 = _simple_exponential_density(100.0)
        rho_h = _simple_exponential_density(100.0 + H)
        ratio = rho_h / rho_0
        assert ratio == pytest.approx(math.exp(-1.0), rel=1e-6)


class TestGetDensityWithoutPymsis:
    """Tests for get_density when pymsis is not available (fallback mode)."""

    def test_fallback_when_pymsis_unavailable(self):
        with patch.object(wrapper_module, "_PYMSIS_AVAILABLE", False):
            rho = get_density(400.0, 0.0, 0.0, 2024, 100, 0.0, 150.0, 150.0, 7.0)
            assert rho > 0
            # Should equal the exponential model at 400 km
            expected = _simple_exponential_density(400.0)
            assert rho == pytest.approx(expected, rel=1e-9)

    def test_fallback_density_at_various_altitudes(self):
        with patch.object(wrapper_module, "_PYMSIS_AVAILABLE", False):
            for alt in [200.0, 400.0, 600.0, 800.0]:
                rho = get_density(alt, 0.0, 0.0, 2024, 100, 0.0, 150.0, 150.0, 7.0)
                assert rho > 0


class TestGetDensityWithPymsis:
    """Tests for get_density when pymsis is available (mocked)."""

    def _make_pymsis_mock(self, density_value: float) -> MagicMock:
        mock_pymsis = MagicMock()
        # pymsis.calculate returns array of shape (1, 11); index 5 is mass density
        result_array = np.zeros(11)
        result_array[5] = density_value
        mock_pymsis.calculate.return_value = result_array.reshape(1, 11)
        return mock_pymsis

    def test_returns_density_from_pymsis(self):
        expected_density = 3.5e-10
        mock_pymsis = self._make_pymsis_mock(expected_density)

        with patch.object(wrapper_module, "_PYMSIS_AVAILABLE", True):
            with patch.dict("sys.modules", {"pymsis": mock_pymsis}):
                with patch.object(wrapper_module, "pymsis", mock_pymsis, create=True):
                    rho = get_density(400.0, 45.0, 30.0, 2024, 100, 43200.0, 150.0, 150.0, 7.0)
                    assert rho == pytest.approx(expected_density, rel=1e-9)

    def test_calls_pymsis_with_correct_parameters(self):
        mock_pymsis = self._make_pymsis_mock(3.5e-10)

        with patch.object(wrapper_module, "_PYMSIS_AVAILABLE", True):
            with patch.object(wrapper_module, "pymsis", mock_pymsis, create=True):
                get_density(400.0, 45.0, 30.0, 2024, 100, 43200.0, 150.0, 155.0, 10.0)
                mock_pymsis.calculate.assert_called_once()
                call_kwargs = mock_pymsis.calculate.call_args
                assert call_kwargs.kwargs["alts"] == 400.0
                assert call_kwargs.kwargs["lat"] == 45.0
                assert call_kwargs.kwargs["lon"] == 30.0
                assert call_kwargs.kwargs["f107"] == 150.0
                assert call_kwargs.kwargs["f107a"] == 155.0

    def test_falls_back_on_nan_result(self):
        mock_pymsis = self._make_pymsis_mock(float("nan"))

        with patch.object(wrapper_module, "_PYMSIS_AVAILABLE", True):
            with patch.object(wrapper_module, "pymsis", mock_pymsis, create=True):
                rho = get_density(400.0, 0.0, 0.0, 2024, 100, 0.0, 150.0, 150.0, 7.0)
                expected = _simple_exponential_density(400.0)
                assert rho == pytest.approx(expected, rel=1e-9)

    def test_falls_back_on_negative_result(self):
        mock_pymsis = self._make_pymsis_mock(-1.0)

        with patch.object(wrapper_module, "_PYMSIS_AVAILABLE", True):
            with patch.object(wrapper_module, "pymsis", mock_pymsis, create=True):
                rho = get_density(400.0, 0.0, 0.0, 2024, 100, 0.0, 150.0, 150.0, 7.0)
                expected = _simple_exponential_density(400.0)
                assert rho == pytest.approx(expected, rel=1e-9)

    def test_returns_positive_density(self):
        mock_pymsis = self._make_pymsis_mock(2.8e-10)

        with patch.object(wrapper_module, "_PYMSIS_AVAILABLE", True):
            with patch.object(wrapper_module, "pymsis", mock_pymsis, create=True):
                rho = get_density(400.0, 0.0, 0.0, 2024, 100, 0.0, 150.0, 150.0, 7.0)
                assert rho > 0
