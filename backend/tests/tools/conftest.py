import pytest
from unittest.mock import Mock
from pydantic_extra_types.coordinate import Coordinate

from app.models import Location, Route, Segment, Accommodation
from app.models.state import AgentState, RouteRequirements


@pytest.fixture
def mock_coordinate():
    """Fixture providing a test coordinate"""
    return Coordinate(latitude=53.8008, longitude=-1.5491)


@pytest.fixture
def mock_location(mock_coordinate):
    """Fixture providing a test location"""
    return Location(name="Leeds", coordinates=mock_coordinate)


@pytest.fixture
def mock_origin():
    """Fixture providing a test origin location"""
    return Location(
        name="Leeds", coordinates=Coordinate(latitude=53.8008, longitude=-1.5491)
    )


@pytest.fixture
def mock_destination():
    """Fixture providing a test destination location"""
    return Location(
        name="York", coordinates=Coordinate(latitude=53.9599, longitude=-1.0873)
    )


@pytest.fixture
def mock_intermediate():
    """Fixture providing a test intermediate location"""
    return Location(
        name="Wetherby", coordinates=Coordinate(latitude=53.9277, longitude=-1.3850)
    )


@pytest.fixture
def mock_accommodation():
    """Fixture providing test accommodation"""
    return [
        Accommodation(
            name="Test Hotel",
            address="123 Test St, Leeds",
            map_link="https://maps.google.com/place/test",
            rating=4.5,
        ),
        Accommodation(
            name="Another Hotel",
            address="456 Another St, Leeds",
            map_link="https://maps.google.com/place/another",
            rating=4.0,
        ),
    ]


@pytest.fixture
def mock_route(mock_origin, mock_destination):
    """Fixture providing a test route"""
    return Route(
        polyline="test_polyline_string",
        origin=mock_origin,
        destination=mock_destination,
        distance=42000,
        elevation_gain=250,
    )


@pytest.fixture
def mock_segment(mock_route, mock_accommodation):
    """Fixture providing a test segment"""
    return Segment(
        day=1,
        route=mock_route,
        accommodation_options=mock_accommodation,
    )


@pytest.fixture
def mock_requirements(mock_origin, mock_destination):
    """Fixture providing test route requirements"""
    return RouteRequirements(
        origin=mock_origin,
        destination=mock_destination,
        intermediates=[],
        daily_distance_km=80,
        context="Test cycling route",
    )


@pytest.fixture
def mock_agent_state(mock_route, mock_requirements):
    """Fixture providing a mock agent state with route and requirements"""
    return AgentState(
        requirements=mock_requirements,
        route=mock_route,
        segments=None,
    )


@pytest.fixture
def mock_agent_state_with_segments(mock_route, mock_requirements, mock_segment):
    """Fixture providing a mock agent state with segments"""
    return AgentState(
        requirements=mock_requirements,
        route=mock_route,
        segments=[mock_segment],
    )


@pytest.fixture
def mock_runtime(mock_agent_state):
    """Fixture providing a mock ToolRuntime"""
    runtime = Mock()
    runtime.state = mock_agent_state
    runtime.tool_call_id = "test_tool_call_id"
    return runtime


@pytest.fixture
def mock_runtime_with_segments(mock_agent_state_with_segments):
    """Fixture providing a mock ToolRuntime with segments"""
    runtime = Mock()
    runtime.state = mock_agent_state_with_segments
    runtime.tool_call_id = "test_tool_call_id"
    return runtime
