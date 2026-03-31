"""
src/transformation.py
---------------------
SILVER LAYER: Rebuilds combined_incidents from the raw posts table.
Uses recursion to link Replies -> Quotes -> Original Posts.
"""

from db_utils import get_db_connection

def aggregate_incidents():
    print("🚀 Starting Recursive Silver Transformation...")
    
    with get_db_connection() as conn:
        # 1. Clear Silver Layer (Wipe only the derived table, NOT 'posts')
        conn.execute("DELETE FROM combined_incidents")
        conn.execute("DELETE FROM analyzed_incidents")
        
        # 2. Load all posts into memory for fast graph traversal
        rows = conn.execute("SELECT uri, root_uri, quote_uri, text, created_at FROM posts").fetchall()
        post_map = {r['uri']: dict(r) for r in rows}

        # 3. Recursive "Find the Parent" function
        def find_ultra_root(uri):
            curr = post_map.get(uri)
            if not curr:
                return uri # Parent is missing/external, this is our local root
            
            # Follow the breadcrumbs: Root URI takes priority, then Quote URI
            parent_uri = curr['root_uri'] or curr['quote_uri']
            
            if parent_uri and parent_uri in post_map:
                return find_ultra_root(parent_uri) # Recurse up the chain
            
            return uri # We've hit the absolute top

        # 4. Group posts by their Ultra Root
        incident_groups = {}
        for uri, post in post_map.items():
            root_key = find_ultra_root(uri)
            if root_key not in incident_groups:
                incident_groups[root_key] = []
            incident_groups[root_key].append(post)

        print(f"  Processed {len(rows)} posts into {len(incident_groups)} unique threads.")

        # 5. Insert into combined_incidents
        new_count = 0
        for key, thread in incident_groups.items():
            # Sort chronologically so the summary flows correctly
            thread.sort(key=lambda x: x['created_at'])
            
            combined_text = " \n ".join([p['text'] for p in thread])
            latest_time = thread[-1]['created_at']
            
            conn.execute("""
                INSERT INTO combined_incidents (incident_key, combined_text, last_updated, llm_processed)
                VALUES (?, ?, ?, 0)
            """, (key, combined_text, latest_time))
            new_count += 1
            
        conn.commit()
    
    print(f"✅ Silver Transformation Complete. {new_count} incidents created.")

if __name__ == "__main__":
    aggregate_incidents()