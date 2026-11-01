#!/usr/bin/env bash
# ==============================================================================
# ⚡ AntiMobile Pro - Universal Smart Installer & Updater
# Supports: Android (Termux), macOS (Apple Silicon / Intel), Linux (Debian, Arch, Fedora), WSL
# ==============================================================================

set -e

# ANSI Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default Configuration
REPO_URL="https://github.com/cgimani/AntiMobile-Pro.git"
DEFAULT_INSTALL_DIR="$HOME/AntiMobile-Pro"
APP_NAME="antimobile"
SHORT_NAME="agy-web"
PORT="7681"

# Banner
print_banner() {
    echo -e "${PURPLE}"
    echo "  █████╗ ███╗   ██╗████████╗██╗███╗   ███╗ ██████╗ ██████╗ ██╗██╗     ███████╗"
    echo " ██╔══██╗████╗  ██║╚══██╔══╝██║████╗ ████║██╔═══██╗██╔══██╗██║██║     ██╔════╝"
    echo " ███████║██╔██╗ ██║   ██║   ██║██╔████╔██║██║   ██║██████╔╝██║██║     █████╗  "
    echo " ██╔══██║██║╚██╗██║   ██║   ██║██║╚██╔╝██║██║   ██║██╔══██╗██║██║     ██╔══╝  "
    echo " ██║  ██║██║ ╚████║   ██║   ██║██║ ╚═╝ ██║╚██████╔╝██████╔╝██║███████╗███████╗"
    echo " ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚═╝╚══════╝╚══════╝"
    echo -e "${CYAN}          ⚡ AntiMobile Pro - وب‌اپلیکیشن پیشرو هوشمند و کلاینت امن AGY ⚡${NC}"
    echo ""
}

# 1. Detect Operating System & Package Manager
detect_os() {
    if [ -n "$PREFIX" ] && [ -d "$PREFIX/bin" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
        OS_TYPE="termux"
        PKG_MGR="pkg"
        BIN_DIR="$PREFIX/bin"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        PKG_MGR="brew"
        BIN_DIR="$HOME/.local/bin"
    elif [ -f /etc/os-release ]; then
        OS_TYPE="linux"
        BIN_DIR="$HOME/.local/bin"
        if command -v apt-get >/dev/null 2>&1; then
            PKG_MGR="apt"
        elif command -v pacman >/dev/null 2>&1; then
            PKG_MGR="pacman"
        elif command -v dnf >/dev/null 2>&1; then
            PKG_MGR="dnf"
        elif command -v apk >/dev/null 2>&1; then
            PKG_MGR="apk"
        else
            PKG_MGR="unknown"
        fi
    else
        OS_TYPE="generic"
        BIN_DIR="$HOME/.local/bin"
        PKG_MGR="unknown"
    fi
    mkdir -p "$BIN_DIR"
}

# 2. Check and Install Dependencies
install_dependencies() {
    echo -e "${BLUE}🔍 در حال بررسی پیش‌نیازهای سیستمی...${NC}"

    case "$OS_TYPE" in
        termux)
            echo -e "${GREEN}📱 محیط شناسایی‌شده: Android Termux${NC}"
            pkg update -y >/dev/null 2>&1 || true
            for pkg in python git curl; do
                if ! command -v $pkg >/dev/null 2>&1; then
                    echo -e "${YELLOW}📦 در حال نصب $pkg...${NC}"
                    pkg install -y $pkg
                fi
            done
            ;;
        macos)
            echo -e "${GREEN}🍏 محیط شناسایی‌شده: macOS ($(uname -m))${NC}"
            if ! command -v python3 >/dev/null 2>&1; then
                if command -v brew >/dev/null 2>&1; then
                    echo -e "${YELLOW}📦 در حال نصب python3 با Homebrew...${NC}"
                    brew install python
                else
                    echo -e "${RED}❌ لطفاً پایتون ۳ را نصب کنید (https://python.org)${NC}"
                    exit 1
                fi
            fi
            ;;
        linux)
            echo -e "${GREEN}🐧 محیط شناسایی‌شده: Linux (${PKG_MGR})${NC}"
            if ! command -v python3 >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
                echo -e "${YELLOW}📦 در حال نصب ابزارهای پایه با دسترسی sudo...${NC}"
                case "$PKG_MGR" in
                    apt)
                        sudo apt-get update && sudo apt-get install -y python3 python3-pip git curl
                        ;;
                    pacman)
                        sudo pacman -Sy --noconfirm python python-pip git curl
                        ;;
                    dnf)
                        sudo dnf install -y python3 python3-pip git curl
                        ;;
                    apk)
                        sudo apk add python3 py3-pip git curl
                        ;;
                esac
            fi
            ;;
    esac

    # Ensure pip is ready and install Tornado
    echo -e "${BLUE}🐍 در حال بررسی کتابخانه‌های پایتون (Tornado)...${NC}"
    python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
    if ! python3 -c "import tornado" >/dev/null 2>&1; then
        echo -e "${YELLOW}📦 در حال نصب کتابخانه Tornado...${NC}"
        python3 -m pip install "tornado>=6.2" --break-system-packages 2>/dev/null || python3 -m pip install "tornado>=6.2"
    fi
    echo -e "${GREEN}✅ پیش‌نیازهای پایتون آماده است.${NC}"
}

# 3. Check for Antigravity Binary
check_agy_binary() {
    echo -e "${BLUE}🧠 در حال بررسی موتور اصلی Antigravity CLI (agy)...${NC}"
    AGY_PATH=""
    if command -v agy >/dev/null 2>&1; then
        AGY_PATH=$(command -v agy)
    elif [ -f "$HOME/.local/bin/agy" ]; then
        AGY_PATH="$HOME/.local/bin/agy"
    elif [ -f "$HOME/.gemini/antigravity-cli/bin/agy" ]; then
        AGY_PATH="$HOME/.gemini/antigravity-cli/bin/agy"
    fi

    if [ -n "$AGY_PATH" ]; then
        echo -e "${GREEN}✅ موتور هوش مصنوعی با موفقیت یافت شد: ${AGY_PATH}${NC}"
    else
        echo -e "${YELLOW}⚠️ توجه: باینری 'agy' در مسیرهای استاندارد سیستم یافت نشد.${NC}"
        echo -e "${YELLOW}   برنامه وب کار خواهد کرد، اما برای اجرای کامل دستورات نیاز است باینری agy در سیستم فعال باشد.${NC}"
    fi
}

# 4. Resolve Installation Directory
resolve_dir() {
    if [ -f "./server.py" ] && [ -f "./index.html" ]; then
        TARGET_DIR="$(pwd)"
        IS_IN_PLACE=true
    else
        TARGET_DIR="$DEFAULT_INSTALL_DIR"
        IS_IN_PLACE=false
    fi
}

# 5. Perform Install or Update
install_or_update() {
    resolve_dir

    if [ "$IS_IN_PLACE" = true ]; then
        echo -e "${CYAN}📂 در حال پیکربندی و به‌روزرسانی پروژه در مسیر فعلی: ${TARGET_DIR}${NC}"
        if [ -d ".git" ]; then
            echo -e "${BLUE}🔄 در حال دریافت آخرین تغییرات از مخزن گیت...${NC}"
            if [ -f "chat_history.json" ]; then
                cp "chat_history.json" "chat_history.json.bak" 2>/dev/null || true
            fi
            git pull --rebase 2>/dev/null || true
            if [ -f "chat_history.json.bak" ] && [ ! -f "chat_history.json" ]; then
                mv "chat_history.json.bak" "chat_history.json" 2>/dev/null || true
            else
                rm -f "chat_history.json.bak" 2>/dev/null || true
            fi
        fi
    else
        if [ -d "$TARGET_DIR" ]; then
            echo -e "${YELLOW}🔄 نسخه قبلی در ${TARGET_DIR} یافت شد. در حال به‌روزرسانی...${NC}"
            cd "$TARGET_DIR"
            if [ -f "chat_history.json" ]; then
                cp "chat_history.json" "chat_history.json.bak" 2>/dev/null || true
            fi
            if [ -d ".git" ]; then
                git fetch origin 2>/dev/null || true
                git pull --rebase 2>/dev/null || true
            fi
            if [ -f "chat_history.json.bak" ]; then
                mv "chat_history.json.bak" "chat_history.json" 2>/dev/null || true
            fi
        else
            echo -e "${CYAN}📥 در حال دریافت فایل‌های پروژه از گیت‌هاب...${NC}"
            git clone "$REPO_URL" "$TARGET_DIR"
            cd "$TARGET_DIR"
        fi
    fi

    # Set executable permissions
    chmod +x start.sh stop.sh agy-app push_to_github.sh 2>/dev/null || true
    if [ -f "server.py" ]; then
        chmod +x server.py
    fi

    # Create Global CLI Shortcuts
    echo -e "${BLUE}🔗 در حال ایجاد دستورات میانبر در ترمینال (${BIN_DIR})...${NC}"
    
    cat <<EOF > "$BIN_DIR/$APP_NAME"
#!/usr/bin/env bash
cd "$TARGET_DIR" && ./start.sh "\$@"
EOF
    chmod +x "$BIN_DIR/$APP_NAME"

    cat <<EOF > "$BIN_DIR/$SHORT_NAME"
#!/usr/bin/env bash
cd "$TARGET_DIR" && ./start.sh "\$@"
EOF
    chmod +x "$BIN_DIR/$SHORT_NAME"

    # Ensure BIN_DIR is in PATH for macOS/Linux
    if [ "$OS_TYPE" != "termux" ]; then
        SHELL_RC=""
        if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
            SHELL_RC="$HOME/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            SHELL_RC="$HOME/.bashrc"
        fi

        if [ -n "$SHELL_RC" ]; then
            if ! grep -q "$BIN_DIR" "$SHELL_RC" 2>/dev/null; then
                echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_RC"
            fi
        fi
    fi

    echo -e "${GREEN}✅ میانبرهای دستوری '${APP_NAME}' و '${SHORT_NAME}' با موفقیت ساخته شدند.${NC}"
}

# 6. Detect IP and Print Summary
print_summary() {
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

    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${BOLD}  🎉 نصب و پیکربندی AntiMobile Pro با موفقیت تکمیل شد!${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "  📂 مسیر نصب پروژه:       ${BOLD}${TARGET_DIR}${NC}"
    echo -e "  🚀 روش راه‌اندازی سریع:   دستور ${BOLD}${CYAN}antimobile${NC} یا ${BOLD}${CYAN}agy-web${NC} یا ${BOLD}${CYAN}./start.sh${NC}"
    echo -e "  🛑 روش توقف سرور:         دستور ${BOLD}${CYAN}./stop.sh${NC}"
    echo -e "  --------------------------------------------------------------"
    echo -e "  📱 آدرس دسترسی محلی:     ${BOLD}${CYAN}http://localhost:${PORT}${NC}"
    if [ "$LOCAL_IP" != "127.0.0.1" ]; then
    echo -e "  🌐 آدرس در شبکه وای‌فای:  ${BOLD}${CYAN}http://${LOCAL_IP}:${PORT}${NC}"
    fi
    echo -e "  🔐 احراز هویت پیش‌فرض:    نام‌کاربری: ${BOLD}admin${NC} | رمز عبور: ${BOLD}antigravity${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo ""
}

# Execution Flow
print_banner
detect_os
install_dependencies
check_agy_binary
install_or_update
print_summary

# Ask user if they want to launch right away
if [ -t 0 ]; then
    read -p "آیا مایلید سرور همین حالا اجرا شود؟ (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$TARGET_DIR" && ./start.sh
    fi
fi
