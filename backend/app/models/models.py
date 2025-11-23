from decimal import Decimal
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate

class Location(BaseModel):
    name: str
    coordinates: Coordinate

class Route(BaseModel):
    polyline: str
    distance: int
    duration: str


class Waypoint(BaseModel):
    day: int
    coordinates: Coordinate
    distance_from_origin: Decimal
    segment_distance: Decimal

