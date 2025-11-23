"""Shared pytest fixtures for testing."""

import pytest
from pydantic_extra_types.coordinate import Coordinate
from unittest.mock import Mock

from app.models.models import Route, Segment, Location, Accommodation
from app.agent.schemas.state import RouteRequirements, AgentState


@pytest.fixture
def sample_coordinate():
    """Sample coordinate for testing."""
    return Coordinate(latitude=48.8566, longitude=2.3522)


@pytest.fixture
def sample_location(sample_coordinate):
    """Sample location for testing."""
    return Location(name="Paris, France", coordinates=sample_coordinate)


@pytest.fixture
def sample_accommodation():
    """Sample accommodation for testing."""
    return Accommodation(
        name="Test Hotel",
        address="123 Test Street, Paris",
        map_link="https://maps.google.com/?q=test",
        rating=4.5,
    )


@pytest.fixture
def sample_route(sample_coordinate):
    """Sample route for testing."""
    origin = Coordinate(latitude=48.8566, longitude=2.3522)
    destination = Coordinate(latitude=45.764, longitude=4.8357)

    return Route(
        polyline="test_polyline_encoded_string",
        origin=origin,
        destination=destination,
        distance=450000,  # 450km in meters
        elevation_gain=2500,
    )


@pytest.fixture
def sample_segment(sample_route, sample_accommodation):
    """Sample segment for testing."""
    return Segment(
        day=1,
        route=sample_route,
        accommodation_options=[sample_accommodation],
    )


@pytest.fixture
def sample_requirements(sample_location):
    """Sample route requirements for testing."""
    destination = Location(
        name="Lyon, France",
        coordinates=Coordinate(latitude=45.764, longitude=4.8357),
    )

    return RouteRequirements(
        origin=sample_location,
        destination=destination,
        intermediates=[],
        daily_distance_km=80,
        context="Cycling tour through France",
    )


@pytest.fixture
def sample_agent_state(sample_route, sample_requirements, sample_segment):
    """Sample agent state for testing."""
    return AgentState(
        messages=[],
        requirements=sample_requirements,
        route=sample_route,
        segments=[sample_segment],
    )


@pytest.fixture
def mock_runtime(sample_agent_state):
    """Mock ToolRuntime for testing."""
    runtime = Mock()
    runtime.state = sample_agent_state
    return runtime
