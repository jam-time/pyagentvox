#!/bin/bash
# Stop PyAgentVox voice chat

set -euo pipefail

PYAGENTVOX_ROOT="C:/projects/pyprojects/pyagentvox"

echo "🛑 Stopping PyAgentVox..."

cd "$PYAGENTVOX_ROOT"
python -m pyagentvox stop

if [ $? -eq 0 ]; then
    echo "✓ PyAgentVox stopped"
    echo ""
    echo "Voice instructions will be removed from CLAUDE.md on next session start."
else
    echo "❌ Failed to stop PyAgentVox"
    echo ""
    echo "Check if it's running with: python -m pyagentvox status"
fi
