import json
from pathlib import Path
import typing

#Returns project root as a Path object.
def getProjectRoot() -> Path:
    current_path = Path(__file__).resolve()

    for parent in current_path.parents:
        if(parent / "pyproject.toml").exists():
            return parent

    raise FileNotFoundError("Root not found")

#Returns the GeoJSON borders for a country. If the country does not exist in the data, it raises a ValueError.
def getGeoJSONCountryBorders(country: str):
    path = getProjectRoot / "external" / "geojson_borders" / "countries" / f"{country}.json"
    if not path.exists():
        raise ValueError("Country does not exist")

    with path.open("", encoding="utf-8") as file:
        return json.load(file)

    

def getGeoJSONAreaBorder(area: str):
    path = getProjectRoot / "external" / "geojson_borders" / "areas" / f"{area}.json"
    if not path.exists():
        raise ValueError("Area does not exist")

    with path.open("", encoding="utf-8") as file:
        return json.load(file)


def getGeoJSONStateBorder(state: str):
    path = getProjectRoot / "external" / "geojson_borders" / "areas" / f"{state}.json"
    if not path.exists():
        raise ValueError("State does not exist")

    with path.open("", encoding="utf-8") as file:
        return json.load(file)