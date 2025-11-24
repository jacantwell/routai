from unittest.mock import Mock, patch

import pytest
from langgraph.types import Command
from pydantic_extra_types.coordinate import Coordinate

from app.tools.route import (add_intermediate_waypoint, adjust_daily_distance,
                             confirm_route, get_route_summary,
                             recalculate_complete_route,
                             remove_intermediate_waypoint)


def test_confirm_route_success(mock_runtime):
    """Test successful route confirmation"""
    result = confirm_route.func(runtime=mock_runtime)

    assert isinstance(result, Command)
    assert result.update["user_confirmed"] is True
    assert len(result.update["messages"]) == 1
    assert "Route confirmed" in result.update["messages"][0].content


@patch("app.tools.route.validate_segments_state")
@patch("app.tools.route.validate_route_state")
def test_get_route_summary_success(
    mock_validate_route, mock_validate_segments, mock_runtime_with_segments
):
    """Test successful route summary retrieval"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements
    segments = mock_runtime_with_segments.state.segments

    mock_validate_route.return_value = (route, requirements)
    mock_validate_segments.return_value = segments

    result = get_route_summary.func(runtime=mock_runtime_with_segments)

    assert result["total_distance_km"] == 42.0
    assert result["total_elevation_gain_m"] == 250
    assert result["num_days"] == 1
    assert result["avg_distance_km"] == 42.0
    assert result["target_daily_distance_km"] == 80
    assert result["days_with_accommodation"] == 1
    assert result["days_without_accommodation"] == []
    assert result["origin"] == "Leeds"
    assert result["destination"] == "York"
    assert result["num_intermediates"] == 0


@patch("app.tools.route.validate_segments_state")
@patch("app.tools.route.validate_route_state")
def test_get_route_summary_with_missing_accommodation(
    mock_validate_route, mock_validate_segments, mock_runtime_with_segments, mock_route
):
    """Test route summary with days missing accommodation"""
    from app.models import Segment

    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    segment_with_accommodation = mock_runtime_with_segments.state.segments[0]
    segment_without_accommodation = Segment(
        day=2, route=mock_route, accommodation_options=[]
    )
    segments = [segment_with_accommodation, segment_without_accommodation]

    mock_validate_route.return_value = (route, requirements)
    mock_validate_segments.return_value = segments

    result = get_route_summary.func(runtime=mock_runtime_with_segments)

    assert result["num_days"] == 2
    assert result["days_with_accommodation"] == 1
    assert result["days_without_accommodation"] == [2]


@patch("app.tools.route.recalculate_segments_with_accommodation")
@patch("app.tools.route.validate_route_state")
def test_adjust_daily_distance_success(
    mock_validate_route, mock_recalculate, mock_runtime_with_segments, mock_segment
):
    """Test successful daily distance adjustment"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_recalculate.return_value = [mock_segment]

    result = adjust_daily_distance.func(
        runtime=mock_runtime_with_segments, new_daily_distance_km=60
    )

    assert isinstance(result, Command)
    assert "segments" in result.update
    assert "requirements" in result.update
    assert result.update["requirements"].daily_distance_km == 60
    mock_recalculate.assert_called_once_with(route, 60)


@patch("app.tools.route.validate_route_state")
def test_adjust_daily_distance_too_low(mock_validate_route, mock_runtime_with_segments):
    """Test error when daily distance is too low"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements
    mock_validate_route.return_value = (route, requirements)

    with pytest.raises(ValueError) as exc_info:
        adjust_daily_distance.func(
            runtime=mock_runtime_with_segments, new_daily_distance_km=10
        )

    assert "must be between 20km and 200km" in str(exc_info.value)


@patch("app.tools.route.validate_route_state")
def test_adjust_daily_distance_too_high(
    mock_validate_route, mock_runtime_with_segments
):
    """Test error when daily distance is too high"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements
    mock_validate_route.return_value = (route, requirements)

    with pytest.raises(ValueError) as exc_info:
        adjust_daily_distance.func(
            runtime=mock_runtime_with_segments, new_daily_distance_km=250
        )

    assert "must be between 20km and 200km" in str(exc_info.value)


@patch("app.tools.route.recalculate_segments_with_accommodation")
@patch("app.tools.route.fetch_route")
@patch("app.tools.route.geocode_location")
@patch("app.tools.route.validate_route_state")
def test_add_intermediate_waypoint_success(
    mock_validate_route,
    mock_geocode,
    mock_fetch_route,
    mock_recalculate,
    mock_runtime_with_segments,
    mock_route,
    mock_segment,
):
    """Test successful addition of intermediate waypoint"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_geocode.return_value = Coordinate(latitude=53.9277, longitude=-1.3850)
    mock_fetch_route.return_value = mock_route
    mock_recalculate.return_value = [mock_segment]

    result = add_intermediate_waypoint.func(
        runtime=mock_runtime_with_segments, waypoint_name="Wetherby"
    )

    assert isinstance(result, Command)
    assert "route" in result.update
    assert "segments" in result.update
    assert "requirements" in result.update
    assert len(result.update["requirements"].intermediates) == 1
    assert result.update["requirements"].intermediates[0].name == "Wetherby"
    mock_geocode.assert_called_once_with("Wetherby")


@patch("app.tools.route.recalculate_segments_with_accommodation")
@patch("app.tools.route.fetch_route")
@patch("app.tools.route.geocode_location")
@patch("app.tools.route.validate_route_state")
def test_add_intermediate_waypoint_at_position(
    mock_validate_route,
    mock_geocode,
    mock_fetch_route,
    mock_recalculate,
    mock_runtime_with_segments,
    mock_route,
    mock_segment,
):
    """Test adding intermediate waypoint at specific position"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_geocode.return_value = Coordinate(latitude=53.9277, longitude=-1.3850)
    mock_fetch_route.return_value = mock_route
    mock_recalculate.return_value = [mock_segment]

    result = add_intermediate_waypoint.func(
        runtime=mock_runtime_with_segments, waypoint_name="Wetherby", insert_position=0
    )

    assert isinstance(result, Command)
    assert len(result.update["requirements"].intermediates) == 1


@patch("app.tools.route.geocode_location")
@patch("app.tools.route.validate_route_state")
def test_add_intermediate_waypoint_geocoding_error(
    mock_validate_route, mock_geocode, mock_runtime_with_segments
):
    """Test error handling when geocoding fails"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_geocode.side_effect = Exception("Geocoding failed")

    with pytest.raises(ValueError) as exc_info:
        add_intermediate_waypoint.func(
            runtime=mock_runtime_with_segments, waypoint_name="InvalidPlace"
        )

    assert "Failed to add waypoint" in str(exc_info.value)


@patch("app.tools.route.geocode_location")
@patch("app.tools.route.validate_route_state")
def test_add_intermediate_waypoint_invalid_position(
    mock_validate_route, mock_geocode, mock_runtime_with_segments
):
    """Test error for invalid insert position"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_geocode.return_value = Coordinate(latitude=53.9277, longitude=-1.3850)

    with pytest.raises(ValueError) as exc_info:
        add_intermediate_waypoint.func(
            runtime=mock_runtime_with_segments,
            waypoint_name="Wetherby",
            insert_position=5,
        )

    assert "Insert position 5 out of range" in str(exc_info.value)


@patch("app.tools.route.recalculate_segments_with_accommodation")
@patch("app.tools.route.fetch_route")
@patch("app.tools.route.validate_route_state")
def test_remove_intermediate_waypoint_success(
    mock_validate_route,
    mock_fetch_route,
    mock_recalculate,
    mock_runtime_with_segments,
    mock_route,
    mock_segment,
    mock_intermediate,
):
    """Test successful removal of intermediate waypoint"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements
    requirements.intermediates = [mock_intermediate]

    mock_validate_route.return_value = (route, requirements)
    mock_fetch_route.return_value = mock_route
    mock_recalculate.return_value = [mock_segment]

    result = remove_intermediate_waypoint.func(
        runtime=mock_runtime_with_segments, waypoint_index=0
    )

    assert isinstance(result, Command)
    assert "route" in result.update
    assert "segments" in result.update
    assert "requirements" in result.update
    assert len(result.update["requirements"].intermediates) == 0


@patch("app.tools.route.validate_route_state")
def test_remove_intermediate_waypoint_no_intermediates(
    mock_validate_route, mock_runtime_with_segments
):
    """Test error when no intermediates to remove"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements
    requirements.intermediates = []

    mock_validate_route.return_value = (route, requirements)

    with pytest.raises(ValueError) as exc_info:
        remove_intermediate_waypoint.func(
            runtime=mock_runtime_with_segments, waypoint_index=0
        )

    assert "No intermediate waypoints to remove" in str(exc_info.value)


@patch("app.tools.route.validate_route_state")
def test_remove_intermediate_waypoint_invalid_index(
    mock_validate_route, mock_runtime_with_segments, mock_intermediate
):
    """Test error for invalid waypoint index"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements
    requirements.intermediates = [mock_intermediate]

    mock_validate_route.return_value = (route, requirements)

    with pytest.raises(ValueError) as exc_info:
        remove_intermediate_waypoint.func(
            runtime=mock_runtime_with_segments, waypoint_index=5
        )

    assert "Invalid waypoint index 5" in str(exc_info.value)


@patch("app.tools.route.recalculate_segments_with_accommodation")
@patch("app.tools.route.fetch_route")
@patch("app.tools.route.geocode_location")
@patch("app.tools.route.validate_route_state")
def test_recalculate_complete_route_new_origin(
    mock_validate_route,
    mock_geocode,
    mock_fetch_route,
    mock_recalculate,
    mock_runtime_with_segments,
    mock_route,
    mock_segment,
):
    """Test recalculating route with new origin"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_geocode.return_value = Coordinate(latitude=51.5074, longitude=-0.1278)
    mock_fetch_route.return_value = mock_route
    mock_recalculate.return_value = [mock_segment]

    result = recalculate_complete_route.func(
        runtime=mock_runtime_with_segments, new_origin="London, UK"
    )

    assert isinstance(result, Command)
    assert "route" in result.update
    assert "segments" in result.update
    assert "requirements" in result.update
    assert result.update["requirements"].origin.name == "London, UK"
    mock_geocode.assert_called_once_with("London, UK")


@patch("app.tools.route.recalculate_segments_with_accommodation")
@patch("app.tools.route.fetch_route")
@patch("app.tools.route.geocode_location")
@patch("app.tools.route.validate_route_state")
def test_recalculate_complete_route_new_destination(
    mock_validate_route,
    mock_geocode,
    mock_fetch_route,
    mock_recalculate,
    mock_runtime_with_segments,
    mock_route,
    mock_segment,
):
    """Test recalculating route with new destination"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_geocode.return_value = Coordinate(latitude=51.5074, longitude=-0.1278)
    mock_fetch_route.return_value = mock_route
    mock_recalculate.return_value = [mock_segment]

    result = recalculate_complete_route.func(
        runtime=mock_runtime_with_segments, new_destination="London, UK"
    )

    assert isinstance(result, Command)
    assert result.update["requirements"].destination.name == "London, UK"


@patch("app.tools.route.recalculate_segments_with_accommodation")
@patch("app.tools.route.fetch_route")
@patch("app.tools.route.convert_place_names_to_locations")
@patch("app.tools.route.validate_route_state")
def test_recalculate_complete_route_with_intermediates(
    mock_validate_route,
    mock_convert_places,
    mock_fetch_route,
    mock_recalculate,
    mock_runtime_with_segments,
    mock_route,
    mock_segment,
    mock_intermediate,
):
    """Test recalculating route with intermediate waypoints"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_convert_places.return_value = [mock_intermediate]
    mock_fetch_route.return_value = mock_route
    mock_recalculate.return_value = [mock_segment]

    result = recalculate_complete_route.func(
        runtime=mock_runtime_with_segments, intermediate_names=["Wetherby"]
    )

    assert isinstance(result, Command)
    assert len(result.update["requirements"].intermediates) == 1
    mock_convert_places.assert_called_once_with(["Wetherby"])


@patch("app.tools.route.geocode_location")
@patch("app.tools.route.validate_route_state")
def test_recalculate_complete_route_geocoding_error(
    mock_validate_route, mock_geocode, mock_runtime_with_segments
):
    """Test error handling when geocoding fails"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_geocode.side_effect = Exception("Geocoding failed")

    with pytest.raises(ValueError) as exc_info:
        recalculate_complete_route.func(
            runtime=mock_runtime_with_segments, new_origin="InvalidPlace"
        )

    assert "Failed to geocode new origin" in str(exc_info.value)


@patch("app.tools.route.fetch_route")
@patch("app.tools.route.validate_route_state")
def test_recalculate_complete_route_fetch_error(
    mock_validate_route, mock_fetch_route, mock_runtime_with_segments
):
    """Test error handling when route fetch fails"""
    route = mock_runtime_with_segments.state.route
    requirements = mock_runtime_with_segments.state.requirements

    mock_validate_route.return_value = (route, requirements)
    mock_fetch_route.side_effect = Exception("Route calculation failed")

    with pytest.raises(ValueError) as exc_info:
        recalculate_complete_route.func(runtime=mock_runtime_with_segments)

    assert "Failed to calculate new route" in str(exc_info.value)
