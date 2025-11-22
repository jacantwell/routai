from app.tools.route import get_location, get_route, generate_waypoints
from app.tools.accommodation import get_accommodation
from pprint import pprint

origin = "Butwal"
destination = "Pokhara"

daily_distance = 80000

origin_coords = get_location.invoke({"place_name": origin})
destination_coords = get_location.invoke({"place_name": destination})

route = get_route.invoke({"origin": origin_coords, "destination": destination_coords})

waypoints = generate_waypoints.invoke(
    {
        "route_polyline": route.polyline,
        "total_distance": route.distance,
        "daily_distance": daily_distance,
    }
)

route_points = (
    [origin_coords] + [wp.coordinates for wp in waypoints] + [destination_coords]
)

accommodation_data = [get_accommodation.invoke({"location": p}) for p in route_points]

results = [[a.model_dump() for a in ad] for ad in accommodation_data]

pprint(results)
