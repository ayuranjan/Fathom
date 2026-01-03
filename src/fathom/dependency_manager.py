# src/fathom/dependency_manager.py

from pathlib import Path
import zipfile
import os
from typing import List

# Import Librarian for project management
from .librarian_new import add_project, list_projects, create_tables

def find_source_jars(cache_path: Path) -> List[Path]:
    """
    Scans the given cache path for all '-sources.jar' files.
    """
    print(f"Scanning for source JARs in {cache_path}...")
    if not cache_path.is_dir():
        print(f"Warning: Cache directory not found: {cache_path}")
        return []
    
    source_jars = list(cache_path.rglob("*-sources.jar"))
    print(f"Found {len(source_jars)} source JAR(s).")
    return source_jars

def extract_and_register_dependencies(source_jars: List[Path], deps_root: Path):
    """
    Extracts source JARs to a target directory and registers them with the Librarian.
    
    Args:
        source_jars: A list of paths to the source JAR files.
        deps_root: The root directory where dependencies will be extracted.
    """
    if not source_jars:
        print("No source JARs to process.")
        return
        
    print(f"Extracting dependencies to {deps_root}...")
    deps_root.mkdir(parents=True, exist_ok=True)
    
    for jar_path in source_jars:
        # Create a unique project name from the JAR file name
        # e.g., commons-lang3-3.12.0
        project_name = f"dep_{jar_path.stem.replace('-sources', '')}"
        
        # Create a subdirectory for this dependency
        extract_path = deps_root / project_name
        
        if extract_path.exists():
            print(f"Dependency '{project_name}' already extracted. Skipping.")
            continue
        
        print(f"  Extracting {jar_path.name} to {extract_path}...")
        try:
            with zipfile.ZipFile(jar_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            # Register this new directory as a project in the Librarian
            print(f"  Registering '{project_name}' with the Librarian...")
            add_project(name=project_name, path=extract_path)
            
        except zipfile.BadZipFile:
            print(f"  Warning: Could not extract {jar_path.name}. It may be a corrupted file.")
        except Exception as e:
            print(f"  An unexpected error occurred while processing {jar_path.name}: {e}")

if __name__ == "__main__":
    print("--- Running Dependency Manager ---")
    
    # Ensure Librarian DB is ready
    create_tables()

    # Define paths
    maven_cache_path = Path.home() / ".m2" / "repository"
    fathom_deps_path = Path(".fathom_deps")

    # 1. Find all source JARs in the cache
    # In a real application, you might want to be more specific about which JARs to index,
    # but for now, we will index all found sources.
    all_source_jars = find_source_jars(maven_cache_path)
    
    # 2. Extract and register them
    extract_and_register_dependencies(all_source_jars, fathom_deps_path)
    
    # 3. List all projects to see the new additions
    print("\n--- Current Projects in Librarian ---")
    projects = list_projects()
    if projects:
        for p in projects:
            print(f"  - {p['name']} (at {p['path']})")
    else:
        print("No projects found.")
