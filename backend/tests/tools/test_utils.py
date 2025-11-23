"""Tests for app.tools.utils module."""

import pytest
from unittest.mock import Mock, patch
from pydantic_extra_types.coordinate import Coordinate

from app.tools.utils import (
    validate_route_state,
    validate_segments_state,
    geocode_location,
    convert_place_names_to_locations,
    recalculate_segments_with_accommodation,
)
from app.models.models import Location


class TestValidateRouteState:
    """Tests for validate_route_state function."""

    def test_validate_route_state_success(self, mock_runtime):
        """Test successful validation of route state."""
        route, requirements = validate_route_state(mock_runtime)

        assert route is not None
        assert requirements is not None
        assert route.distance == 450000
        assert requirements.daily_distance_km == 80

    def test_validate_route_state_no_route(self, mock_runtime):
        """Test validation fails when route is missing."""
        mock_runtime.state.route = None

        with pytest.raises(ValueError, match="No route found in state"):
            validate_route_state(mock_runtime)

    def test_validate_route_state_no_requirements(self, mock_runtime):
        """Test validation fails when requirements are missing."""
        mock_runtime.state.requirements = None

        with pytest.raises(ValueError, match="No requirements found in state"):
            validate_route_state(mock_runtime)


class TestValidateSegmentsState:
    """Tests for validate_segments_state function."""

    def test_validate_segments_state_success(self, mock_runtime):
        """Test successful validation of segments state."""
        segments = validate_segments_state(mock_runtime)

        assert segments is not None
        assert len(segments) == 1
        assert segments[0].day == 1

    def test_validate_segments_state_no_segments(self, mock_runtime):
        """Test validation fails when segments are missing."""
        mock_runtime.state.segments = None

        with pytest.raises(ValueError, match="No segments found in state"):
            validate_segments_state(mock_runtime)

    def test_validate_segments_state_empty_list(self, mock_runtime):
        """Test validation fails when segments list is empty."""
        mock_runtime.state.segments = []

        with pytest.raises(ValueError, match="No segments found in state"):
            validate_segments_state(mock_runtime)


class TestGeocodeLocation:
    """Tests for geocode_location function."""

    @patch("app.tools.utils.requests.get")
    def test_geocode_location_success(self, mock_get):
        """Test successful geocoding of a location."""
        # Mock the API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {"lat": 48.8566, "lng": 2.3522}
                    }
                }
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = geocode_location("Paris, France")

        assert isinstance(result, Coordinate)
        assert result.latitude == 48.8566
        assert result.longitude == 2.3522
        mock_get.assert_called_once()

    @patch("app.tools.utils.requests.get")
    def test_geocode_location_not_found(self, mock_get):
        """Test geocoding with location not found."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "ZERO_RESULTS",
            "results": [],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Could not find location"):
            geocode_location("NonexistentPlace12345")

    @patch("app.tools.utils.requests.get")
    def test_geocode_location_api_error(self, mock_get):
        """Test geocoding with API error."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(ValueError, match="Failed to geocode location"):
            geocode_location("Paris, France")


class TestConvertPlaceNamesToLocations:
    """Tests for convert_place_names_to_locations function."""

    @patch("app.tools.utils.geocode_location")
    def test_convert_place_names_success(self, mock_geocode):
        """Test successful conversion of place names to locations."""
        # Mock geocode responses
        mock_geocode.side_effect = [
            Coordinate(latitude=48.8566, longitude=2.3522),  # Paris
            Coordinate(latitude=45.764, longitude=4.8357),  # Lyon
        ]

        result = convert_place_names_to_locations(["Paris, France", "Lyon, France"])

        assert len(result) == 2
        assert all(isinstance(loc, Location) for loc in result)
        assert result[0].name == "Paris, France"
        assert result[1].name == "Lyon, France"
        assert mock_geocode.call_count == 2

    @patch("app.tools.utils.geocode_location")
    def test_convert_place_names_with_error(self, mock_geocode):
        """Test conversion fails when geocoding fails for one place."""
        mock_geocode.side_effect = [
            Coordinate(latitude=48.8566, longitude=2.3522),  # Paris
            ValueError("Failed to geocode"),  # Second place fails
        ]

        with pytest.raises(ValueError, match="Failed to geocode"):
            convert_place_names_to_locations(["Paris, France", "InvalidPlace"])

    @patch("app.tools.utils.geocode_location")
    def test_convert_place_names_empty_list(self, mock_geocode):
        """Test conversion with empty list."""
        result = convert_place_names_to_locations([])

        assert result == []
        mock_geocode.assert_not_called()


class TestRecalculateSegmentsWithAccommodation:
    """Tests for recalculate_segments_with_accommodation function."""

    @patch("app.tools.utils.get_accommodation")
    @patch("app.tools.utils.calculate_segments")
    def test_recalculate_segments_success(
        self, mock_calculate_segments, mock_get_accommodation, sample_route, sample_segment, sample_accommodation
    ):
        """Test successful recalculation of segments with accommodation."""
        # Mock calculate_segments to return a list of segments
        mock_calculate_segments.return_value = [sample_segment]

        # Mock get_accommodation to return accommodation options
        mock_get_accommodation.return_value = [sample_accommodation]

        result = recalculate_segments_with_accommodation(sample_route, 80)

        assert len(result) == 1
        assert result[0].accommodation_options == [sample_accommodation]
        mock_calculate_segments.assert_called_once_with(
            sample_route.polyline, 80000  # 80km * 1000
        )
        mock_get_accommodation.assert_called_once()

    @patch("app.tools.utils.get_accommodation")
    @patch("app.tools.utils.calculate_segments")
    def test_recalculate_segments_accommodation_error(
        self, mock_calculate_segments, mock_get_accommodation, sample_route, sample_segment
    ):
        """Test recalculation handles accommodation lookup errors gracefully."""
        mock_calculate_segments.return_value = [sample_segment]
        mock_get_accommodation.side_effect = Exception("API error")

        result = recalculate_segments_with_accommodation(sample_route, 80)

        assert len(result) == 1
        assert result[0].accommodation_options == []

    @patch("app.tools.utils.get_accommodation")
    @patch("app.tools.utils.calculate_segments")
    def test_recalculate_segments_custom_radius(
        self, mock_calculate_segments, mock_get_accommodation, sample_route, sample_segment, sample_accommodation
    ):
        """Test recalculation with custom accommodation radius."""
        mock_calculate_segments.return_value = [sample_segment]
        mock_get_accommodation.return_value = [sample_accommodation]

        result = recalculate_segments_with_accommodation(sample_route, 100, accommodation_radius_km=10)

        assert len(result) == 1
        mock_get_accommodation.assert_called_once_with(
            sample_segment.route.destination, radius=10
        )
