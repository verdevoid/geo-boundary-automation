import os
import json
import osmnx as ox
import geopandas as gpd
from shapely.ops import unary_union

# ------------------------------
# CONFIGURATION
# ------------------------------

CITIES = [
    "South Cotabato, Philippines"
]

ADMIN_LEVEL = "8"  
# In PH:
# 4 = Region
# 6 = Province
# 8 = City/Municipality

OUTPUT_FOLDER = "output"

# ------------------------------
# SETUP
# ------------------------------

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# ------------------------------
# FUNCTIONS
# ------------------------------

def clean_geometry(geometry):
    """
    Fix invalid polygons and simplify geometry slightly.
    """
    if not geometry.is_valid:
        geometry = geometry.buffer(0)

    geometry = geometry.simplify(tolerance=0.0001, preserve_topology=True)
    return geometry


def validate_geometry(geometry):
    """
    Validate geometry and print issues.
    """
    if not geometry.is_valid:
        print("Invalid Geometry:", explain_validity(geometry))
        return False
    return True

def write_pretty_geojson(data, path):
    """
    Pretty-print GeoJSON with coordinates exactly like your template.
    Handles Polygon or MultiPolygon.
    """
    def format_coords(coords, indent=6):
        """
        Recursively format coordinates with each pair on its own line.
        """
        if isinstance(coords[0][0], (float, int)):
            # Single polygon
            lines = [f"{' ' * indent}[{c[0]}, {c[1]}]" for c in coords]
            return "[\n" + ",\n".join(lines) + "\n" + ' ' * (indent - 2) + "]"
        else:
            # MultiPolygon or nested arrays
            lines = [format_coords(c, indent + 2) for c in coords]
            return "[\n" + ",\n".join(lines) + "\n" + ' ' * (indent - 2) + "]"

    lines = ["{"]
    lines.append(f'  "type": "{data["type"]}",')
    lines.append(f'  "features": [')

    for i, feat in enumerate(data["features"]):
        lines.append("    {")
        lines.append(f'      "type": "{feat["type"]}",')
        lines.append(f'      "id": {feat.get("id", "null")},')
        # Pretty-print properties
        prop_json = json.dumps(feat.get("properties", {}), indent=6)
        prop_lines = ["      \"properties\": {"]
        for line in prop_json.splitlines()[1:-1]:  # skip outer braces
            prop_lines.append("      " + line)
        prop_lines.append("      },")
        lines.extend(prop_lines)
        # Geometry
        lines.append("      \"geometry\": {")
        lines.append(f'        "type": "{feat["geometry"]["type"]}",')
        lines.append(f'        "coordinates": {format_coords(feat["geometry"]["coordinates"], 10)}')
        lines.append("      }")
        lines.append("    }" + ("," if i < len(data["features"]) - 1 else ""))
    
    lines.append("  ]")
    lines.append("}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def process_city(city_name):
    print(f"\nProcessing: {city_name}")
    try:
        # 1. Fetch data
        gdf = ox.features_from_place(
            city_name, {"boundary": "administrative", "admin_level": ADMIN_LEVEL}
        )
        if gdf.empty:
            print("No features found.")
            return

        # 2. Keep only Polygon/MultiPolygon
        gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
        gdf = gdf[['name', 'geometry']]  # minimal properties
        gdf = gdf.to_crs(epsg=4326)

        # 3. Clean & simplify
        gdf["geometry"] = gdf["geometry"].apply(lambda g: g.buffer(0) if not g.is_valid else g)
        gdf["geometry"] = gdf.simplify(tolerance=0.0001, preserve_topology=True)

        # 4. Merge all polygons into one
        merged_geom = unary_union(gdf.geometry.tolist())

        # 5. Prepare GeoJSON dict with one Feature
        feature = {
            "type": "Feature",
            "id": None,
            "properties": {
                "name": city_name,
                "source": "user-drawn",
                "nurseries": [],
            },
            "geometry": json.loads(gpd.GeoSeries([merged_geom]).to_json())["features"][0]["geometry"]
        }

        geo_dict = {
            "type": "FeatureCollection",
            "features": [feature]
        }

        # 6. Write pretty-printed coordinates
        safe_name = city_name.replace(",", "").replace(" ", "_")
        output_path = os.path.join(OUTPUT_FOLDER, f"{safe_name}.geojson")
        write_pretty_geojson(geo_dict, output_path)

        print(f"Exported Merged Polygon: {output_path}")

    except Exception as e:
        print("Error:", e)

# ------------------------------
# MAIN EXECUTION
# ------------------------------

if __name__ == "__main__":
    for city in CITIES:
        process_city(city)

    print("\nBatch processing complete.")