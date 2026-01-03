# src/fathom/librarian.py

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import yaml
import os

# --- Configuration Loading (copied from other modules) ---
def load_config(config_path: Path = Path("config.yaml")) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()
DB_PATH = Path(CONFIG["librarian"]["db_path"])

# --- Database Connection ---
def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# --- Table Creation ---
def create_tables():
    """Creates the necessary tables in the database if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL,
            last_indexed_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print(f"Database tables ensured for {DB_PATH}.")

# --- CRUD Operations ---
def add_project(name: str, path: Path) -> Optional[int]:
    """Adds a new project to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO projects (name, path) VALUES (?, ?)", (name, str(path.resolve())))
        conn.commit()
        print(f"Project '{name}' added at '{path}'.")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        print(f"Error: Project with name '{name}' already exists.")
        return None
    finally:
        conn.close()

def get_project_path(name: str) -> Optional[Path]:
    """Retrieves the absolute Path for a given project name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM projects WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Path(row['path'])
    return None

def list_projects() -> List[Dict[str, Any]]:
    """Lists all registered projects."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, path, last_indexed_at FROM projects ORDER BY name")
    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return projects

def update_project_timestamp(name: str):
    """Updates the 'last_indexed_at' timestamp for a project."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("UPDATE projects SET last_indexed_at = ? WHERE name = ?", (now, name))
    conn.commit()
    conn.close()
    print(f"Project '{name}' last_indexed_at updated to {now}.")

def remove_project(name: str):
    """Removes a project from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    print(f"Project '{name}' removed from the database.")


if __name__ == "__main__":
    print("--- Testing Librarian Module ---")
    
    # Ensure tables are created
    create_tables()

    test_project_name = "test_project_fathom"
    test_project_path = Path("/tmp/fathom_test_project") # Use a temporary path for testing

    # Add a project
    print(f"\nAdding project: {test_project_name} at {test_project_path}")
    add_project(test_project_name, test_project_path)
    add_project(test_project_name, test_project_path) # Should show integrity error

    # List projects
    print("\nListing all projects:")
    all_projects = list_projects()
    for p in all_projects:
        print(f"  Name: {p['name']}, Path: {p['path']}, Last Indexed: {p['last_indexed_at']}")

    # Get project path
    print(f"\nGetting path for '{test_project_name}':")
    path = get_project_path(test_project_name)
    if path:
        print(f"  Path: {path}")
    else:
        print(f"  Project '{test_project_name}' not found.")

    # Update timestamp
    print(f"\nUpdating timestamp for '{test_project_name}'...")
    update_project_timestamp(test_project_name)
    
    # List projects again to see updated timestamp
    print("\nListing all projects (after timestamp update):")
    all_projects = list_projects()
    for p in all_projects:
        print(f"  Name: {p['name']}, Path: {p['path']}, Last Indexed: {p['last_indexed_at']}")

    # Remove project
    print(f"\nRemoving project: {test_project_name}")
    remove_project(test_project_name)

    # List projects after removal
    print("\nListing all projects (after removal):")
    all_projects = list_projects()
    if not all_projects:
        print("  No projects found.")
    else:
        for p in all_projects:
            print(f"  Name: {p['name']}, Path: {p['path']}, Last Indexed: {p['last_indexed_at']}")
    
    # Clean up the test database file
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"\nCleaned up test database file: {DB_PATH}")
