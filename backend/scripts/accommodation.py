from pprint import pprint

from pydantic_extra_types.coordinate import Coordinate

from app.tools.accommodation import get_accommodation

coords = Coordinate(latitude=27.690759, longitude=83.465226)  # type: ignore

result = get_accommodation.invoke({"location": coords})

nice_r = [r.model_dump() for r in result]

pprint(nice_r)
