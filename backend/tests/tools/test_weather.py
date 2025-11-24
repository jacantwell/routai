import pytest

from app.tools.weather import get_weather


def test_get_weather_default_celsius():
    """Test get_weather with default celsius units"""
    result = get_weather.invoke({"location_name": "Paris"})

    assert "Paris" in result
    assert "22 degrees C" in result
    assert "Next 5 days" not in result


def test_get_weather_fahrenheit():
    """Test get_weather with fahrenheit units"""
    result = get_weather.invoke({"location_name": "New York", "units": "fahrenheit"})

    assert "New York" in result
    assert "72 degrees F" in result
    assert "Next 5 days" not in result


def test_get_weather_with_forecast():
    """Test get_weather with forecast included"""
    result = get_weather.invoke({"location_name": "London", "include_forecast": True})

    assert "London" in result
    assert "22 degrees C" in result
    assert "Next 5 days: Sunny" in result


def test_get_weather_fahrenheit_with_forecast():
    """Test get_weather with fahrenheit and forecast"""
    result = get_weather.invoke(
        {"location_name": "Tokyo", "units": "fahrenheit", "include_forecast": True}
    )

    assert "Tokyo" in result
    assert "72 degrees F" in result
    assert "Next 5 days: Sunny" in result


def test_get_weather_return_type():
    """Test that get_weather returns a string"""
    result = get_weather.invoke({"location_name": "Berlin"})

    assert isinstance(result, str)
