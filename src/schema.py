"""
src/schema.py
-------------
The Master Schema for the Medallion Architecture.
Includes Bronze (Raw), Silver (Aggregated), Silver+ (AI), and Gold (Mart) layers.
"""

TABLES = {
# 1. BRONZE: Raw source of truth (Immutable)
    "posts": """
        CREATE TABLE IF NOT EXISTS posts (
            uri TEXT PRIMARY KEY,
            root_uri TEXT,
            parent_uri TEXT, -- <--- ADD THIS LINE
            quote_uri TEXT,
            text TEXT,
            created_at TEXT,
            author TEXT,
            likes INTEGER DEFAULT 0
        )
    """,
    # 2. SILVER: Aggregated Threads (Transformation Layer)
    "combined_incidents": """
        CREATE TABLE IF NOT EXISTS combined_incidents (
            incident_key TEXT PRIMARY KEY,
            combined_text TEXT,
            last_updated TEXT,
            llm_processed BOOLEAN DEFAULT 0
        )
    """,

    # 3. SILVER+: AI Insights (Ollama Analysis Layer)
    "analyzed_incidents": """
        CREATE TABLE IF NOT EXISTS analyzed_incidents (
            incident_key TEXT PRIMARY KEY,
            display_name TEXT,
            severity INTEGER,
            extracted_location TEXT,
            summary TEXT,
            analysis_timestamp TEXT,
            FOREIGN KEY(incident_key) REFERENCES combined_incidents(incident_key)
        )
    """,

    # 4. REFERENCE: The Location Cache (Geocoder Logic)
    "coordinates": """
        CREATE TABLE IF NOT EXISTS coordinates (
            place_name TEXT PRIMARY KEY,
            lat REAL,
            lng REAL,
            last_validated TEXT
        )
    """,
    "zone_coordinates": """
        CREATE TABLE IF NOT EXISTS zone_coordinates (
            zone_number INTEGER PRIMARY KEY,
            address TEXT,
            lat REAL,
            lng REAL
        )
    """,

    # 5. GOLD: Final Presentation Mart (Flattened for Map)
    "incident_marts": """
        CREATE TABLE IF NOT EXISTS incident_marts (
            incident_key TEXT PRIMARY KEY,
            display_name TEXT,
            severity INTEGER,
            zone INTEGER,
            lat REAL,
            lng REAL,
            summary TEXT,
            last_updated TEXT,
            FOREIGN KEY(incident_key) REFERENCES analyzed_incidents(incident_key)
        )
    """
}

# Helpful for performance on the Silver/Gold joins
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_posts_root ON posts(root_uri);",
    "CREATE INDEX IF NOT EXISTS idx_posts_quote ON posts(quote_uri);",
    "CREATE INDEX IF NOT EXISTS idx_combined_processed ON combined_incidents(llm_processed);"
]