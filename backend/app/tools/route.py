from langchain.tools import tool
import numpy as np
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Latitude, Longitude, Coordinate
import requests
import polyline
from geopy.distance import geodesic
from decimal import Decimal

from app.config.config import settings

GOOGLE_ROUTES_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_GEOCODING_API_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

class BicycleRoutingNotAccepted(Exception):
    pass

class Route(BaseModel):
    polyline: str
    distance: int
    duration: str


class Waypoint(BaseModel):
    day: int
    coordinates: Coordinate
    distance_from_origin: Decimal
    segment_distance: Decimal


@tool
def calculate_days(total_length: int, daily_length: int) -> int:
    """Given a total trip length and a requested daily ride length calculate the number of days for the trip.

    Args:
        total_length: Length of the whole trip in kilometres
        daily_length: Requested daily ride length in kilometres
    """
    return int(np.ceil(total_length / daily_length))


@tool
def get_location(place_name: str) -> Coordinate:
    """Convert a place name to a coordinates object using Google Geocoding API.

    Args:
        place_name: The name of a place, e.g Amsterdam

    Returns:
        Coordinate: A Coordinate object with latitude and longitude

    Raises:
        ValueError: If the place cannot be found or API request fails
    """
    params = {"address": place_name, "key": settings.GOOGLE_API_KEY}

    try:
        response = requests.get(GOOGLE_GEOCODING_API_ENDPOINT, params=params)
        response.raise_for_status()

        data = response.json()

        if data["status"] != "OK" or not data.get("results"):
            raise ValueError(
                f"Could not find location: {place_name}. Status: {data['status']}"
            )

        # Get the first result
        location = data["results"][0]["geometry"]["location"]

        return Coordinate(latitude=location["lat"], longitude=location["lng"])

    except requests.RequestException as e:
        raise ValueError(f"Failed to geocode location '{place_name}': {str(e)}")


@tool
def get_route(origin: Coordinate, destination: Coordinate) -> Route:
    """Calculate a route between 2 points using Google Routes API.

    Args:
        origin: The starting location
        destination: The final location

    Returns:
        Route: Route object containing polyline, distance in meters, and duration

    Raises:
        ValueError: If route calculation fails
    """
    routing_strategies = [
        {
            "travelMode": "BICYCLE",
            # No routingPreference allowed for BICYCLE
        },
        {
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_UNAWARE", 
            "routeModifiers": {"avoidHighways": True, "avoidFerries": True}
        }
    ]

    base_request = {
        "origin": {
            "location": {
                "latLng": {"latitude": origin.latitude, "longitude": origin.longitude}
            }
        },
        "destination": {
            "location": {
                "latLng": {"latitude": destination.latitude, "longitude": destination.longitude}
            }
        },
        "computeAlternativeRoutes": False,
        "languageCode": "en-US",
        "units": "METRIC",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
    }

    last_error = None
    for strategy in routing_strategies:
        # Merge the base request with the current strategy settings
        request_body = base_request | strategy

        try:
            response = requests.post(
                GOOGLE_ROUTES_API_ENDPOINT, json=request_body, headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            
            # If 'routes' is missing, this strategy failed to find a path
            if not data or "routes" not in data:
                print(f"Warning: No route found for {strategy['travelMode']}. Attempting fallback...")
                continue 

            route_data = data["routes"][0]
            
            return Route(
                polyline=route_data["polyline"]["encodedPolyline"],
                distance=route_data["distanceMeters"],
                duration=route_data["duration"],
            )

        except Exception as e:
            last_error = e
            print(f"Error requesting {strategy['travelMode']}: {e}")
            # Continue to next strategy

    raise ValueError(f"Could not calculate route. All attempts failed. Last error: {last_error}")

@tool
def generate_waypoints(
    route_polyline: str, daily_distance: int, total_distance: float
) -> list[Waypoint]:
    """
    Generate intermediate waypoints along a route based on daily cycling distance.

    This function divides a route into daily segments by identifying points along
    the route that are approximately daily_distance_km apart. Each waypoint represents
    where a cyclist would end their day.

    Args:
        route_polyline: Encoded polyline string from Google Routes API
        daily_distance: Target distance per day in meters
        total_distance: Total route distance in meters

    Returns:
        List of waypoint dictionaries, ordered by distance from origin (ascending).
        Each waypoint contains:
        - day_number: Which day this waypoint ends (1-indexed)
        - coordinate: Coordinate object with lat/lng
        - distance_from_origin_km: Cumulative distance from start
        - segment_distance_km: Distance from previous waypoint

    Example:
        >>> waypoints = generate_waypoints(polyline_str, 100, 450)
        >>> len(waypoints)  # For a 450km route with 100km/day
        4  # Days 1, 2, 3, 4 (day 5 ends at destination)
        >>> waypoints[0].day
        1
        >>> waypoints[0].distance_from_origin
        ~100
    """
    # Decode the polyline into (lat, lng) tuples
    coordinates = polyline.decode(route_polyline)

    if not coordinates or len(coordinates) < 2:
        raise ValueError("Invalid polyline: must contain at least 2 points")

    # Calculate number of waypoints needed (excluding destination)
    num_days = int(np.ceil(total_distance / daily_distance))
    num_waypoints = num_days - 1  # Last day ends at destination

    print(num_waypoints)

    waypoints = []
    cumulative_distance = 0.0
    target_distance = daily_distance / 1000
    day_number = 1
    previous_waypoint_distance = 0.0

    # Iterate through the polyline segments
    for i in range(len(coordinates) - 1):
        point1 = coordinates[i]
        point2 = coordinates[i + 1]

        # Calculate distance of this segment
        segment_distance = geodesic(point1, point2).kilometers
        cumulative_distance += segment_distance

        # Check if we've reached or passed the target distance for this day
        if cumulative_distance >= target_distance and len(waypoints) < num_waypoints:
            # Use the point we just reached (point2)
            waypoint = Waypoint(
                day=day_number,
                coordinates=Coordinate(
                    latitude=point2[0], longitude=point2[1] # type: ignore
                ),
                distance_from_origin=round(cumulative_distance, 2),
                segment_distance=round(
                    cumulative_distance - previous_waypoint_distance, 2
                ),
            )

            waypoints.append(waypoint)
            previous_waypoint_distance = cumulative_distance
            day_number += 1
            target_distance += (daily_distance / 1000)

    return waypoints
