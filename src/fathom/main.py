# src/fathom/main.py

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Dict, Any, Literal

# Import Librarian for project management
from .librarian import get_project_path, create_tables

# Import our backend search functions
from .indexer import semantic_search
from .searcher import literal_search
from .scip_querier import structural_search # Import the ROBUST structural search

# --- Pydantic Models for API Data Validation ---
class SearchRequest(BaseModel):
    project_name: str = Field(..., description="The name of the project to search in (e.g., 'sample_java_project').")
    query: str = Field(..., description="The search query. For structural search, use a user-friendly FQN like 'com.example.Main.greet'.")
    search_type: Literal['semantic', 'literal', 'structural'] = Field(..., description="The type of search to perform.")
    n_results: int = Field(5, description="Number of results to return for semantic search.")

class SearchResponse(BaseModel):
    search_type: str
    results: List[Dict[str, Any]]
    message: str = "Success"

# --- FastAPI Application ---
app = FastAPI(
    title="Fathom Search Engine",
    description="An API for semantic, literal, and structural code search, integrated with Librarian (Robust Structural).",
    version="0.1.0"
)

# --- FastAPI Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Ensure database tables are created on startup."""
    print("FastAPI app starting up. Ensuring Librarian database tables exist...")
    create_tables()
    print("Librarian database tables checked.")

# --- API Endpoint ---
@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Main search endpoint for Fathom.
    Routes the query to the appropriate backend based on `search_type`.
    """
    try:
        project_root = get_project_path(request.project_name)
        if not project_root:
            raise HTTPException(status_code=404, detail=f"Project '{request.project_name}' not found in Librarian.")
        
        elif request.search_type == "semantic":
            print(f"Performing semantic search for: '{request.query}' in project '{request.project_name}'")
            results = semantic_search(project_root, request.query, request.n_results)
            formatted_results = []
            if results and results.get('documents'):
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "distance": results['distances'][0][i],
                        "document": doc,
                        "metadata": results['metadatas'][0][i]
                    })
            return SearchResponse(search_type="semantic", results=formatted_results)

        elif request.search_type == "literal":
            print(f"Performing literal search for: '{request.query}' in project '{request.project_name}'")
            results = literal_search(project_root, request.query)
            return SearchResponse(search_type="literal", results=results)

        elif request.search_type == "structural":
            print(f"Performing structural search for: '{request.query}' in project '{request.project_name}'")
            # For structural search, the query is the user-friendly fully qualified symbol name
            scip_output_dir = Path(".fathom_indexes") / "scip"
            scip_index_file = scip_output_dir / f"{project_root.name}.scip"
            
            results = structural_search(scip_index_file, project_root, request.query)
            return SearchResponse(search_type="structural", results=results)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.get("/", summary="Health Check")
async def root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Fathom Search Engine is running (Librarian integrated, Robust Structural)."}


if __name__ == "__main__":
    print("Starting Fathom Search Engine with Uvicorn (Librarian integrated, Robust Structural).")
    print("Access the API documentation at http://127.0.0.1:8000/docs")
    
    uvicorn.run("src.fathom.main:app", host="127.0.0.1", port=8000, reload=True)
