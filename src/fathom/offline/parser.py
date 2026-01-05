# src/fathom/parser.py (Corrected parser using tree_sitter_languages)

from pathlib import Path
from tree_sitter import Parser
from tree_sitter_languages import get_language, get_parser

# Define paths - used mainly for the example and to ensure consistency
# The grammar_dir and build_lib_path are no longer strictly needed for this
# new approach as tree_sitter_languages handles internal management.
# We keep them defined for clarity and if there's any future need for low-level access.
grammar_dir = Path(__file__).parent.parent.parent / ".fathom_grammars"
build_lib_path = grammar_dir / "fathom_grammars.so"

def setup_java_parser() -> Parser:
    """
    Sets up and returns a tree-sitter Parser instance configured for Java.

    This function leverages the `tree_sitter_languages` library to automatically
    handle the downloading, compilation, and loading of the Java grammar.
    """
    # Get the Java language object and parser instance directly
    # `get_parser()` automatically loads and configures the parser for the specified language
    java_parser = get_parser("java")
    return java_parser

# Create a singleton parser instance to be imported by other modules
# This variable name needs to be unique if both parser.py and parser_fixed.py are imported
java_parser = setup_java_parser()

if __name__ == "__main__":
    # Example usage: Parse the sample Java file and print its syntax tree

    print("Testing the Java parser with tree_sitter_languages (fixed version)...")
    
    parser = setup_java_parser()
    
    sample_file_path = Path(__file__).parent.parent.parent / "sample_java_project/com/example/Main.java"
    
    if not sample_file_path.exists():
        print(f"Error: Sample file not found at: {sample_file_path}")
    else:
        with open(sample_file_path, "rb") as f:
            source_code = f.read()
        
        tree = parser.parse(source_code)
        
        root_node = tree.root_node
        print(f"Successfully parsed {sample_file_path}.")
        print("\n--- Abstract Syntax Tree (S-expression) ---")
        print(root_node.sexp())

        # Example of querying the tree (similar to the provided examples)
        language = get_language("java") # Get the language object for querying
        
        # Query for all method declarations
        method_pattern = """
            (method_declaration
                name: (identifier) @method_name
                parameters: (formal_parameters) @method_parameters
                body: (block) @method_body
            )
        """
        method_query = language.query(method_pattern)
        method_captures = method_query.captures(root_node)

        print("\n--- Captured Method Declarations ---")
        for captured_node, tag in method_captures:
            if tag == "method_name":
                print(f"Method Name: {captured_node.text.decode('utf-8')}")
            elif tag == "method_parameters":
                print(f"  Parameters: {captured_node.text.decode('utf-8')}")
            elif tag == "method_body":
                print(f"  Body Start Line: {captured_node.start_point[0]}, End Line: {captured_node.end_point[0]}")
