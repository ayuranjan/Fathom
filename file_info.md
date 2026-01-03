# Fathom Project File Information

This document summarizes the purpose and implementation logic of key files in the Fathom project.

## 1. `config.yaml`

*   **Purpose:** Central configuration file for the entire Fathom project.
*   **Implementation Logic:**
    *   Defines paths for the Librarian's SQLite database (`fathom_librarian.db`).
    *   Specifies the embedding model (`microsoft/unixcoder-base`) for semantic search.
    *   Sets storage paths for SCIP indexes (`.fathom_indexes/scip`) and ChromaDB data (`.fathom_indexes/chroma`).
    *   Configures the host (`127.0.0.1`) and port (`8000`) for the FastAPI search engine.

## 2. `pyproject.toml`

*   **Purpose:** Modern, standardized file for Python project build system configuration and metadata.
*   **Implementation Logic:**
    *   Defines the `build-system` using `setuptools>=61.0` and `setuptools.build_meta`.
    *   Specifies project `metadata` under `[project]`: `name` ("fathom"), `version` ("0.0.1"), `authors`, `description`, `readme` ("README.md").
    *   Declares the required Python version: `requires-python = ">=3.12"`.
    *   Includes `classifiers` for PyPI categorization.
    *   Configures `setuptools` to find packages within the `src` directory (`where = ["src"]`).

## 3. `requirements.txt`

*   **Purpose:** Lists all Python package dependencies with their pinned versions.
*   **Implementation Logic:**
    *   Used by `pip install -r requirements.txt` to install project dependencies into the Python environment.
    *   Ensures consistent dependency versions across different environments.
    *   Includes libraries like `tree-sitter`, `tree_sitter_languages`, `chromadb`, `sentence-transformers`, `fastapi`, `uvicorn`, `PyYAML`, `watchdog`, etc.

## 4. `setup.sh`

*   **Purpose:** Automated shell script for setting up system-level dependencies and the Python environment.
*   **Implementation Logic:**
    *   Checks for and installs Homebrew (macOS package manager).
    *   Installs command-line tools: `ripgrep` (for literal search), `coursier`, `protoc`, `scip-java` (for structural indexing).
    *   Sets up a Python 3.12 virtual environment (`.venv`).
    *   Installs Python dependencies listed in `requirements.txt` into the virtual environment.
    *   Clones the Tree-sitter Java grammar into `.fathom_grammars/tree-sitter-java`.

## 5. `src/fathom/librarian.py`

*   **Purpose:** Manages metadata about code projects in an SQLite database.
*   **Implementation Logic:**
    *   Loads `db_path` from `config.yaml` for the SQLite database file (`fathom_librarian.db`).
    *   `get_db_connection()`: Establishes a connection to the SQLite database, with `row_factory` set to `sqlite3.Row` for dictionary-like row access.
    *   `create_tables()`: Creates the `projects` table (if not exists) with `id`, `name`, `path`, and `last_indexed_at` columns.
    *   `add_project(name, path)`: Inserts a new project record, handling unique name constraints.
    *   `get_project_path(name)`: Retrieves the `Path` to a project's root directory.
    *   `list_projects()`: Fetches and returns all registered projects as a list of dictionaries.
    *   `update_project_timestamp(name)`: Updates the `last_indexed_at` field for a project.
    *   `remove_project(name)`: Deletes a project record.
    *   Includes `if __name__ == "__main__":` block for self-testing.

## 6. `manage.py`

*   **Purpose:** Command-line interface (CLI) for managing Fathom projects.
*   **Implementation Logic:**
    *   Uses `argparse` to define subcommands: `add`, `remove`, `list`, `index` (semantic), `index-scip` (structural).
    *   Imports project management functions from `fathom.librarian`, `fathom.indexer` (semantic), and `fathom.scip_integrator` (structural).
    *   Calls `create_tables()` to ensure the Librarian database is ready.
    *   Routes commands to the appropriate backend functions based on `args.command`:
        *   `add`: Calls `add_project` after path validation.
        *   `remove`: Calls `remove_project`.
        *   `list`: Calls `list_projects` and formats output.
        *   `index`: Calls `index_project_semantic`.
        *   `index-scip`: Calls `get_project_path` and then `run_scip_java_index`.

## 7. `src/fathom/parser.py`

*   **Purpose:** Configures and provides the Tree-sitter parser for Java source code.
*   **Implementation Logic:**
    *   Imports `tree_sitter.Parser` and `tree_sitter_languages.get_language`, `get_parser`.
    *   `setup_java_parser()`: Leverages `tree_sitter_languages.get_parser("java")` to automatically handle loading and configuring the Java grammar.
    *   `java_parser`: A singleton instance of the configured Java parser.
    *   Includes `if __name__ == "__main__":` block with example usage to parse a sample Java file and print its AST and method declarations using Tree-sitter queries.

## 8. `src/fathom/indexer.py`

*   **Purpose:** Core module for semantic indexing and search. Processes Java files, creates embeddings, and manages ChromaDB collections.
*   **Implementation Logic:**
    *   Loads configuration from `config.yaml`.
    *   `find_java_files(root_dir)`: Recursively finds all `.java` files in a directory.
    *   `extract_method_info(root_node, source_code, file_path)`:
        *   Uses Tree-sitter queries (`(method_declaration) @method`) to find method nodes in the AST.
        *   Extracts `method_name`, `code` (method body), `file_path`, `class_name`, `start_line`, `end_line`, `parameters`, `return_type`.
        *   Decodes Tree-sitter byte strings to UTF-8.
    *   `load_embedding_model()`: Loads `microsoft/unixcoder-base` `SentenceTransformer` model.
    *   `setup_chroma_client()`: Connects to a `chromadb.PersistentClient` using `chroma_db_path` from config.
    *   `index_project(project_name)`:
        *   Ensures Librarian tables exist and retrieves `project_root`.
        *   Finds Java files, sets up parser and embedding model.
        *   **Explicitly sets `SentenceTransformerEmbeddingFunction` when creating/getting ChromaDB collection to prevent dimension mismatches.**
        *   Iterates files: parses, extracts method info.
        *   Generates `documents_to_add` (method code), `metadatas_to_add` (other extracted info), `ids_to_add` (SHA256 hash).
        *   Uses `embedding_model.encode()` to create embeddings from method `code`.
        *   `collection.add()`: Stores embeddings, documents, metadata, and IDs in the project's dedicated ChromaDB collection.
        *   Calls `update_project_timestamp()` in Librarian.
    *   `semantic_search(project_root, query, n_results)`:
        *   Sets up ChromaDB client and gets the project's collection.
        *   **Crucially, it queries ChromaDB using `query_texts=[query]`, relying on the collection's pre-configured embedding function to embed the natural language query for comparison with stored code embeddings.**
    *   Includes `if __name__ == "__main__":` block for self-testing and demonstration of indexing and semantic search.

## 9. `src/fathom/scip_pb2.py`

*   **Purpose:** Provides Python data structures for interacting with SCIP (Source Code Indexing Protocol) binary files.
*   **Implementation Logic:**
    *   This file is **auto-generated** by the Protobuf compiler from `scip.proto`. It should not be manually edited.
    *   Defines Python classes (e.g., `Index`, `Document`, `Occurrence`, `Symbol`, `Range`) that represent the hierarchical structure and types of data found in an `index.scip` file.
    *   These classes include methods for serializing and deserializing (parsing) binary SCIP data into Python objects, allowing Fathom to programmatically access definitions, references, and other structural information.

## 10. `src/fathom/scip_integrator.py`

*   **Purpose:** Automates the generation of SCIP index files for Java projects using the external `scip-java` tool.
*   **Implementation Logic:**
    *   Loads `config.yaml` to get the `scip_index_path`.
    *   `run_scip_java_index(project_root, output_file)`:
        *   Validates `project_root` exists.
        *   Determines `full_output_path` for the `.scip` file and ensures its directory exists.
        *   Saves `original_cwd`, then uses `subprocess.run()` to execute `scip-java index --output <path>`.
        *   **`cwd=project_root` is used so `scip-java` runs from the Java project's root**, allowing it to find build files (e.g., `pom.xml`).
        *   Handles `FileNotFoundError` (if `scip-java` is not installed), `subprocess.CalledProcessError` (if `scip-java` fails), and general `Exception`s.
        *   Always restores `original_cwd` in a `finally` block.
        *   Returns the `Path` to the generated `.scip` file on success.
    *   Includes `if __name__ == "__main__":` block for self-testing `scip-java` integration with a sample project.
