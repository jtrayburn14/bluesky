"""
src/ollama_process.py
---------------------
SILVER+ LAYER: Performs AI Analysis on combined incidents.
Outputs results to the 'analyzed_incidents' table.
"""

import json
import re
import requests
import datetime
import sqlite3
from json import JSONDecodeError
from db_utils import get_db_connection

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "llama3.2:latest"

SYSTEM_PROMPT = """You are an emergency dispatcher analyzer. 
Analyze the following police scanner transcript and return ONLY a JSON object.
JSON Fields:
- display_name: A short, punchy headline (e.g., 'Structure Fire in Hill District')
- severity: 0 (test/non-event) to 5 (extreme emergency)
- extracted_location: The most specific street address or intersection found.
- summary: A 1-2 sentence technical summary of the event.
"""

def analyze_incidents():
    print("🧠 Starting Ollama Analysis (Silver+ Layer)...")
    
    with get_db_connection() as conn:
        # 1. Fetch incidents that haven't been analyzed yet
        # We join to analyzed_incidents to see what's missing
        unprocessed = conn.execute("""
            SELECT c.incident_key, c.combined_text 
            FROM combined_incidents c
            LEFT JOIN analyzed_incidents a ON c.incident_key = a.incident_key
            WHERE a.incident_key IS NULL
            and llm_processed = 0
            order by last_updated desc
        """).fetchall()

        if not unprocessed:
            print("  [v] All incidents are already analyzed. Nothing to do.")
            return

        print(f"  Processing {len(unprocessed)} new incidents...")

        for inc in unprocessed:
            print(f"  Analyzing: {inc['incident_key'][:15]}...", end=" ", flush=True)
            
            # Try to atomically claim this incident for processing. Use llm_processed=2 as "in-progress".
            try:
                cur = conn.execute(
                    "UPDATE combined_incidents SET llm_processed = 2 WHERE incident_key = ? AND llm_processed = 0",
                    (inc['incident_key'],)
                )
                conn.commit()
                # If no rows were updated, someone else is processing this row; skip it.
                if cur.rowcount == 0:
                    print("Skipped (claimed by another worker).")
                    continue
            except Exception as e:
                print(f"Error claiming incident for processing: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                continue

            try:
                payload = {
                    "model": MODEL_NAME,
                    "prompt": inc['combined_text'],
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                    "format": "json"
                }

                response = requests.post(OLLAMA_URL, json=payload, timeout=90)

                # Basic HTTP-level checks
                if response.status_code != 200:
                    print(f"Error: Ollama returned status {response.status_code}. Response body:\n{response.text}")
                    # reset claim so it can be retried
                    try:
                        conn.execute("UPDATE combined_incidents SET llm_processed = 0 WHERE incident_key = ?", (inc['incident_key'],))
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    continue

                # Ollama usually returns JSON with a `response` field that itself is a string
                # but models sometimes emit extra text. Be defensive when parsing.
                resp_json = None
                try:
                    resp_json = response.json()
                except Exception:
                    # fallback to raw text
                    resp_json = { 'response': response.text }

                # If the Ollama API returned an error object, surface it and skip
                if isinstance(resp_json, dict) and 'error' in resp_json:
                    print(f"Ollama API error: {resp_json.get('error')}")
                    continue

                raw = resp_json.get('response') if isinstance(resp_json, dict) else str(resp_json)

                # If the model returned a JSON string, parse it. Otherwise try to extract a JSON object.
                data = None
                try:
                    if isinstance(raw, str):
                        data = json.loads(raw)
                    else:
                        data = raw
                except JSONDecodeError:
                    # try to locate a JSON object inside the text
                    m = re.search(r"\{.*\}", str(raw), flags=re.DOTALL)
                    if m:
                        try:
                            data = json.loads(m.group(0))
                        except JSONDecodeError:
                            data = None
                    else:
                        data = None

                if not isinstance(data, dict):
                    print("Warning: failed to parse model output as JSON. Inserting a minimal record and attaching raw output for inspection.")
                    # store the raw output in the summary so we don't lose context
                    data = {
                        'display_name': 'Model parsing error',
                        'severity': 0,
                        'extracted_location': 'Unknown',
                        'summary': (raw or '')[:1000]
                    }

                # validate/clamp severity
                try:
                    severity = int(float(data.get('severity', 0)))
                except Exception:
                    severity = 0
                severity = max(0, min(5, severity))

                display_name = data.get('display_name') or 'Unknown Incident'
                extracted_location = data.get('extracted_location') or 'Unknown'
                summary = data.get('summary') or ''


                # 2+3. Atomically insert analyzed_incidents and mark the combined record as processed.
                # This ensures llm_processed is only set to 1 if the insert succeeds and the commit completes.
                try:
                    conn.execute("""
                        INSERT INTO analyzed_incidents 
                        (incident_key, display_name, severity, extracted_location, summary, analysis_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        inc['incident_key'],
                        display_name,
                        severity,
                        extracted_location,
                        summary,
                        datetime.datetime.now().isoformat()
                    ))

                    conn.execute("UPDATE combined_incidents SET llm_processed = 1 WHERE incident_key = ?", (inc['incident_key'],))
                    conn.commit()

                except sqlite3.IntegrityError as e:
                    # Do not mark processed on integrity errors; rollback so the insert did not persist.
                    print(f"DB IntegrityError when inserting analyzed_incidents: {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    # reset claim so it can be retried
                    try:
                        conn.execute("UPDATE combined_incidents SET llm_processed = 0 WHERE incident_key = ?", (inc['incident_key'],))
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    continue
                except Exception as e:
                    # Any other DB error should rollback and not mark the combined record.
                    print(f"DB Error during insert/update/commit: {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    # reset claim so it can be retried
                    try:
                        conn.execute("UPDATE combined_incidents SET llm_processed = 0 WHERE incident_key = ?", (inc['incident_key'],))
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    continue

                print("Done.")

            except Exception as e:
                # Last-resort catch-all to avoid the whole loop stopping
                print(f"Unexpected error during analysis: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                continue

    print("✅ Analysis Complete.")

if __name__ == "__main__":
    analyze_incidents()