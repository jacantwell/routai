"""Tests for reverse_geocode function"""

from unittest.mock import Mock, patch

import requests

from app.utils.utils import reverse_geocode


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_success_with_locality(
    mock_settings, mock_get, mock_coordinate
):
    """Test successful reverse geocoding with locality result"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {"types": ["locality", "political"], "formatted_address": "Leeds, UK"},
            {
                "types": ["administrative_area_level_2", "political"],
                "formatted_address": "West Yorkshire, UK",
            },
            {
                "types": ["administrative_area_level_1", "political"],
                "formatted_address": "England, UK",
            },
        ],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = reverse_geocode(mock_coordinate)

    assert result == "Leeds, UK"
    mock_get.assert_called_once()
    call_params = mock_get.call_args[1]["params"]
    assert call_params["latlng"] == "53.8008,-1.5491"
    assert call_params["key"] == "test_api_key"


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_success_with_postal_town(
    mock_settings, mock_get, mock_coordinate
):
    """Test successful reverse geocoding with postal_town result"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {"types": ["postal_town"], "formatted_address": "York, UK"},
            {
                "types": ["administrative_area_level_2", "political"],
                "formatted_address": "West Yorkshire, UK",
            },
            {
                "types": ["administrative_area_level_1", "political"],
                "formatted_address": "England, UK",
            },
        ],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = reverse_geocode(mock_coordinate)

    assert result == "York, UK"


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_fallback_to_admin_area_2(
    mock_settings, mock_get, mock_coordinate
):
    """Test fallback to administrative_area_level_2 when no locality found"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {
                "types": ["administrative_area_level_2", "political"],
                "formatted_address": "West Yorkshire, UK",
            },
            {
                "types": ["administrative_area_level_1", "political"],
                "formatted_address": "England, UK",
            },
        ],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = reverse_geocode(mock_coordinate)

    assert result == "West Yorkshire, UK"


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_fallback_to_admin_area_1(
    mock_settings, mock_get, mock_coordinate
):
    """Test fallback to administrative_area_level_1 when no locality or admin_2 found"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {
                "types": ["administrative_area_level_1", "political"],
                "formatted_address": "England, UK",
            }
        ],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = reverse_geocode(mock_coordinate)

    assert result == "England, UK"


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_fallback_to_first_result(
    mock_settings, mock_get, mock_coordinate
):
    """Test fallback to first result when no specific type matches"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [{"types": ["route"], "formatted_address": "A61, Leeds, UK"}],
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = reverse_geocode(mock_coordinate)

    assert result == "A61, Leeds, UK"


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_handles_non_ok_status(
    mock_settings, mock_get, mock_coordinate
):
    """Test handling of non-OK status from geocoding API"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = reverse_geocode(mock_coordinate)

    assert result == "Location at 53.8008,-1.5491"


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_handles_empty_results(
    mock_settings, mock_get, mock_coordinate
):
    """Test handling of empty results from geocoding API"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_response = Mock()
    mock_response.json.return_value = {"status": "OK", "results": []}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = reverse_geocode(mock_coordinate)

    assert result == "Location at 53.8008,-1.5491"


@patch("app.utils.utils.requests.get")
@patch("app.utils.utils.settings")
def test_reverse_geocode_handles_request_exception(
    mock_settings, mock_get, mock_coordinate
):
    """Test handling of request exceptions"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = (
        "https://maps.googleapis.com/maps/api/geocode/json"
    )

    mock_get.side_effect = requests.RequestException("Network error")

    result = reverse_geocode(mock_coordinate)

    assert result == "Location at 53.8008,-1.5491"
