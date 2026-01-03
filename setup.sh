#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# --- Color Codes for Output ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Helper function to check if a command exists ---
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Step 1: Check for Homebrew ---
echo -e "${YELLOW}Step 1: Checking for Homebrew...${NC}"
if ! command_exists brew; then
    echo -e "${RED}Error: Homebrew is not installed.${NC}"
    echo "Please install Homebrew by following the instructions at https://brew.sh/, then run this script again."
    exit 1
fi
echo -e "${GREEN}Homebrew found.${NC}\n"

# --- Step 2: Install Ripgrep ---
echo -e "${YELLOW}Step 2: Checking for ripgrep (rg)...${NC}"
if ! command_exists rg; then
    echo "ripgrep not found. Installing via Homebrew..."
    brew install ripgrep
else
    echo -e "${GREEN}ripgrep is already installed.${NC}"
fi
echo ""

# --- Step 3: Install Coursier ---
echo -e "${YELLOW}Step 3: Checking for Coursier...${NC}"
if ! command_exists coursier; then
    echo "Coursier not found. Installing via Homebrew..."
    brew install coursier/formulas/coursier
else
    echo -e "${GREEN}Coursier is already installed.${NC}"
fi
echo ""

# --- Step 4: Install Protocol Buffers (protoc) ---
echo -e "${YELLOW}Step 4: Checking for Protocol Buffers compiler (protoc)...${NC}"
if ! command_exists protoc; then
    echo "protoc not found. Installing via Homebrew..."
    brew install protobuf
else
    echo -e "${GREEN}protoc is already installed.${NC}"
fi
echo ""

# --- Step 5: Install scip-java ---
echo -e "${YELLOW}Step 5: Checking for scip-java...${NC}"
if ! command_exists scip-java; then
    echo "scip-java not found. Building binary using Coursier..."
    echo "(This may take a moment...)"
    coursier bootstrap --standalone -o scip-java com.sourcegraph:scip-java_2.13:0.11.2 --main com.sourcegraph.scip_java.ScipJava
    
    echo -e "\n${GREEN}scip-java binary has been created in the current directory.${NC}"
    echo -e "${YELLOW}To make it available everywhere, please run the following command to move it to your path:${NC}"
    echo -e "  sudo mv scip-java /usr/local/bin/"
    echo "You may be prompted for your password."
    echo "After moving it, please re-run this script to confirm the setup."
    exit 0
else
    echo -e "${GREEN}scip-java is already installed.${NC}"
fi
echo ""

# --- Step 6: Set up Python Environment ---
echo -e "${YELLOW}Step 6: Setting up Python 3.12 virtual environment...${NC}"
if ! command_exists python3.12; then
    echo -e "${RED}Error: python3.12 is not installed.${NC}"
    echo "Please install Python 3.12 (e.g., 'brew install python@3.12') and ensure 'python3.12' is in your PATH."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating Python 3.12 virtual environment in '.venv'..."
    python3.12 -m venv .venv
else
    echo "Virtual environment '.venv' already exists."
fi
echo ""

echo -e "${YELLOW}Step 7: Installing Python dependencies...${NC}"
.venv/bin/pip install -r requirements.txt
echo -e "${GREEN}Python dependencies installed.${NC}\n"

# --- Step 8: Download Tree-sitter Grammar ---
echo -e "${YELLOW}Step 8: Checking for Tree-sitter Java grammar...${NC}"
if [ ! -d ".fathom_grammars/tree-sitter-java" ]; then
    echo "Cloning Java grammar for Tree-sitter..."
    git clone https://github.com/tree-sitter/tree-sitter-java.git .fathom_grammars/tree-sitter-java
else
    echo -e "${GREEN}Tree-sitter Java grammar already present.${NC}"
fi
echo ""

# --- Final Success Message ---
echo -e "${GREEN}✅ Fathom project setup is complete!${NC}"
echo "You can now run the indexer and searcher scripts."
echo "For example: .venv/bin/python -m src.fathom.indexer_fixed"
