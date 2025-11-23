"""Tests for app.tools.segment module."""

import pytest
from unittest.mock import patch

from app.tools.segment import get_segment_details


class TestGetSegmentDetails:
    """Tests for get_segment_details tool."""

    @patch("app.tools.segment.validate_segments_state")
    def test_get_segment_details_success(
        self, mock_validate_segments, mock_runtime, sample_segment, sample_accommodation
    ):
        """Test successful retrieval of segment details."""
        mock_validate_segments.return_value = [sample_segment]

        result = get_segment_details.func(mock_runtime, 1)

        assert result["day"] == 1
        assert result["distance_km"] == 450.0
        assert result["elevation_gain_m"] == 2500
        assert result["accommodation_count"] == 1
        assert result["has_accommodation"] is True
        assert len(result["accommodation_options"]) == 1
        assert result["accommodation_options"][0]["name"] == sample_accommodation.name

    @patch("app.tools.segment.validate_segments_state")
    def test_get_segment_details_with_coordinates(
        self, mock_validate_segments, mock_runtime, sample_segment
    ):
        """Test segment details include origin and destination coordinates."""
        mock_validate_segments.return_value = [sample_segment]

        result = get_segment_details.func(mock_runtime, 1)

        assert "origin" in result
        assert "latitude" in result["origin"]
        assert "longitude" in result["origin"]
        assert "destination" in result
        assert "latitude" in result["destination"]
        assert "longitude" in result["destination"]

    @patch("app.tools.segment.validate_segments_state")
    def test_get_segment_details_no_accommodation(
        self, mock_validate_segments, mock_runtime, sample_segment
    ):
        """Test segment details when no accommodation is available."""
        sample_segment.accommodation_options = []
        mock_validate_segments.return_value = [sample_segment]

        result = get_segment_details.func(mock_runtime, 1)

        assert result["accommodation_count"] == 0
        assert result["has_accommodation"] is False
        assert result["accommodation_options"] == []

    @patch("app.tools.segment.validate_segments_state")
    def test_get_segment_details_invalid_day_too_low(
        self, mock_validate_segments, mock_runtime, sample_segment
    ):
        """Test segment details with invalid day number (too low)."""
        mock_validate_segments.return_value = [sample_segment]

        with pytest.raises(ValueError, match="Invalid day number 0"):
            get_segment_details.func(mock_runtime, 0)

    @patch("app.tools.segment.validate_segments_state")
    def test_get_segment_details_invalid_day_too_high(
        self, mock_validate_segments, mock_runtime, sample_segment
    ):
        """Test segment details with invalid day number (too high)."""
        mock_validate_segments.return_value = [sample_segment]

        with pytest.raises(ValueError, match="Invalid day number 5. Route has 1 days"):
            get_segment_details.func(mock_runtime, 5)

    @patch("app.tools.segment.validate_segments_state")
    def test_get_segment_details_multiple_segments(
        self, mock_validate_segments, mock_runtime, sample_segment, sample_route
    ):
        """Test retrieving details from a multi-segment route."""
        from app.models.models import Segment

        segment2 = Segment(day=2, route=sample_route, accommodation_options=[])
        mock_validate_segments.return_value = [sample_segment, segment2]

        result = get_segment_details.func(mock_runtime, 2)

        assert result["day"] == 2
        assert result["has_accommodation"] is False
