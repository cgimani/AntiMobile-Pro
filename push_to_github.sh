#!/usr/bin/env bash
# ==============================================================================
# 🚀 AntiMobile Pro - Smart GitHub Publisher & Sync Script
# Target: https://github.com/cgimani/AntiMobile-Pro.git
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
NC='\033[0m'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

SSH_REPO="git@github.com:cgimani/AntiMobile-Pro.git"
HTTPS_REPO="https://github.com/cgimani/AntiMobile-Pro.git"

echo -e "${PURPLE}================================================================${NC}"
echo -e "${BOLD}  ⚡ AntiMobile Pro - اسکریپت هوشمند انتشار و همگام‌سازی با گیت‌هاب${NC}"
echo -e "${PURPLE}================================================================${NC}"
echo ""

# 1. Privacy & Security Sanity Check
echo -e "${BLUE}🔍 مرحله ۱: بررسی و ممیزی داده‌های شخصی و حساس...${NC}"

SENSITIVE_FILES=("chat_history.json" "auth_config.json" "server.log" ".env")
for f in "${SENSITIVE_FILES[@]}"; do
    if [ -f "$DIR/$f" ]; then
        echo -e "${YELLOW}   ⚠️ فایل حساس یافت شد: $f - در حال بررسی وضعیت در گیت...${NC}"
        # Make sure it's untracked
        git rm --cached "$f" 2>/dev/null || true
    fi
done

# Clean any macOS .DS_Store
find "$DIR" -name ".DS_Store" -delete 2>/dev/null || true
find "$DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo -e "${GREEN}✅ بررسی داده‌های شخصی انجام شد (هیچ دیتای حساسی در مخزن قرار نخواهد گرفت).${NC}"

# 2. Configure Git Repository & Branch
echo -e "${BLUE}🔧 مرحله ۲: پیکربندی شاخه اصلی و مشخصات متعهد (Committer)...${NC}"

if [ ! -d ".git" ]; then
    echo -e "${CYAN}   در حال راه‌اندازی مخزن گیت...${NC}"
    git init -b main
else
    # Ensure on main branch
    git branch -M main 2>/dev/null || true
fi

# Set sanitized author if not already configured
CURRENT_NAME=$(git config user.name || true)
CURRENT_EMAIL=$(git config user.email || true)

if [ -z "$CURRENT_NAME" ] || [[ "$CURRENT_EMAIL" == *".local"* ]] || [[ "$CURRENT_EMAIL" == *"localhost"* ]]; then
    echo -e "${YELLOW}   مشخصات محلی ناشناس تشخیص داده شد. تنظیم مؤلف رسمی: cgimani${NC}"
    git config user.name "cgimani"
    git config user.email "cgimani@users.noreply.github.com"
fi

# Set remote origin (prefer HTTPS if configured or fallback to SSH)
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || true)
if [ -z "$CURRENT_REMOTE" ]; then
    git remote add origin "$HTTPS_REPO"
fi

# Stage all files
git add -A

# Check if there is anything to commit
if git diff --staged --quiet; then
    echo -e "${YELLOW}ℹ️ تغییری برای ثبت کامیت جدید وجود ندارد.${NC}"
else
    COMMIT_MSG="${1:-feat(v3.1.0): smart installer with update/uninstall support, semantic versioning, and live CLI streaming}"
    echo -e "${CYAN}💾 در حال ثبت کامیت با پیام: '${COMMIT_MSG}'${NC}"
    git commit -m "$COMMIT_MSG"
fi

# 3. Test GitHub Push
echo -e "${BLUE}🔐 مرحله ۳: ارسال تغییرات به گیت‌هاب (Push)...${NC}"

# First attempt: Try pushing directly via current configured remote (HTTPS with Keychain or SSH)
if git push origin main 2>/dev/null; then
    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${BOLD}  🎉 پروژه AntiMobile Pro با موفقیت در گیت‌هاب بروزرسانی شد!${NC}"
    echo -e "  🔗 لینک مخزن: ${CYAN}https://github.com/cgimani/AntiMobile-Pro${NC}"
    echo -e "${GREEN}================================================================${NC}"
    exit 0
fi

# If direct push failed, test SSH
SSH_SUCCESS=false
SSH_KEY_FILE="$HOME/.ssh/id_ed25519"

# Test SSH connection with github.com
if ssh -i "$SSH_KEY_FILE" -o BatchMode=yes -o ConnectTimeout=6 -T git@github.com 2>&1 | grep -E -q "successfully authenticated|Hi cgimani"; then
    SSH_SUCCESS=true
fi

if [ "$SSH_SUCCESS" = true ]; then
    echo -e "${GREEN}✅ احراز هویت SSH با موفقیت تایید شد.${NC}"
    echo -e "${CYAN}🚀 در حال ارسال پروژه به گیت‌هاب (git push -u origin main)...${NC}"
    git push -u origin main
    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${BOLD}  🎉 پروژه AntiMobile Pro با موفقیت در گیت‌هاب منتشر گردید!${NC}"
    echo -e "  🔗 لینک مخزن: ${CYAN}https://github.com/cgimani/AntiMobile-Pro${NC}"
    echo -e "${GREEN}================================================================${NC}"
    exit 0
fi

# If SSH failed, provide smart diagnostics and options
echo -e "${YELLOW}⚠️ کلید SSH شما هنوز در حساب گیت‌هاب ثبت نشده یا اجازه دسترسی مستقیم ندارد.${NC}"

if [ -f "${SSH_KEY_FILE}.pub" ]; then
    PUB_KEY=$(cat "${SSH_KEY_FILE}.pub")
    echo ""
    echo -e "${PURPLE}----------------------------------------------------------------${NC}"
    echo -e "${BOLD}🔑 کلید عمومی SSH سیستم شما:${NC}"
    echo -e "${CYAN}${PUB_KEY}${NC}"
    echo -e "${PURPLE}----------------------------------------------------------------${NC}"
    echo -e "👉 برای فعال‌سازی کافی است مراحل زیر را انجام دهید:"
    echo -e "   ۱. وارد لینک شوید: ${CYAN}https://github.com/settings/ssh/new${NC}"
    echo -e "   ۲. کلید بالا را در کادر Key قرار دهید و دکمه ${BOLD}Add SSH key${NC} را بزنید."
    echo -e "${PURPLE}----------------------------------------------------------------${NC}"
fi

echo ""
echo -e "${BOLD}روش‌های ادامه:${NC}"
echo "  [1] تلاش مجدد با SSH (بعد از افزودن کلید به گیت‌هاب)"
echo "  [2] ارسال از طریق توکن شخصی گیت‌هاب (Personal Access Token / HTTPS)"
echo "  [3] خروج"
echo ""

if [ -t 0 ]; then
    read -p "لطفاً یک گزینه را انتخاب کنید [1/2/3]: " -n 1 -r CHOICE
    echo ""
    case "$CHOICE" in
        1)
            echo -e "${CYAN}🔄 در حال تست مجدد ارتباط SSH...${NC}"
            if ssh -i "$SSH_KEY_FILE" -o ConnectTimeout=8 -T git@github.com 2>&1 | grep -E -q "successfully authenticated|Hi cgimani"; then
                echo -e "${GREEN}✅ احراز هویت تایید شد! در حال ارسال...${NC}"
                git push -u origin main
                echo -e "${GREEN}🎉 با موفقیت ارسال شد!${NC}"
            else
                echo -e "${RED}❌ هنوز دسترسی SSH تایید نشده است. لطفاً کلید بالا را به تنظیمات گیت‌هاب اضافه کنید.${NC}"
            fi
            ;;
        2)
            echo -e "${CYAN}🔑 لطفاً توکن دسترسی شخصی گیت‌هاب (PAT) با مجوز repo را وارد کنید:${NC}"
            read -s -p "Token: " GH_TOKEN
            echo ""
            if [ -n "$GH_TOKEN" ]; then
                git remote set-url origin "https://cgimani:${GH_TOKEN}@github.com/cgimani/AntiMobile-Pro.git"
                echo -e "${CYAN}🚀 در حال ارسال با توکن HTTPS...${NC}"
                git push -u origin main
                # Reset URL back to clean remote so token is not stored in git config
                git remote set-url origin "$HTTPS_REPO"
                echo -e "${GREEN}🎉 با موفقیت ارسال شد!${NC}"
            else
                echo -e "${RED}❌ توکنی وارد نشد.${NC}"
            fi
            ;;
        *)
            echo "عملیات متوقف شد."
            ;;
    esac
else
    echo -e "${YELLOW}اجرا در محیط غیرتعاملی. برای پوش دستی، دستور زیر را اجرا کنید:${NC}"
    echo "  git push -u origin main"
fi
