#!/usr/bin/env bash
# ==============================================================================
# ⏹ Antigravity Web PWA - Stop Script
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🛑 در حال متوقف کردن سرور Antigravity PWA..."

PORT="${PORT:-7681}"

if command -v lsof >/dev/null 2>&1; then
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
fi
pkill -f "python3.*server.py" 2>/dev/null || true
sleep 0.5

if pgrep -f "python3.*server.py" > /dev/null 2>&1; then
    pkill -9 -f "python3.*server.py" 2>/dev/null || true
fi

echo "✅ سرور با موفقیت متوقف گردید."
