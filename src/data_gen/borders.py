import geopandas as gpd
from pathlib import Path

def getProjectRoot() -> Path:
    """
    Returns project root as a Path object.
    """
    current_path = Path(__file__).resolve()

    for parent in current_path.parents:
        if(parent / "pyproject.toml").exists():
            return parent

    raise FileNotFoundError("Root not found")


def getGeoJSONCountryBorders(country: str) -> gpd.GeoDataFrame:
    """
    Returns the GeoJSON borders for a country. If the country does not exist in the data, it raises a ValueError.
    """
    path = getProjectRoot / "external" / "geojson_borders" / "countries" / f"{country}.json"
    if not path.exists():
        raise ValueError("Country does not exist")

    return gpd.read_file(path)

    
def getGeoJSONAreaBorder(area: str) -> gpd.GeoDataFrame:
    """
    Returns the GeoJSON borders for a area. If the area does not exist in the data, it raises a ValueError.
    """
    path = getProjectRoot / "external" / "geojson_borders" / "areas" / f"{area}.json"
    if not path.exists():
        raise ValueError("Area does not exist")

    return gpd.read_file(path)


def getGeoJSONStateBorder(state: str) -> gpd.GeoDataFrame:
    """
    Returns the GeoJSON borders for a state. If the state does not exist in the data, it raises a ValueError.
    """
    path = getProjectRoot / "external" / "geojson_borders" / "areas" / f"{state}.json"
    if not path.exists():
        raise ValueError("State does not exist")

    return gpd.read_file(path)

