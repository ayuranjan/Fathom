# Fathom: A Code-Aware Search Engine

## Project Overview

Fathom is a multi-faceted code search engine designed to provide deep, contextual understanding of codebases for Large Language Models (LLMs). It overcomes traditional keyword search limitations by incorporating semantic and structural analysis.

**Core Components:**

*   **The Librarian:** Manages registered code repositories and their indexing status using an SQLite database.
*   **The Indexing Worker:** Analyzes code, extracts information, generates embeddings, and builds search indices (semantic, structural, and literal).
*   **The Search Engine:** A FastAPI-based API that routes LLM queries to the appropriate backend index and synthesizes results.

## Setup and Installation

### 1. Clone the Repository

(Assuming you have cloned this repository already.)

### 2. Run the Automated Setup Script

This script will check for and install all system dependencies (Homebrew, ripgrep, coursier, protoc, scip-java) and set up the Python virtual environment and dependencies.

```bash
bash setup.sh
```
*Note: The first time `scip-java` runs, it may require `sudo` to move a binary to your PATH. Follow the on-screen instructions.*

### 3. Activate the Virtual Environment

```bash
source .venv/bin/activate
```

## How to Use Fathom

### 1. Manage Projects with `manage.py`

Use the `manage.py` CLI to interact with the Librarian.

```bash
# Add a new project (replace with your actual project path)
python3 manage.py add sample_java_project ./sample_java_project

# List all registered projects
python3 manage.py list

# Remove a project
python3 manage.py remove my-old-project
```

### 2. Index a Project

Once a project is added, index it. This will perform both semantic and structural indexing.

```bash
# Run semantic indexing for 'sample_java_project'
python3 manage.py index sample_java_project

# Run structural (SCIP) indexing for 'sample_java_project'
python3 manage.py index-scip sample_java_project
```

### 3. Start the API Server

Run the FastAPI server. It will automatically reload on code changes.

```bash
uvicorn src.fathom.main:app --host "127.0.0.1" --port 8000 --reload
```
Access the API documentation at `http://127.0.0.1:8000/docs`.

### 4. Query the API

Use `curl` or any API client to send search requests.

```bash
# Example Semantic Search
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "sample_java_project",
    "query": "how to greet someone",
    "search_type": "semantic"
  }'

# Example Literal Search
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "sample_java_project",
    "query": "System.out.println",
    "search_type": "literal"
  }'

# Example Structural Search (using a Fully Qualified Name)
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "sample_java_project",
    "query": "com.example.Main.greet",
    "search_type": "structural"
  }'

# Example: Project not found
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "non_existent_project",
    "query": "test",
    "search_type": "literal"
  }'
```

## Project Structure

*   `config.yaml`: Global project configuration.
*   `fathom_librarian.db`: SQLite database for project management.
*   `manage.py`: CLI for project management and indexing.
*   `requirements.txt`: Python dependencies.
*   `setup.sh`: Automated setup script for system and Python dependencies.
*   `pyproject.toml`: Project metadata and build configuration.
*   `src/fathom/`: Main Python source code.
    *   `__init__.py`: Python package indicator.
    *   `dependency_manager.py`: Manages external Java dependencies.
    *   `indexer.py`: Handles semantic indexing into ChromaDB.
    *   `librarian.py`: Manages project metadata in SQLite.
    *   `main.py`: FastAPI application entry point.
    *   `parser.py`: Tree-sitter Java parser setup.
    *   `scip_pb2.py`: Protobuf generated classes for SCIP.
    *   `scip_integrator.py`: Integrates `scip-java` for structural indexing.
    *   `scip_querier.py`: Queries `index.scip` files for structural search.
    *   `searcher.py`: Implements literal search using `ripgrep`.
*   `.fathom_grammars/`: Stores Tree-sitter grammars (e.g., `tree-sitter-java`).
*   `.fathom_indexes/`: Stores generated indexes (e.g., `chroma/`, `scip/`).
*   `.fathom_deps/`: Stores extracted Java dependencies for indexing.
*   `sample_java_project/`: A sample Java project for testing.
*   `_old_development_files/`: Contains older, intermediate, or debug scripts.