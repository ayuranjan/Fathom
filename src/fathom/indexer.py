# src/fathom/indexer.py

from pathlib import Path
import yaml
from typing import List, Dict, Any
import hashlib

from tree_sitter import Node
from sentence_transformers import SentenceTransformer
import chromadb
# QueryResult type hint removed as it's not available in this version of chromadb

# Import our corrected Java parser
from .parser import setup_java_parser, get_language
# Import Librarian for project management
from .librarian import get_project_path, update_project_timestamp, create_tables

# --- Configuration Loading ---
def load_config(config_path: Path = Path("config.yaml")) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# --- File System Utilities ---
def find_java_files(root_dir: Path) -> List[Path]:
    """Recursively finds all .java files within a given root directory."""
    if not root_dir.is_dir():
        raise ValueError(f"Root directory not found: {root_dir}")
    return list(root_dir.rglob("*.java"))

# --- Tree-sitter Parsing and Extraction ---
def extract_method_info(root_node: Node, source_code: bytes, file_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts method information from a Tree-sitter root node.
    """
    methods_info = []
    language = get_language("java")
    query_string = "(method_declaration) @method"
    method_query = language.query(query_string)
    method_nodes = method_query.captures(root_node)

    for node, _ in method_nodes:
        method_data = { "file_path": str(file_path), "class_name": "N/A" }
        name_node = node.child_by_field_name("name")
        body_node = node.child_by_field_name("body")
        
        parent = node.parent
        while parent:
            if parent.type == 'class_declaration':
                class_name_node = parent.child_by_field_name('name')
                if class_name_node:
                    method_data['class_name'] = class_name_node.text.decode('utf-8')
                break
            parent = parent.parent

        if name_node and body_node:
            method_data.update({
                'method_name': name_node.text.decode('utf-8'),
                'code': body_node.text.decode('utf-8'),
                'start_line': body_node.start_point[0] + 1,
                'end_line': body_node.end_point[0] + 1,
            })
            params_node = node.child_by_field_name("parameters")
            if params_node:
                 method_data['parameters'] = params_node.text.decode('utf-8')
            type_node = node.child_by_field_name("type")
            if type_node:
                method_data['return_type'] = type_node.text.decode('utf-8')
            methods_info.append(method_data)
    return methods_info
    
# --- Embedding Model Loading ---
def load_embedding_model() -> SentenceTransformer:
    """Loads the sentence transformer model specified in the config."""
    model_name = CONFIG["indexing"]["embedding_model"]
    print(f"Loading embedding model: {model_name}...")
    model = SentenceTransformer(model_name)
    print("Embedding model loaded successfully.")
    return model

# --- ChromaDB Client Setup ---
def setup_chroma_client() -> chromadb.Client:
    """Sets up the ChromaDB client."""
    chroma_db_path = CONFIG["indexing"]["chroma_db_path"]
    print(f"Connecting to ChromaDB at path: {chroma_db_path}")
    client = chromadb.PersistentClient(path=str(chroma_db_path))
    return client

# --- Main Indexing Logic (Librarian Integrated) ---
def index_project(project_name: str): # Accepts project_name now
    """Main function to index a given project by name."""
    print(f"Starting indexing for project: {project_name}")

    # Ensure Librarian tables exist before using it
    create_tables()

    project_root = get_project_path(project_name) # Get path from Librarian
    if not project_root:
        print(f"Error: Project '{project_name}' not found in Librarian. Please add it first.")
        return

    java_files = find_java_files(project_root)
    if not java_files:
        print(f"No Java files found in {project_root}. Exiting.")
        return

    parser = setup_java_parser()
    embedding_model = load_embedding_model()
    chroma_client = setup_chroma_client()

    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    embedding_function = SentenceTransformerEmbeddingFunction(model_name=CONFIG["indexing"]["embedding_model"])

    collection_name = f"fathom-code-snippets-{project_root.name.replace('.', '-').replace('/', '-')}"
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function
    )
    print(f"Using ChromaDB collection: {collection_name}")
    total_indexed_methods = 0

    for file_path in java_files:
        print(f"Processing file: {file_path}")
        with open(file_path, "rb") as f:
            source_code_bytes = f.read()
        tree = parser.parse(source_code_bytes)
        methods_data = extract_method_info(tree.root_node, source_code_bytes, file_path)
        if methods_data:
            documents_to_add, metadatas_to_add, ids_to_add = [], [], []
            for method in methods_data:
                unique_str = f"{method['file_path']}-{method.get('class_name', '')}-{method.get('method_name', '')}-{method.get('start_line', '')}"
                method_id = hashlib.sha256(unique_str.encode()).hexdigest()
                documents_to_add.append(method['code'])
                metadatas_to_add.append({key: val for key, val in method.items() if key != 'code'})
                ids_to_add.append(method_id)
            if documents_to_add:
                embeddings = embedding_model.encode(documents_to_add).tolist()
                collection.add(embeddings=embeddings, documents=documents_to_add, metadatas=metadatas_to_add, ids=ids_to_add)
                total_indexed_methods += len(documents_to_add)
                print(f"  Indexed {len(documents_to_add)} methods from {file_path}")
    print(f"\nFinished indexing project. Total methods indexed: {total_indexed_methods}")
    
    # --- LIBRARIAN INTEGRATION: Update timestamp ---
    update_project_timestamp(project_name)
    print(f"Librarian: Updated last_indexed_at for '{project_name}'.")


# --- SEMANTIC SEARCH FUNCTION ---
def semantic_search(project_root: Path, query: str, n_results: int = 5):
    """Performs a semantic search on an indexed project."""
    chroma_client = setup_chroma_client()
    collection_name = f"fathom-code-snippets-{project_root.name.replace('.', '-').replace('/', '-')}"
    
    print(f"Querying ChromaDB collection: {collection_name}")
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception as e:
        print(f"Error getting collection {collection_name}: {e}")
        return None

    results = collection.query(query_texts=[query], n_results=n_results)
    return results


if __name__ == "__main__":
    sample_project_name = "sample_java_project"
    print(f"--- Running Indexer for '{sample_project_name}' ---")
    
    # Clean up old database entries for testing
    from .librarian import remove_project
    remove_project(sample_project_name)
    
    # Add project before indexing
    from .librarian import add_project
    sample_project_path = Path(__file__).parent.parent.parent / "sample_java_project"
    add_project(sample_project_name, sample_project_path)

    index_project(sample_project_name)
    
    print("\n--- Running Semantic Search ---")
    search_query = "how to greet someone"
    
    # Need to get project_root from Librarian for search as well
    project_root_for_search = get_project_path(sample_project_name)
    if project_root_for_search:
        search_results = semantic_search(project_root_for_search, search_query)
        if search_results and search_results.get('documents'):
            print(f"\nTop search results for: '{search_query}'")
            for i, doc in enumerate(search_results['documents'][0]):
                metadata = search_results['metadatas'][0][i]
                distance = search_results['distances'][0][i]
                print(f"\nResult {i+1} (Distance: {distance:.4f}):")
                print(f"  File: {metadata.get('file_path')}")
                print(f"  Class: {metadata.get('class_name')}, Method: {metadata.get('method_name')}{metadata.get('parameters')}")
                print(f"  Code: {doc[:200]}...")
        else:
            print("Semantic search failed or returned no results.")
    else:
        print(f"Project '{sample_project_name}' not found for semantic search.")
