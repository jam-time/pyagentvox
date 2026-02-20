#!/bin/bash
# Avatar Tags Skill - Query and filter avatar images by tag
# Usage: /avatar-tags [list|filter|current] [options]

set -euo pipefail

PYAGENTVOX_ROOT="C:/projects/pyprojects/pyagentvox"
COMMAND="${1:-list}"
shift 2>/dev/null || true

cd "$PYAGENTVOX_ROOT"

case "$COMMAND" in
    list)
        echo "🏷️  Querying avatar tags..."
        echo ""
        python -m pyagentvox.avatar_tags tags
        ;;

    filter)
        # Pass all remaining arguments to the filter subcommand
        # Need to find PID of running PyAgentVox
        PID_FILE=""
        for f in "$TMPDIR"pyagentvox_*.pid "${TEMP:-/tmp}"/pyagentvox_*.pid /tmp/pyagentvox_*.pid 2>/dev/null; do
            if [ -f "$f" ]; then
                PID_FILE="$f"
                break
            fi
        done

        if [ -z "$PID_FILE" ]; then
            echo "❌ PyAgentVox is not running"
            echo ""
            echo "Start it first with: /voice"
            exit 1
        fi

        PID=$(cat "$PID_FILE" | tr -d '[:space:]')

        # Check for --reset flag
        RESET=""
        INCLUDE=""
        EXCLUDE=""
        REQUIRE_ALL=""

        while [ $# -gt 0 ]; do
            case "$1" in
                --reset)
                    RESET="--reset"
                    shift
                    ;;
                --include)
                    INCLUDE="--include $2"
                    shift 2
                    ;;
                --exclude)
                    EXCLUDE="--exclude $2"
                    shift 2
                    ;;
                --require-all)
                    REQUIRE_ALL="--require-all"
                    shift
                    ;;
                *)
                    echo "❌ Unknown option: $1"
                    echo ""
                    echo "Usage: /avatar-tags filter [--include tags] [--exclude tags] [--reset]"
                    exit 1
                    ;;
            esac
        done

        if [ -n "$RESET" ]; then
            echo "🔄 Resetting avatar filters..."
            python -m pyagentvox.avatar_tags filter --pid "$PID" --reset
        else
            echo "🏷️  Applying avatar filters..."
            # Build filter command dynamically
            FILTER_CMD="python -m pyagentvox.avatar_tags filter --pid $PID"
            [ -n "$INCLUDE" ] && FILTER_CMD="$FILTER_CMD $INCLUDE"
            [ -n "$EXCLUDE" ] && FILTER_CMD="$FILTER_CMD $EXCLUDE"
            [ -n "$REQUIRE_ALL" ] && FILTER_CMD="$FILTER_CMD $REQUIRE_ALL"
            eval $FILTER_CMD
        fi

        echo ""
        echo "✨ Avatar images will update on next emotion change"
        ;;

    current)
        # Show current filter state
        PID_FILE=""
        for f in "$TMPDIR"pyagentvox_*.pid "${TEMP:-/tmp}"/pyagentvox_*.pid /tmp/pyagentvox_*.pid 2>/dev/null; do
            if [ -f "$f" ]; then
                PID_FILE="$f"
                break
            fi
        done

        if [ -z "$PID_FILE" ]; then
            echo "❌ PyAgentVox is not running"
            echo ""
            echo "Start it first with: /voice"
            exit 1
        fi

        PID=$(cat "$PID_FILE" | tr -d '[:space:]')

        echo "🏷️  Current avatar filters:"
        echo ""
        python -m pyagentvox.avatar_tags current --pid "$PID"
        ;;

    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        echo "Usage: /avatar-tags [list|filter|current] [options]"
        echo ""
        echo "Commands:"
        echo "  list                    - Show all tags with counts"
        echo "  filter --include tags   - Show only specific tags"
        echo "  filter --exclude tags   - Hide specific tags"
        echo "  filter --reset          - Clear all filters"
        echo "  current                 - Show current filter state"
        exit 1
        ;;
esac
