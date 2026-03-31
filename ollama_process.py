"""
ollama_process.py
-----------------
Reads unprocessed posts from the posts table, sends each to Ollama
(llama3.2) to extract location and severity, and saves results to
the processed_posts table.

Usage:
    python ollama_process.py

Requirements:
    pip install requests
"""

import sqlite3
import requests
import json
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = "pittsburgh.db"
OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "llama3.2"
FALLBACK_LOCATION = "Pittsburgh, PA"

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection) -> None:
    """Add processed_posts table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_posts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id        INTEGER UNIQUE REFERENCES posts(id),
            severity       INTEGER,
            location       TEXT,
            location_found BOOLEAN,
            processed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("processed_posts table ready.")


# ---------------------------------------------------------------------------
# Ollama inference
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """You are analyzing Pittsburgh police scanner posts.

Extract the following from this post and return ONLY valid JSON, nothing else:
1. "location": the most specific Pittsburgh location mentioned (street, neighborhood, etc). If none found, use "{fallback}".
2. "location_found": true if a real location was found, false if using fallback.
3. "severity": YOU MUST ALWAYS return a score from 0-5, never null or missing:
   0 = Not a scanner post (e.g. news article, repost, unrelated content)
   1 = Trivial / silly (e.g. noise complaint, old person called about a protest)
   2 = Minor (e.g. minor fender bender, small disturbance)
   3 = Moderate (e.g. fight, theft, non-injury accident)
   4 = Serious (e.g. armed robbery, serious injury)
   5 = Critical / life threatening (e.g. shots fired, person stabbed, homicide)

Post: {text}

Respond ONLY with JSON like this:
{{"location": "Fifth Ave and Craig St", "location_found": true, "severity": 3}}"""


def call_ollama(text: str) -> dict | None:
    """Send a post to Ollama and return parsed JSON result."""
    prompt = PROMPT_TEMPLATE.format(text=text, fallback=FALLBACK_LOCATION)
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
        }, timeout=60)
        raw = resp.json()["response"].strip()
        # Strip markdown code fences if model adds them
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [warn] Could not parse JSON from Ollama response: {raw}")
        return None
    except Exception as e:
        print(f"  [error] Ollama call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Processing loop
# ---------------------------------------------------------------------------

def process_posts(conn: sqlite3.Connection) -> None:
    """Fetch all unprocessed posts and run them through Ollama."""
    unprocessed = conn.execute("""
        SELECT id, text FROM posts
        WHERE llm_processed = 0
        ORDER BY created_at DESC
    """).fetchall()

    total = len(unprocessed)
    print(f"\nFound {total} unprocessed post(s).\n" + "-" * 45)

    for i, (post_id, text) in enumerate(unprocessed, 1):
        print(f"[{i}/{total}] post_id={post_id} ...", end=" ")

        result = call_ollama(text)

        if result is None:
            # Ollama failed — use fallback values
            result = {
                "location": FALLBACK_LOCATION,
                "location_found": False,
                "severity": None,
            }

        # Validate severity is in range
        severity = result.get("severity")
        if severity is None:
            severity = 3
        else:
            severity = max(0, min(5, int(severity)))  # 0-5 now

        location = result.get("location") or FALLBACK_LOCATION
        location_found = bool(result.get("location_found", False))

        try:
            conn.execute("""
                INSERT OR IGNORE INTO processed_posts
                    (post_id, severity, location, location_found)
                VALUES (?, ?, ?, ?)
            """, (post_id, severity, location, location_found))

            conn.execute("""
                UPDATE posts SET llm_processed = 1 WHERE id = ?
            """, (post_id,))

            conn.commit()
            print(f"severity={severity} location='{location}' found={location_found}")
        except sqlite3.Error as e:
            print(f"\n  [db error] {e}")

        time.sleep(0.1)  # slight breathing room between requests

    print("-" * 45)
    print(f"Done. {total} post(s) processed.\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        process_posts(conn)


if __name__ == "__main__":
    main()