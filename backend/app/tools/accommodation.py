from langchain.tools import tool
from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate

import requests
import os

from app.config.config import settings

GOOGLE_PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"


class Accommodation(BaseModel):
    name: str
    address: str
    map_link: str
    rating: float


@tool
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
            GOOGLE_PLACES_API_ENDPOINT, json=request_body, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        accommodation_data = data.get("places", [])
        results = [
            Accommodation(
                name=acom["displayName"]["text"],
                address=acom["formattedAddress"],
                map_link=acom["googleMapsUri"],
                rating=acom["rating"],
            )
            for acom in accommodation_data
        ]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error making request to Google Places API: {str(e)}")
    except Exception as e:
        raise e

    return results
