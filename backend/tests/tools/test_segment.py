import pytest
from unittest.mock import patch

from app.tools.segment import get_segment_details


@patch("app.tools.segment.validate_segments_state")
def test_get_segment_details_success(
    mock_validate_segments, mock_runtime_with_segments
):
    """Test successful retrieval of segment details"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]

    result = get_segment_details.func(
        runtime=mock_runtime_with_segments, day_number=1
    )

    assert result["day"] == 1
    assert result["distance_km"] == 42.0
    assert result["elevation_gain_m"] == 250
    assert result["origin"]["latitude"] == 53.8008
    assert result["origin"]["longitude"] == -1.5491
    assert result["destination"]["latitude"] == 53.9599
    assert result["destination"]["longitude"] == -1.0873
    assert result["accommodation_count"] == 2
    assert result["has_accommodation"] is True
    mock_validate_segments.assert_called_once_with(mock_runtime_with_segments)


@patch("app.tools.segment.validate_segments_state")
def test_get_segment_details_accommodation_options(
    mock_validate_segments, mock_runtime_with_segments
):
    """Test that accommodation options are properly included"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]

    result = get_segment_details.func(
        runtime=mock_runtime_with_segments, day_number=1
    )

    assert len(result["accommodation_options"]) == 2
    assert result["accommodation_options"][0]["name"] == "Test Hotel"
    assert result["accommodation_options"][0]["rating"] == 4.5
    assert result["accommodation_options"][0]["address"] == "123 Test St, Leeds"
    assert result["accommodation_options"][1]["name"] == "Another Hotel"
    assert result["accommodation_options"][1]["rating"] == 4.0


@patch("app.tools.segment.validate_segments_state")
def test_get_segment_details_no_accommodation(
    mock_validate_segments, mock_runtime_with_segments, mock_route
):
    """Test segment details when no accommodation is available"""
    from app.models import Segment

    segment_no_accommodation = Segment(
        day=1, route=mock_route, accommodation_options=[]
    )
    mock_validate_segments.return_value = [segment_no_accommodation]

    result = get_segment_details.func(
        runtime=mock_runtime_with_segments, day_number=1
    )

    assert result["accommodation_count"] == 0
    assert result["has_accommodation"] is False
    assert result["accommodation_options"] == []


@patch("app.tools.segment.validate_segments_state")
def test_get_segment_details_invalid_day_number_too_high(
    mock_validate_segments, mock_runtime_with_segments
):
    """Test error handling for day number exceeding total days"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]

    with pytest.raises(ValueError) as exc_info:
        get_segment_details.func(
            runtime=mock_runtime_with_segments, day_number=5
        )

    assert "Invalid day number 5" in str(exc_info.value)
    assert "Route has 1 days" in str(exc_info.value)


@patch("app.tools.segment.validate_segments_state")
def test_get_segment_details_invalid_day_number_zero(
    mock_validate_segments, mock_runtime_with_segments
):
    """Test error handling for day number less than 1"""
    segment = mock_runtime_with_segments.state.segments[0]
    mock_validate_segments.return_value = [segment]

    with pytest.raises(ValueError) as exc_info:
        get_segment_details.func(
            runtime=mock_runtime_with_segments, day_number=0
        )

    assert "Invalid day number 0" in str(exc_info.value)


@patch("app.tools.segment.validate_segments_state")
def test_get_segment_details_multiple_segments(
    mock_validate_segments, mock_runtime_with_segments, mock_route, mock_accommodation
):
    """Test retrieving details from multiple segments"""
    from app.models import Segment

    segment1 = mock_runtime_with_segments.state.segments[0]
    segment2 = Segment(day=2, route=mock_route, accommodation_options=mock_accommodation)
    mock_validate_segments.return_value = [segment1, segment2]

    result = get_segment_details.func(
        runtime=mock_runtime_with_segments, day_number=2
    )

    assert result["day"] == 2
    assert result["distance_km"] == 42.0
