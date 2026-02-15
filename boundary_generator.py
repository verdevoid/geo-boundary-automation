import os
import json
import time
from datetime import datetime
import geopandas as gpd
import difflib

DATASET_PATH = "philippines-json-maps/2019/geojson"
OUTPUT_FOLDER = "output"
INDEX_FILE = "boundary_index.json"

PROVINCE_FOLDER = os.path.join(DATASET_PATH, "provinces/medres")
MUNICITY_FOLDER = os.path.join(DATASET_PATH, "municties/medres")

PLACES = [
    "Batanes",
    "Cagayan",
    "Isabela",
    "Neuva Vizcaya",   # intentional typo test
    "Quirino",
    "Tuguegarao",
    "Ilagan",
    "Santiago"
]

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)


# --------------------------------------------------
# BUILD OR LOAD CACHE
# --------------------------------------------------

def build_index():
    print("Building boundary index (first run only)...")

    index = {}

    for folder in [PROVINCE_FOLDER, MUNICITY_FOLDER]:
        for file in os.listdir(folder):
            if file.endswith(".json"):
                full_path = os.path.join(folder, file)
                try:
                    gdf = gpd.read_file(full_path)

                    cols = gdf.columns

                    # Province level
                    if "ADM1_EN" in cols:
                        name = str(gdf.iloc[0]["ADM1_EN"]).strip()
                        index[name.lower()] = full_path

                    # City/Municipality level
                    if "ADM2_EN" in cols:
                        name = str(gdf.iloc[0]["ADM2_EN"]).strip()
                        index[name.lower()] = full_path

                except Exception:
                    continue

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print("Indexed entries:", len(index))
    print("Index saved.")
    return index



def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return build_index()


# --------------------------------------------------
# FUZZY MATCHING
# --------------------------------------------------

def find_best_match(place_name, index):
    place_name_lower = place_name.lower()

    if place_name_lower in index:
        return index[place_name_lower]

    # Fuzzy matching
    matches = difflib.get_close_matches(
        place_name_lower,
        index.keys(),
        n=1,
        cutoff=0.7
    )

    if matches:
        print(f"Fuzzy matched '{place_name}' → '{matches[0]}'")
        return index[matches[0]]

    return None


# --------------------------------------------------
# GEOJSON GENERATOR
# --------------------------------------------------

def generate_feature(polygon, name):
    coords = [list(polygon.exterior.coords)]

    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": coords
        },
        "id": int(time.time() * 1000),
        "properties": {
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "name": name,
            "source": "user-drawn",
            "nurseries": []
        }
    }


def process_place(place_name, index):
    print(f"\nProcessing: {place_name}")

    file_path = find_best_match(place_name, index)

    if not file_path:
        print("No matching boundary found.")
        return

    print("Matched file:", file_path)

    gdf = gpd.read_file(file_path)
    gdf = gdf.to_crs(epsg=4326)
    gdf["geometry"] = gdf["geometry"].buffer(0)

    geom = gdf.iloc[0].geometry
    features = []

    if geom.geom_type == "MultiPolygon":
        print("Splitting MultiPolygon...")
        for i, poly in enumerate(geom.geoms, start=1):
            features.append(generate_feature(poly, f"{place_name} {i}"))
    else:
        features.append(generate_feature(geom, place_name))

    output = {
        "type": "FeatureCollection",
        "features": features
    }

    safe_name = place_name.replace(" ", "_")
    output_path = os.path.join(OUTPUT_FOLDER, f"{safe_name}.geojson")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Exported:", output_path)
    print("Features generated:", len(features))


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    index = load_index()

    for place in PLACES:
        process_place(place, index)

    print("\nBatch processing complete.")
