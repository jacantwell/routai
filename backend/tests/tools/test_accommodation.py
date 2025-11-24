import pytest
from unittest.mock import patch, Mock
from pydantic_extra_types.coordinate import Coordinate

from app.tools.accommodation import (
    find_accommodation_at_location,
    search_accommodation_for_day,
)
from app.models import Accommodation


@patch("app.tools.accommodation.get_accommodation")
@patch("app.tools.accommodation.geocode_location")
def test_find_accommodation_at_location_success(mock_geocode, mock_get_accommodation):
    """Test successful accommodation search at location"""
    mock_geocode.return_value = Coordinate(latitude=48.8566, longitude=2.3522)
    mock_get_accommodation.return_value = [
        Accommodation(
            name="Paris Hotel",
            address="123 Paris St",
            map_link="https://maps.google.com/paris",
            rating=4.5,
        )
    ]

    result = find_accommodation_at_location.invoke({"place_name": "Paris, France"})

    assert len(result) == 1
    assert result[0].name == "Paris Hotel"
    mock_geocode.assert_called_once_with("Paris, France")
    mock_get_accommodation.assert_called_once_with(
        Coordinate(latitude=48.8566, longitude=2.3522), radius=5
    )


@patch("app.tools.accommodation.get_accommodation")
@patch("app.tools.accommodation.geocode_location")
def test_find_accommodation_with_custom_radius(mock_geocode, mock_get_accommodation):
    """Test accommodation search with custom radius"""
    mock_geocode.return_value = Coordinate(latitude=51.5074, longitude=-0.1278)
    mock_get_accommodation.return_value = []

    result = find_accommodation_at_location.invoke(
        {"place_name": "London, UK", "radius_km": 10}
    )

    assert result == []
    mock_geocode.assert_called_once_with("London, UK")
    mock_get_accommodation.assert_called_once_with(
        Coordinate(latitude=51.5074, longitude=-0.1278), radius=10
    )


@patch("app.tools.accommodation.get_accommodation")
@patch("app.tools.accommodation.geocode_location")
def test_find_accommodation_multiple_results(mock_geocode, mock_get_accommodation):
    """Test accommodation search returning multiple results"""
    mock_geocode.return_value = Coordinate(latitude=53.8008, longitude=-1.5491)
    mock_get_accommodation.return_value = [
        Accommodation(
            name="Hotel A",
            address="123 A St",
            map_link="https://maps.google.com/a",
            rating=4.5,
        ),
        Accommodation(
            name="Hotel B",
            address="456 B St",
            map_link="https://maps.google.com/b",
            rating=4.0,
        ),
    ]

    result = find_accommodation_at_location.invoke({"place_name": "Leeds, UK"})

    assert len(result) == 2
    assert result[0].name == "Hotel A"
    assert result[1].name == "Hotel B"


@patch("app.tools.accommodation.get_accommodation")
@patch("app.tools.accommodation.geocode_location")
def test_find_accommodation_geocoding_error(mock_geocode, mock_get_accommodation):
    """Test error handling when geocoding fails"""
    mock_geocode.side_effect = ValueError("Could not find location")

    with pytest.raises(ValueError) as exc_info:
        find_accommodation_at_location.invoke({"place_name": "InvalidLocation123"})

    assert "Could not find location" in str(exc_info.value)
    mock_get_accommodation.assert_not_called()


@patch("app.tools.accommodation.get_accommodation")
@patch("app.tools.accommodation.validate_segments_state")
def test_search_accommodation_for_day_success(
    mock_validate_segments, mock_get_accommodation, mock_runtime_with_segments
):
    """Test successful accommodation search for a specific day"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]
    mock_get_accommodation.return_value = [
        Accommodation(
            name="Day 1 Hotel",
            address="123 Day 1 St",
            map_link="https://maps.google.com/day1",
            rating=4.5,
        )
    ]

    result = search_accommodation_for_day.func(
        runtime=mock_runtime_with_segments, day_number=1
    )

    assert len(result) == 1
    assert result[0].name == "Day 1 Hotel"
    mock_validate_segments.assert_called_once_with(mock_runtime_with_segments)
    mock_get_accommodation.assert_called_once_with(segment.route.destination, radius=10)


@patch("app.tools.accommodation.get_accommodation")
@patch("app.tools.accommodation.validate_segments_state")
def test_search_accommodation_for_day_custom_radius(
    mock_validate_segments, mock_get_accommodation, mock_runtime_with_segments
):
    """Test accommodation search with custom radius"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]
    mock_get_accommodation.return_value = []

    result = search_accommodation_for_day.func(
        runtime=mock_runtime_with_segments, day_number=1, search_radius_km=15
    )

    assert result == []
    mock_get_accommodation.assert_called_once_with(segment.route.destination, radius=15)


@patch("app.tools.accommodation.validate_segments_state")
def test_search_accommodation_for_day_invalid_day_number(
    mock_validate_segments, mock_runtime_with_segments
):
    """Test error handling for invalid day number"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]

    with pytest.raises(ValueError) as exc_info:
        search_accommodation_for_day.func(
            runtime=mock_runtime_with_segments, day_number=5
        )

    assert "Invalid day number 5" in str(exc_info.value)
    assert "Route has 1 days" in str(exc_info.value)


@patch("app.tools.accommodation.validate_segments_state")
def test_search_accommodation_for_day_zero_day_number(
    mock_validate_segments, mock_runtime_with_segments
):
    """Test error handling for day number less than 1"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]

    with pytest.raises(ValueError) as exc_info:
        search_accommodation_for_day.func(
            runtime=mock_runtime_with_segments, day_number=0
        )

    assert "Invalid day number 0" in str(exc_info.value)
