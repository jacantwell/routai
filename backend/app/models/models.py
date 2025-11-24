from typing import Optional

from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate


class Location(BaseModel):
    name: str
    coordinates: Coordinate


class Accommodation(BaseModel):
    name: str
    address: str
    map_link: str
    rating: Optional[float]


class Route(BaseModel):
    polyline: str
    origin: Coordinate
    destination: Coordinate
    distance: int
    elevation_gain: int


class Segment(BaseModel):
    day: int
    route: Route
    accommodation_options: list[Accommodation] = []
