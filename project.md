# Fathom: A Code-Aware Search Engine - Project Documentation

## 1. Introduction & Vision

### The Problem

Traditional code search tools, while fast, are often limited to keyword-based matching. They excel at finding specific strings but fall short when it comes to understanding the *intent* behind a query. Developers and Large Language Models (LLMs) alike need to ask questions like "How do we handle retries?" or "Where is the `User` class defined?", which keyword search cannot answer effectively.

### The Fathom Solution

Fathom is a multi-faceted, code-aware search engine designed to bridge this gap. It provides a unified API that understands code on three different levels:

1.  **Semantically ("The Brain"):** Understands the *meaning* of code, allowing for natural language queries about concepts and logic.
2.  **Literally ("The Eyes"):** Provides high-speed, exact string and pattern matching for finding specific error codes, log messages, or variable names.
3.  **Structurally ("The Eyes"):** Understands the code's structure, enabling "go-to-definition" and "find-references" style queries.

By combining these three search backends, Fathom aims to provide a comprehensive and intelligent code navigation and understanding tool, primarily for consumption by LLMs and developer tools.

---

## 2. Core Features & Capabilities

*   **Semantic Search:** Ask natural language questions like "how to greet someone" and get back the most relevant code snippets from the codebase, ranked by semantic similarity.
*   **Literal Search:** Perform blazing-fast text searches for any string or pattern, powered by `ripgrep`.
*   **Structural Search:** Find the exact definition of a class or method within the codebase using precise location data from `scip-java`.
*   **Unified Search API:** A single, easy-to-use `/search` API endpoint that intelligently routes queries to the appropriate search backend.
*   **Multi-Project Management (The Librarian):** A persistent SQLite database registers and manages multiple codebases, allowing the engine to be project-aware.
*   **Automated Setup:** A `setup.sh` script automates the installation of all system-level dependencies (`ripgrep`, `coursier`, `protoc`, `scip-java`) and Python packages, ensuring a smooth onboarding experience.
*   **CLI for Management:** A `manage.py` script provides a user-friendly command-line interface for adding, removing, listing, and indexing projects in the Librarian.

---

## 3. Architecture & Implementation Details

Fathom is built on a modular architecture, with clear separation of concerns between its components.

### Component Breakdown

#### A. The Librarian (Manager)

*   **File:** `src/fathom/librarian.py`
*   **Technology:** SQLite, `sqlite3` (Python standard library).
*   **Functionality:** 
    *   Creates and manages a `fathom_librarian.db` SQLite database file.
    *   Defines a `projects` table with columns: `id`, `name` (unique), `path`, and `last_indexed_at`.
    *   Provides CRUD functions (`add`, `remove`, `get_project_path`, `list_projects`) and a function to update the indexing timestamp.

#### B. The Indexing Worker (Writer)

This component is responsible for analyzing code and creating the search indexes.

*   **Semantic Indexing:**
    *   **Files:** `src/fathom/parser.py`, `src/fathom/indexer.py`.
    *   **Process:** 
        1.  `tree-sitter` (via `tree-sitter-languages`) is used to parse Java code into an Abstract Syntax Tree (AST).
        2.  A Tree-sitter query extracts all method declarations from the AST.
        3.  The code from each method body is embedded into a vector using the `microsoft/unixcoder-base` model from `sentence-transformers`.
        4.  The vector embedding, along with metadata (file path, class/method name, line numbers), is stored in a persistent `ChromaDB` database located at `.fathom_indexes/chroma/`.

*   **Structural Indexing:**
    *   **Files:** `src/fathom/scip_integrator.py`, `src/fathom/scip_querier.py`, `src/fathom/scip_pb2.py`.
    *   **Process:** 
        1.  The `scip_integrator` script runs `scip-java index` on a target project. `scip-java` automatically detects the Maven `pom.xml` and triggers a build.
        2.  This process generates a binary `index.scip` file containing Protobuf-formatted structural code intelligence data.
        3.  The `scip.proto` schema was downloaded and compiled using `protoc` into `scip_pb2.py`, a Python module containing the necessary classes to parse the Protobuf data.
        4.  The `scip_querier` script (`scip_querier_robust.py`) loads the `index.scip` file, parses it using the generated Python classes, and iterates through its `occurrences` to find symbol definitions. It uses a robust heuristic to convert user-friendly queries (e.g., "com.example.Main.greet") into SCIP's internal descriptor format and performs accurate suffix-based matching.

#### C. The Search Engine (Reader)

*   **Files:** `src/fathom/main.py`, `src/fathom/searcher.py`.
*   **Process:** 
    *   A `FastAPI` server provides the main application interface.
    *   On startup, it ensures the Librarian database is initialized.
    *   It exposes a `/search` endpoint that accepts a `project_name`, `query`, and `search_type`.
    *   It calls the Librarian to resolve the `project_name` to a file path.
    *   Based on `search_type`, it routes the request to the appropriate backend function:
        *   `semantic`: Calls `semantic_search` from `indexer_librarian_fixed.py`.
        *   `literal`: Calls `literal_search` from `searcher_new.py`, which executes `ripgrep` as a subprocess.
        *   `structural`: Calls `structural_search` from `scip_querier_robust.py`.

---

## 4. Workarounds and Technical Challenges

The implementation process involved overcoming several technical hurdles.

1.  **`tree-sitter` Python Version Compatibility:**
    *   **Challenge:** Our initial attempts to use `tree-sitter` failed due to version incompatibilities. The documented `Language.build_library` method was missing, and the `py-tree-sitter-languages` helper package was incompatible with the newer Python 3.13.
    *   **Resolution:** This was successfully resolved by creating a Python 3.12 virtual environment and pinning the underlying `tree-sitter` package to a known compatible version (`tree-sitter==0.20.1`) in `requirements.txt`, allowing `tree_sitter_languages` to function correctly.

2.  **SCIP Structural Search Accuracy:**
    *   **Challenge:** Initially, the structural search used a simplistic substring matching method for SCIP symbols, which was identified as an accuracy bottleneck for languages with features like method overloading.
    *   **Resolution:** The structural search logic in `src/fathom/scip_querier_robust.py` was refined to convert user-friendly queries (e.g., `com.example.Main.greet`) into a precise SCIP-like descriptor format (e.g., `com/example/Main#greet().`) and then perform a robust `endswith` matching on the full SCIP symbol string. This ensures accurate identification of specific definitions, addressing the initial accuracy concern.

3.  **External Tool Dependencies:**
    *   **Challenge:** The project depends on several command-line tools (`ripgrep`, `coursier`, `protoc`, `scip-java`, `maven`). Requiring users to install these manually is error-prone.
    *   **Workaround:** We created a comprehensive `setup.sh` script that automatically checks for and installs these dependencies using Homebrew, greatly simplifying the setup process for new users.

4.  **ChromaDB Duplicate Entries:**
    *   **Challenge:** Re-indexing a project multiple times (especially after file path changes) can lead to duplicate entries in ChromaDB if old data is not explicitly cleared.
    *   **Current State:** The `if __name__ == "__main__":` block in `indexer_librarian_fixed.py` demonstrates a cleanup pattern (`remove_project` then `add_project` before indexing) to ensure a clean state for testing. A more integrated cleanup within the `manage.py index` command is a potential future improvement.

---

## 5. How to Use Fathom

1.  **Run the Setup Script:**
    For first-time setup, run the automated setup script. This will install all system and Python dependencies.
    ```bash
    ./setup.sh
    ```
    *Note: The first time this runs, it will build `scip-java` and ask you to move it to your path with a `sudo` command. You will need to run the script a second time after doing so.*

2.  **Manage Projects:**
    Use the `manage.py` script to add your projects to the Librarian.
    ```bash
    # Add a project
    .venv/bin/python manage.py add my-app /path/to/your/java/app

    # List all projects
    .venv/bin/python manage.py list
    ```

3.  **Index a Project:**
    Once a project is added, run the indexers. This will perform both semantic and structural indexing.
    ```bash
    # Index the project named 'my-app'
    .venv/bin/python manage.py index my-app
    ```

4.  **Start the API Server:**
    Run the FastAPI server in a dedicated terminal window.
    ```bash
    .venv/bin/python -m uvicorn src.fathom.main:app --reload
    ```

5.  **Query the API:**
    Use `curl` or navigate to the auto-generated documentation at `http://127.0.0.1:8000/docs` to send search requests.
    ```bash
    # Example Structural Search
    curl -X 'POST' 'http://127.0.0.1:8000/search' \
      -H 'Content-Type: application/json' \
      -d '{
      "project_name": "my-app",
      "query": "com/your/package/YourClass#yourMethod().",
      "search_type": "structural"
    }'
    ```