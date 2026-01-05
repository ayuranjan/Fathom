# src/fathom/searcher.py

from pathlib import Path
import subprocess
import json
import yaml
from typing import List, Dict, Any, Optional

# --- Configuration Loading ---
def load_config(config_path: Path = Path("config.yaml")) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# --- Literal Search using Ripgrep ---
def literal_search(project_root: Path, query: str) -> List[Dict[str, Any]]:
    """
    Performs a literal search using ripgrep within the specified project root.

    Args:
        project_root: The root directory of the project to search.
        query: The string pattern to search for.

    Returns:
        A list of dictionaries, where each dictionary represents a match
        and contains file_path, line_number, and the matching text.
    """
    if not project_root.is_dir():
        print(f"Error: Project root not found or is not a directory: {project_root}")
        return []

    # Use --json output for easy parsing
    # -i for case-insensitive, -w for whole word (optional, depends on user intent)
    # --line-number for line numbers
    command = [
        "rg",
        "--json",
        "--line-number",
        "--context", "1", # Show 1 line of context around match
        query,
        str(project_root)
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False) # Changed check=True to check=False
        
        # ripgrep returns 0 for matches, 1 for no matches, and >1 for errors
        if result.returncode == 0:
            matches = []
            for line in result.stdout.splitlines():
                try:
                    json_obj = json.loads(line)
                    if json_obj["type"] == "match":
                        data = json_obj["data"]
                        match_data = {
                            "type": "match",
                            "file_path": data["path"]["text"],
                            "line_number": data["line_number"],
                            "match_text": data["lines"]["text"].strip() if "text" in data["lines"] else "",
                            "absolute_offset": data["absolute_offset"],
                            "submatches": []
                        }
                        for submatch in data["submatches"]:
                            match_data["submatches"].append({
                                "start": submatch["start"],
                                "end": submatch["end"],
                                "match": submatch["match"]["text"]
                            })
                        matches.append(match_data)
                    elif json_obj["type"] == "context":
                        # Optionally handle context lines if needed, for now we filter to just matches
                        pass
                except json.JSONDecodeError:
                    # ripgrep might output non-JSON lines for errors or warnings, ignore them
                    pass
            return matches
        elif result.returncode == 1:
            # No matches found, this is not an error for ripgrep
            return []
        else:
            # A true error occurred
            print(f"Error executing ripgrep: {result.returncode}")
            print(f"Stderr: {result.stderr}")
            return []

    except FileNotFoundError:
        print("Error: ripgrep (rg) command not found.")
        print("Please ensure ripgrep is installed and available in your system's PATH.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during literal search: {e}")
        return []

if __name__ == "__main__":
    # Example usage
    sample_project_path = Path(__file__).parent.parent.parent / "sample_java_project"
    
    print("--- Testing Literal Search ---")
    
    # Test 1: Search for a specific word
    search_query_1 = "System.out.println"
    print(f"\nSearching for: '{search_query_1}' in {sample_project_path}")
    results_1 = literal_search(sample_project_path, search_query_1)
    if results_1:
        for result in results_1:
            print(f"  File: {result['file_path']}, Line: {result['line_number']}, Match: {result['match_text']}")
    else:
        print("  No matches found.")

    # Test 2: Search for a method name
    search_query_2 = "greet"
    print(f"\nSearching for: '{search_query_2}' in {sample_project_path}")
    results_2 = literal_search(sample_project_path, search_query_2)
    if results_2:
        for result in results_2:
            print(f"  File: {result['file_path']}, Line: {result['line_number']}, Match: {result['match_text']}")
    else:
        print("  No matches found.")

    # Test 3: Search for something not present
    search_query_3 = "nonExistentFunction"
    print(f"\nSearching for: '{search_query_3}' in {sample_project_path}")
    results_3 = literal_search(sample_project_path, search_query_3)
    if results_3:
        for result in results_3:
            print(f"  File: {result['file_path']}, Line: {result['line_number']}, Match: {result['match_text']}")
    else:
        print("  No matches found.")
