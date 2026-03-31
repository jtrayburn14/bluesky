import os
from atproto import Client
from db_utils import get_db_connection

HANDLE = os.getenv("BSKY_HANDLE")
PASSWORD = os.getenv("BSKY_PASSWORD")
TARGET_ACTOR = "pgh-scanner.com"

def fetch_and_store_posts():
    client = Client()
    client.login(HANDLE, PASSWORD)
    
    print(f"📡 Fetching full history for {TARGET_ACTOR}...")
    
    cursor = None
    total_new = 0
    
    with get_db_connection() as conn:
        while True:
            # Fetch with pagination
            response = client.get_author_feed(actor=TARGET_ACTOR, limit=100, cursor=cursor)
            
            for item in response.feed:
                post = item.post
                record = post.record
                
                # --- THREADING LOGIC (REPLIES) ---
                root_uri = None
                parent_uri = None
                # record.reply is a model object, not a dict
                reply_ref = getattr(record, 'reply', None)
                if reply_ref:
                    root_uri = reply_ref.root.uri
                    parent_uri = reply_ref.parent.uri

                # --- EMBED LOGIC (QUOTES) ---
                quote_uri = None
                embed = getattr(record, 'embed', None)
                if embed:
                    # Case 1: Simple Quote (app.bsky.embed.record)
                    if hasattr(embed, 'record') and hasattr(embed.record, 'uri'):
                        quote_uri = embed.record.uri
                    # Case 2: Quote with Media (app.bsky.embed.recordWithMedia)
                    elif hasattr(embed, 'record') and hasattr(embed.record, 'record'):
                        if hasattr(embed.record.record, 'uri'):
                            quote_uri = embed.record.record.uri

                # --- DB INSERT ---
                post_data = {
                    "uri": post.uri,
                    "root_uri": root_uri,
                    "parent_uri": parent_uri,
                    "quote_uri": quote_uri,
                    "author": post.author.handle,
                    "text": record.text,
                    "created_at": record.created_at,
                    "likes": getattr(post, 'like_count', 0)
                }

                conn.execute("""
                    INSERT OR IGNORE INTO posts 
                    (uri, root_uri, parent_uri, quote_uri, author, text, created_at, likes)
                    VALUES (:uri, :root_uri, :parent_uri, :quote_uri, :author, :text, :created_at, :likes)
                """, post_data)
                
                if conn.total_changes > 0:
                    total_new += 1

            # Pagination check
            cursor = response.cursor
            if not cursor:
                break
            print(f"  ... {total_new} posts processed so far ...")

        conn.commit()
    
    print(f"✅ Ingestion Complete. Total new posts added: {total_new}")

if __name__ == "__main__":
    fetch_and_store_posts()