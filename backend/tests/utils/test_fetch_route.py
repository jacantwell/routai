from unittest.mock import Mock, patch

import pytest
import requests

from app.models import Route
from app.utils.utils import fetch_route


@patch("app.utils.utils.get_elevation_gain")
@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_fetch_route_success_bicycle(
    mock_settings, mock_post, mock_elevation, mock_origin, mock_destination
):
    """Test successful route fetch with bicycle mode"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_ROUTES_API_ENDPOINT = (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )
    mock_elevation.return_value = 250

    mock_response = Mock()
    mock_response.json.return_value = {
        "routes": [
            {
                "distanceMeters": 42000,
                "duration": "7200s",
                "polyline": {"encodedPolyline": "test_polyline_string"},
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = fetch_route(mock_origin, mock_destination)

    assert isinstance(result, Route)
    assert result.polyline == "test_polyline_string"
    assert result.origin == mock_origin
    assert result.destination == mock_destination
    assert result.distance == 42000
    assert result.elevation_gain == 250

    # Verify bicycle mode was tried first
    first_call_body = mock_post.call_args_list[0][1]["json"]
    assert first_call_body["travelMode"] == "BICYCLE"


@patch("app.utils.utils.get_elevation_gain")
@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_fetch_route_with_intermediates(
    mock_settings,
    mock_post,
    mock_elevation,
    mock_origin,
    mock_destination,
    mock_intermediate,
):
    """Test route fetch with intermediate waypoints"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_ROUTES_API_ENDPOINT = (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )
    mock_elevation.return_value = 300

    mock_response = Mock()
    mock_response.json.return_value = {
        "routes": [
            {
                "distanceMeters": 50000,
                "duration": "8000s",
                "polyline": {"encodedPolyline": "test_polyline_with_intermediate"},
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = fetch_route(
        mock_origin, mock_destination, intermediates=[mock_intermediate]
    )

    assert result.distance == 50000

    # Verify intermediate was included in request
    request_body = mock_post.call_args[1]["json"]
    assert len(request_body["intermediates"]) == 1
    assert request_body["intermediates"][0]["via"] is True
    assert request_body["intermediates"][0]["location"]["latLng"]["latitude"] == 53.9277


@patch("app.utils.utils.get_elevation_gain")
@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_fetch_route_fallback_to_drive(
    mock_settings, mock_post, mock_elevation, mock_origin, mock_destination
):
    """Test fallback to DRIVE mode when BICYCLE fails"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_ROUTES_API_ENDPOINT = (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )
    mock_elevation.return_value = 200

    # First call (bicycle) returns no routes, second call (drive) succeeds
    mock_response_bicycle = Mock()
    mock_response_bicycle.json.return_value = {}
    mock_response_bicycle.raise_for_status = Mock()

    mock_response_drive = Mock()
    mock_response_drive.json.return_value = {
        "routes": [
            {
                "distanceMeters": 45000,
                "duration": "3600s",
                "polyline": {"encodedPolyline": "drive_polyline"},
            }
        ]
    }
    mock_response_drive.raise_for_status = Mock()

    mock_post.side_effect = [mock_response_bicycle, mock_response_drive]

    result = fetch_route(mock_origin, mock_destination)

    assert result.polyline == "drive_polyline"
    assert result.distance == 45000

    # Verify both modes were attempted
    assert mock_post.call_count == 2
    first_call_body = mock_post.call_args_list[0][1]["json"]
    second_call_body = mock_post.call_args_list[1][1]["json"]
    assert first_call_body["travelMode"] == "BICYCLE"
    assert second_call_body["travelMode"] == "DRIVE"
    assert second_call_body["routingPreference"] == "TRAFFIC_UNAWARE"


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_fetch_route_all_strategies_fail(
    mock_settings, mock_post, mock_origin, mock_destination
):
    """Test error handling when all routing strategies fail"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_ROUTES_API_ENDPOINT = (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )

    # All calls return empty results
    mock_response = Mock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    with pytest.raises(ValueError) as exc_info:
        fetch_route(mock_origin, mock_destination)


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_fetch_route_request_exception(
    mock_settings, mock_post, mock_origin, mock_destination
):
    """Test handling of request exceptions"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_ROUTES_API_ENDPOINT = (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )

    mock_post.side_effect = requests.RequestException("Network error")

    with pytest.raises(ValueError) as exc_info:
        fetch_route(mock_origin, mock_destination)
