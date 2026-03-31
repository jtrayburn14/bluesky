Project Spec: Bluesky Pittsburgh Scanner
1. Project Overview
High-level Goal: A data pipeline that ingests Pittsburgh-related scanner posts from Bluesky, performs LLM-based sentiment/severity analysis and location extraction, and visualizes the results on a geographic map.

Target Audience: Personal/Portfolio project (potential LinkedIn showcase).

Problem Statement: Raw scanner data is noisy and lacks structure. This project converts unstructured social media posts into actionable, localized data points.

2. Tech Stack
Language: Python

Containerization: Docker

Database: SQLite

LLM Engine: Ollama (Local)

Visualization: D3.js or Mapbox (TBD)

Libraries: atproto (Bluesky API), requests, pydantic (recommended for LLM output parsing).

Environment: VS Code

3. Core Features (MVP)
Ingestion: Syncing new posts from specific Pittsburgh-centric Bluesky accounts.

Processing: Extracting severity (1-5) and specific location names using Ollama.

Geocoding: Converting extracted location strings into Lat/Lng coordinates.

Visualization: A map interface showing incident "heat" or markers based on severity.

4. Technical Architecture
Data Model (Updated)
Plaintext
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
App Flow
Sync: Download/Mount the latest SQLite DB from storage.

Ingest: Fetch new posts via atproto. Handle threads by checking root_uri.

Process: Pass text to Ollama.

Constraint: Must output valid JSON with severity and location.

Geocode: Check COORDINATES table for location_raw. If missing, hit a geocoding API.

Deploy/Store: Update the DB and push to remote storage (GCS/S3/LiteFS).

5. Implementation Roadmap
[x] Phase 1: Basic ingestion from Bluesky.

[ ] Phase 2: Refine Ollama extraction (JSON mode & prompt tuning).

[ ] Phase 3: Implement geocoding logic (Pittsburgh-specific bounding box).

[ ] Phase 4: Build basic D3/Mapbox dashboard.

6. AI Instructions & "Rules"
Schema Consistency: All SQL queries must align with the POSTS and PROCESSED_POSTS tables.

Handling Threads: If a post has a root_uri, it belongs to a thread. Prioritize the text of the entire thread for better location context.

Error Handling: If Ollama fails to return JSON, log the error and mark location_found as false.