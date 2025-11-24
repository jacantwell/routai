import random

import polyline
import requests
from app.config import settings
from app.models import Accommodation, Route, Segment
from geopy.distance import geodesic
from pydantic_extra_types.coordinate import Coordinate



def get_elevation_gain(polyline: str) -> int:
    """Calculate the elevation gain for a polyline route

    Args:
        polyline: The polyline to calculate for

    Returns:
        elevation: Total elevation gain in meters
    """
    # Mock data
    return random.randint(200, 2000)


def get_accommodation(location: Coordinate, radius: int = 5) -> list[Accommodation]:
    """Find accommodation options within a given radius around a given location

    Args:
        location: The location to search near
        radius: Radius, in km, around which to search
    """

    # Convert radius from km to meters (Google API uses meters)
    radius_meters = radius * 1000

    location_area = {
        "circle": {
            "center": {"latitude": location.latitude, "longitude": location.longitude},
            "radius": radius_meters,
        }
    }

    request_body = {
        "locationRestriction": location_area,
        # "regionCode": "GB", #
        "includedTypes": ["lodging"],
        "maxResultCount": 5,
    }

    # 2. Define the Field Mask (Comma separated list of fields you want)
    field_mask = (
        "places.displayName,places.formattedAddress,places.googleMapsUri,places.rating"
    )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_API_KEY,
        "X-Goog-FieldMask": field_mask,
    }

    try:
        response = requests.post(
            settings.GOOGLE_PLACES_API_ENDPOINT, json=request_body, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        accommodation_data = data.get("places", [])
        results = [
            Accommodation(
                name=acom["displayName"]["text"],
                address=acom.get("formattedAddress"),
                map_link=acom.get("googleMapsUri"),
                rating=acom.get("rating"),
            )
            for acom in accommodation_data
        ]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error making request to Google Places API: {str(e)}")
    except Exception as e:
        raise e

    return results


def fetch_route(
    origin: Coordinate,
    destination: Coordinate,
    intermediates: list[Coordinate] = [],
) -> Route:
    """Calculate a route between 2 points using Google Routes API.

    Args:
        origin: The starting location
        destination: The final location
        intermediates: A list of intermediate points the route must pass through in ascending order.

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
            "routeModifiers": {"avoidHighways": True, "avoidFerries": True},
        },
    ]

    intermediates_request = []
    for ip in intermediates:
        intermediates_request.append(
            {
                "via": True,
                "location": {
                    "latLng": {"latitude": ip.latitude, "longitude": ip.longitude}
                },
            }
        )

    base_request = {
        "origin": {
            "location": {
                "latLng": {"latitude": origin.latitude, "longitude": origin.longitude}
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination.latitude,
                    "longitude": destination.longitude,
                }
            }
        },
        "intermediates": intermediates_request,
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
                settings.GOOGLE_ROUTES_API_ENDPOINT, json=request_body, headers=headers
            )
            response.raise_for_status()

            data = response.json()

            # If 'routes' is missing, this strategy failed to find a path
            if not data or "routes" not in data:
                print(
                    f"Warning: No route found for {strategy['travelMode']}. Attempting fallback..."
                )
                continue

            route_data = data["routes"][0]
            polyline = route_data["polyline"]["encodedPolyline"]

            return Route(
                polyline=polyline,
                origin=origin,
                destination=destination,
                distance=route_data["distanceMeters"],
                elevation_gain=get_elevation_gain(polyline),
            )

        except Exception as e:
            last_error = e
            print(f"Error requesting {strategy['travelMode']}: {e}")
            # Continue to next strategy

    raise ValueError(
        f"Could not calculate route. All attempts failed. Last error: {last_error}"
    )


def calculate_segments(route_polyline: str, daily_distance: int) -> list[Segment]:
    """
    Generate route segments based on daily cycling distance.

    This function divides a route into daily segments by identifying points along
    the route that are approximately daily_distance apart. Each segment represents
    a day's cycling with its own route polyline, origin, and destination.

    Args:
        route_polyline: Encoded polyline string from Google Routes API
        daily_distance: Target distance per day in meters
        total_distance: Total route distance in meters

    Returns:
        List of segments with route details for each day

    """
    # Decode the polyline into (lat, lng) tuples
    coordinates = polyline.decode(route_polyline)

    if not coordinates or len(coordinates) < 2:
        raise ValueError("Invalid polyline: must contain at least 2 points")

    segments = []
    cumulative_distance = 0.0
    target_distance = daily_distance / 1000  # convert to km
    day_number = 1
    segment_start_idx = 0
    segment_distance = 0.0

    # Iterate through the polyline segments
    for i in range(len(coordinates) - 1):
        point1 = coordinates[i]
        point2 = coordinates[i + 1]

        # Calculate distance of this edge
        edge_distance = geodesic(point1, point2).kilometers
        cumulative_distance += edge_distance
        segment_distance += edge_distance

        # Check if we've reached or passed the target distance for this day
        if cumulative_distance >= target_distance:
            # Create segment from segment_start_idx to current point (i+1)
            segment_coords = coordinates[segment_start_idx : i + 2]
            segment_polyline = polyline.encode(segment_coords)

            route = Route(
                polyline=segment_polyline,
                origin=Coordinate(
                    latitude=coordinates[segment_start_idx][0],  # type: ignore
                    longitude=coordinates[segment_start_idx][1],  # type: ignore
                ),
                destination=Coordinate(
                    latitude=point2[0],  # type: ignore
                    longitude=point2[1],  # type: ignore
                ),
                distance=int(segment_distance * 1000),  # convert to meters
                elevation_gain=get_elevation_gain(segment_polyline),
            )

            segment = Segment(day=day_number, route=route, accommodation_options=[])

            segments.append(segment)

            # Reset for next segment
            segment_start_idx = i + 1
            segment_distance = 0.0
            day_number += 1
            target_distance += daily_distance / 1000

    # Handle the final segment (from last split point to destination)
    if segment_start_idx < len(coordinates) - 1:
        segment_coords = coordinates[segment_start_idx:]
        segment_polyline = polyline.encode(segment_coords)

        route = Route(
            polyline=segment_polyline,
            origin=Coordinate(
                latitude=coordinates[segment_start_idx][0],  # type: ignore
                longitude=coordinates[segment_start_idx][1],  # type: ignore
            ),
            destination=Coordinate(
                latitude=coordinates[-1][0],  # type: ignore
                longitude=coordinates[-1][1],  # type: ignore
            ),
            distance=int(segment_distance * 1000),  # convert to meters
            elevation_gain=get_elevation_gain(segment_polyline),
        )

        segment = Segment(day=day_number, route=route, accommodation_options=[])

        segments.append(segment)

    return segments
