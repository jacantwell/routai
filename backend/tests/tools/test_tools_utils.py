import pytest
from unittest.mock import Mock, patch
from pydantic_extra_types.coordinate import Coordinate
import requests

from app.tools.utils import (
    validate_route_state,
    validate_segments_state,
    geocode_location,
    convert_place_names_to_locations,
    recalculate_segments_with_accommodation,
)
from app.models import Location
from app.models.state import AgentState


def test_validate_route_state_success(mock_runtime):
    """Test successful route state validation"""
    route, requirements = validate_route_state(mock_runtime)

    assert route is not None
    assert requirements is not None
    assert route.polyline == "test_polyline_string"
    assert requirements.daily_distance_km == 80


def test_validate_route_state_missing_route():
    """Test error when route is missing from state"""
    runtime = Mock()
    state = AgentState(requirements=None, route=None)
    runtime.state = state

    with pytest.raises(ValueError) as exc_info:
        validate_route_state(runtime)

    assert "Route calculation required" in str(exc_info.value)


def test_validate_route_state_missing_requirements(mock_route):
    """Test error when requirements are missing from state"""
    runtime = Mock()
    state = AgentState(requirements=None, route=mock_route)
    runtime.state = state

    with pytest.raises(ValueError) as exc_info:
        validate_route_state(runtime)

    assert "Requirements validation required" in str(exc_info.value)


def test_validate_segments_state_success(mock_runtime_with_segments):
    """Test successful segments state validation"""
    segments = validate_segments_state(mock_runtime_with_segments)

    assert segments is not None
    assert len(segments) == 1
    assert segments[0].day == 1


def test_validate_segments_state_missing_segments():
    """Test error when segments are missing from state"""
    runtime = Mock()
    state = AgentState(requirements=None, route=None, segments=None)
    runtime.state = state

    with pytest.raises(ValueError) as exc_info:
        validate_segments_state(runtime)

    assert "Segment generation required" in str(exc_info.value)


@patch("app.tools.utils.requests.get")
@patch("app.tools.utils.settings")
def test_geocode_location_success(mock_settings, mock_get):
    """Test successful geocoding of location"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 48.8566, "lng": 2.3522}}}],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = geocode_location("Paris, France")

    assert isinstance(result, Coordinate)
    assert result.latitude == 48.8566
    assert result.longitude == 2.3522


@patch("app.tools.utils.requests.get")
@patch("app.tools.utils.settings")
def test_geocode_location_not_found(mock_settings, mock_get):
    """Test geocoding when location is not found"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    with pytest.raises(ValueError) as exc_info:
        geocode_location("InvalidLocation12345")

    assert "Could not find location" in str(exc_info.value)


@patch("app.tools.utils.requests.get")
@patch("app.tools.utils.settings")
def test_geocode_location_request_exception(mock_settings, mock_get):
    """Test handling of request exceptions"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_get.side_effect = requests.RequestException("Network error")

    with pytest.raises(ValueError) as exc_info:
        geocode_location("Paris, France")

    assert "Failed to geocode location" in str(exc_info.value)


@patch("app.tools.utils.geocode_location")
def test_convert_place_names_to_locations_success(mock_geocode):
    """Test successful conversion of place names to locations"""
    mock_geocode.side_effect = [
        Coordinate(latitude=48.8566, longitude=2.3522),
        Coordinate(latitude=51.5074, longitude=-0.1278),
    ]

    result = convert_place_names_to_locations(["Paris, France", "London, UK"])

    assert len(result) == 2
    assert isinstance(result[0], Location)
    assert result[0].name == "Paris, France"
    assert result[0].coordinates.latitude == 48.8566
    assert isinstance(result[1], Location)
    assert result[1].name == "London, UK"
    assert result[1].coordinates.latitude == 51.5074


@patch("app.tools.utils.geocode_location")
def test_convert_place_names_to_locations_empty_list(mock_geocode):
    """Test conversion with empty list"""
    result = convert_place_names_to_locations([])

    assert result == []
    mock_geocode.assert_not_called()


@patch("app.tools.utils.geocode_location")
def test_convert_place_names_to_locations_error(mock_geocode):
    """Test error handling when geocoding fails"""
    mock_geocode.side_effect = ValueError("Could not find location")

    with pytest.raises(ValueError) as exc_info:
        convert_place_names_to_locations(["InvalidPlace123"])

    assert "Failed to geocode" in str(exc_info.value)


@patch("app.tools.utils.get_accommodation")
@patch("app.tools.utils.calculate_segments")
def test_recalculate_segments_with_accommodation_success(
    mock_calculate_segments, mock_get_accommodation, mock_route, mock_segment
):
    """Test successful recalculation of segments with accommodation"""
    mock_calculate_segments.return_value = [mock_segment]
    mock_get_accommodation.return_value = []

    result = recalculate_segments_with_accommodation(mock_route, 80)

    assert len(result) == 1
    assert result[0].day == 1
    mock_calculate_segments.assert_called_once_with(
        "test_polyline_string", 80000, mock_route.origin, mock_route.destination
    )
    mock_get_accommodation.assert_called_once()


@patch("app.tools.utils.get_accommodation")
@patch("app.tools.utils.calculate_segments")
def test_recalculate_segments_with_accommodation_custom_radius(
    mock_calculate_segments, mock_get_accommodation, mock_route, mock_segment
):
    """Test recalculation with custom accommodation radius"""
    mock_calculate_segments.return_value = [mock_segment]
    mock_get_accommodation.return_value = []

    result = recalculate_segments_with_accommodation(
        mock_route, 80, accommodation_radius_km=10
    )

    assert len(result) == 1
    mock_get_accommodation.assert_called_once_with(
        mock_segment.route.destination.coordinates, radius=10
    )


@patch("app.tools.utils.get_accommodation")
@patch("app.tools.utils.calculate_segments")
def test_recalculate_segments_accommodation_error_handling(
    mock_calculate_segments, mock_get_accommodation, mock_route, mock_segment
):
    """Test that accommodation errors don't stop segment generation"""
    mock_calculate_segments.return_value = [mock_segment]
    mock_get_accommodation.side_effect = Exception("API error")

    result = recalculate_segments_with_accommodation(mock_route, 80)

    assert len(result) == 1
    assert result[0].accommodation_options == []


@patch("app.tools.utils.get_accommodation")
@patch("app.tools.utils.calculate_segments")
def test_recalculate_segments_multiple_segments(
    mock_calculate_segments, mock_get_accommodation, mock_route, mock_segment
):
    """Test recalculation with multiple segments"""
    from app.models import Segment

    segment1 = mock_segment
    segment2 = Segment(day=2, route=mock_route, accommodation_options=[])
    mock_calculate_segments.return_value = [segment1, segment2]
    mock_get_accommodation.return_value = []

    result = recalculate_segments_with_accommodation(mock_route, 80)

    assert len(result) == 2
    assert result[0].day == 1
    assert result[1].day == 2
    assert mock_get_accommodation.call_count == 2
