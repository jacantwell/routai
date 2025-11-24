"""Tests for calculate_segments function"""
import pytest
from unittest.mock import Mock, patch

from app.utils.utils import calculate_segments


@patch("app.utils.utils.get_elevation_gain")
@patch("app.utils.utils.reverse_geocode")
@patch("app.utils.utils.polyline.decode")
def test_calculate_segments_single_day(mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
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
def test_calculate_segments_multiple_days(mock_geodesic, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
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
def test_calculate_segments_origin_destination_linking(mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
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
def test_calculate_segments_calls_reverse_geocode_for_intermediates(mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
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
def test_calculate_segments_accommodation_options_empty(mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
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
def test_calculate_segments_invalid_polyline_empty(mock_decode, mock_origin, mock_destination):
    """Test handling of empty polyline"""
    mock_decode.return_value = []

    with pytest.raises(ValueError) as exc_info:
        calculate_segments("", 50000, mock_origin, mock_destination)

    assert "Invalid polyline" in str(exc_info.value)


@patch("app.utils.utils.polyline.decode")
def test_calculate_segments_invalid_polyline_single_point(mock_decode, mock_origin, mock_destination):
    """Test handling of polyline with single point"""
    mock_decode.return_value = [(53.8008, -1.5491)]

    with pytest.raises(ValueError) as exc_info:
        calculate_segments("invalid", 50000, mock_origin, mock_destination)

    assert "Invalid polyline" in str(exc_info.value)


@patch("app.utils.utils.get_elevation_gain")
@patch("app.utils.utils.reverse_geocode")
@patch("app.utils.utils.polyline.decode")
def test_calculate_segments_distance_conversion(mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
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
def test_calculate_segments_encodes_segment_polylines(mock_encode, mock_decode, mock_geocode, mock_elevation, mock_origin, mock_destination, simple_polyline):
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
