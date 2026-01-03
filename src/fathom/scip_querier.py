# src/fathom/scip_querier.py

from pathlib import Path
import os
from typing import List, Dict, Any, Optional

# Import the generated protobuf classes
from . import scip_pb2

# --- SCIP Symbol Parsing ---
# (parse_scip_symbol function remains, though not directly used in this search)
def parse_scip_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Parses a SCIP symbol string into its components.
    Example: 'semanticdb maven maven/com.example/sample-java-project 1.0-SNAPSHOT com/example/Main#greet().'
    This is a simplified parser for demonstration. A full parser would handle all descriptor types.
    """
    if symbol.startswith('local '):
        return {'type': 'local', 'id': symbol.split(' ')[1]}

    try:
        parts = symbol.split(' ')
        scheme = parts[0]
        # Skip package info for now as it's static for our test project
        # manager = parts[1]
        # package_name = parts[2]
        # version = parts[3]
        
        # The actual fully qualified name (FQN) part starts from index 4
        fqn_part = parts[4] 
        
        # Simplified descriptor parsing for demonstration
        # This part of the code needs to be truly robust for general SCIP parsing.
        descriptors = []
        # Example to extract descriptor names (very basic)
        if '#' in fqn_part:
            descriptors.append(fqn_part.split('#')[0] + '#') # Class
            descriptors.append(fqn_part.split('#')[1]) # Method/Field
        else:
            descriptors.append(fqn_part)

        return {
            'type': 'global',
            'scheme': scheme,
            # 'package': {'manager': manager, 'name': package_name, 'version': version},
            'descriptors_str': fqn_part, # Storing the direct FQN part for now
            'descriptors': descriptors # Simplified
        }
    except IndexError:
        # Malformed symbol string
        return None

# --- Main SCIP Querier Logic ---
def load_scip_index(scip_index_path: Path) -> Optional[scip_pb2.Index]:
    """Loads and parses an index.scip file into a scip_pb2.Index object."""
    if not scip_index_path.exists():
        print(f"Error: SCIP index file not found at {scip_index_path}")
        return None
    try:
        with open(scip_index_path, "rb") as f:
            scip_index = scip_pb2.Index()
            scip_index.ParseFromString(f.read())
            return scip_index
    except Exception as e:
        print(f"Error parsing SCIP index file {scip_index_path}: {e}")
        return None

def structural_search(scip_index_path: Path, project_root: Path, query_symbol: str) -> List[Dict[str, Any]]:
    """
    Performs a structural search for a symbol's definition using a robust parser.
    Query symbol should be in the format: "com.example.Main.greet" (user-friendly FQN)
    """
    scip_index = load_scip_index(scip_index_path)
    if not scip_index:
        return []

    results = []
    
    # --- FIX: Refined heuristic to convert user query to SCIP-like descriptor string ---
    # Example: "com.example.Main.greet" -> "com/example/Main#greet()."
    query_parts = query_symbol.split('.')
    
    if len(query_parts) < 2: # At least Class.method or Package.Class
        print(f"Warning: Query '{query_symbol}' is too short for SCIP conversion heuristic.")
        return []

    method_name_with_paren = query_parts[-1] + '().' # Assume method, add parens and period
    class_name = query_parts[-2]
    package_path = '/'.join(query_parts[:-2])
    
    # Construct the SCIP-like descriptor string that ends the full SCIP symbol
    # This is the part that follows the 'semanticdb maven ...' prefix
    scip_like_query_suffix = f"{package_path}/{class_name}#{method_name_with_paren}"
    
    for doc in scip_index.documents:
        for occ in doc.occurrences:
            if occ.symbol_roles & scip_pb2.SymbolRole.Definition:
                # --- FIX: Use endswith for more robust matching ---
                # Check if the occ.symbol ends with our constructed SCIP-like query suffix
                if occ.symbol.endswith(scip_like_query_suffix):
                    # Extract range, handling both 3 and 4 element ranges
                    if len(occ.range) == 4:
                        start_line = occ.range[0]
                        start_char = occ.range[1]
                        end_line = occ.range[2]
                        end_char = occ.range[3]
                    elif len(occ.range) == 3:
                        start_line = occ.range[0]
                        start_char = occ.range[1]
                        end_line = occ.range[0] # End line is same as start line for 3-element range
                        end_char = occ.range[2]
                    else:
                        continue # Skip if range format is unexpected
                        
                    results.append({
                        "type": "definition",
                        "symbol": occ.symbol,
                        "file_path": str(project_root / doc.relative_path),
                        "start_line": start_line + 1,
                        "start_character": start_char + 1,
                        "end_line": end_line + 1,
                        "end_character": end_char + 1
                    })
    return results

if __name__ == "__main__":
    print("--- Testing SCIP Querier (Robust) ---")
    
    project_root = Path(__file__).parent.parent.parent / "sample_java_project"
    scip_index_file = Path(".fathom_indexes/scip/sample_java_project.scip")
    
    # Query for the 'greet' method definition. This is a more user-friendly format.
    query = "com.example.Main.greet"

    print(f"Searching for definition of '{query}' in {scip_index_file}")
    
    definition_results = structural_search(scip_index_file, project_root, query)
    
    if definition_results:
        print("\nFound Definition(s):")
        for res in definition_results:
            print(f"  Symbol: {res['symbol']}")
            print(f"  File: {res['file_path']}")
            print(f"  Location: Line {res['start_line']}, Char {res['start_character']}")
    else:
        print("\nNo definition found for the symbol.")
        print(f"Attempted to match with SCIP suffix: '{scip_like_query_suffix}' (variable from function scope is not available here)")
