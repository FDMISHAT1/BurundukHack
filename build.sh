#!/bin/bash
# Build BurundukHack into a standalone executable
# Works on Linux and macOS

set -e

echo "=== BurundukHack Builder ==="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+"
    exit 1
fi

# Install build deps in venv if needed
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "[1/3] Installing dependencies..."
pip install -q rich pyyaml prompt_toolkit pyinstaller

echo "[2/3] Building executable..."
pyinstaller burunduk.spec --clean --noconfirm 2>&1 | tail -5

echo "[3/3] Done!"
echo ""

if [ -f "dist/BurundukHack" ]; then
    SIZE=$(du -h dist/BurundukHack | cut -f1)
    echo "  Output: dist/BurundukHack ($SIZE)"
    echo "  Run:    ./dist/BurundukHack"
    echo ""
    echo "  To distribute: just copy dist/BurundukHack"
    echo "  No Python or dependencies needed on target machine!"
else
    echo "  ERROR: Build failed. Check output above."
    exit 1
fi
