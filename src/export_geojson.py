"""
src/export_geojson.py
---------------------
Export Script: Converts the Gold Mart into a GeoJSON JS file.
CRITICAL: Swaps (Lat, Lng) to [Lng, Lat] for Leaflet/GeoJSON standards.
"""

import json
import os
from db_utils import get_db_connection

# Define the output path (same directory as index.html)
OUTPUT_FILE = "data.js"

def export_to_geojson():
    print(f"📡 Exporting Gold Mart to {OUTPUT_FILE}...")
    
    with get_db_connection() as conn:
        # 1. Fetch all geocoded incidents
        # We explicitly filter for NOT NULL to avoid empty points breaking the map
        query = """
            SELECT incident_key, display_name, severity, lat, lng, summary, last_updated
            FROM incident_marts
            WHERE lat IS NOT NULL AND lng IS NOT NULL
        """
        rows = conn.execute(query).fetchall()

        if not rows:
            print("  [!] No geocoded data found in incident_marts. Run geocoder.py first.")
            return

        # 2. Build the GeoJSON structure
        features = []
        for row in rows:
            feature = {
                "type": "Feature",
                "properties": {
                    "id": row['incident_key'],
                    "title": row['display_name'],
                    "severity": row['severity'],
                    "summary": row['summary'],
                    "updated": row['last_updated']
                },
                "geometry": {
                    "type": "Point",
                    # GeoJSON standard is [Longitude, Latitude]
                    "coordinates": [row['lng'], row['lat']]
                }
            }
            features.append(feature)

        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }

        # 3. Write as a JavaScript variable to bypass CORS issues
        with open(OUTPUT_FILE, "w") as f:
            f.write(f"var incidentData = {json.dumps(geojson_data, indent=2)};")
        
        print(f"✅ Success! Exported {len(features)} incidents.")

if __name__ == "__main__":
    export_to_geojson()