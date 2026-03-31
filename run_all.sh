#!/bin/sh
set -e # Exit on any error

echo "🚀 STARTING PITTSBURGH SCANNER PIPELINE"
echo "----------------------------------------"

# 0. Setup
python src/db_utils.py

# 1. Bronze Layer
python src/bluesky_ingest.py

# 2. Silver Layer
python src/transformation.py

# 3. Gold Analysis (Primary)
python src/ollama_process.py

# 4. Secondary Validation (The "Skeptic" Pass)
python src/validator.py

# 5. Presentation Layer (Spatial)
python src/geocoder.py

echo "----------------------------------------"
echo "✅ PIPELINE COMPLETE. READY FOR VIZ."