#!/usr/bin/env bash
# Code Obfuscation Script using Pyarmor

set -e

echo "============================================="
echo "  Starting Code Obfuscation with Pyarmor"
echo "============================================="

# Ensure pyarmor is installed
if ! command -v pyarmor &> /dev/null; then
    echo "Pyarmor not found. Installing pyarmor..."
    pip install -U pyarmor
fi

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Root Directory: $ROOT_DIR"
echo "Component Directory: $SCRIPT_DIR"

# Clean previous build artifacts
echo "Cleaning up previous build..."
rm -rf "$ROOT_DIR/dist"

# Generate obfuscated package
# We specify the output directory to be $ROOT_DIR/dist
echo "Obfuscating main.py and utils.py..."
pyarmor gen -O "$ROOT_DIR/dist" "$SCRIPT_DIR/main.py" "$SCRIPT_DIR/utils.py"

echo "Verifying obfuscated code..."
if [ -f "$ROOT_DIR/dist/main.py" ]; then
    echo "✓ Obfuscation completed successfully!"
    echo "✓ Obfuscated files located in: $ROOT_DIR/dist"
else
    echo "✗ Error: Obfuscation failed, dist/main.py not found."
    exit 1
fi
