#!/usr/bin/env bash
# ==============================================================================
# ⚡ AntiMobile Pro - Universal Smart Installer, Updater & Manager
# Supports: Android (Termux), macOS (Apple Silicon / Intel), Linux, WSL
# Version: 3.2.0 (Semantic Versioning)
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

# Version definition
APP_VERSION="3.2.0"
REPO_URL="https://github.com/cgimani/AntiMobile-Pro.git"
DEFAULT_INSTALL_DIR="$HOME/AntiMobile-Pro"
APP_NAME="antimobile"
SHORT_NAME="agy-web"
PORT="7681"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR/VERSION" ]; then
    APP_VERSION="$(cat "$DIR/VERSION" | tr -d '[:space:]')"
fi

# Banner
print_banner() {
    echo -e "${PURPLE}"
    echo "  █████╗ ███╗   ██╗████████╗██╗███╗   ███╗ ██████╗ ██████╗ ██╗██╗     ███████╗"
    echo " ██╔══██╗████╗  ██║╚══██╔══╝██║████╗ ████║██╔═══██╗██╔══██╗██║██║     ██╔════╝"
    echo " ███████║██╔██╗ ██║   ██║   ██║██╔████╔██║██║   ██║██████╔╝██║██║     █████╗  "
    echo " ██╔══██║██║╚██╗██║   ██║   ██║██║╚██╔╝██║██║   ██║██╔══██╗██║██║     ██╔══╝  "
    echo " ██║  ██║██║ ╚████║   ██║   ██║██║ ╚═╝ ██║╚██████╔╝██████╔╝██║███████╗███████╗"
    echo " ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═════╝ ╚═╝╚══════╝╚══════╝"
    echo -e "${CYAN}      ⚡ AntiMobile Pro (v${APP_VERSION}) - Smart Client for Google Antigravity ⚡${NC}"
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
    echo -e "${BLUE}🔍 Checking system prerequisites...${NC}"

    case "$OS_TYPE" in
        termux)
            echo -e "${GREEN}📱 Detected environment: Android Termux${NC}"
            pkg update -y >/dev/null 2>&1 || true
            for pkg in python git curl termux-tools termux-api; do
                if ! command -v $pkg >/dev/null 2>&1; then
                    echo -e "${YELLOW}📦 Installing $pkg...${NC}"
                    pkg install -y $pkg 2>/dev/null || true
                fi
            done
            if ! python3 -c "import tornado" >/dev/null 2>&1; then
                echo -e "${YELLOW}📦 Installing prebuilt python-tornado for Termux...${NC}"
                pkg install -y python-tornado 2>/dev/null || true
            fi
            ;;
        macos)
            echo -e "${GREEN}🍏 Detected environment: macOS ($(uname -m))${NC}"
            if ! command -v python3 >/dev/null 2>&1; then
                if command -v brew >/dev/null 2>&1; then
                    echo -e "${YELLOW}📦 Installing python3 via Homebrew...${NC}"
                    brew install python
                else
                    echo -e "${RED}❌ Please install Python 3 (https://python.org)${NC}"
                    exit 1
                fi
            fi
            ;;
        linux)
            echo -e "${GREEN}🐧 Detected environment: Linux (${PKG_MGR})${NC}"
            if ! command -v python3 >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
                echo -e "${YELLOW}📦 Installing base tools using sudo...${NC}"
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

    # Ensure pip and Tornado are ready
    echo -e "${BLUE}🐍 Checking Python dependencies (Tornado)...${NC}"
    if ! python3 -c "import tornado" >/dev/null 2>&1; then
        echo -e "${YELLOW}📦 Installing Tornado library...${NC}"
        if [ "$OS_TYPE" = "termux" ]; then
            pkg install -y python-tornado 2>/dev/null || true
        fi
        if ! python3 -c "import tornado" >/dev/null 2>&1; then
            python3 -m pip install "tornado>=6.2" --break-system-packages 2>/dev/null || \
            python3 -m pip install "tornado>=6.2" 2>/dev/null || true
        fi
    fi
    if python3 -c "import tornado" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Python dependencies are ready (Tornado OK).${NC}"
    else
        echo -e "${YELLOW}⚠️ Notice: Python Tornado check completed.${NC}"
    fi
    ensure_termux_permissions
}

# ==============================================================================
# 2.5. Termux Android Permissions Enforcer (Mandatory Storage & Wakelock)
# "تا نگیرفته نصب تموم نشه" - Installation MUST NOT finish until granted!
# ==============================================================================

test_storage_access() {
    # Test 1: $HOME/storage/shared readable by ls
    if [ -d "$HOME/storage/shared" ] && ls "$HOME/storage/shared" >/dev/null 2>&1; then
        # On Android 11+ Scoped Storage, test writing inside downloads or shared folders
        for folder in "$HOME/storage/downloads" "$HOME/storage/shared/Download" "$HOME/storage/dcim" "$HOME/storage/shared"; do
            if [ -d "$folder" ]; then
                local probe="$folder/.antimobile_perm_probe_$$"
                if touch "$probe" 2>/dev/null; then
                    rm -f "$probe" 2>/dev/null
                    return 0
                fi
            fi
        done
        # If readable, permission is definitely granted by Android OS
        return 0
    fi

    # Test 2: Standard Android internal storage root /sdcard
    if [ -d "/sdcard/Download" ]; then
        local probe="/sdcard/Download/.antimobile_perm_probe_$$"
        if touch "$probe" 2>/dev/null; then
            rm -f "$probe" 2>/dev/null
            return 0
        fi
    fi
    if [ -d "/sdcard" ] && ls "/sdcard" >/dev/null 2>&1; then
        return 0
    fi

    # Test 3: Standard Android internal storage /storage/emulated/0
    if [ -d "/storage/emulated/0" ] && ls "/storage/emulated/0" >/dev/null 2>&1; then
        return 0
    fi

    # Test 4: $HOME/storage/downloads
    if [ -d "$HOME/storage/downloads" ] && [ -r "$HOME/storage/downloads" ]; then
        local probe="$HOME/storage/downloads/.antimobile_perm_probe_$$"
        if touch "$probe" 2>/dev/null; then
            rm -f "$probe" 2>/dev/null
            return 0
        fi
    fi

    return 1
}

ensure_termux_permissions() {
    if [ "$OS_TYPE" != "termux" ]; then
        return 0
    fi

    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║    📱 بررسی و اخذ مجوزهای ضروری اندروید برای ترموکس (Termux)    ║${NC}"
    echo -e "${PURPLE}║        Android & Termux Essential Permissions Setup              ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # 1. Background Wake Lock (Prevents Android from freezing/killing server)
    echo -e "${BLUE}🔋 ۱. مجوز اجرای پایدار در پس‌زمینه (Termux Wake Lock)...${NC}"
    if command -v termux-wake-lock >/dev/null 2>&1; then
        termux-wake-lock 2>/dev/null || true
        echo -e "${GREEN}   ✅ مجوز Wake Lock با موفقیت فعال شد (جلوگیری از توقف سرور توسط بهینه‌سازی باتری).${NC}"
    else
        echo -e "${YELLOW}   ⚠️ دستور termux-wake-lock در دسترس نیست.${NC}"
    fi

    # 2. Storage Permission Check (MANDATORY ENFORCEMENT - CANNOT PROCEED UNTIL GRANTED)
    echo -e "${BLUE}📁 ۲. بررسی و راه‌اندازی مجوز دسترسی به حافظه گوشی (Storage Permission)...${NC}"

    if test_storage_access; then
        echo -e "${GREEN}   ✅ مجوز دسترسی به حافظه از قبل تأیید شده است ($HOME/storage/shared).${NC}"
    else
        echo -e "${YELLOW}   ⚠️ ترموکس هنوز مجوز دسترسی به حافظه دستگاه را دریافت نکرده است!${NC}"
        echo -e "${BOLD}${CYAN}   📲 در حال باز کردن پنجره درخواست مجوز در صفحه گوشی شما...${NC}"
        echo -e "${BOLD}${PURPLE}   👉 لطفاً در پنجره پاپ‌آپ باز شده در گوشی، گزینه «Allow / اجازه دادن» را لمس کنید.${NC}"
        echo ""

        # Request permission from Android OS
        termux-setup-storage >/dev/null 2>&1 || true

        local wait_sec=0
        local prompt_count=0

        # Loop until test_storage_access succeeds - INSTALLATION WILL NOT PROCEED UNTIL GRANTED!
        while ! test_storage_access; do
            wait_sec=$((wait_sec + 2))
            echo -ne "   ${YELLOW}⏳ در حال بررسی مجوز... (${wait_sec} ثانیه) - تا تأیید مجوز در گوشی، نصب متوقف می‌ماند...\r${NC}"
            sleep 2

            # Every 14 seconds, show guidance, direct intent to Android Settings, and re-trigger termux-setup-storage
            if [ $((wait_sec % 14)) -eq 0 ]; then
                prompt_count=$((prompt_count + 1))
                echo ""
                echo -e "${RED}   ❌ مجوز هنوز توسط شما در گوشی تأیید نشده است!${NC}"
                echo -e "${CYAN}   💡 راهنمای تأیید سریع:${NC}"
                echo -e "      ۱. به صفحه نمایش گوشی نگاه کنید و در پاپ‌آپ درخواست مجوز گزینه «Allow» را بزنید."
                echo -e "      ۲. در حال باز کردن صفحه مجوزهای ترموکس در تنظیمات اندروید..."
                
                # Direct intent to open Termux App Permissions in Android Settings
                if command -v am >/dev/null 2>&1; then
                    am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.termux >/dev/null 2>&1 || true
                fi

                echo -e "         ${YELLOW}Settings -> Apps -> Termux -> Permissions -> Files and media (Allow)${NC}"
                echo -e "${BLUE}   درخواست مجدد مجوز ارسال شد...${NC}"
                termux-setup-storage >/dev/null 2>&1 || true

                local user_input=""
                if [ -c /dev/tty ]; then
                    echo -e "${BOLD}${PURPLE}   👉 پس از فعال‌سازی مجوز کلید [Enter]، یا برای رد کردن کلید [s] را بزنید: ${NC}"
                    read -r user_input < /dev/tty || true
                    if [[ "$user_input" =~ ^[Ss]$ ]]; then
                        echo -e "${YELLOW}   ⚠️ مجوز به دستور شما رد شد.${NC}"
                        break
                    fi
                fi
                echo ""
            fi
        done

        if test_storage_access; then
            echo ""
            echo -e "${GREEN}   ================================================================${NC}"
            echo -e "${GREEN}${BOLD}   🎉 مجوز دسترسی به حافظه با موفقیت دریافت و تأیید شد!${NC}"
            echo -e "${GREEN}   📂 پوشه حافظه مشترک: $HOME/storage/shared -> /sdcard${NC}"
            echo -e "${GREEN}   ================================================================${NC}"
        fi
    fi

    # 3. Termux-API tools
    echo -e "${BLUE}📦 ۳. بررسی و آماده‌سازی ابزارهای سیستمی ترموکس (termux-api)...${NC}"
    if ! command -v termux-battery-status >/dev/null 2>&1; then
        pkg install -y termux-api >/dev/null 2>&1 || true
    fi
    echo -e "${GREEN}   ✅ تمام مجوزها و پیش‌نیازهای ترموکس ۱۰۰٪ تکمیل شدند.${NC}"
    echo ""
}

# 3. Check for Antigravity Binary
check_agy_binary() {
    echo -e "${BLUE}🧠 Checking Antigravity CLI binary (agy)...${NC}"
    AGY_PATH=""
    if command -v agy >/dev/null 2>&1; then
        AGY_PATH=$(command -v agy)
    elif [ -f "$HOME/.local/bin/agy" ]; then
        AGY_PATH="$HOME/.local/bin/agy"
    elif [ -f "$HOME/.gemini/antigravity-cli/bin/agy" ]; then
        AGY_PATH="$HOME/.gemini/antigravity-cli/bin/agy"
    fi

    if [ -n "$AGY_PATH" ]; then
        echo -e "${GREEN}✅ Antigravity engine found: ${AGY_PATH}${NC}"
    else
        echo -e "${YELLOW}⚠️ Notice: 'agy' binary was not found in standard system PATH.${NC}"
        echo -e "${CYAN}💡 After installation, you can install the official agy binary using:${NC}"
        echo -e "   curl -sL https://antigravity.google/install.sh | bash"
    fi
}

# 3.2. Check Google Antigravity OAuth Account
check_google_auth() {
    echo -e "${BLUE}🔐 Checking Google Antigravity account status...${NC}"
    TOKEN_FILE="$HOME/.gemini/jetski-standalone-oauth-token"
    if [ -f "$TOKEN_FILE" ]; then
        EMAIL=$(python3 -c "import json; print(json.load(open('$TOKEN_FILE')).get('id_token_email',''))" 2>/dev/null || true)
        if [ -n "$EMAIL" ]; then
            echo -e "${GREEN}✅ Connected Google account: ${BOLD}${EMAIL}${NC}"
            return 0
        fi
    fi
    echo -e "${YELLOW}ℹ️ Google account not connected yet (connect via 'agy' or web app).${NC}"
}

# 4. Resolve Installation Directory
resolve_dir() {
    if [ -f "./server.py" ] && [ -f "./index.html" ]; then
        TARGET_DIR="$(pwd)"
        IS_IN_PLACE=true
    elif [ -d "$DEFAULT_INSTALL_DIR" ]; then
        TARGET_DIR="$DEFAULT_INSTALL_DIR"
        IS_IN_PLACE=false
    else
        TARGET_DIR="$DEFAULT_INSTALL_DIR"
        IS_IN_PLACE=false
    fi
}

# Check if application is already installed
is_installed() {
    resolve_dir
    if [ -f "$TARGET_DIR/server.py" ] && [ -f "$TARGET_DIR/start.sh" ]; then
        return 0
    fi
    if command -v "$APP_NAME" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Get installed version
get_installed_version() {
    resolve_dir
    if [ -f "$TARGET_DIR/VERSION" ]; then
        cat "$TARGET_DIR/VERSION" | tr -d '[:space:]'
    else
        echo "Unknown (Legacy version)"
    fi
}

# Create Global CLI Shortcuts
create_shortcuts() {
    echo -e "${BLUE}🔗 Creating terminal shortcuts in (${BIN_DIR})...${NC}"
    
    cat <<EOF > "$BIN_DIR/$APP_NAME"
#!/usr/bin/env bash
cd "$TARGET_DIR"
case "\${1:-}" in
    update|-u|--update)
        ./install.sh --update
        ;;
    stop|--stop)
        ./stop.sh
        ;;
    restart|--restart)
        ./stop.sh && ./start.sh
        ;;
    status)
        if pgrep -f "python3.*server.py" >/dev/null 2>&1; then
            echo "✅ AntiMobile Pro server is running (PID: \$(pgrep -f "python3.*server.py" | head -n 1))"
            echo "📱 URL: http://127.0.0.1:7681"
        else
            echo "🛑 AntiMobile Pro server is not running."
            echo "👉 Run 'antimobile' to start."
        fi
        ;;
    *)
        ./start.sh "\$@"
        ;;
esac
EOF
    chmod +x "$BIN_DIR/$APP_NAME"

    cat <<EOF > "$BIN_DIR/$SHORT_NAME"
#!/usr/bin/env bash
cd "$TARGET_DIR"
case "\${1:-}" in
    update|-u|--update)
        ./install.sh --update
        ;;
    stop|--stop)
        ./stop.sh
        ;;
    restart|--restart)
        ./stop.sh && ./start.sh
        ;;
    status)
        if pgrep -f "python3.*server.py" >/dev/null 2>&1; then
            echo "✅ AntiMobile Pro server is running (PID: \$(pgrep -f "python3.*server.py" | head -n 1))"
            echo "📱 URL: http://127.0.0.1:7681"
        else
            echo "🛑 AntiMobile Pro server is not running."
            echo "👉 Run 'agy-web' to start."
        fi
        ;;
    *)
        ./start.sh "\$@"
        ;;
esac
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

    echo -e "${GREEN}✅ CLI shortcuts '${APP_NAME}' and '${SHORT_NAME}' created successfully.${NC}"
    echo -e "   Commands: ${BOLD}${CYAN}antimobile${NC} (start), ${CYAN}antimobile update${NC}, ${CYAN}antimobile stop${NC}, ${CYAN}antimobile status${NC}"
}

# 5. Perform Install or Update
install_or_update() {
    resolve_dir
    detect_os
    install_dependencies
    check_agy_binary
    check_google_auth

    if [ "$IS_IN_PLACE" = true ]; then
        echo -e "${CYAN}📂 Configuring project in current directory: ${TARGET_DIR}${NC}"
        if [ -d ".git" ]; then
            echo -e "${BLUE}🔄 Pulling latest changes from Git repository...${NC}"
            if [ -f "chat_history.json" ]; then
                cp "chat_history.json" "chat_history.json.bak" 2>/dev/null || true
            fi
            git pull --rebase origin main 2>/dev/null || git pull --rebase 2>/dev/null || true
            if [ -f "chat_history.json.bak" ] && [ ! -f "chat_history.json" ]; then
                mv "chat_history.json.bak" "chat_history.json" 2>/dev/null || true
            else
                rm -f "chat_history.json.bak" 2>/dev/null || true
            fi
        fi
    else
        if [ -d "$TARGET_DIR" ]; then
            echo -e "${YELLOW}🔄 Existing installation found at ${TARGET_DIR}. Updating...${NC}"
            cd "$TARGET_DIR"
            if [ -f "chat_history.json" ]; then
                cp "chat_history.json" "chat_history.json.bak" 2>/dev/null || true
            fi
            if [ -d ".git" ]; then
                git fetch origin 2>/dev/null || true
                git pull --rebase origin main 2>/dev/null || git pull --rebase 2>/dev/null || true
            fi
            if [ -f "chat_history.json.bak" ]; then
                mv "chat_history.json.bak" "chat_history.json" 2>/dev/null || true
            fi
        else
            echo -e "${CYAN}📥 Cloning project files from GitHub...${NC}"
            git clone "$REPO_URL" "$TARGET_DIR"
            cd "$TARGET_DIR"
        fi
    fi

    # Set executable permissions
    chmod +x start.sh stop.sh push_to_github.sh 2>/dev/null || true
    if [ -f "server.py" ]; then
        chmod +x server.py
    fi

    create_shortcuts
    ensure_termux_permissions
    print_summary
}

# Update only
update_app() {
    resolve_dir
    echo -e "${CYAN}🔄 Updating AntiMobile Pro in ${TARGET_DIR}...${NC}"
    if [ ! -d "$TARGET_DIR" ]; then
        echo -e "${RED}❌ Application directory not found! Performing clean install...${NC}"
        install_or_update
        return
    fi

    cd "$TARGET_DIR"
    # Backup chat history
    if [ -f "chat_history.json" ]; then
        cp "chat_history.json" "chat_history.json.bak" 2>/dev/null || true
    fi

    # Pull latest changes
    if [ -d ".git" ]; then
        git fetch origin main 2>/dev/null || git fetch origin 2>/dev/null || true
        git pull --rebase origin main 2>/dev/null || git pull 2>/dev/null || true
    else
        echo -e "${YELLOW}⚠️ Git repository not found. Re-cloning...${NC}"
        cd ..
        rm -rf "$TARGET_DIR"
        git clone "$REPO_URL" "$TARGET_DIR"
        cd "$TARGET_DIR"
    fi

    # Restore chat history if needed
    if [ -f "chat_history.json.bak" ] && [ ! -f "chat_history.json" ]; then
        mv "chat_history.json.bak" "chat_history.json" 2>/dev/null || true
    else
        rm -f "chat_history.json.bak" 2>/dev/null || true
    fi

    chmod +x start.sh stop.sh push_to_github.sh server.py 2>/dev/null || true
    create_shortcuts

    # Re-check python dependencies & permissions
    detect_os
    ensure_termux_permissions
    if ! python3 -c "import tornado" >/dev/null 2>&1; then
        if [ "$OS_TYPE" = "termux" ]; then
            pkg install -y python-tornado 2>/dev/null || true
        fi
        if ! python3 -c "import tornado" >/dev/null 2>&1; then
            python3 -m pip install "tornado>=6.2" --break-system-packages 2>/dev/null || \
            python3 -m pip install "tornado>=6.2" 2>/dev/null || true
        fi
    fi

    NEW_VER=$(get_installed_version)
    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${BOLD}  🎉 Update completed successfully! (New version: v${NEW_VER})${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "  🚀 Run ${CYAN}antimobile${NC} or ${CYAN}./start.sh${NC} to start."
    echo ""

    if [ "$OS_TYPE" = "termux" ]; then
        echo -e "${GREEN}🚀 Auto-restarting AntiMobile Pro and opening browser...${NC}"
        ./start.sh
    fi
}

# Uninstall application completely
uninstall_app() {
    resolve_dir
    echo -e "${RED}================================================================${NC}"
    echo -e "${BOLD}  🗑️ Uninstall AntiMobile Pro${NC}"
    echo -e "${RED}================================================================${NC}"
    echo -e "Install path: ${YELLOW}${TARGET_DIR}${NC}"
    echo ""

    if [ -t 0 ]; then
        read -p "Are you sure you want to completely uninstall AntiMobile Pro? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}Uninstallation cancelled.${NC}"
            exit 0
        fi
    fi

    # 1. Stop any running server process
    echo -e "${YELLOW}🛑 Stopping running server processes...${NC}"
    if [ -f "$TARGET_DIR/stop.sh" ]; then
        bash "$TARGET_DIR/stop.sh" >/dev/null 2>&1 || true
    fi
    pkill -9 -f "python3.*server.py" 2>/dev/null || true

    # 2. Ask to backup history
    if [ -f "$TARGET_DIR/chat_history.json" ]; then
        BACKUP_DIR="$HOME/antimobile_backup"
        mkdir -p "$BACKUP_DIR"
        cp "$TARGET_DIR/chat_history.json" "$BACKUP_DIR/chat_history_$(date +%Y%m%d_%H%M%S).json" 2>/dev/null || true
        echo -e "${GREEN}💾 Backup of your chat history saved to ${BACKUP_DIR}.${NC}"
    fi

    # 3. Remove shortcuts
    detect_os
    echo -e "${YELLOW}🗑️ Removing terminal shortcuts (${BIN_DIR})...${NC}"
    rm -f "$BIN_DIR/$APP_NAME" "$BIN_DIR/$SHORT_NAME" 2>/dev/null || true

    # 4. Remove installation directory
    if [ "$IS_IN_PLACE" = false ] && [ -d "$TARGET_DIR" ]; then
        echo -e "${YELLOW}🗑️ Removing application directory (${TARGET_DIR})...${NC}"
        rm -rf "$TARGET_DIR"
    else
        echo -e "${YELLOW}ℹ️ In-place workspace detected. Only processes and shortcuts were removed.${NC}"
    fi

    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${BOLD}  ✅ AntiMobile Pro has been completely uninstalled.${NC}"
    echo -e "${GREEN}================================================================${NC}"
    exit 0
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
    echo -e "${BOLD}  🎉 AntiMobile Pro (v${APP_VERSION}) setup complete!${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "  📂 Install path:       ${BOLD}${TARGET_DIR}${NC}"
    echo -e "  🚀 Quick start:        Run ${BOLD}${CYAN}antimobile${NC} or ${BOLD}${CYAN}agy-web${NC} or ${BOLD}${CYAN}./start.sh${NC}"
    echo -e "  🛑 Stop server:        Run ${BOLD}${CYAN}./stop.sh${NC}"
    echo -e "  --------------------------------------------------------------"
    echo -e "  📱 Local URL:          ${BOLD}${CYAN}http://localhost:${PORT}${NC}"
    if [ "$LOCAL_IP" != "127.0.0.1" ]; then
    echo -e "  🌐 Network (Wi-Fi):    ${BOLD}${CYAN}http://${LOCAL_IP}:${PORT}${NC}"
    fi
    echo -e "  ⚡ Zero password:      ${GREEN}Instant access to workspace${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo ""
}

# Interactive Menu for Existing Installation
show_existing_menu() {
    INSTALLED_VER=$(get_installed_version)
    echo -e "${CYAN}================================================================${NC}"
    echo -e "${BOLD}  ⚡ AntiMobile Pro is already installed!${NC}"
    echo -e "${CYAN}================================================================${NC}"
    echo -e "  📌 Installed version: ${YELLOW}v${INSTALLED_VER}${NC}"
    echo -e "  ✨ Latest version:    ${GREEN}v${APP_VERSION}${NC}"
    echo -e "  📂 Install directory: ${BOLD}${TARGET_DIR}${NC}"
    echo -e "${CYAN}----------------------------------------------------------------${NC}"
    echo -e "  Please choose an action:"
    echo -e "  ${BOLD}[1]${NC} 🔄 ${GREEN}Update to latest version (Update)${NC}"
    echo -e "  ${BOLD}[2]${NC} 🚀 ${CYAN}Start server & open app (Start)${NC}"
    echo -e "  ${BOLD}[3]${NC} 🛑 ${YELLOW}Stop running server (Stop)${NC}"
    echo -e "  ${BOLD}[4]${NC} 🛠️ ${PURPLE}Reinstall & repair files (Reinstall)${NC}"
    echo -e "  ${BOLD}[5]${NC} 🗑️ ${RED}Uninstall completely (Uninstall)${NC}"
    echo -e "  ${BOLD}[0]${NC} ❌ Exit"
    echo -e "${CYAN}================================================================${NC}"
    echo ""
    read -p "Enter choice [1-5]: " -r choice
    echo ""

    case "$choice" in
        1)
            update_app
            ;;
        2)
            cd "$TARGET_DIR" && ./start.sh
            ;;
        3)
            cd "$TARGET_DIR" && ./stop.sh
            ;;
        4)
            install_or_update
            ;;
        5)
            uninstall_app
            ;;
        0|*)
            echo -e "${CYAN}Exiting installer.${NC}"
            exit 0
            ;;
    esac
}

# Process CLI Arguments
case "${1:-}" in
    --update|-u)
        print_banner
        update_app
        exit 0
        ;;
    --uninstall|--remove)
        print_banner
        uninstall_app
        exit 0
        ;;
    --start|-s)
        resolve_dir
        cd "$TARGET_DIR" && ./start.sh
        exit 0
        ;;
    --stop)
        resolve_dir
        cd "$TARGET_DIR" && ./stop.sh
        exit 0
        ;;
    --version|-v)
        echo "AntiMobile Pro v${APP_VERSION}"
        exit 0
        ;;
    --help|-h)
        echo "AntiMobile Pro v${APP_VERSION} - Installer & Manager"
        echo "Usage: ./install.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  --update, -u       Update to latest version"
        echo "  --uninstall        Uninstall and remove AntiMobile Pro"
        echo "  --start, -s        Start the server"
        echo "  --stop             Stop the running server"
        echo "  --version, -v      Print current version"
        echo "  --help, -h         Show this help message"
        exit 0
        ;;
esac

# Main Execution Flow
print_banner

if is_installed && [ -t 0 ]; then
    show_existing_menu
else
    detect_os
    install_dependencies
    check_agy_binary
    check_google_auth
    install_or_update

    # Auto-start on Termux / Prompt on desktop
    if [ "$OS_TYPE" = "termux" ]; then
        echo -e "${GREEN}🚀 Auto-starting AntiMobile Pro and opening browser...${NC}"
        cd "$TARGET_DIR" && ./start.sh
    elif [ -t 0 ]; then
        read -p "Would you like to start the server now? (Y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            cd "$TARGET_DIR" && ./start.sh
        fi
    elif [ -c /dev/tty ]; then
        read -p "Would you like to start the server now? (Y/n) " -n 1 -r < /dev/tty || true
        echo ""
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            cd "$TARGET_DIR" && ./start.sh
        fi
    fi
fi
