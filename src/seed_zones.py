"""
src/seed_zones.py
-----------------
Populates the zone_coordinates table with Police Station locations.
"""

from db_utils import get_db_connection

ZONES = [
    (1, "1501 Brighton Rd, Pittsburgh, PA 15212", 40.4572, -80.0158),
    (2, "2000 Centre Ave, Pittsburgh, PA 15219", 40.4435, -79.9793),
    (3, "830 E Warrington Ave, Pittsburgh, PA 15210", 40.4219, -79.9912),
    (4, "5858 Northumberland St, Pittsburgh, PA 15217", 40.4381, -79.9214),
    (5, "1401 Washington Blvd, Pittsburgh, PA 15206", 40.4744, -79.9091),
    (6, "312 S Main St, Pittsburgh, PA 15220", 40.4414, -80.0331)
]

def seed():
    with get_db_connection() as conn:
        print("🌱 Seeding Police Zone coordinates...")
        conn.executemany("""
            INSERT OR REPLACE INTO zone_coordinates (zone_number, address, lat, lng)
            VALUES (?, ?, ?, ?)
        """, ZONES)
        conn.commit()
    print("✅ Zones seeded.")

if __name__ == "__main__":
    seed()