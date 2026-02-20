#!/bin/bash
# STT Control Skill - Enable/disable speech recognition at runtime
# Usage: /stt-control [on|off]

set -euo pipefail

PYAGENTVOX_ROOT="C:/projects/pyprojects/pyagentvox"
STATE="${1:-on}"

# Validate state argument
if [ "$STATE" != "on" ] && [ "$STATE" != "off" ]; then
    echo "❌ Invalid state: $STATE"
    echo ""
    echo "Usage: /stt-control [on|off]"
    echo ""
    echo "Examples:"
    echo "  /stt-control on   - Enable speech recognition"
    echo "  /stt-control off  - Disable speech recognition (keyboard only)"
    exit 1
fi

# Control STT (CLI handles running check)
if [ "$STATE" = "on" ]; then
    echo "🎤 Enabling speech recognition..."
else
    echo "⏸️ Disabling speech recognition..."
fi

cd "$PYAGENTVOX_ROOT"
python -m pyagentvox stt "$STATE"

if [ $? -eq 0 ]; then
    echo "✓ STT ${STATE}"
    echo ""
    if [ "$STATE" = "on" ]; then
        echo "💬 I'm listening for your voice commands!"
    else
        echo "⌨️  Voice input paused (keyboard only)"
    fi
else
    echo "❌ Failed to control STT"
fi
