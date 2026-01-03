# Fathom: A Code-Aware Search Engine - Project Plan

This document outlines the architecture, roadmap, and technical decisions for building **Fathom**, a multi-faceted search engine designed to provide deep, contextual understanding of codebases for Large Language Models like Gemini.

## Project Overview: The 3-Component Architecture

Fathom is composed of three core services that work in concert:

*   **The Librarian:** The central coordinator. It's a lightweight service that tracks all registered code repositories and their indexing status using an SQLite database. It acts as the source of truth for what projects Fathom knows about and how fresh their data is.

*   **The Indexing Worker:** The offline workhorse. This is a background process (Python script) responsible for analyzing code and building the search indexes. It operates in three distinct ways:
    1.  **Semantic Indexing:** Uses `tree-sitter` to parse code into logical blocks (methods/functions), generates vector embeddings for them, and stores them in a **ChromaDB** vector database. This powers "what does this do?" queries.
    2.  **Structural Indexing:** Leverages `scip-java` (and other future `scip-*` indexers) to create a precise map of code symbols (definitions, references). This powers "go-to-definition" and "find-references" queries.
    3.  **Literal Indexing:** Uses `ripgrep` to enable high-speed, plain-text search across the entire codebase. This powers "find this exact string" queries.

*   **The Search Engine:** The public-facing API. This is a Python server that receives queries, intelligently routes them to the correct backend (ChromaDB, SCIP, or ripgrep), and synthesizes the results into a single, coherent response for the user or AI.

---

## Detailed Plan & Technical Enhancements

This plan follows a phased approach to deliver value incrementally.

### Phase 1: The "Brain" (Ingestion & Semantic Search)

**Goal:** Achieve a foundational understanding of the *meaning* of the code.

**Deliverable:** A Python script that can traverse a Java project directory, parse method bodies, generate embeddings, and store them in ChromaDB.

#### Key Decisions & Enhancements:

1.  **Technology Stack:**
    *   **Python:** The primary language for scripting and coordination.
    *   **Tree-sitter:** Excellent for robustly parsing source code into a concrete syntax tree (CST). We will start with the `tree-sitter-java` grammar.
    *   **ChromaDB:** A developer-friendly, open-source vector database. It's easy to set up and ideal for our use case.
    *   **Embedding Model:** The choice of model is critical. We recommend starting with a high-performing, open-source sentence-transformer model like `all-MiniLM-L6-v2` for its balance of speed and quality. This can be configured to allow for swapping in more powerful models later.

2.  **Indexing Process:**
    *   The script will recursively scan for `.java` files.
    *   For each file, it will use `tree-sitter` to identify class and method declarations.
    *   **Enhancement:** Instead of just embedding the raw code, we will store a structured document in ChromaDB containing:
        *   The vector embedding of the code block.
        *   The raw code text itself.
        *   **Crucial Metadata:** The file path, start line, end line, and the method/class name. This metadata is vital for providing actionable results.

### Phase 2: The "Eyes" (Literal & Structural Search)

**Goal:** Give the AI precision tools for exact matching and code navigation.

**Deliverable:** Integration of `ripgrep` for literal search and `scip-java` for structural analysis.

#### Key Decisions & Enhancements:

1.  **Literal Search: `ripgrep` over Zoekt**
    *   We will use `ripgrep` for literal search.
    *   **Justification:** `ripgrep` requires zero pre-indexing and is incredibly fast. While `Zoekt` is more powerful for web-scale repositories, it adds significant architectural complexity (sharding, indexing pipelines). `ripgrep` provides 90% of the benefit with 10% of the effort, making it the right choice for our initial build. We can treat a future migration to Zoekt as a scaling-related optimization.

2.  **Structural Search: `scip-java`**
    *   The Indexing Worker will be responsible for running the `scip-java` command-line tool on target projects.
    *   **Prerequisite:** This requires that the Java project is a standard Maven or Gradle project, as `scip-java` hooks into the build process. The system must be able to detect the build tool and invoke it correctly (e.g., `mvn compile`).
    *   The output `index.scip` file will be stored in a designated location managed by the Librarian.

### Phase 3: The "Manager" & The "Engine" (Bringing It All Together)

**Goal:** Create a robust, scalable system that can manage multiple projects and serve queries.

**Deliverable:** The Librarian service and the Search Engine API.

#### Key Decisions & Enhancements:

1.  **The Librarian (SQLite)**
    *   **Schema Design:** We'll use a simple but effective schema:
        *   `projects`: `(id, name, local_path, last_indexed_timestamp)`
        *   `indexed_files`: `(project_id, file_path, content_hash, last_indexed_timestamp)`
    *   **Change Detection:** The `content_hash` (e.g., SHA-256) is critical. The Indexing Worker will calculate the hash of a file before processing. If the hash matches the one in the database, the file is skipped, making re-indexing highly efficient. This is more reliable than relying only on timestamps.

2.  **The Search Engine (API)**
    *   **Framework: FastAPI over "FastMCP"**
        *   We recommend building the server with **FastAPI**.
        *   **Justification:** FastAPI is a modern, high-performance Python web framework that offers automatic API documentation (via OpenAPI/Swagger), data validation with Pydantic, and excellent support for asynchronous operations. This will make the API easier to build, test, and consume.
    *   **Query Routing Logic:** The core of the engine will be a "router" that inspects the user's query:
        *   **Keywords:** Queries containing "where is", "definition of", "find usages" will be routed to the **SCIP index**.
        *   **Semantic Nature:** General "how to", "what does", or "example of" queries will be routed to the **ChromaDB vector index**.
        *   **Literal Patterns:** Queries containing specific, quoted strings, error codes, or file paths will be routed to **ripgrep**.
    *   **API Endpoint:** A primary `/search` endpoint will accept a JSON payload:
        ```json
        {
          "project_name": "my-cool-project",
          "query": "how do we handle database connection retries?",
          "search_type": "auto" // or "semantic", "literal", "structural"
        }
        ```
        This allows for both automatic routing (`auto`) or user-specified search types.

## Overall System Enhancements

1.  **Configuration Management:**
    *   A central `config.yaml` file will be used to manage all settings: database paths, ChromaDB host/port, embedding model names, and paths to external tools (`ripgrep`). This avoids hardcoding values.

2.  **Indexing Strategy:**
    *   The system will support two modes for the Indexing Worker:
        1.  **Cron Job:** A scheduled task (e.g., nightly) that iterates through all registered projects and re-indexes stale files. This is simple and reliable.
        2.  **File Watcher (Future):** For more real-time updates, a file-watching service (using a library like `watchdog`) can be implemented later. This adds complexity but provides instant indexing. We will start with the cron job approach.
