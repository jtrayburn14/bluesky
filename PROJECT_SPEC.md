# Project Spec: Pittsburgh Scanner AI Pipeline

## 1. Objective
An automated ETL pipeline that ingests police scanner data from Bluesky, aggregates fragmented threads into incidents, and uses LLMs to categorize, locate, and visualize public safety events in Pittsburgh.

## 2. Data Architecture (Medallion Model)
* **Bronze (Raw):** `posts` table. Immutable storage of every post and thread metadata.
* **Silver (Enriched):** `combined_posts` table. Context-aware incident aggregation with AI-generated headlines (`display_name`), summaries, and severity scores.
* **Utility (Cache):** `coordinates` table. Persistent storage of geocoded locations to minimize API latency and costs.
* **Gold (Presentation):** `incident_marts` table. A flattened, high-performance table optimized for map visualization.

## 3. Pipeline Stages
1.  **Ingestion:** Scrapes @pgh-scanner.com via ATProto API.
2.  **Transformation:** Reconstructs incident context by joining replies and quotes.
3.  **Primary Inference:** Ollama (Llama 3.2) extracts entities and initial severity.
4.  **Secondary Validation:** A specialized check for `Severity 0` records to confirm "Non-Incident" status or re-classify.
5.  **Spatial Enrichment:** Geocoding via Nominatim with local caching.

## 4. Technical Stack
* **Language:** Python 3.12 (Modular `src/` structure)
* **Database:** SQLite 3 (Star Schema)
* **Inference:** Ollama (Local LLM)
* **Containerization:** Docker & Docker Compose