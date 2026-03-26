"""
bluesky_ingest.py
-----------------
Pulls all posts from a single Bluesky account (@pgh-scanner.com)
and stores them in a local SQLite database.

Usage:
    python bluesky_ingest.py

Requirements:
    pip install atproto
"""

import sqlite3
import time
from atproto import Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TARGET_HANDLE = "pgh-scanner.com"
DB_PATH = "pittsburgh.db"
FETCH_LIMIT = 100  # max per page (Bluesky API max is 100)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist yet."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            uri           TEXT UNIQUE,
            author        TEXT,
            text          TEXT,
            created_at    TEXT,
            likes         INTEGER DEFAULT 0,
            llm_processed BOOLEAN DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id    INTEGER REFERENCES posts(id),
            place_name TEXT,
            geocoded   BOOLEAN DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coordinates (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            place_name   TEXT UNIQUE,
            lat          REAL,
            lng          REAL,
            display_name TEXT
        )
    """)
    conn.commit()
    print("DB initialized.")


# ---------------------------------------------------------------------------
# Bluesky ingestion
# ---------------------------------------------------------------------------

def fetch_all_posts(client: Client) -> list[dict]:
    """
    Paginate through all posts from TARGET_HANDLE using the cursor.
    Bluesky returns a cursor when more pages exist — we keep fetching
    until there's nothing left.
    """
    all_posts = []
    cursor = None
    page = 1

    while True:
        print(f"  Fetching page {page}...", end=" ")
        params = {"actor": TARGET_HANDLE, "limit": FETCH_LIMIT}
        if cursor:
            params["cursor"] = cursor

        try:
            response = client.app.bsky.feed.get_author_feed(params)
        except Exception as e:
            print(f"\n  [error] API call failed: {e}")
            break

        feed = response.feed
        if not feed:
            print("no more posts.")
            break

        for item in feed:
            post = item.post
            # Skip reposts — only keep original posts by this account
            if post.author.handle != TARGET_HANDLE:
                continue
            all_posts.append({
                "uri":        post.uri,
                "author":     post.author.handle,
                "text":       post.record.text,
                "created_at": post.record.created_at,
                "likes":      post.like_count or 0,
            })

        print(f"{len(feed)} fetched ({len(all_posts)} total so far).")

        cursor = getattr(response, "cursor", None)
        if not cursor:
            break

        page += 1
        time.sleep(0.3)  # be polite to the API

    return all_posts


def save_posts(conn: sqlite3.Connection, posts: list[dict]) -> int:
    """Insert posts into DB, skipping any already stored. Returns new row count."""
    new = 0
    for p in posts:
        try:
            before = conn.total_changes
            conn.execute(
                """
                INSERT OR IGNORE INTO posts (uri, author, text, created_at, likes)
                VALUES (:uri, :author, :text, :created_at, :likes)
                """,
                p,
            )
            if conn.total_changes > before:
                new += 1
        except sqlite3.Error as e:
            print(f"  [db error] {e}")
    conn.commit()
    return new


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    client = Client()
    # No login needed for public accounts.
    # If the account is private, add:
    #   client.login("your.handle.bsky.social", "your-app-password")

    print(f"Target account: @{TARGET_HANDLE}")
    print(f"DB: {DB_PATH}\n" + "-" * 45)

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)

        print(f"\nFetching all posts from @{TARGET_HANDLE}...")
        posts = fetch_all_posts(client)

        print(f"\nSaving {len(posts)} post(s) to DB...")
        new_count = save_posts(conn, posts)

        print("-" * 45)
        print(f"Done. {new_count} new post(s) added to {DB_PATH}\n")


if __name__ == "__main__":
    main()