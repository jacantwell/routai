import pytest

from app.tools.weather import get_weather


def test_get_weather_return_type():
    """Test that get_weather returns a string"""
    result = get_weather.invoke({"location_name": "Berlin"})

    assert isinstance(result, str)
