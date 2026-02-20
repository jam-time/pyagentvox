#!/bin/bash
# TTS Control Skill - Enable/disable text-to-speech at runtime
# Usage: /tts-control [on|off]

set -euo pipefail

PYAGENTVOX_ROOT="C:/projects/pyprojects/pyagentvox"
STATE="${1:-on}"

# Validate state argument
if [ "$STATE" != "on" ] && [ "$STATE" != "off" ]; then
    echo "❌ Invalid state: $STATE"
    echo ""
    echo "Usage: /tts-control [on|off]"
    echo ""
    echo "Examples:"
    echo "  /tts-control on   - Enable text-to-speech"
    echo "  /tts-control off  - Disable text-to-speech (silent mode)"
    exit 1
fi

# Control TTS (CLI handles running check)
if [ "$STATE" = "on" ]; then
    echo "🔊 Enabling text-to-speech..."
else
    echo "🔇 Disabling text-to-speech..."
fi

cd "$PYAGENTVOX_ROOT"
python -m pyagentvox tts "$STATE"

if [ $? -eq 0 ]; then
    echo "✓ TTS ${STATE}"
    echo ""
    if [ "$STATE" = "on" ]; then
        echo "💬 I'll speak my responses again!"
    else
        echo "📝 I'll stay silent (text only)"
    fi
else
    echo "❌ Failed to control TTS"
fi
