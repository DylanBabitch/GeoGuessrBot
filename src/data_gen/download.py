import os
import random
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

import borders

from pyproj import Transformer
from shapely.geometry import box, Point, Polygon, MultiPolygon

#CONFIG
API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]

GRID_SIZE = 100_000 #100km
PANOS_PER_CELL = 10
VIEWS_PER_PANO = 4

MAX_ATTEMPTS_PER_CELL = 300

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 640

FOV = 90
PITCH = 0

OUTPUT_DIR = Path("streetview_dataset")
IMAGE_DIR = OUTPUT_DIR / "images"
MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"

OUTPUT_DIR.mkdir(exist_ok=True)
IMAGE_DIR.mkdir(exist_ok=True)


#LOAD US GEOMETRY
country = borders.getGeoJSONCountryBorders("usa")

# "EPSG:9311 is the spatial reference identifier for the NAD27 / US National Atlas Equal Area coordinate reference system, 
# a projected map system used across the United States. It employs a Lambert azimuthal equal-area projection and is scaled in meters."
# from Google definition, basically just flattens the us into a 2d map
us_land = country.to_crs("EPSG:9311")

# combined islands into one geometry
us_geometry = us_land.geometry.union_all()


#HELPER FUNCTIONS
#creates a grid of US based on config settings
def create_grid():
    xmin, ymin, xmax, ymax = us_land.total_bounds

    cells = []

    x = xmin

    while x < xmax:
        y = ymin

        while y < ymax:
            square = box(x, y, x + GRID_SIZE, y + GRID_SIZE)

            clipped = square.intersection(us_geometry)

            if not clipped.is_empty:
                cells.append(clipped)

            y += GRID_SIZE

        x += GRID_SIZE

    grid = gpd.GeoDataFrame({"cell_id": range(len(cells))}, geometry=cells, crs="EPSG:9311")

    return grid


def get_polygons(geometry):
    """
    Returns polygon pieces from either Polygon, MultiPolygon, or GeometryCollection objects
    """
    if isinstance(geometry, Polygon):
        return [geometry]

    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)

    if hasattr(geometry, "geoms"):
        polygons = []

        for geom in geometry.geoms:
            polygons.extend(get_polygons(geom))

        return polygons

    return []


def random_point_in_geometry(geometry):
    """
    Chooses a polygon component weighted by area, then generates a random point inside it.
    """

    polygons = get_polygons(geometry)

    if not polygons:
        return None
    polygon = random.choices(polygons, weights=[p.area for p in polygons], k=1)[0]

    minx, miny, maxx, maxy = polygon.bounds

    #single bounding box is rectangle and polygon is not, it randomly generates up to 1000 points
    # within the bounding box and returns the first point within the polygon
    for _ in range(1000):
        point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))

        if polygon.contains(point):
            return point


    return polygon.representative_point()



#COORDINATE CONVERSION
#Google Street View API uses EPSG 4326
def point_to_lat_lon(point):
    transformer = Transformer.from_crs("EPSG:9311", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(point.x, point.y)
    return lat, lon



#GOOGLE STREETVIEW METADATA
METADATA_URL = ("https://maps.googleapis.com/maps/api/streetview/metadata")


def get_streetview_metadata(lat, lon):
    params = {"location": f"{lat},{lon}", "key": API_KEY,}

    try:
        response = requests.get(METADATA_URL, params=params, timeout=10)

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as e:
        print(f"Metadata request failed: {e}")
        return None

    if data.get("status") != "OK":
        return None

    return data


#DOWNLOAD STREET IMAGE
IMAGE_URL = "https://maps.googleapis.com/maps/api/streetview"

def download_image(pano_id, heading, output_path):
    params = {"size": f"{IMAGE_WIDTH}x{IMAGE_HEIGHT}", "pano": pano_id, "heading": heading,"pitch": PITCH, "fov": FOV, "return_error_code": "true", "key": API_KEY,}

    try:
        response = requests.get(IMAGE_URL, params=params, timeout=20)

        response.raise_for_status()

    except requests.RequestException as e:
        print(f"Image request failed: {e}")
        return False

    with open(output_path, "wb") as file:
        file.write(response.content)

    return True


#DOWNLOAD PANORAMA VIEW
def download_panorama_views(pano_id, cell_id, pano_index, metadata, requested_lat, requested_lon,):
    rows = []

    # Randomize orientation so north is not always image 0
    starting_heading = random.uniform(0, 360)

    headings = [(starting_heading + i * 90) % 360 for i in range(VIEWS_PER_PANO)]

    pano_location = metadata["location"]

    pano_lat = pano_location["lat"]
    pano_lon = pano_location["lng"]

    capture_date = metadata.get("date")

    for view_index, heading in enumerate(headings):

        filename = f"cell_{cell_id:04d}_"f"pano_{pano_index:03d}_"f"view_{view_index}.jpg"

        output_path = IMAGE_DIR / filename

        success = download_image(pano_id,heading,output_path)

        if not success:
            continue

        rows.append(
            {
                "filename": filename,
                "cell_id": cell_id,
                "pano_id": pano_id,

                "requested_lat": requested_lat,
                "requested_lon": requested_lon,

                "pano_lat": pano_lat,
                "pano_lon": pano_lon,

                "capture_date": capture_date,

                "heading": heading,
                "pitch": PITCH,
                "fov": FOV,
            }
        )

    return rows



# PROCESS A SINGLE CELL
def process_cell(cell,seen_panos):
    cell_id = cell["cell_id"]
    geometry = cell.geometry

    rows = []

    accepted = 0
    attempts = 0

    print(f"\nCell {cell_id}")

    while (accepted < PANOS_PER_CELL and attempts < MAX_ATTEMPTS_PER_CELL):
        attempts += 1

        # Generate candidate point
        point = random_point_in_geometry(geometry)

        if point is None:
            continue

        lat, lon = point_to_lat_lon(point)

        metadata = get_streetview_metadata(lat, lon)

        if metadata is None:
            continue

        pano_id = metadata.get("pano_id")

        if pano_id is None:
            continue

        if pano_id in seen_panos:
            continue

        seen_panos.add(pano_id)

        # Download 4 views
        panorama_rows = download_panorama_views(
            pano_id=pano_id,
            cell_id=cell_id,
            pano_index=accepted,
            metadata=metadata,
            requested_lat=lat,
            requested_lon=lon,
        )

        # dont count failed panoramas
        if not panorama_rows:
            continue

        rows.extend(panorama_rows)

        accepted += 1

        print(
            f"  {accepted}/{PANOS_PER_CELL} panoramas "
            f"({attempts} attempts)"
        )

        # dont hammer endpoint
        time.sleep(0.05)

    if accepted < PANOS_PER_CELL:
        print(
            f"  Only found {accepted} panoramas "
            f"after {attempts} attempts"
        )

    return rows


# MAIN

def main():

    print("Creating grid...")

    grid = create_grid()

    print(f"Created {len(grid)} US grid cells")

    seen_panos = set()
    manifest_rows = []

    if MANIFEST_PATH.exists():

        existing = pd.read_csv(MANIFEST_PATH)

        manifest_rows = existing.to_dict("records")

        seen_panos.update(
            existing["pano_id"]
            .dropna()
            .astype(str)
            .tolist()
        )

        print(
            f"Loaded {len(seen_panos)} existing panoramas"
        )


    test_grid = grid.iloc[:5]

    for _, cell in test_grid.iterrows():

        cell_rows = process_cell(
            cell,
            seen_panos
        )

        manifest_rows.extend(cell_rows)

        pd.DataFrame(
            manifest_rows
        ).to_csv(
            MANIFEST_PATH,
            index=False
        )

    print("\nDone.")

    print(
        f"Manifest: {MANIFEST_PATH}"
    )

    print(
        f"Images: {IMAGE_DIR}"
    )


if __name__ == "__main__":
    main()