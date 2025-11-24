import pytest
from pydantic_extra_types.coordinate import Coordinate

from app.models import Location


@pytest.fixture
def mock_coordinate():
    """Fixture providing a test coordinate"""
    return Coordinate(latitude=53.8008, longitude=-1.5491)  # type: ignore


@pytest.fixture
def mock_location(mock_coordinate):
    """Fixture providing a test location coordinate"""
    return mock_coordinate


@pytest.fixture
def mock_origin():
    """Fixture providing a test origin location"""
    return Location(
        name="Leeds", coordinates=Coordinate(latitude=53.8008, longitude=-1.5491)   # type: ignore
    )


@pytest.fixture
def mock_destination():
    """Fixture providing a test destination location"""
    return Location(
        name="York", coordinates=Coordinate(latitude=53.9599, longitude=-1.0873)    # type: ignore
    )


@pytest.fixture
def mock_intermediate():
    """Fixture providing a test intermediate location"""
    return Location(
        name="Wetherby", coordinates=Coordinate(latitude=53.9277, longitude=-1.3850)    # type: ignore
    )


@pytest.fixture
def simple_polyline():
    """Fixture providing a simple encoded polyline"""
    # This represents a simple straight line with a few points
    return "u{r~Hzza}Abcd@efg@hij@klm@"
