import pytest
from unittest.mock import Mock, patch
import requests

from app.utils.utils import get_accommodation


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_get_accommodation_success(mock_settings, mock_post, mock_coordinate):
    """Test successful accommodation search"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

    mock_response = Mock()
    mock_response.json.return_value = {
        "places": [
            {
                "displayName": {"text": "Test Hotel"},
                "formattedAddress": "123 Test St, Leeds",
                "googleMapsUri": "https://maps.google.com/place/test",
                "rating": 4.5,
            },
            {
                "displayName": {"text": "Another Hotel"},
                "formattedAddress": "456 Another St, Leeds",
                "googleMapsUri": "https://maps.google.com/place/another",
                "rating": 4.0,
            },
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = get_accommodation(mock_coordinate, radius=5)

    assert len(result) == 2
    assert result[0].name == "Test Hotel"
    assert result[0].address == "123 Test St, Leeds"
    assert result[0].map_link == "https://maps.google.com/place/test"
    assert result[0].rating == 4.5
    assert result[1].name == "Another Hotel"


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_get_accommodation_with_custom_radius(mock_settings, mock_post, mock_coordinate):
    """Test accommodation search with custom radius"""
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

    mock_response = Mock()
    mock_response.json.return_value = {"places": []}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    get_accommodation(mock_coordinate, radius=10)

    request_body = mock_post.call_args[1]["json"]
    assert request_body["locationRestriction"]["circle"]["radius"] == 10000


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_get_accommodation_empty_results(mock_settings, mock_post, mock_coordinate):
    """Test handling of empty results"""

    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

    mock_response = Mock()
    mock_response.json.return_value = {"places": []}
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = get_accommodation(mock_coordinate)

    assert result == []


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_get_accommodation_all_fields_present(mock_settings, mock_post, mock_coordinate):
    """Test handling when all optional fields are present"""

    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

    mock_response = Mock()
    mock_response.json.return_value = {
        "places": [
            {
                "displayName": {"text": "Complete Hotel"},
                "formattedAddress": "789 Complete St, Leeds",
                "googleMapsUri": "https://maps.google.com/complete",
                "rating": 4.8,
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response

    result = get_accommodation(mock_coordinate)

    assert len(result) == 1
    assert result[0].name == "Complete Hotel"
    assert result[0].address == "789 Complete St, Leeds"
    assert result[0].map_link == "https://maps.google.com/complete"
    assert result[0].rating == 4.8


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_get_accommodation_request_exception(mock_settings, mock_post, mock_coordinate):
    """Test handling of request exceptions"""
    
    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"
    
    mock_post.side_effect = requests.exceptions.RequestException("Network error")

    with pytest.raises(Exception) as exc_info:
        get_accommodation(mock_coordinate)

    assert "Error making request to Google Places API" in str(exc_info.value)


@patch("app.utils.utils.requests.post")
@patch("app.utils.utils.settings")
def test_get_accommodation_generic_error(mock_settings, mock_post, mock_coordinate):
    """Test handling of base errors"""

    mock_settings.GOOGLE_API_KEY = "test_api_key"
    mock_settings.GOOGLE_PLACES_API_ENDPOINT ="https://places.googleapis.com/v1/places:searchNearby"

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
    mock_post.return_value = mock_response

    with pytest.raises(Exception) as exc_info:
        get_accommodation(mock_coordinate)
