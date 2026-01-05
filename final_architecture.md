# Fathom: Final Architecture

This document outlines the final, enhanced architecture for the Fathom project, designed to act as a comprehensive Meta-Context Provider (MCP) for coding agents. The architecture is split into two main phases: Offline Indexing and Online Querying.

## Step 1: Offline Indexing

This phase is responsible for processing source code and building a rich, queryable knowledge base in a central Postgres database.

### 1A. Run SCIP / Language Indexer
*   **Action:** Generate `.scip` files for each project and its dependencies using a language-specific indexer like `scip-java`. This is an offline, one-time (per code version) process.
*   **Extracted Data:** The `.scip` files contain a wealth of structural information, including:
    *   **Symbols:** Definitions for methods, classes, variables, etc.
    *   **References:** Where each symbol is used.
    *   **Calls / Callees:** The call graph (who calls whom).
    *   **Inheritance / Overrides:** Class hierarchy and polymorphism information.

### 1B. Convert SCIP → Postgres Tables
*   **Action:** A dedicated script will parse the generated `.scip` files and populate a relational Postgres database.
*   **Schema Design:** The database schema is designed to represent the code as a graph.

    **Symbols (nodes):**
    ```sql
    CREATE TABLE symbols (
        id BIGSERIAL PRIMARY KEY,
        repo TEXT,
        file_path TEXT,
        name TEXT,
        type TEXT,  -- method/class/variable
        start_line INT,
        end_line INT
    );
    ```

    **Symbol References (edges):**
    ```sql
    CREATE TABLE "references" (
        id BIGSERIAL PRIMARY KEY,
        symbol_id BIGINT REFERENCES symbols(id),
        referenced_by_id BIGINT REFERENCES symbols(id)
    );
    ```

    **Call Relationships (edges):**
    ```sql
    CREATE TABLE calls (
        caller_id BIGINT REFERENCES symbols(id),
        callee_id BIGINT REFERENCES symbols(id),
        PRIMARY KEY (caller_id, callee_id)
    );
    ```

    **Inheritance / Overrides (edges):**
    ```sql
    CREATE TABLE inheritance (
        parent_id BIGINT REFERENCES symbols(id),
        child_id BIGINT REFERENCES symbols(id),
        PRIMARY KEY (parent_id, child_id)
    );
    ```

    **Optional: `pgvector` for Semantic Embeddings:**
    ```sql
    -- Requires the pgvector extension to be created first.
    CREATE TABLE embeddings (
        symbol_id BIGINT REFERENCES symbols(id),
        embedding vector(1536), -- Dimension can be adjusted
        PRIMARY KEY (symbol_id)
    );
    ```
*   **Rationale:**
    *   All nodes (symbols, files) and edges (references, calls, inheritance) are stored within the same Postgres instance, allowing for powerful relational and graph-like queries.
    *   Vector embeddings for semantic search are co-located using the `pgvector` extension.

## Step 2: Online Query Flow

This phase details how an incoming query from an agent or user is processed to retrieve context.

### 2A. Zoekt (Lexical Search)
*   **Input:** A user query (regex or literal string).
*   **Output:** A set of candidate files or symbols that match lexically.
*   **Purpose:** Acts as an extremely fast, cheap pre-filter to narrow down the search space to a relevant subset of files.

### 2B. Semantic Search (Vector)
*   **Input:** A natural language query.
*   **Process:**
    1.  Uses `pgvector`'s nearest neighbor search capabilities.
    2.  The search can be performed on the candidate set from Zoekt or across the entire project.
*   **Output:** A set of candidate symbols ranked by semantic similarity. This set can be combined with Zoekt's results.

### 2C. Structural / Graph Search (Postgres)
*   **Input:** A candidate symbol (or symbols) from the previous steps.
*   **Process:** Uses Recursive Common Table Expressions (CTEs) in Postgres to perform multi-hop traversals of the code graph.
*   **Example (Find all recursive callers of a method):**
    ```sql
    WITH RECURSIVE callers(id, depth) AS (
        SELECT id, 1
        FROM symbols
        WHERE name = 'processPayment'

        UNION ALL

        SELECT r.referenced_by_id, c.depth + 1
        FROM calls r
        JOIN callers c ON r.callee_id = c.id
    )
    SELECT s.name, s.file_path, c.depth
    FROM callers c
    JOIN symbols s ON s.id = c.id;
    ```


## Step 3: Agent / RAG Integration

This is the final step where the collected information is synthesized into a coherent response for the end-user.

*   **Input:** The original user query.
*   **Step 1: Lexical Pre-filtering:** Use Zoekt to get a set of candidate files.
*   **Step 2: Semantic Filtering:** Use `pgvector` search to get a set of candidate symbols.
*   **Step 3: Graph Expansion:** Use Recursive CTEs in Postgres to get the full graph context for the top candidate symbols (e.g., all callers, callees, parent/child classes).
*   **Step 4: RAG (Retrieval-Augmented Generation):** An LLM agent combines the retrieved context (code snippets, graph metadata, embeddings) to generate a comprehensive and accurate response.
