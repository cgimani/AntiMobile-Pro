#!/usr/bin/env bash
# ==============================================================================
# ⚡ AntiMobile Pro - Runner Script (Cross-Platform)
# Compatible with: Android (Termux), macOS, Linux, WSL
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PORT="${PORT:-7681}"

# ANSI Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Kill any existing server instance on PORT or by process name
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
fi
pkill -9 -f "python3.*server.py" 2>/dev/null || true
sleep 0.8

# Start Tornado Server in background
nohup python3 "$DIR/server.py" > "$DIR/server.log" 2>&1 &
SERVER_PID=$!
sleep 1.2

# Verify server started
if ! ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "❌ خطا در راه‌اندازی سرور! لاگ سرور را بررسی کنید:"
    cat "$DIR/server.log" 2>/dev/null | tail -n 15
    exit 1
fi

# Detect Local IP
LOCAL_IP=""
if command -v ip >/dev/null 2>&1; then
    LOCAL_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
fi
if [ -z "$LOCAL_IP" ] && command -v ifconfig >/dev/null 2>&1; then
    LOCAL_IP=$(ifconfig 2>/dev/null | grep -E 'inet (addr:)?192\.168\.|10\.|172\.' | awk '{print $2}' | sed 's/addr://' | head -n 1)
fi
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi

echo -e "${GREEN}================================================================${NC}"
echo -e "${BOLD}  🚀 سرور هوشمند AntiMobile Pro با موفقیت اجرا شد!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "  📱 آدرس محلی (Localhost):  ${CYAN}http://127.0.0.1:${PORT}${NC}"
if [ "$LOCAL_IP" != "127.0.0.1" ]; then
echo -e "  🌐 آدرس شبکه (Wi-Fi):       ${CYAN}http://${LOCAL_IP}:${PORT}${NC}"
fi
echo -e "  ⚡ بدون نیاز به پسورد:      ${GREEN}ورود مستقیم و پرسرعت${NC}"
echo -e "  ⚙️ شناسه پروسه (PID):       ${SERVER_PID}"
echo -e "${GREEN}----------------------------------------------------------------${NC}"
echo -e "  برای توقف سرور دستور زیر را اجرا کنید: ${YELLOW}./stop.sh${NC}"
echo -e "${GREEN}================================================================${NC}"

# Auto-open in default browser
if command -v am >/dev/null 2>&1; then
    # Android Termux
    am start -a android.intent.action.VIEW -d "http://127.0.0.1:${PORT}" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
    # macOS
    open "http://127.0.0.1:${PORT}" 2>/dev/null || true
elif command -v xdg-open >/dev/null 2>&1; then
    # Linux
    xdg-open "http://127.0.0.1:${PORT}" 2>/dev/null || true
fi
