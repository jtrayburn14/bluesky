"""
src/geocoder.py
---------------
GOLD LAYER: Resolves locations to coordinates.
Handles "Zone X" mentions by snapping to Police Station coordinates.
"""

import re
import datetime
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from db_utils import get_db_connection

# Initialize Geocoder
geolocator = Nominatim(user_agent="pgh_scanner_analytics_v1")
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.1)

def extract_zone_number(text):
    """Helper to find 'Zone 5' etc inside the extracted_location string."""
    if not text: return None
    match = re.search(r'zone\s*(\d+)', text.lower())
    return int(match.group(1)) if match else None

def build_gold_mart():
    print("🌍 Building Gold Layer...")
    
    with get_db_connection() as conn:
        # NOTICE: No 'a.zone' here, as it's intentionally not in the table
        to_process = conn.execute("""
            SELECT a.incident_key, a.display_name, a.severity, a.extracted_location, a.summary, c.last_updated 
            FROM analyzed_incidents a
            JOIN combined_incidents c ON a.incident_key = c.incident_key
            LEFT JOIN incident_marts g ON a.incident_key = g.incident_key
            WHERE g.incident_key IS NULL
        """).fetchall()

        if not to_process:
            print("  [v] Gold Mart is up to date.")
            return

        for inc in to_process:
            lat, lng = None, None
            loc_str = inc['extracted_location']
            
            # 1. Try to find a Zone ID from the location string
            zone_id = extract_zone_number(loc_str)
            
            # 2. Logic: If it IS a Zone mention, try the Station Fallback first
            if zone_id:
                zone_data = conn.execute(
                    "SELECT lat, lng FROM zone_coordinates WHERE zone_number = ?", 
                    (zone_id,)
                ).fetchone()
                if zone_data:
                    lat, lng = zone_data['lat'], zone_data['lng']

            # 3. If no Lat/Lng yet (or not a Zone), try Cache/API
            if not lat and loc_str and loc_str.lower() not in ['unknown', 'none']:
                cache = conn.execute(
                    "SELECT lat, lng FROM coordinates WHERE place_name = ?", 
                    (loc_str,)
                ).fetchone()
                
                if cache:
                    lat, lng = cache['lat'], cache['lng']
                else:
                    try:
                        print(f"  [api] Geocoding: {loc_str}")
                        query = f"{loc_str}, Pittsburgh, PA"
                        location = geocode_service(query)
                        if location:
                            lat, lng = location.latitude, location.longitude
                            conn.execute("""
                                INSERT OR IGNORE INTO coordinates (place_name, lat, lng, last_validated)
                                VALUES (?, ?, ?, ?)
                            """, (loc_str, lat, lng, datetime.datetime.now().isoformat()))
                    except Exception as e:
                        print(f"  [!] Error: {e}")

            # 4. Final Save to Gold (Includes the zone_id we extracted via Regex)
            if lat and lng:
                conn.execute("""
                    INSERT INTO incident_marts 
                    (incident_key, display_name, severity, zone, lat, lng, summary, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    inc['incident_key'],
                    inc['display_name'],
                    inc['severity'],
                    zone_id, # This is the regex result, not a db column
                    lat,
                    lng,
                    inc['summary'],
                    inc['last_updated']
                ))
                conn.commit()

    print("✅ Gold Layer Build Complete.")

if __name__ == "__main__":
    build_gold_mart()