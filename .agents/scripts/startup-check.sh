#!/bin/bash
# Startup Check — Verify yesterday's activity
# Run this at the start of each build session

set -e

# Get workspace root (2 levels up from .agents/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

LOGS_DIR="$WORKSPACE_ROOT/docs/logs"
PROGRESS_FILE="$WORKSPACE_ROOT/docs/PROGRESS.md"
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null)

echo "╔════════════════════════════════════════════════════════╗"
echo "║         Evolution Stables — Session Startup           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check if logs directory exists
if [ ! -d "$LOGS_DIR" ]; then
    echo "⚠️  WARNING: docs/logs/ directory not found!"
    echo "   Run: mkdir -p docs/logs"
    echo ""
    exit 1
fi

# Check for today's log (already started?)
if [ -f "$LOGS_DIR/$TODAY.md" ]; then
    echo "📝 Today's session already logged: $TODAY.md"
    echo ""
    echo "   Continue working? Or wrap up with '/done'?"
    echo ""
else
    echo "✅ No session logged for today yet ($TODAY)"
    echo ""
fi

# Check for yesterday's log
if [ -f "$LOGS_DIR/$YESTERDAY.md" ]; then
    echo "✅ Yesterday's session logged: $YESTERDAY.md"
    echo ""
    echo "   Last session summary:"
    grep -A 10 "^## Done" "$LOGS_DIR/$YESTERDAY.md" | head -6 | sed 's/^/   /'
    echo ""
else
    echo "⚠️  No session logged for yesterday ($YESTERDAY)"
    echo ""
    echo "   Possible reasons:"
    echo "   - Weekend/holiday"
    echo "   - Forgot to run '/done'"
    echo "   - First day of new project"
    echo ""
fi

# Show current phase from PROGRESS.md
if [ -f "$PROGRESS_FILE" ]; then
    echo "📊 Current Progress:"
    grep -A 3 "^## Current State" "$PROGRESS_FILE" | tail -2 | sed 's/^/   /'
    echo ""
    
    echo "📋 What's Next:"
    grep -A 5 "^## What's Next" "$PROGRESS_FILE" | tail -3 | sed 's/^/   /'
    echo ""
else
    echo "⚠️  WARNING: docs/PROGRESS.md not found!"
    echo ""
fi

# Show deployed functions status
echo "🔧 Cloud Functions Status:"
if command -v gcloud &> /dev/null; then
    gcloud functions list --project=evolution-engine --format="table(name,state)" 2>/dev/null | tail -n +2 | sed 's/^/   /' || echo "   (gcloud not available)"
else
    echo "   (gcloud not available)"
fi
echo ""

echo "════════════════════════════════════════════════════════"
echo "Ready to build! 🚀"
echo "════════════════════════════════════════════════════════"
echo ""
