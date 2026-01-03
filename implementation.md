# Fathom: Implementation Summary & Next Steps

This document provides a summary of the Fathom project's implementation to date and outlines the plan for the final core component: The Librarian.

---

## Fathom: Implementation Summary

The core Fathom search engine is now operational as a functional prototype. It successfully integrates three distinct search backends (semantic, literal, and structural) into a unified API.

### Completed Components

#### 1. Automated Setup (`setup.sh`)

A comprehensive setup script was created to automate the installation of all system-level and Python dependencies, making the project easier to onboard for new users.
*   **Functionality:** Checks for and installs `ripgrep`, `coursier`, `protoc` (via `protobuf`), and `scip-java`. It also creates the Python virtual environment and installs all required `pip` packages.
*   **Files Created:** `setup.sh`

#### 2. Phase 1: The "Brain" (Semantic Search)

This component understands the *meaning* of code.
*   **Functionality:** Uses `tree-sitter` to parse Java code into methods, generates vector embeddings for each method using `sentence-transformers`, and stores them in a persistent `ChromaDB` database. A search function queries this database to find semantically similar code snippets.
*   **Files Created:** `src/fathom/parser_fixed.py`, `src/fathom/indexer_with_query_fixed.py`

#### 3. Phase 2: The "Eyes" (Literal & Structural Search)

This component provides precision for exact matching and code navigation.
*   **Literal Search:**
    *   **Functionality:** Uses `ripgrep` (`rg`) to perform high-speed, literal text searches across a project. The results are parsed from `rg`'s JSON output.
    *   **Files Created:** `src/fathom/searcher_new.py`
*   **Structural Search:**
    *   **Functionality:** Uses `scip-java` to generate an `index.scip` file for a Java project. A Python querier was built to parse this Protobuf file and find the definition of a given symbol.
    *   **Files Created:** `scip.proto`, `scip_pb2.py`, `src/fathom/scip_integrator_final_working.py`, `src/fathom/scip_querier_final_working.py`

#### 4. Phase 3: The "Engine" (API Server)

This component brings all search backends together into a single, unified API.
*   **Functionality:** A `FastAPI` server provides a `/search` endpoint that accepts a query and a `search_type`. It intelligently routes the request to the correct backend (semantic, literal, or structural) and returns the results in a standardized JSON format.
*   **Files Created:** `src/fathom/main_final.py`

---

## Next Steps: Phase 3 - The Librarian (Manager)

The final core component from the original plan is The Librarian. Its purpose is to manage multiple projects, track their indexing status, and allow the Fathom engine to search across different codebases.

### Goal

To replace the current hardcoded project path logic with a persistent database that tracks all registered projects.

### Technology

*   **Database:** SQLite (lightweight, file-based, perfect for this use case).
*   **Python Library:** `sqlite3` (built-in to Python).

### Implementation Plan

#### Step 1: Create the Librarian Module (`src/fathom/librarian.py`)

This new file will contain all database interaction logic, abstracting it away from the rest of the application.

*   **Database Connection:** A function to connect to the SQLite database file (e.g., `fathom_librarian.db`).
*   **Schema Setup:** A function `create_tables()` to create the necessary tables if they don't exist:
    *   **`projects` table:**
        *   `id` INTEGER PRIMARY KEY
        *   `name` TEXT NOT NULL UNIQUE (e.g., "sample_java_project")
        *   `path` TEXT NOT NULL (e.g., "/Users/ayuranjan/Desktop/Project/Fathom/sample_java_project")
        *   `last_indexed_at` TIMESTAMP
*   **CRUD Functions:**
    *   `add_project(name: str, path: str)`: Adds a new project to the database.
    *   `remove_project(name: str)`: Removes a project.
    *   `get_project_path(name: str) -> Path`: Retrieves the file path for a given project name.
    *   `list_projects() -> List[Dict]`: Returns a list of all registered projects.
    *   `update_project_timestamp(name: str)`: Updates the `last_indexed_at` field to the current time after indexing.

#### Step 2: Integrate Librarian with the Search Engine

The `main_final.py` script will be updated to use the new Librarian.

*   The `get_project_path()` helper function inside `main_final.py` will be removed.
*   It will be replaced with calls to `librarian.get_project_path()` to resolve the `project_name` from an API request to a file system path.

#### Step 3: Integrate Librarian with the Indexers

The indexing scripts (`indexer_with_query_fixed.py` and `scip_integrator_final_working.py`) will be updated.

*   The main function in these scripts will be modified to accept a project `name` instead of a `path`.
*   They will use `librarian.get_project_path()` to find the project on disk.
*   After a successful indexing run, they will call `librarian.update_project_timestamp()` to record that the project's indexes are now up-to-date.

#### Step 4: Create a Management CLI (`manage.py`)

To make the Librarian usable, we'll create a simple command-line interface in the project root.

*   **File:** `manage.py`
*   **Functionality:** This script will use Python's `argparse` to create a simple CLI tool for managing projects.
    *   `python manage.py add <name> <path>`: To register a new project.
    *   `python manage.py remove <name>`: To unregister a project.
    *   `python manage.py list`: To show all registered projects.
    *   `python manage.py index <name>`: A shortcut to run both the semantic and structural indexers for a specific project.
