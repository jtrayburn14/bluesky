"""
src/validator.py
----------------
SECONDARY VALIDATION: Re-evaluates Severity 0 incidents to ensure no 
legitimate emergencies were missed due to ambiguous wording.
"""

from db_utils import get_db_connection
import requests
import json
OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "llama3.2:latest"

VALIDATOR_SYSTEM_PROMPT = """You are a Quality Assurance Auditor for emergency data.
Your job is to look at incidents marked as 'Severity 0' (Non-Incidents/Tests) and 
determine if they were correctly classified. 

If it's actually an emergency, re-classify it (1-5).
If it's truly a test, drill, or non-event, keep it at 0."""

def validate_low_severity():
    with get_db_connection() as conn:
        # Pull incidents marked as 0 from the analyzed layer
        low_sev_incidents = conn.execute("""
            SELECT incident_key, summary, display_name 
            FROM analyzed_incidents 
            WHERE severity = 0
        """).fetchall()

        if not low_sev_incidents:
            print("No Severity 0 incidents to validate.")
            return

        print(f"Validating {len(low_sev_incidents)} 'Severity 0' records...")

        for inc in low_sev_incidents:
            prompt = f"Original Classification: {inc['display_name']}\nText: {inc['combined_text']}\n\nIs this actually an emergency? Return JSON: {{'is_emergency': bool, 'new_severity': int, 'reason': 'string'}}"
            
            try:
                resp = requests.post(OLLAMA_URL, json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "system": VALIDATOR_SYSTEM_PROMPT,
                    "stream": False,
                    "format": "json"
                }, timeout=60)
                
                # defensive parsing similar to ollama_process
                resp_json = resp.json() if resp.status_code == 200 else {'response': resp.text}
                try:
                    result = json.loads(resp_json.get('response', '{}'))
                except Exception:
                    result = {}
                
                if result.get('is_emergency'):
                    new_sev = result.get('new_severity', 1)
                    conn.execute("UPDATE combined_posts SET severity = ? WHERE id = ?", (new_sev, inc['id']))
                    print(f"  [Re-Classified] {inc['display_name']} -> Severity {new_sev}")
                else:
                    print(f"  [Confirmed 0] {inc['display_name']}")
                
                conn.commit()
            except Exception as e:
                print(f"  [error] Validation failed for {inc['id']}: {e}")

if __name__ == "__main__":
    validate_low_severity()