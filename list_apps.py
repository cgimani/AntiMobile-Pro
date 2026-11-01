#!/usr/bin/env python3
"""
Android Background Process & App Inspector
Detects background applications and services depending on permission level.
"""

import subprocess
import shutil
import os
import sys

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        return res.stdout.strip()
    except Exception as e:
        return ""

def check_permission_level():
    # Check root
    if shutil.which("su"):
        test_root = run_cmd("su -c id 2>/dev/null")
        if "uid=0" in test_root:
            return "ROOT", "su -c"
    
    # Check rish (Shizuku)
    if shutil.which("rish"):
        test_rish = run_cmd("rish -c id 2>/dev/null")
        if "uid=2000" in test_rish or "uid=0" in test_rish:
            return "SHIZUKU", "rish -c"

    # Check local adb
    if shutil.which("adb"):
        test_adb = run_cmd("adb shell id 2>/dev/null")
        if "uid=2000" in test_adb or "uid=0" in test_adb:
            return "ADB", "adb shell"

    return "SANDBOX", None

def get_sandbox_processes():
    out = run_cmd("ps -eo pid,user,comm,args")
    lines = out.splitlines()
    procs = []
    for line in lines[1:]:
        parts = line.split(None, 3)
        if len(parts) >= 4:
            procs.append({
                "pid": parts[0],
                "user": parts[1],
                "comm": parts[2],
                "cmd": parts[3]
            })
    return procs

def get_android_apps(prefix):
    cmd = f'{prefix} "dumpsys activity processes | grep -E \'PID #|ProcessRecord\'"'
    out = run_cmd(cmd)
    if not out:
        # Fallback to ps -A
        cmd = f'{prefix} "ps -A -o PID,NAME"'
        out = run_cmd(cmd)
    return out

def main():
    print("=" * 55)
    print(" 🔍 برسی و شناسایی برنامه‌های پس‌زمینه (Background Apps)")
    print("=" * 55)

    mode, prefix = check_permission_level()
    print(f"سطح دسترسی فعلی محیط: [{mode}]")

    if mode in ["ROOT", "SHIZUKU", "ADB"]:
        print(f"دسترسی سیستمی برقرار است. در حال دریافت لیست برنامه‌های فعال گوشی...")
        apps_raw = get_android_apps(prefix)
        print(apps_raw[:2000] if apps_raw else "برنامه‌ای یافت نشد.")
    else:
        print("\n⚠️ محدودیت امنیتی اندروید (SELinux / App Sandboxing):")
        print("در نسخه‌های مدرن اندروید، هر برنامه (از جمله Termux) در یک کاربر ایزوله اجرا می‌شود.")
        print("برنامه‌های عادی اجازه خواندن پروسه‌های سایر اپلیکیشن‌ها را ندارند.\n")
        
        print("📋 پروسه‌های پس‌زمینه فعال در محیط کاربری فعلی (Termux):")
        procs = get_sandbox_processes()
        for p in procs:
            print(f" • PID: {p['pid']:<6} | {p['comm']:<15} | {p['cmd']}")

if __name__ == "__main__":
    main()
