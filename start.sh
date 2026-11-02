#!/usr/bin/env bash
# ==============================================================================
# ⚡ AntiMobile Pro - Runner Script (Cross-Platform)
# Compatible with: Android (Termux), macOS, Linux, WSL
# Version: 3.2.0
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PORT="${PORT:-7681}"

# ANSI Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# 1. Android Termux Optimizations (Wake Lock)
if [ -n "$PREFIX" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
    if command -v termux-wake-lock >/dev/null 2>&1; then
        termux-wake-lock 2>/dev/null || true
    fi
fi

# 2. Terminate any previous instance on PORT or by name
pkill -9 -f "python3.*server.py" 2>/dev/null || true
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
fi
sleep 0.5

# 3. Start Tornado Server in background
nohup python3 "$DIR/server.py" > "$DIR/server.log" 2>&1 &
SERVER_PID=$!

# 4. Wait & verify server readiness (POSIX-compliant, works on 100% Android versions)
SERVER_READY=false
for i in {1..15}; do
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        break
    fi
    if command -v curl >/dev/null 2>&1; then
        if curl -s -o /dev/null -m 1 "http://127.0.0.1:${PORT}/"; then
            SERVER_READY=true
            break
        fi
    else
        if [ $i -ge 4 ]; then
            SERVER_READY=true
            break
        fi
    fi
    sleep 0.3
done

if [ "$SERVER_READY" = false ]; then
    echo -e "${RED}❌ Failed to start server! Checking server log:${NC}"
    if [ -f "$DIR/server.log" ]; then
        cat "$DIR/server.log" | tail -n 25
    fi
    exit 1
fi

# 5. Detect IPs
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

VERSION="$(cat "$DIR/VERSION" 2>/dev/null || echo "3.2.0")"

echo -e "${GREEN}================================================================${NC}"
echo -e "${BOLD}  🚀 AntiMobile Pro (v${VERSION}) server started successfully!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "  📱 Local URL (Localhost):  ${BOLD}${CYAN}http://127.0.0.1:${PORT}${NC}"
if [ "$LOCAL_IP" != "127.0.0.1" ]; then
echo -e "  🌐 Network URL (Wi-Fi):    ${BOLD}${CYAN}http://${LOCAL_IP}:${PORT}${NC}"
fi
echo -e "  ⚡ Access mode:             ${GREEN}Instant workspace (No password required)${NC}"
echo -e "  ⚙️ Process ID (PID):        ${SERVER_PID}"
echo -e "${GREEN}----------------------------------------------------------------${NC}"
echo -e "  To stop the server run:     ${YELLOW}./stop.sh${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""

# 6. Auto-open browser across all platforms
OPEN_URL="http://127.0.0.1:${PORT}"
echo -e "${BLUE}🌐 Opening browser (${OPEN_URL})...${NC}"

if [ -n "$PREFIX" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
    # Android Termux: try termux-open-url, then termux-open, then am start
    if command -v termux-open-url >/dev/null 2>&1; then
        termux-open-url "$OPEN_URL" >/dev/null 2>&1 || true
    elif command -v termux-open >/dev/null 2>&1; then
        termux-open "$OPEN_URL" >/dev/null 2>&1 || true
    elif command -v am >/dev/null 2>&1; then
        am start --user 0 -a android.intent.action.VIEW -d "$OPEN_URL" >/dev/null 2>&1 || \
        am start -a android.intent.action.VIEW -d "$OPEN_URL" >/dev/null 2>&1 || true
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open "$OPEN_URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$OPEN_URL" >/dev/null 2>&1 || true
fi
