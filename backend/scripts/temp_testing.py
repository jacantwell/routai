from app.tools.accommodation import get_accommodation
from pydantic_extra_types.coordinate import Latitude, Longitude, Coordinate
from pprint import pprint

lat = Latitude(27.690759)
long = Longitude(83.465226)

coords = Coordinate(latitude=lat, longitude=long)

result = get_accommodation.invoke({"location": coords})

pprint(result)