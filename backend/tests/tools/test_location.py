import pytest
from unittest.mock import patch
from pydantic_extra_types.coordinate import Coordinate

from app.tools.location import get_location


@patch("app.tools.location.geocode_location")
def test_get_location_success(mock_geocode):
    """Test successful location geocoding"""
    mock_geocode.return_value = Coordinate(latitude=48.8566, longitude=2.3522)

    result = get_location.invoke({"place_name": "Paris, France"})

    assert isinstance(result, Coordinate)
    assert result.latitude == 48.8566
    assert result.longitude == 2.3522
    mock_geocode.assert_called_once_with("Paris, France")


@patch("app.tools.location.geocode_location")
def test_get_location_landmark(mock_geocode):
    """Test geocoding a landmark"""
    mock_geocode.return_value = Coordinate(latitude=48.8584, longitude=2.2945)

    result = get_location.invoke({"place_name": "Eiffel Tower, Paris"})

    assert isinstance(result, Coordinate)
    assert result.latitude == 48.8584
    assert result.longitude == 2.2945
    mock_geocode.assert_called_once_with("Eiffel Tower, Paris")


@patch("app.tools.location.geocode_location")
def test_get_location_coordinates_returned(mock_geocode):
    """Test that coordinates are properly returned"""
    expected_coords = Coordinate(latitude=51.5074, longitude=-0.1278)
    mock_geocode.return_value = expected_coords

    result = get_location.invoke({"place_name": "London, UK"})

    assert result == expected_coords
    mock_geocode.assert_called_once_with("London, UK")


@patch("app.tools.location.geocode_location")
def test_get_location_error_handling(mock_geocode):
    """Test error handling when geocoding fails"""
    mock_geocode.side_effect = ValueError("Could not find location")

    with pytest.raises(ValueError) as exc_info:
        get_location.invoke({"place_name": "NonexistentPlace12345"})

    assert "Could not find location" in str(exc_info.value)
