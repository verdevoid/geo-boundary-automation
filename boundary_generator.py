import os
import json
import osmnx as ox
import geopandas as gpd

OUTPUT_FOLDER = "output"

PLACES = [
    {"name": "Quezon City, Philippines", "admin_level": "6"},
    {"name": "Makati City, Philippines", "admin_level": "6"},
    {"name": "Batanes, Philippines", "admin_level": "6"},
    # add more here
]

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)


def process_place(place_name, expected_admin_level=None):
    print(f"\nProcessing: {place_name}")

    try:
        # 1️⃣ Get exact matched boundary
        gdf = ox.geocode_to_gdf(place_name)

        if gdf.empty:
            print("No boundary found.")
            return

        # 2️⃣ Check admin level if requested
        # Extract OSM identifiers
        osm_type = gdf.iloc[0].get("type", "unknown")
        osm_id = gdf.iloc[0].get("osmid", "N/A")

        print("OSM ID:", osm_id)
        print("OSM Type:", osm_type)

        # Query Overpass for tags
        tags_gdf = ox.features_from_polygon(
            gdf.iloc[0].geometry,
            tags={"boundary": "administrative"}
        )

        if not tags_gdf.empty and "admin_level" in tags_gdf.columns:
            detected_levels = tags_gdf["admin_level"].unique()
            print("Detected admin levels in polygon:", detected_levels)
        else:
            print("Could not detect admin_level via Overpass.")
        # 3️⃣ Clean geometry only (no simplification for QA phase)
        gdf = gdf.to_crs(epsg=4326)
        gdf["geometry"] = gdf["geometry"].apply(
            lambda g: g.buffer(0) if not g.is_valid else g
        )

        # 4️⃣ Sanity checks
        geom = gdf.iloc[0].geometry

        print("Geometry type:", geom.geom_type)
        print("Vertex count:", len(list(geom.exterior.coords)) if geom.geom_type == "Polygon" else "MultiPolygon")

        # 5️⃣ Export
        safe_name = place_name.replace(",", "").replace(" ", "_")
        output_path = os.path.join(OUTPUT_FOLDER, f"{safe_name}.geojson")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json.loads(gdf.to_json()), f, indent=2)

        print(f"Exported: {output_path}")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    for entry in PLACES:
        process_place(entry["name"], entry["admin_level"])

    print("\nBatch processing complete.")
