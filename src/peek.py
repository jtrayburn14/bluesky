"""
src/peek.py
-----------
A SQL scratchpad that can also export to a clean, viewable HTML dashboard.
Usage: 
  - python src/peek.py          (Terminal output)
  - python src/peek.py --web    (Generates index.html)
"""

import sys
import os
from db_utils import get_db_connection

# Update this query to whatever you want to see in your "Web View"
QUERY = """
SELECT count(distinct incident_key)
from combined_incidents
"""

def generate_html(rows, cols):
    """Generates a simple, styled HTML table."""
    style = """
    <style>
        body { font-family: sans-serif; background: #1a1a1a; color: #e0e0e0; padding: 40px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #2d2d2d; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #3d3d3d; color: #00d4ff; text-transform: uppercase; font-size: 12px; }
        tr:hover { background: #353535; }
        .sev-5 { color: #ff4d4d; font-weight: bold; }
        .sev-4 { color: #ffa64d; }
        .sev-0 { color: #888; opacity: 0.6; }
    </style>
    """
    
    html = f"<html><head>{style}<title>PGH Scanner Mart</title></head><body>"
    html += "<h1>📡 Pittsburgh Scanner: Gold Mart View</h1>"
    html += "<table><tr>"
    
    for col in cols:
        html += f"<th>{col}</th>"
    html += "</tr>"

    for row in rows:
        # Simple color coding for severity
        sev_class = f"sev-{row[0]}"
        html += f"<tr class='{sev_class}'>"
        for val in list(row):
            html += f"<td>{val}</td>"
        html += "</tr>"
    
    html += "</table></body></html>"
    
    with open("index.html", "w") as f:
        f.write(html)
    print(f"\n✅ Dashboard generated: {os.path.abspath('index.html')}")

def run_query(web_mode=False):
    with get_db_connection() as conn:
        try:
            cursor = conn.execute(QUERY)
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()

            if not rows:
                print("No records found.")
                return

            if web_mode:
                generate_html(rows, cols)
            else:
                # Standard Terminal View
                print(f"\nCOLUMNS: {' | '.join(cols)}")
                print("-" * 100)
                for row in rows:
                    print(" | ".join(str(val) for val in list(row)))

        except Exception as e:
            print(f"SQL Error: {e}")

if __name__ == "__main__":
    is_web = "--web" in sys.argv
    run_query(web_mode=is_web)