import logging
import random

import polyline
import requests
from app.config import settings
from app.models import Accommodation, Route, Segment, Location
from geopy.distance import geodesic
from pydantic_extra_types.coordinate import Coordinate

logger = logging.getLogger(__name__)



def get_elevation_gain(polyline: str) -> int:
    """Calculate the elevation gain for a polyline route

    Args:
        polyline: The polyline to calculate for

    Returns:
        elevation: Total elevation gain in meters
    """
    # Mock data
    return random.randint(200, 2000)


def reverse_geocode(coordinates: Coordinate) -> str:
    """Convert coordinates to a place name using Google Geocoding API.
    
    This uses reverse geocoding to find the most appropriate place name
    for the given coordinates, preferring locality or administrative area names.
    
    Args:
        coordinates: The coordinates to reverse geocode
        
    Returns:
        str: The place name (e.g., "Leeds, UK" or "Lyon, France")
        
    Raises:
        ValueError: If reverse geocoding fails
    """
    params = {
        "latlng": f"{coordinates.latitude},{coordinates.longitude}",
        "key": settings.GOOGLE_API_KEY,
    }
    
    try:
        response = requests.get(settings.GOOGLE_GEOCODING_API_ENDPOINT, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data["status"] != "OK" or not data.get("results"):
            logger.warning(
                f"Could not reverse geocode coordinates {coordinates.latitude},{coordinates.longitude}. "
                f"Status: {data['status']}"
            )
            # Fallback to coordinate string
            return f"Location at {coordinates.latitude:.4f},{coordinates.longitude:.4f}"
        
        # Try to find the most relevant place name from the results
        # Priority: locality > administrative_area_level_2 > administrative_area_level_1 > first result
        results = data["results"]
        
        # Look for a result with a locality (city/town)
        for result in results:
            types = result.get("types", [])
            if "locality" in types or "postal_town" in types:
                return result["formatted_address"]
        
        # Look for administrative area level 2 (county/district)
        for result in results:
            types = result.get("types", [])
            if "administrative_area_level_2" in types:
                return result["formatted_address"]
        
        # Look for administrative area level 1 (state/region)
        for result in results:
            types = result.get("types", [])
            if "administrative_area_level_1" in types:
                return result["formatted_address"]
        
        # Fall back to first result's formatted address
        return results[0]["formatted_address"]
        
    except requests.RequestException as e:
        logger.error(f"Failed to reverse geocode coordinates: {str(e)}")
        # Fallback to coordinate string
        return f"Location at {coordinates.latitude:.4f},{coordinates.longitude:.4f}"


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
    origin: Location,
    destination: Location,
    intermediates: list[Location] = [],
) -> Route:
    """Calculate a route between 2 points using Google Routes API.

    Args:
        origin: The starting location (with name and coordinates)
        destination: The final location (with name and coordinates)
        intermediates: A list of intermediate locations the route must pass through in ascending order.

    Returns:
        Route: Route object containing polyline, origin, destination, distance in meters, and elevation gain

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
    for loc in intermediates:
        intermediates_request.append(
            {
                "via": True,
                "location": {
                    "latLng": {
                        "latitude": loc.coordinates.latitude,
                        "longitude": loc.coordinates.longitude,
                    }
                },
            }
        )

    base_request = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin.coordinates.latitude,
                    "longitude": origin.coordinates.longitude,
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": destination.coordinates.latitude,
                    "longitude": destination.coordinates.longitude,
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
            route_polyline = route_data["polyline"]["encodedPolyline"]

            return Route(
                polyline=route_polyline,
                origin=origin,
                destination=destination,
                distance=route_data["distanceMeters"],
                elevation_gain=get_elevation_gain(route_polyline),
            )

        except Exception as e:
            last_error = e
            print(f"Error requesting {strategy['travelMode']}: {e}")
            # Continue to next strategy

    raise ValueError(
        f"Could not calculate route. All attempts failed. Last error: {last_error}"
    )


def calculate_segments(
    route_polyline: str,
    daily_distance: int,
    route_origin: Location,
    route_destination: Location,
) -> list[Segment]:
    """
    Generate route segments based on daily cycling distance.

    This function divides a route into daily segments by identifying points along
    the route that are approximately daily_distance apart. Each segment represents
    a day's cycling with its own route polyline, origin, and destination.
    
    Segment endpoint names are determined by:
    - First segment origin: Uses the route origin name
    - Last segment destination: Uses the route destination name  
    - Intermediate endpoints: Uses reverse geocoding to find the nearest place name

    Args:
        route_polyline: Encoded polyline string from Google Routes API
        daily_distance: Target distance per day in meters
        route_origin: Origin location of the overall route (used for first segment)
        route_destination: Destination location of the overall route (used for last segment)

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

            # Determine origin location for this segment
            if segment_start_idx == 0:
                # First segment uses the route origin
                segment_origin = route_origin
            else:
                # Intermediate segments: reverse geocode to get place name
                origin_coord = Coordinate(
                    latitude=coordinates[segment_start_idx][0],  # type: ignore
                    longitude=coordinates[segment_start_idx][1],  # type: ignore
                )
                origin_name = reverse_geocode(origin_coord)
                segment_origin = Location(
                    name=origin_name,
                    coordinates=origin_coord,
                )

            # Determine destination location for this segment
            # Use reverse geocoding to get the place name
            dest_coord = Coordinate(
                latitude=point2[0],  # type: ignore
                longitude=point2[1],  # type: ignore
            )
            dest_name = reverse_geocode(dest_coord)
            segment_destination = Location(
                name=dest_name,
                coordinates=dest_coord,
            )

            route = Route(
                polyline=segment_polyline,
                origin=segment_origin,
                destination=segment_destination,
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

        # Determine origin for final segment
        if segment_start_idx == 0:
            # Only one segment - use route origin
            segment_origin = route_origin
        else:
            # Multiple segments - reverse geocode the starting point
            origin_coord = Coordinate(
                latitude=coordinates[segment_start_idx][0],  # type: ignore
                longitude=coordinates[segment_start_idx][1],  # type: ignore
            )
            origin_name = reverse_geocode(origin_coord)
            segment_origin = Location(
                name=origin_name,
                coordinates=origin_coord,
            )

        # Final segment always uses the route destination
        segment_destination = route_destination

        route = Route(
            polyline=segment_polyline,
            origin=segment_origin,
            destination=segment_destination,
            distance=int(segment_distance * 1000),  # convert to meters
            elevation_gain=get_elevation_gain(segment_polyline),
        )

        segment = Segment(day=day_number, route=route, accommodation_options=[])

        segments.append(segment)

    # Update intermediate segments so each segment's origin matches the previous segment's destination
    if len(segments) > 1:
        for i in range(len(segments) - 1):
            # Make the next segment's origin use the same Location object as this segment's destination
            segments[i + 1].route.origin = segments[i].route.destination

    logger.info(f"Generated {len(segments)} segments with reverse-geocoded place names")
    
    return segments