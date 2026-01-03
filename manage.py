# manage.py

import argparse
from pathlib import Path
from fathom.librarian import (
    add_project, 
    remove_project, 
    list_projects, 
    create_tables,
    get_project_path
)
from fathom.indexer import index_project as index_project_semantic
from fathom.scip_integrator import run_scip_java_index

def main():
    parser = argparse.ArgumentParser(
        description="Fathom Project Management CLI. Manage projects and trigger indexing."
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # --- Add Project Command ---
    add_parser = subparsers.add_parser("add", help="Add a new project to the Librarian.")
    add_parser.add_argument("name", type=str, help="The name of the project.")
    add_parser.add_argument("path", type=str, help="The absolute path to the project directory.")

    # --- Remove Project Command ---
    remove_parser = subparsers.add_parser("remove", help="Remove a project from the Librarian.")
    remove_parser.add_argument("name", type=str, help="The name of the project to remove.")

    # --- List Projects Command ---
    list_parser = subparsers.add_parser("list", help="List all registered projects.")

    # --- Index Project Command (Semantic) ---
    index_parser = subparsers.add_parser("index", help="Run SEMANTIC indexing for a registered project.")
    index_parser.add_argument("name", type=str, help="The name of the project to index.")
    
    # --- Index Project Command (Structural/SCIP) ---
    index_scip_parser = subparsers.add_parser("index-scip", help="Run STRUCTURAL (SCIP) indexing for a registered project.")
    index_scip_parser.add_argument("name", type=str, help="The name of the project to index with SCIP.")


    args = parser.parse_args()

    # Ensure tables are created before any operation
    create_tables()

    if args.command == "add":
        project_path = Path(args.path)
        if not project_path.exists() or not project_path.is_dir():
            print(f"Error: Provided path '{args.path}' does not exist or is not a directory.")
            return
        add_project(args.name, project_path)
    elif args.command == "remove":
        remove_project(args.name)
    elif args.command == "list":
        projects = list_projects()
        if projects:
            print("\nRegistered Fathom Projects:")
            for p in projects:
                print(f"  Name: {p['name']}")
                print(f"    Path: {p['path']}")
                print(f"    Last Indexed: {p['last_indexed_at'] if p['last_indexed_at'] else 'Never'}")
                print("-" * 30)
        else:
            print("No projects registered.")
    elif args.command == "index":
        print(f"Initiating semantic indexing for project: '{args.name}'...")
        index_project_semantic(args.name)
        print(f"Semantic indexing process for '{args.name}' completed.")
    elif args.command == "index-scip":
        print(f"Initiating SCIP structural indexing for project: '{args.name}'...")
        project_path = get_project_path(args.name)
        if not project_path:
            print(f"Error: Project '{args.name}' not found.")
            return
        project_scip_file = Path(f"{project_path.name}.scip")
        run_scip_java_index(project_path, output_file=project_scip_file)
        print(f"SCIP structural indexing for '{args.name}' completed.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
