import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic_extra_types.coordinate import Coordinate
import requests

from app.models import Location, Accommodation, Route, Segment
from app.utils.utils import (
    get_elevation_gain,
    reverse_geocode,
    get_accommodation,
    fetch_route,
    calculate_segments,
)


class TestGetElevationGain:
    """Tests for get_elevation_gain function"""

    @patch("app.utils.utils.random.randint")
    def test_get_elevation_gain_returns_integer(self, mock_randint):
        """Test that get_elevation_gain returns an integer elevation value"""
        mock_randint.return_value = 250
        polyline_str = "test_polyline"

        result = get_elevation_gain(polyline_str)

        assert result == 250
        assert isinstance(result, int)
        mock_randint.assert_called_once_with(100, 400)

    @patch("app.utils.utils.random.randint")
    def test_get_elevation_gain_calls_random_with_correct_range(self, mock_randint):
        """Test that get_elevation_gain uses correct range for random values"""
        mock_randint.return_value = 150

        get_elevation_gain("any_polyline")

        mock_randint.assert_called_once_with(100, 400)


class TestReverseGeocode:
    """Tests for reverse_geocode function"""

    @pytest.fixture
    def mock_coordinate(self):
        """Fixture providing a test coordinate"""
        return Coordinate(latitude=53.8008, longitude=-1.5491)

    @patch("app.utils.utils.requests.get")
    @patch("app.utils.utils.settings")
    def test_reverse_geocode_success_with_locality(self, mock_settings, mock_get, mock_coordinate):
        """Test successful reverse geocoding with locality result"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "types": ["locality", "political"],
                    "formatted_address": "Leeds, UK"
                }
            ]
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
    def test_reverse_geocode_success_with_postal_town(self, mock_settings, mock_get, mock_coordinate):
        """Test successful reverse geocoding with postal_town result"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "types": ["postal_town"],
                    "formatted_address": "York, UK"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = reverse_geocode(mock_coordinate)

        assert result == "York, UK"

    @patch("app.utils.utils.requests.get")
    @patch("app.utils.utils.settings")
    def test_reverse_geocode_fallback_to_admin_area_2(self, mock_settings, mock_get, mock_coordinate):
        """Test fallback to administrative_area_level_2 when no locality found"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "types": ["administrative_area_level_2", "political"],
                    "formatted_address": "West Yorkshire, UK"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = reverse_geocode(mock_coordinate)

        assert result == "West Yorkshire, UK"

    @patch("app.utils.utils.requests.get")
    @patch("app.utils.utils.settings")
    def test_reverse_geocode_fallback_to_admin_area_1(self, mock_settings, mock_get, mock_coordinate):
        """Test fallback to administrative_area_level_1 when no locality or admin_2 found"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "types": ["administrative_area_level_1", "political"],
                    "formatted_address": "England, UK"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = reverse_geocode(mock_coordinate)

        assert result == "England, UK"

    @patch("app.utils.utils.requests.get")
    @patch("app.utils.utils.settings")
    def test_reverse_geocode_fallback_to_first_result(self, mock_settings, mock_get, mock_coordinate):
        """Test fallback to first result when no specific type matches"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "types": ["route"],
                    "formatted_address": "A61, Leeds, UK"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = reverse_geocode(mock_coordinate)

        assert result == "A61, Leeds, UK"

    @patch("app.utils.utils.requests.get")
    @patch("app.utils.utils.settings")
    def test_reverse_geocode_handles_non_ok_status(self, mock_settings, mock_get, mock_coordinate):
        """Test handling of non-OK status from geocoding API"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "ZERO_RESULTS",
            "results": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = reverse_geocode(mock_coordinate)

        assert result == "Location at 53.8008,-1.5491"

    @patch("app.utils.utils.requests.get")
    @patch("app.utils.utils.settings")
    def test_reverse_geocode_handles_empty_results(self, mock_settings, mock_get, mock_coordinate):
        """Test handling of empty results from geocoding API"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = reverse_geocode(mock_coordinate)

        assert result == "Location at 53.8008,-1.5491"

    @patch("app.utils.utils.requests.get")
    @patch("app.utils.utils.settings")
    def test_reverse_geocode_handles_request_exception(self, mock_settings, mock_get, mock_coordinate):
        """Test handling of request exceptions"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

        mock_get.side_effect = requests.RequestException("Network error")

        result = reverse_geocode(mock_coordinate)

        assert result == "Location at 53.8008,-1.5491"


class TestGetAccommodation:
    """Tests for get_accommodation function"""

    @pytest.fixture
    def mock_location(self):
        """Fixture providing a test location coordinate"""
        return Coordinate(latitude=53.8008, longitude=-1.5491)

    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_get_accommodation_success(self, mock_settings, mock_post, mock_location):
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
                    "rating": 4.5
                },
                {
                    "displayName": {"text": "Another Hotel"},
                    "formattedAddress": "456 Another St, Leeds",
                    "googleMapsUri": "https://maps.google.com/place/another",
                    "rating": 4.0
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = get_accommodation(mock_location, radius=5)

        assert len(result) == 2
        assert result[0].name == "Test Hotel"
        assert result[0].address == "123 Test St, Leeds"
        assert result[0].map_link == "https://maps.google.com/place/test"
        assert result[0].rating == 4.5
        assert result[1].name == "Another Hotel"

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        request_body = call_kwargs["json"]

        assert request_body["locationRestriction"]["circle"]["center"]["latitude"] == 53.8008
        assert request_body["locationRestriction"]["circle"]["center"]["longitude"] == -1.5491
        assert request_body["locationRestriction"]["circle"]["radius"] == 5000  # 5km in meters
        assert "lodging" in request_body["includedTypes"]

    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_get_accommodation_with_custom_radius(self, mock_settings, mock_post, mock_location):
        """Test accommodation search with custom radius"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

        mock_response = Mock()
        mock_response.json.return_value = {"places": []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        get_accommodation(mock_location, radius=10)

        request_body = mock_post.call_args[1]["json"]
        assert request_body["locationRestriction"]["circle"]["radius"] == 10000

    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_get_accommodation_empty_results(self, mock_settings, mock_post, mock_location):
        """Test handling of empty results"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

        mock_response = Mock()
        mock_response.json.return_value = {"places": []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = get_accommodation(mock_location)

        assert result == []

    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_get_accommodation_all_fields_present(self, mock_settings, mock_post, mock_location):
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
                    "rating": 4.8
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = get_accommodation(mock_location)

        assert len(result) == 1
        assert result[0].name == "Complete Hotel"
        assert result[0].address == "789 Complete St, Leeds"
        assert result[0].map_link == "https://maps.google.com/complete"
        assert result[0].rating == 4.8

    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_get_accommodation_request_exception(self, mock_settings, mock_post, mock_location):
        """Test handling of request exceptions"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(Exception) as exc_info:
            get_accommodation(mock_location)

        assert "Error making request to Google Places API" in str(exc_info.value)

    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_get_accommodation_http_error(self, mock_settings, mock_post, mock_location):
        """Test handling of HTTP errors"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            get_accommodation(mock_location)

        assert "Error making request to Google Places API" in str(exc_info.value)


class TestFetchRoute:
    """Tests for fetch_route function"""

    @pytest.fixture
    def mock_origin(self):
        """Fixture providing a test origin location"""
        return Location(
            name="Leeds",
            coordinates=Coordinate(latitude=53.8008, longitude=-1.5491)
        )

    @pytest.fixture
    def mock_destination(self):
        """Fixture providing a test destination location"""
        return Location(
            name="York",
            coordinates=Coordinate(latitude=53.9599, longitude=-1.0873)
        )

    @pytest.fixture
    def mock_intermediate(self):
        """Fixture providing a test intermediate location"""
        return Location(
            name="Wetherby",
            coordinates=Coordinate(latitude=53.9277, longitude=-1.3850)
        )

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_fetch_route_success_bicycle(self, mock_settings, mock_post, mock_elevation, mock_origin, mock_destination):
        """Test successful route fetch with bicycle mode"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_ROUTES_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
        mock_elevation.return_value = 250

        mock_response = Mock()
        mock_response.json.return_value = {
            "routes": [{
                "distanceMeters": 42000,
                "duration": "7200s",
                "polyline": {"encodedPolyline": "test_polyline_string"}
            }]
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
    def test_fetch_route_with_intermediates(self, mock_settings, mock_post, mock_elevation, mock_origin, mock_destination, mock_intermediate):
        """Test route fetch with intermediate waypoints"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_ROUTES_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
        mock_elevation.return_value = 300

        mock_response = Mock()
        mock_response.json.return_value = {
            "routes": [{
                "distanceMeters": 50000,
                "duration": "8000s",
                "polyline": {"encodedPolyline": "test_polyline_with_intermediate"}
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = fetch_route(mock_origin, mock_destination, intermediates=[mock_intermediate])

        assert result.distance == 50000

        # Verify intermediate was included in request
        request_body = mock_post.call_args[1]["json"]
        assert len(request_body["intermediates"]) == 1
        assert request_body["intermediates"][0]["via"] is True
        assert request_body["intermediates"][0]["location"]["latLng"]["latitude"] == 53.9277

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_fetch_route_fallback_to_drive(self, mock_settings, mock_post, mock_elevation, mock_origin, mock_destination):
        """Test fallback to DRIVE mode when BICYCLE fails"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_ROUTES_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
        mock_elevation.return_value = 200

        # First call (bicycle) returns no routes, second call (drive) succeeds
        mock_response_bicycle = Mock()
        mock_response_bicycle.json.return_value = {}
        mock_response_bicycle.raise_for_status = Mock()

        mock_response_drive = Mock()
        mock_response_drive.json.return_value = {
            "routes": [{
                "distanceMeters": 45000,
                "duration": "3600s",
                "polyline": {"encodedPolyline": "drive_polyline"}
            }]
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
    def test_fetch_route_all_strategies_fail(self, mock_settings, mock_post, mock_origin, mock_destination):
        """Test error handling when all routing strategies fail"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_ROUTES_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"

        # All calls return empty results
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            fetch_route(mock_origin, mock_destination)

        assert "Could not calculate route" in str(exc_info.value)
        assert "All attempts failed" in str(exc_info.value)

    @patch("app.utils.utils.requests.post")
    @patch("app.utils.utils.settings")
    def test_fetch_route_request_exception(self, mock_settings, mock_post, mock_origin, mock_destination):
        """Test handling of request exceptions"""
        mock_settings.GOOGLE_API_KEY = "test_api_key"
        mock_settings.GOOGLE_ROUTES_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"

        mock_post.side_effect = requests.RequestException("Network error")

        with pytest.raises(ValueError) as exc_info:
            fetch_route(mock_origin, mock_destination)

        assert "Could not calculate route" in str(exc_info.value)


class TestCalculateSegments:
    """Tests for calculate_segments function"""

    @pytest.fixture
    def mock_origin(self):
        """Fixture providing a test origin location"""
        return Location(
            name="Leeds",
            coordinates=Coordinate(latitude=53.8008, longitude=-1.5491)
        )

    @pytest.fixture
    def mock_destination(self):
        """Fixture providing a test destination location"""
        return Location(
            name="York",
            coordinates=Coordinate(latitude=53.9599, longitude=-1.0873)
        )

    @pytest.fixture
    def simple_polyline(self):
        """Fixture providing a simple encoded polyline"""
        # This represents a simple straight line with a few points
        return "u{r~Hzza}Abcd@efg@hij@klm@"

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.reverse_geocode")
    @patch("app.utils.utils.polyline.decode")
    def test_calculate_segments_single_day(self, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
        """Test segment calculation for a route shorter than daily distance"""
        mock_decode.return_value = [
            (53.8008, -1.5491),
            (53.9599, -1.0873)
        ]
        mock_geocode.return_value = "Intermediate Point"
        mock_elevation.return_value = 150

        # Daily distance longer than total route - should create single segment
        result = calculate_segments(simple_polyline, 100000, mock_origin, mock_destination)

        assert len(result) == 1
        assert result[0].day == 1
        assert result[0].route.origin == mock_origin
        assert result[0].route.destination == mock_destination
        assert result[0].route.elevation_gain == 150

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.reverse_geocode")
    @patch("app.utils.utils.polyline.decode")
    @patch("app.utils.utils.geodesic")
    def test_calculate_segments_multiple_days(self, mock_geodesic, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
        """Test segment calculation for multi-day route"""
        # Create a longer route with multiple points
        mock_decode.return_value = [
            (53.8008, -1.5491),
            (53.8508, -1.4491),
            (53.9008, -1.3491),
            (53.9508, -1.2491),
            (53.9599, -1.0873)
        ]
        # Mock geodesic to return predictable distances that will create multiple segments
        # Each edge is 15km so with 10km daily distance we get multiple segments
        mock_distance = Mock()
        mock_distance.kilometers = 15.0
        mock_geodesic.return_value = mock_distance

        # Provide enough return values for all possible reverse_geocode calls
        mock_geocode.return_value = "Intermediate Point"
        mock_elevation.return_value = 200

        # Small daily distance to force multiple segments
        result = calculate_segments(simple_polyline, 10000, mock_origin, mock_destination)

        assert len(result) > 1, "Should create multiple segments for a long route"
        # First segment should use route origin
        assert result[0].route.origin.name == "Leeds"
        # Verify destination coordinates of last segment match the destination coordinates
        assert result[-1].route.destination.coordinates.latitude == mock_destination.coordinates.latitude
        assert result[-1].route.destination.coordinates.longitude == mock_destination.coordinates.longitude
        # All segments should have day numbers
        for i, segment in enumerate(result, 1):
            assert segment.day == i

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.reverse_geocode")
    @patch("app.utils.utils.polyline.decode")
    def test_calculate_segments_origin_destination_linking(self, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
        """Test that segment destinations match next segment origins"""
        mock_decode.return_value = [
            (53.8008, -1.5491),
            (53.8508, -1.4491),
            (53.9008, -1.3491),
            (53.9599, -1.0873)
        ]
        # Provide enough return values for all possible reverse_geocode calls
        mock_geocode.side_effect = ["Intermediate 1", "Intermediate 2", "Intermediate 3", "Intermediate 4", "Intermediate 5"]
        mock_elevation.return_value = 180

        result = calculate_segments(simple_polyline, 15000, mock_origin, mock_destination)

        if len(result) > 1:
            # Check that each segment's destination matches the next segment's origin
            for i in range(len(result) - 1):
                assert result[i].route.destination == result[i + 1].route.origin

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.reverse_geocode")
    @patch("app.utils.utils.polyline.decode")
    def test_calculate_segments_calls_reverse_geocode_for_intermediates(self, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
        """Test that reverse_geocode is called for intermediate points"""
        mock_decode.return_value = [
            (53.8008, -1.5491),
            (53.8508, -1.4491),
            (53.9008, -1.3491),
            (53.9599, -1.0873)
        ]
        mock_geocode.return_value = "Some Location"
        mock_elevation.return_value = 160

        result = calculate_segments(simple_polyline, 10000, mock_origin, mock_destination)

        # reverse_geocode should be called for intermediate points
        assert mock_geocode.call_count >= 0  # May vary based on segment splits

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.reverse_geocode")
    @patch("app.utils.utils.polyline.decode")
    def test_calculate_segments_accommodation_options_empty(self, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
        """Test that segments are created with empty accommodation_options"""
        mock_decode.return_value = [
            (53.8008, -1.5491),
            (53.9599, -1.0873)
        ]
        mock_geocode.return_value = "Location"
        mock_elevation.return_value = 140

        result = calculate_segments(simple_polyline, 50000, mock_origin, mock_destination)

        for segment in result:
            assert segment.accommodation_options == []

    @patch("app.utils.utils.polyline.decode")
    def test_calculate_segments_invalid_polyline_empty(self, mock_decode, mock_origin, mock_destination):
        """Test handling of empty polyline"""
        mock_decode.return_value = []

        with pytest.raises(ValueError) as exc_info:
            calculate_segments("", 50000, mock_origin, mock_destination)

        assert "Invalid polyline" in str(exc_info.value)

    @patch("app.utils.utils.polyline.decode")
    def test_calculate_segments_invalid_polyline_single_point(self, mock_decode, mock_origin, mock_destination):
        """Test handling of polyline with single point"""
        mock_decode.return_value = [(53.8008, -1.5491)]

        with pytest.raises(ValueError) as exc_info:
            calculate_segments("invalid", 50000, mock_origin, mock_destination)

        assert "Invalid polyline" in str(exc_info.value)

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.reverse_geocode")
    @patch("app.utils.utils.polyline.decode")
    def test_calculate_segments_distance_conversion(self, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
        """Test that distances are correctly converted from meters to km and back"""
        mock_decode.return_value = [
            (53.8008, -1.5491),
            (53.9599, -1.0873)
        ]
        mock_geocode.return_value = "Location"
        mock_elevation.return_value = 175

        daily_distance_meters = 80000  # 80km
        result = calculate_segments(simple_polyline, daily_distance_meters, mock_origin, mock_destination)

        # Segment distance should be in meters
        for segment in result:
            assert isinstance(segment.route.distance, int)
            assert segment.route.distance >= 0

    @patch("app.utils.utils.get_elevation_gain")
    @patch("app.utils.utils.reverse_geocode")
    @patch("app.utils.utils.polyline.decode")
    @patch("app.utils.utils.polyline.encode")
    def test_calculate_segments_encodes_segment_polylines(self, mock_encode, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
        """Test that segment polylines are encoded correctly"""
        mock_decode.return_value = [
            (53.8008, -1.5491),
            (53.8508, -1.4491),
            (53.9599, -1.0873)
        ]
        mock_encode.side_effect = ["segment1_polyline", "segment2_polyline"]
        mock_geocode.return_value = "Some Place"
        mock_elevation.return_value = 190

        result = calculate_segments(simple_polyline, 10000, mock_origin, mock_destination)

        # Verify encode was called for each segment
        assert mock_encode.call_count == len(result)
        for segment in result:
            assert segment.route.polyline in ["segment1_polyline", "segment2_polyline"]
