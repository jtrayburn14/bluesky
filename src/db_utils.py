"""
src/db_utils.py
---------------
Utility functions for database connection management and schema initialization.
"""

import sqlite3
import os
from schema import TABLES, INDEXES

# The database lives in the root of the /app container
DB_PATH = "pittsburgh.db"

def get_db_connection():
    """
    Creates a connection to the SQLite database.
    Sets row_factory to Row so columns can be accessed by name.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database using the definitions in schema.py.
    This is idempotent; it won't delete data if tables already exist.
    """
    print(f"Initializing database at: {os.path.abspath(DB_PATH)}")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Create all defined tables
        for table_name, ddl in TABLES.items():
            try:
                cursor.execute(ddl)
                print(f"  [ok] Table verified: {table_name}")
            except sqlite3.Error as e:
                print(f"  [error] Failed to create table {table_name}: {e}")
        
        # 2. Create all defined indexes
        for idx_sql in INDEXES:
            try:
                cursor.execute(idx_sql)
            except sqlite3.Error as e:
                print(f"  [error] Failed to create index: {e}")
                
        conn.commit()
    print("Database initialization complete.")

if __name__ == "__main__":
    # If run directly, just initialize the DB
    init_db()