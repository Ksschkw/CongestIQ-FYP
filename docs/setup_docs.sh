# Creates the documentation scaffold for the MARL TCP Congestion Control FYP
# Run: chmod +x setup_docs.sh && ./setup_docs.sh
#I run this in the root btw
set -e  # Exit on any error

PROJECT_ROOT="$HOME/Projects/fyp"
DOCS_DIR="$PROJECT_ROOT/docs"

echo "============================================"
echo "  MARL TCP FYP - Documentation Scaffold"
echo "============================================"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Docs Directory: $DOCS_DIR"
echo ""

# Verify we're in the right place
if [ ! -d "$PROJECT_ROOT" ]; then
    echo "ERROR: $PROJECT_ROOT does not exist."
    echo "Make sure your FYP project is at ~/Projects/fyp"
    exit 1
fi

# Create docs root
mkdir -p "$DOCS_DIR"
echo "[1/8] Created docs/ root"

# M1: Network Sandbox
mkdir -p "$DOCS_DIR/m1-network-sandbox"/{code,results,videos,notes}
echo "[2/8] Created m1-network-sandbox/ with subfolders"

# M2: Congestion Dynamics
mkdir -p "$DOCS_DIR/m2-congestion-dynamics"/{code,results,videos,notes}
echo "[3/8] Created m2-congestion-dynamics/ with subfolders"

# M3: Single-Agent RL Environment
mkdir -p "$DOCS_DIR/m3-single-agent-rl"/{code,results,videos,notes}
echo "[4/8] Created m3-single-agent-rl/ with subfolders"

# M4: MARL Training
mkdir -p "$DOCS_DIR/m4-marl-training"/{code,results,videos,notes}
echo "[5/8] Created m4-marl-training/ with subfolders"

# M5: Full Evaluation
mkdir -p "$DOCS_DIR/m5-evaluation"/{code,results,videos,notes}
echo "[6/8] Created m5-evaluation/ with subfolders"

# M6: Final Documentation & Defense
mkdir -p "$DOCS_DIR/m6-final-documentation"/{code,results,videos,notes}
echo "[7/8] Created m6-final-documentation/ with subfolders"

# Create a global notes folder for cross-cutting documentation
mkdir -p "$DOCS_DIR/_global-notes"
echo "[8/8] Created _global-notes/ for cross-cutting documentation"

echo ""
echo "============================================"
echo "  Documentation scaffold created."
echo "============================================"
echo ""
echo "Structure:"
find "$DOCS_DIR" -type d | sed "s|$DOCS_DIR|docs|" | sort
echo ""
echo "Next step: Write M1 README and get the topology script."