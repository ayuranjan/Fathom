# src/fathom/scip_integrator.py

from pathlib import Path
import subprocess
import yaml
import os
from typing import Dict, Any, Optional

# --- Configuration Loading ---
def load_config(config_path: Path = Path("config.yaml")) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def run_scip_java_index(project_root: Path, output_file: Path = Path("index.scip")) -> Optional[Path]:
    """
    Runs the 'scip-java index' command in the specified project root.

    Args:
        project_root: The root directory of the Java project (must contain pom.xml or build.gradle).
        output_file: The name of the SCIP index file to generate.

    Returns:
        The path to the generated index.scip file if successful, otherwise None.
    """
    if not project_root.is_dir():
        print(f"Error: Project root not found or is not a directory: {project_root}")
        return None
    
    # --- FIX: Make the output path absolute ---
    # Resolve the path relative to the current working directory to get an absolute path.
    scip_output_dir = Path(CONFIG["indexing"]["scip_index_path"]).resolve()
    scip_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the full, absolute output path for the index file
    full_output_path = scip_output_dir / output_file

    original_cwd = Path.cwd()
    try:
        print(f"Running 'scip-java index' for project: {project_root.name}")
        print(f"Outputting SCIP index to: {full_output_path}")
        
        command = [
            "scip-java",
            "index",
            "--output", str(full_output_path),
        ]
        
        # We still run from the project's root, but the output path is now absolute
        # so it will be written to the correct location.
        result = subprocess.run(
            command,
            cwd=project_root, # Run scip-java from within the target project directory
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"Successfully ran scip-java. Output file should be at {full_output_path}")
        return full_output_path
        
    except FileNotFoundError:
        print("Error: scip-java command not found.")
        print("Please ensure scip-java is installed and available in your system's PATH.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing scip-java index (Exit Code: {e.returncode}):")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during scip-java indexing: {e}")
        return None
    finally:
        os.chdir(original_cwd)
