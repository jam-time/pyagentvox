#!/bin/bash
# Voice Modify Skill - Modify voice settings at runtime
# Usage: /voice-modify <setting>

set -euo pipefail

PYAGENTVOX_ROOT="C:/projects/pyprojects/pyagentvox"
SETTING="${1:-}"

# Check if setting argument provided
if [ -z "$SETTING" ]; then
    echo "❌ Missing setting"
    echo ""
    echo "Usage: /voice-modify <setting>"
    echo ""
    echo "Formats:"
    echo "  pitch=<value>           - Adjust pitch for all emotions"
    echo "  speed=<value>           - Adjust speed for all emotions"
    echo "  <emotion>.pitch=<value> - Adjust pitch for specific emotion"
    echo "  <emotion>.speed=<value> - Adjust speed for specific emotion"
    echo "  all.pitch=<value>       - Adjust pitch for all emotions"
    echo ""
    echo "Examples:"
    echo "  /voice-modify pitch=+5      - Increase pitch by 5Hz (all emotions)"
    echo "  /voice-modify speed=-10     - Decrease speed by 10% (all emotions)"
    echo "  /voice-modify neutral.pitch=+10  - Increase neutral pitch by 10Hz"
    echo "  /voice-modify cheerful.speed=-5  - Decrease cheerful speed by 5%"
    echo "  /voice-modify all.pitch=-3       - Decrease all pitches by 3Hz"
    echo ""
    echo "Emotions: neutral, cheerful, excited, empathetic, warm, calm, focused"
    exit 1
fi

# Modify voice settings (CLI handles running check)
echo "🎵 Modifying voice settings..."
echo "   Setting: $SETTING"
echo ""

cd "$PYAGENTVOX_ROOT"
python -m pyagentvox modify "$SETTING"

if [ $? -eq 0 ]; then
    echo ""
    echo "✨ Voice settings updated!"
    echo ""
    echo "💬 Changes will apply to my next response"
else
    echo ""
    echo "❌ Failed to modify voice settings"
    echo ""
    echo "Check the setting format or try: /voice-modify (without args for help)"
fi
