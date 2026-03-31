# bluesky

To run yourself:
- make sure you have a Bluesky account
- create a .env file in the root dir
- add a BSKY_HANDLE with you handle
- create a app_password within bluesky (setting -> security & privacy ...)
- add your app_password to the .env as BSKY_PASSWORD

data structure can be found in src/schema.py

Running the api ingestion only:
```
docker compose run pipeline python src/bluesky_ingest.py
```
Running the sentiment analysis only:
```
docker compose run pipeline python src/ollama_process.py
```

QA:
- make any query changes to the file peek.py
- then run:
    ```
    docker compose run pipeline python src/peek.py
    ```
- or if you just want to query everything run:
```


Initialize & Ingest (Bronze):
docker compose run pipeline python src/bluesky_ingest.py

Transform (Silver):
docker compose run pipeline python src/transformation.py

Analyze (Silver Enrichment):
docker compose run pipeline python src/ollama_process.py