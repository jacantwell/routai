import pytest
from unittest.mock import patch
from pydantic_extra_types.coordinate import Coordinate

from app.tools.location import get_location


@patch("app.tools.location.geocode_location")
def test_get_location_success(mock_geocode):
    """Test successful location geocoding"""
    mock_geocode.return_value = Coordinate(latitude=48.8566, longitude=2.3522)

    result = get_location.invoke({"place_name": "Paris"})

    assert isinstance(result, Coordinate)
    assert result.latitude == 48.8566
    assert result.longitude == 2.3522
    mock_geocode.assert_called_once_with("Paris")


@patch("app.tools.location.geocode_location")
def test_get_location_error_handling(mock_geocode):
    """Test error handling when geocoding fails"""
    mock_geocode.side_effect = ValueError("Could not find location")

    with pytest.raises(ValueError) as exc_info:
        get_location.invoke({"place_name": "NonexistentPlace12345"})

    assert "Could not find location" in str(exc_info.value)
