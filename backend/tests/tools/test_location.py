"""Tests for app.tools.location module."""

import pytest
from unittest.mock import patch
from pydantic_extra_types.coordinate import Coordinate

from app.tools.location import get_location


class TestGetLocation:
    """Tests for get_location tool."""

    @patch("app.tools.location.geocode_location")
    def test_get_location_success(self, mock_geocode):
        """Test successful location lookup."""
        expected_coordinate = Coordinate(latitude=48.8566, longitude=2.3522)
        mock_geocode.return_value = expected_coordinate

        result = get_location.invoke({"place_name": "Paris, France"})

        assert isinstance(result, Coordinate)
        assert result.latitude == 48.8566
        assert result.longitude == 2.3522
        mock_geocode.assert_called_once_with("Paris, France")

    @patch("app.tools.location.geocode_location")
    def test_get_location_not_found(self, mock_geocode):
        """Test location lookup when place is not found."""
        mock_geocode.side_effect = ValueError("Could not find location")

        with pytest.raises(ValueError, match="Could not find location"):
            get_location.invoke({"place_name": "NonexistentPlace12345"})

    @patch("app.tools.location.geocode_location")
    def test_get_location_with_landmark(self, mock_geocode):
        """Test location lookup for a landmark."""
        expected_coordinate = Coordinate(latitude=48.8584, longitude=2.2945)
        mock_geocode.return_value = expected_coordinate

        result = get_location.invoke({"place_name": "Eiffel Tower, Paris"})

        assert isinstance(result, Coordinate)
        assert result.latitude == 48.8584
        assert result.longitude == 2.2945
        mock_geocode.assert_called_once_with("Eiffel Tower, Paris")

    @patch("app.tools.location.geocode_location")
    def test_get_location_api_error(self, mock_geocode):
        """Test location lookup with API error."""
        mock_geocode.side_effect = ValueError("Failed to geocode location: Network error")

        with pytest.raises(ValueError, match="Failed to geocode location"):
            get_location.invoke({"place_name": "Amsterdam"})
