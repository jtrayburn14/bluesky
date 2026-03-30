# bluesky

DE project 

data:
```
POSTS (Raw Data)
├── id             (Primary Key)
├── uri            (Unique ATProto URI)
├── author         (DID or Handle)
├── text           (Original content)
├── created_at     (Timestamp)
├── root_uri       (FK to parent - for threads)
├── parent_uri     (FK to immediate parent)
├── quote_uri      (URI of quoted post)
└── llm_processed  (Boolean)

PROCESSED_POSTS
├── id             (Primary Key)
├── post_id        (FK → POSTS.id)
├── severity       (INTEGER 1-5)
├── location_raw   (TEXT - as extracted by LLM)
├── location_found (BOOLEAN - true if extraction succeeded)
└── processed_at   (Timestamp)

COORDINATES (Cache for Geocoding)
├── place_name     (PK - e.g., "Liberty Ave & 11th St")
├── lat            (FLOAT)
├── lng            (FLOAT)
└── display_name   (TEXT - full address from provider)
```
Running the api ingestion:
```
docker compose run --rm pipeline python bluesky_ingest.py
```
Running the sentiment analysis:
```
docker compose run --rm pipeline python ollama_process.py
```

QA:
```
docker compose run --rm pipeline bash
sqlite3 pittsburgh.db
```