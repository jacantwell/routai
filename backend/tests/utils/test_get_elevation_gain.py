"""Tests for get_elevation_gain function"""
from unittest.mock import patch

from app.utils.utils import get_elevation_gain


@patch("app.utils.utils.random.randint")
def test_get_elevation_gain_returns_integer(mock_randint):
    """Test that get_elevation_gain returns an integer elevation value"""
    mock_randint.return_value = 250
    polyline_str = "test_polyline"

    result = get_elevation_gain(polyline_str)

    assert result == 250
    assert isinstance(result, int)
    mock_randint.assert_called_once_with(100, 400)


@patch("app.utils.utils.random.randint")
def test_get_elevation_gain_calls_random_with_correct_range(mock_randint):
    """Test that get_elevation_gain uses correct range for random values"""
    mock_randint.return_value = 150

    get_elevation_gain("any_polyline")

    mock_randint.assert_called_once_with(100, 400)
