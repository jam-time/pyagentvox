#!/bin/bash
# Voice Chat Skill - Start PyAgentVox with options
# Usage: /voice [profile] [tts-only] [debug] [custom]

set -euo pipefail

PYAGENTVOX_ROOT="C:/projects/pyprojects/pyagentvox"

# Parse all arguments (supports combining profile + modes)
PROFILE=""
TTS_ONLY=""
DEBUG=""
CONFIG=""

for ARG in "$@"; do
    case "$ARG" in
        michelle|jenny|emma|aria|ava|sonia|libby)
            PROFILE="--profile $ARG"
            ;;
        tts-only)
            TTS_ONLY="--tts-only"
            ;;
        debug)
            DEBUG="--debug"
            ;;
        custom)
            # Use pyagentvox.yaml from current directory
            if [ -f "pyagentvox.yaml" ]; then
                CONFIG="--config pyagentvox.yaml"
            else
                echo "❌ No pyagentvox.yaml found in current directory"
                exit 1
            fi
            ;;
        *)
            echo "❌ Unknown option: $ARG"
            echo ""
            echo "Usage: /voice [profile] [tts-only] [debug] [custom]"
            echo ""
            echo "Profiles: michelle, jenny, emma, aria, ava, sonia, libby"
            echo "Modes: tts-only, debug, custom"
            echo ""
            echo "Examples:"
            echo "  /voice michelle"
            echo "  /voice michelle tts-only"
            echo "  /voice jenny debug"
            echo "  /voice tts-only debug"
            exit 1
            ;;
    esac
done

# Check if already running using PyAgentVox CLI
if python -m pyagentvox status 2>&1 | grep -q "Status: ✓ Running"; then
    echo "⚠️  PyAgentVox is already running"
    echo ""
    echo "To restart, first stop with: /voice-stop"
    echo "Or to switch voice: /voice-switch <profile>"
    exit 1
fi

# Start PyAgentVox
echo "🌙 Starting PyAgentVox Voice Chat..."

# Show active configuration
if [ -n "$PROFILE" ]; then
    # Extract profile name from --profile argument
    PROFILE_NAME="${PROFILE#--profile }"
    echo "   Profile: ${PROFILE_NAME}"
else
    echo "   Profile: default"
fi

MODES=""
if [ -n "$TTS_ONLY" ]; then
    MODES="${MODES}TTS-only, "
fi
if [ -n "$DEBUG" ]; then
    MODES="${MODES}Debug, "
fi
if [ -n "$CONFIG" ]; then
    MODES="${MODES}Custom config, "
fi

if [ -n "$MODES" ]; then
    # Remove trailing comma and space
    MODES="${MODES%, }"
    echo "   Modes: ${MODES}"
fi

cd "$PYAGENTVOX_ROOT"

# Build command (use 'start' subcommand)
CMD="python -m pyagentvox start"
if [ -n "$PROFILE" ]; then
    CMD="$CMD $PROFILE"
fi
if [ -n "$TTS_ONLY" ]; then
    CMD="$CMD $TTS_ONLY"
fi
if [ -n "$DEBUG" ]; then
    CMD="$CMD $DEBUG"
fi
if [ -n "$CONFIG" ]; then
    CMD="$CMD $CONFIG"
fi

# Run in background
LOG_FILE="/tmp/pyagentvox_$$.log"
$CMD > "$LOG_FILE" 2>&1 &
PID=$!

echo "   PID: $PID"
echo "   Log: $LOG_FILE"
echo ""
echo "✨ Voice chat started!"
echo ""
echo "💬 Start talking - your speech will automatically appear in Claude Code!"
echo "🎤 Say 'stop listening' to stop PyAgentVox"
echo ""
echo "To stop manually: /voice-stop"
