"""Tests for app.tools.weather module."""

import pytest

from app.tools.weather import get_weather


class TestGetWeather:
    """Tests for get_weather tool."""

    def test_get_weather_celsius_default(self):
        """Test weather lookup with default celsius units."""
        result = get_weather.func("Paris")

        assert "Paris" in result
        assert "22 degrees C" in result
        assert "Next 5 days" not in result

    def test_get_weather_fahrenheit(self):
        """Test weather lookup with fahrenheit units."""
        result = get_weather.func("New York", "fahrenheit")

        assert "New York" in result
        assert "72 degrees F" in result
        assert "Next 5 days" not in result

    def test_get_weather_with_forecast(self):
        """Test weather lookup with forecast included."""
        result = get_weather.func("London", "celsius", True)

        assert "London" in result
        assert "22 degrees C" in result
        assert "Next 5 days: Sunny" in result

    def test_get_weather_with_forecast_fahrenheit(self):
        """Test weather lookup with forecast and fahrenheit."""
        result = get_weather.func("Miami", "fahrenheit", True)

        assert "Miami" in result
        assert "72 degrees F" in result
        assert "Next 5 days: Sunny" in result

    def test_get_weather_minimal_params(self):
        """Test weather lookup with only required parameters."""
        result = get_weather.func("Tokyo")

        assert isinstance(result, str)
        assert "Tokyo" in result
