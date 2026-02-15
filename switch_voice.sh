#!/bin/bash
# Switch PyAgentVox to a different voice profile

PROFILE=$1

if [ -z "$PROFILE" ]; then
    echo "Usage: switch_voice.sh <profile>"
    echo "Available profiles: michelle, jenny, aria, emma, ava, sonia, libby, maisie"
    exit 1
fi

echo "🔄 Switching to profile: $PROFILE"

# Kill existing PyAgentVox instance
PID_FILE="/tmp/pyagentvox.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    echo "   Stopping old instance (PID: $OLD_PID)..."

    # Kill the PID and all its children
    pkill -P "$OLD_PID" 2>/dev/null || true
    kill "$OLD_PID" 2>/dev/null || true

    # Also kill any python process running pyagentvox
    pkill -f "pyagentvox" 2>/dev/null || true

    # Remove PID file
    rm -f "$PID_FILE"

    # Wait a moment for cleanup
    sleep 1
fi

# Start new instance
cd "$(dirname "$0")"
echo "   Starting new instance with profile: $PROFILE..."
uv run python -m pyagentvox --profile "$PROFILE" > /tmp/pyagentvox.log 2>&1 &

# Wait for PID file to be created
sleep 2

if [ -f "$PID_FILE" ]; then
    NEW_PID=$(cat "$PID_FILE")
    echo "✓  PyAgentVox started with $PROFILE profile (PID: $NEW_PID)"
    echo "   Log file: /tmp/pyagentvox.log"
else
    echo "❌ Failed to start PyAgentVox"
    echo "   Check log: /tmp/pyagentvox.log"
    exit 1
fi
