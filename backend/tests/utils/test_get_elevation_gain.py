from app.utils.utils import get_elevation_gain


def test_get_elevation_gain_returns_integer(simple_polyline):
    """Test that get_elevation_gain returns an integer elevation value"""

    result = get_elevation_gain(simple_polyline)

    assert isinstance(result, int)
