"""Tests for app.tools.route module."""

import pytest
from unittest.mock import patch, Mock
from pydantic_extra_types.coordinate import Coordinate
from langgraph.types import Command

from app.tools.route import (
    get_route_summary,
    adjust_daily_distance,
    add_intermediate_waypoint,
    remove_intermediate_waypoint,
    recalculate_complete_route,
)
from app.models.models import Location, Segment, Route


class TestGetRouteSummary:
    """Tests for get_route_summary tool."""

    @patch("app.tools.route.validate_segments_state")
    @patch("app.tools.route.validate_route_state")
    def test_get_route_summary_success(
        self, mock_validate_route, mock_validate_segments, mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test successful route summary retrieval."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_validate_segments.return_value = [sample_segment]

        result = get_route_summary.func(mock_runtime)

        assert result["total_distance_km"] == 450.0
        assert result["total_elevation_gain_m"] == 2500
        assert result["num_days"] == 1
        assert result["avg_distance_km"] == 450.0
        assert result["target_daily_distance_km"] == 80
        assert result["days_with_accommodation"] == 1
        assert result["days_without_accommodation"] == []
        assert result["origin"] == "Paris, France"
        assert result["destination"] == "Lyon, France"
        assert result["num_intermediates"] == 0

    @patch("app.tools.route.validate_segments_state")
    @patch("app.tools.route.validate_route_state")
    def test_get_route_summary_with_missing_accommodation(
        self, mock_validate_route, mock_validate_segments, mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test route summary with days missing accommodation."""
        segment_no_accommodation = Segment(day=2, route=sample_route, accommodation_options=[])
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_validate_segments.return_value = [sample_segment, segment_no_accommodation]

        result = get_route_summary.func(mock_runtime)

        assert result["num_days"] == 2
        assert result["days_with_accommodation"] == 1
        assert result["days_without_accommodation"] == [2]


class TestAdjustDailyDistance:
    """Tests for adjust_daily_distance tool."""

    @patch("app.tools.route.recalculate_segments_with_accommodation")
    @patch("app.tools.route.validate_route_state")
    def test_adjust_daily_distance_success(
        self, mock_validate_route, mock_recalculate, mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test successful daily distance adjustment."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_recalculate.return_value = [sample_segment]

        result = adjust_daily_distance.func(mock_runtime, 100)

        assert isinstance(result, Command)
        assert "segments" in result.update
        assert "requirements" in result.update
        assert result.update["requirements"].daily_distance_km == 100
        mock_recalculate.assert_called_once_with(sample_route, 100)

    @patch("app.tools.route.validate_route_state")
    def test_adjust_daily_distance_too_low(
        self, mock_validate_route, mock_runtime, sample_route, sample_requirements
    ):
        """Test daily distance adjustment with value too low."""
        mock_validate_route.return_value = (sample_route, sample_requirements)

        with pytest.raises(ValueError, match="Daily distance must be between 20km and 200km"):
            adjust_daily_distance.func(mock_runtime, 10)

    @patch("app.tools.route.validate_route_state")
    def test_adjust_daily_distance_too_high(
        self, mock_validate_route, mock_runtime, sample_route, sample_requirements
    ):
        """Test daily distance adjustment with value too high."""
        mock_validate_route.return_value = (sample_route, sample_requirements)

        with pytest.raises(ValueError, match="Daily distance must be between 20km and 200km"):
            adjust_daily_distance.func(mock_runtime, 250)


class TestAddIntermediateWaypoint:
    """Tests for add_intermediate_waypoint tool."""

    @patch("app.tools.route.recalculate_segments_with_accommodation")
    @patch("app.tools.route.fetch_route")
    @patch("app.tools.route.geocode_location")
    @patch("app.tools.route.validate_route_state")
    def test_add_intermediate_waypoint_success(
        self, mock_validate_route, mock_geocode, mock_fetch_route, mock_recalculate,
        mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test successful addition of intermediate waypoint."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_geocode.return_value = Coordinate(latitude=47.0, longitude=3.0)
        mock_fetch_route.return_value = sample_route
        mock_recalculate.return_value = [sample_segment]

        result = add_intermediate_waypoint.func(mock_runtime, "Dijon, France")

        assert isinstance(result, Command)
        assert "route" in result.update
        assert "segments" in result.update
        assert "requirements" in result.update
        assert len(result.update["requirements"].intermediates) == 1
        assert result.update["requirements"].intermediates[0].name == "Dijon, France"

    @patch("app.tools.route.recalculate_segments_with_accommodation")
    @patch("app.tools.route.fetch_route")
    @patch("app.tools.route.geocode_location")
    @patch("app.tools.route.validate_route_state")
    def test_add_intermediate_waypoint_at_position(
        self, mock_validate_route, mock_geocode, mock_fetch_route, mock_recalculate,
        mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test adding waypoint at specific position."""
        # Add an existing intermediate
        sample_requirements.intermediates = [
            Location(name="Existing", coordinates=Coordinate(latitude=46.0, longitude=3.5))
        ]
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_geocode.return_value = Coordinate(latitude=47.0, longitude=3.0)
        mock_fetch_route.return_value = sample_route
        mock_recalculate.return_value = [sample_segment]

        result = add_intermediate_waypoint.func(mock_runtime, "Dijon, France", 0)

        assert len(result.update["requirements"].intermediates) == 2
        assert result.update["requirements"].intermediates[0].name == "Dijon, France"
        assert result.update["requirements"].intermediates[1].name == "Existing"

    @patch("app.tools.route.geocode_location")
    @patch("app.tools.route.validate_route_state")
    def test_add_intermediate_waypoint_geocoding_fails(
        self, mock_validate_route, mock_geocode, mock_runtime, sample_route, sample_requirements
    ):
        """Test adding waypoint when geocoding fails."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_geocode.side_effect = Exception("Location not found")

        with pytest.raises(ValueError, match="Failed to add waypoint"):
            add_intermediate_waypoint.func(mock_runtime, "InvalidPlace12345")

    @patch("app.tools.route.geocode_location")
    @patch("app.tools.route.validate_route_state")
    def test_add_intermediate_waypoint_invalid_position(
        self, mock_validate_route, mock_geocode, mock_runtime, sample_route, sample_requirements
    ):
        """Test adding waypoint with invalid position."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_geocode.return_value = Coordinate(latitude=47.0, longitude=3.0)

        with pytest.raises(ValueError, match="Insert position .* out of range"):
            add_intermediate_waypoint.func(mock_runtime, "Dijon, France", 10)


class TestRemoveIntermediateWaypoint:
    """Tests for remove_intermediate_waypoint tool."""

    @patch("app.tools.route.recalculate_segments_with_accommodation")
    @patch("app.tools.route.fetch_route")
    @patch("app.tools.route.validate_route_state")
    def test_remove_intermediate_waypoint_success(
        self, mock_validate_route, mock_fetch_route, mock_recalculate,
        mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test successful removal of intermediate waypoint."""
        # Add intermediates to remove
        sample_requirements.intermediates = [
            Location(name="Waypoint1", coordinates=Coordinate(latitude=47.0, longitude=3.0)),
            Location(name="Waypoint2", coordinates=Coordinate(latitude=46.0, longitude=3.5)),
        ]
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_fetch_route.return_value = sample_route
        mock_recalculate.return_value = [sample_segment]

        result = remove_intermediate_waypoint.func(mock_runtime, 0)

        assert isinstance(result, Command)
        assert len(result.update["requirements"].intermediates) == 1
        assert result.update["requirements"].intermediates[0].name == "Waypoint2"

    @patch("app.tools.route.validate_route_state")
    def test_remove_intermediate_waypoint_no_intermediates(
        self, mock_validate_route, mock_runtime, sample_route, sample_requirements
    ):
        """Test removing waypoint when there are no intermediates."""
        sample_requirements.intermediates = []
        mock_validate_route.return_value = (sample_route, sample_requirements)

        with pytest.raises(ValueError, match="No intermediate waypoints to remove"):
            remove_intermediate_waypoint.func(mock_runtime, 0)

    @patch("app.tools.route.validate_route_state")
    def test_remove_intermediate_waypoint_invalid_index(
        self, mock_validate_route, mock_runtime, sample_route, sample_requirements
    ):
        """Test removing waypoint with invalid index."""
        sample_requirements.intermediates = [
            Location(name="Waypoint1", coordinates=Coordinate(latitude=47.0, longitude=3.0)),
        ]
        mock_validate_route.return_value = (sample_route, sample_requirements)

        with pytest.raises(ValueError, match="Invalid waypoint index"):
            remove_intermediate_waypoint.func(mock_runtime, 5)


class TestRecalculateCompleteRoute:
    """Tests for recalculate_complete_route tool."""

    @patch("app.tools.route.recalculate_segments_with_accommodation")
    @patch("app.tools.route.fetch_route")
    @patch("app.tools.route.geocode_location")
    @patch("app.tools.route.validate_route_state")
    def test_recalculate_complete_route_new_origin_destination(
        self, mock_validate_route, mock_geocode, mock_fetch_route, mock_recalculate,
        mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test complete route recalculation with new origin and destination."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_geocode.side_effect = [
            Coordinate(latitude=50.0, longitude=3.0),  # New origin
            Coordinate(latitude=43.0, longitude=5.0),  # New destination
        ]
        mock_fetch_route.return_value = sample_route
        mock_recalculate.return_value = [sample_segment]

        result = recalculate_complete_route.func(mock_runtime, "Brussels, Belgium", "Marseille, France")

        assert isinstance(result, Command)
        assert result.update["requirements"].origin.name == "Brussels, Belgium"
        assert result.update["requirements"].destination.name == "Marseille, France"

    @patch("app.tools.route.recalculate_segments_with_accommodation")
    @patch("app.tools.route.fetch_route")
    @patch("app.tools.route.convert_place_names_to_locations")
    @patch("app.tools.route.validate_route_state")
    def test_recalculate_complete_route_with_intermediates(
        self, mock_validate_route, mock_convert_places, mock_fetch_route, mock_recalculate,
        mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test complete route recalculation with intermediate waypoints."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_convert_places.return_value = [
            Location(name="Lyon", coordinates=Coordinate(latitude=45.764, longitude=4.8357)),
            Location(name="Dijon", coordinates=Coordinate(latitude=47.0, longitude=3.0)),
        ]
        mock_fetch_route.return_value = sample_route
        mock_recalculate.return_value = [sample_segment]

        result = recalculate_complete_route.func(mock_runtime, None, None, ["Lyon", "Dijon"])

        assert len(result.update["requirements"].intermediates) == 2
        assert result.update["requirements"].intermediates[0].name == "Lyon"

    @patch("app.tools.route.recalculate_segments_with_accommodation")
    @patch("app.tools.route.fetch_route")
    @patch("app.tools.route.validate_route_state")
    def test_recalculate_complete_route_keep_existing(
        self, mock_validate_route, mock_fetch_route, mock_recalculate,
        mock_runtime, sample_route, sample_requirements, sample_segment
    ):
        """Test complete route recalculation keeping existing values."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_fetch_route.return_value = sample_route
        mock_recalculate.return_value = [sample_segment]

        result = recalculate_complete_route.func(mock_runtime)

        # Should keep existing origin, destination, and intermediates
        assert result.update["requirements"].origin == sample_requirements.origin
        assert result.update["requirements"].destination == sample_requirements.destination

    @patch("app.tools.route.geocode_location")
    @patch("app.tools.route.validate_route_state")
    def test_recalculate_complete_route_geocoding_fails(
        self, mock_validate_route, mock_geocode, mock_runtime, sample_route, sample_requirements
    ):
        """Test complete route recalculation when geocoding fails."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_geocode.side_effect = Exception("Location not found")

        with pytest.raises(ValueError, match="Failed to geocode new origin"):
            recalculate_complete_route.func(mock_runtime, "InvalidPlace12345")

    @patch("app.tools.route.validate_route_state")
    @patch("app.tools.route.fetch_route")
    @patch("app.tools.route.geocode_location")
    def test_recalculate_complete_route_fetch_fails(
        self, mock_geocode, mock_fetch_route, mock_validate_route,
        mock_runtime, sample_route, sample_requirements
    ):
        """Test complete route recalculation when route fetch fails."""
        mock_validate_route.return_value = (sample_route, sample_requirements)
        mock_geocode.return_value = Coordinate(latitude=50.0, longitude=3.0)
        mock_fetch_route.side_effect = Exception("Route calculation failed")

        with pytest.raises(ValueError, match="Failed to calculate new route"):
            recalculate_complete_route.func(mock_runtime, "Brussels, Belgium")
