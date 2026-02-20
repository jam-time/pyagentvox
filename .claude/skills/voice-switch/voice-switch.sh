#!/bin/bash
# Voice Profile Switch Skill - Hot-swap voice profiles without restarting
# Usage: /voice-switch <profile>

set -euo pipefail

PYAGENTVOX_ROOT="C:/projects/pyprojects/pyagentvox"
PROFILE="${1:-}"

# Check if profile argument provided
if [ -z "$PROFILE" ]; then
    echo "❌ Missing profile name"
    echo ""
    echo "Usage: /voice-switch <profile>"
    echo ""
    echo "Available profiles:"
    echo "  michelle - Sweet, empathetic, caring"
    echo "  jenny    - Energetic, playful, upbeat"
    echo "  emma     - Warm, nurturing, understanding"
    echo "  aria     - Professional, confident, bright"
    echo "  ava      - Clear, precise, versatile"
    echo "  sonia    - British, calm, professional"
    echo "  libby    - British, friendly, approachable"
    echo "  default  - Clear, precise (Ava voice)"
    exit 1
fi

# Switch profile (CLI handles running check)
echo "🌙 Switching voice profile..."
echo "   From: Current profile"
echo "   To:   $PROFILE"
echo ""

cd "$PYAGENTVOX_ROOT"
python -m pyagentvox switch "$PROFILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✨ Profile switched successfully!"
    echo ""
    echo "💬 The new voice will be used for my next response"
else
    echo ""
    echo "❌ Failed to switch profile"
    echo ""
    echo "Check PyAgentVox logs or try: /voice-stop && /voice $PROFILE"
fi
