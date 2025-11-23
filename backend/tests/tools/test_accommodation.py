"""Tests for app.tools.accommodation module."""

import pytest
from unittest.mock import patch, Mock
from pydantic_extra_types.coordinate import Coordinate

from app.tools.accommodation import (
    find_accommodation_at_location,
    search_accommodation_for_day,
)
from app.models.models import Accommodation


class TestFindAccommodationAtLocation:
    """Tests for find_accommodation_at_location tool."""

    @patch("app.tools.accommodation.get_accommodation")
    @patch("app.tools.accommodation.geocode_location")
    def test_find_accommodation_success(self, mock_geocode, mock_get_accommodation, sample_accommodation):
        """Test successful accommodation search at a location."""
        mock_geocode.return_value = Coordinate(latitude=48.8566, longitude=2.3522)
        mock_get_accommodation.return_value = [sample_accommodation]

        result = find_accommodation_at_location.invoke({
            "place_name": "Paris, France",
        })

        assert len(result) == 1
        assert result[0].name == "Test Hotel"
        mock_geocode.assert_called_once_with("Paris, France")
        mock_get_accommodation.assert_called_once()

    @patch("app.tools.accommodation.get_accommodation")
    @patch("app.tools.accommodation.geocode_location")
    def test_find_accommodation_with_custom_radius(self, mock_geocode, mock_get_accommodation, sample_accommodation):
        """Test accommodation search with custom radius."""
        mock_geocode.return_value = Coordinate(latitude=48.8566, longitude=2.3522)
        mock_get_accommodation.return_value = [sample_accommodation]

        result = find_accommodation_at_location.invoke({
            "place_name": "Lyon, France",
            "radius_km": 10,
        })

        assert len(result) == 1
        mock_geocode.assert_called_once_with("Lyon, France")
        mock_get_accommodation.assert_called_once_with(
            mock_geocode.return_value, radius=10
        )

    @patch("app.tools.accommodation.get_accommodation")
    @patch("app.tools.accommodation.geocode_location")
    def test_find_accommodation_none_found(self, mock_geocode, mock_get_accommodation):
        """Test accommodation search when none are found."""
        mock_geocode.return_value = Coordinate(latitude=48.8566, longitude=2.3522)
        mock_get_accommodation.return_value = []

        result = find_accommodation_at_location.invoke({
            "place_name": "Remote Place",
        })

        assert result == []

    @patch("app.tools.accommodation.geocode_location")
    def test_find_accommodation_location_not_found(self, mock_geocode):
        """Test accommodation search when location cannot be found."""
        mock_geocode.side_effect = ValueError("Could not find location")

        with pytest.raises(ValueError, match="Could not find location"):
            find_accommodation_at_location.invoke({
                "place_name": "NonexistentPlace12345",
            })


class TestSearchAccommodationForDay:
    """Tests for search_accommodation_for_day tool."""

    @patch("app.tools.accommodation.get_accommodation")
    @patch("app.tools.accommodation.validate_segments_state")
    def test_search_accommodation_for_day_success(
        self, mock_validate_segments, mock_get_accommodation, mock_runtime, sample_segment, sample_accommodation
    ):
        """Test successful accommodation search for a specific day."""
        from app.tools.accommodation import search_accommodation_for_day as search_fn

        mock_validate_segments.return_value = [sample_segment]
        mock_get_accommodation.return_value = [sample_accommodation]

        result = search_fn.func(mock_runtime, 1)

        assert len(result) == 1
        assert result[0].name == "Test Hotel"
        mock_validate_segments.assert_called_once_with(mock_runtime)
        mock_get_accommodation.assert_called_once_with(
            sample_segment.route.destination, radius=10
        )

    @patch("app.tools.accommodation.get_accommodation")
    @patch("app.tools.accommodation.validate_segments_state")
    def test_search_accommodation_with_custom_radius(
        self, mock_validate_segments, mock_get_accommodation, mock_runtime, sample_segment, sample_accommodation
    ):
        """Test accommodation search with custom radius."""
        from app.tools.accommodation import search_accommodation_for_day as search_fn

        mock_validate_segments.return_value = [sample_segment]
        mock_get_accommodation.return_value = [sample_accommodation]

        result = search_fn.func(mock_runtime, 1, 20)

        assert len(result) == 1
        mock_get_accommodation.assert_called_once_with(
            sample_segment.route.destination, radius=20
        )

    @patch("app.tools.accommodation.validate_segments_state")
    def test_search_accommodation_invalid_day_number_too_low(
        self, mock_validate_segments, mock_runtime, sample_segment
    ):
        """Test accommodation search with invalid day number (too low)."""
        from app.tools.accommodation import search_accommodation_for_day as search_fn

        mock_validate_segments.return_value = [sample_segment]

        with pytest.raises(ValueError, match="Invalid day number 0"):
            search_fn.func(mock_runtime, 0)

    @patch("app.tools.accommodation.validate_segments_state")
    def test_search_accommodation_invalid_day_number_too_high(
        self, mock_validate_segments, mock_runtime, sample_segment
    ):
        """Test accommodation search with invalid day number (too high)."""
        from app.tools.accommodation import search_accommodation_for_day as search_fn

        mock_validate_segments.return_value = [sample_segment]

        with pytest.raises(ValueError, match="Invalid day number 5. Route has 1 days"):
            search_fn.func(mock_runtime, 5)

    @patch("app.tools.accommodation.get_accommodation")
    @patch("app.tools.accommodation.validate_segments_state")
    def test_search_accommodation_none_found(
        self, mock_validate_segments, mock_get_accommodation, mock_runtime, sample_segment
    ):
        """Test accommodation search when none are found."""
        from app.tools.accommodation import search_accommodation_for_day as search_fn

        mock_validate_segments.return_value = [sample_segment]
        mock_get_accommodation.return_value = []

        result = search_fn.func(mock_runtime, 1)

        assert result == []
