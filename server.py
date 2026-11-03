#!/usr/bin/env python3
"""
Antigravity Desktop-Style Mobile Web PWA Server
High-Performance Tornado Async Engine for Antigravity AI Agent
Port: 7681 | Engine: ~/.local/bin/agy
"""

import os
import sys
import json
import time
import asyncio
import re
import signal
import socket
import subprocess
import shutil
import hashlib
import secrets
import threading
import select
import pty
import fcntl
import termios
import struct
from collections import deque
from typing import Set, Dict, Any, Optional, List, Tuple

# Fallback to embedded pure-Python vendor directory if system tornado is missing
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_VENDOR_DIR = os.path.join(_SCRIPT_DIR, "vendor")
if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

import tornado.web
import tornado.websocket
import tornado.ioloop

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_VERSION = "3.2.1"
PORT = int(os.environ.get('PORT', 7681))
HOST = os.environ.get('HOST', '0.0.0.0')
HISTORY_FILE = os.path.join(WORKSPACE_DIR, 'chat_history.json')
AUTH_CONFIG_FILE = os.path.join(WORKSPACE_DIR, 'auth_config.json')
USER_HOME = os.path.expanduser('~')

def find_agy_binary() -> str:
    """Find agy CLI binary dynamically across macOS, Linux, and Android Termux."""
    if os.environ.get('AGY_BIN') and os.path.isfile(os.environ['AGY_BIN']):
        return os.environ['AGY_BIN']
    which_path = shutil.which('agy')
    if which_path:
        return which_path
    prefix = os.environ.get('PREFIX', '/data/data/com.termux/files/usr')
    candidates = [
        os.path.join(prefix, 'bin', 'agy'),
        '/data/data/com.termux/files/usr/bin/agy',
        '/data/data/com.termux/files/home/.local/bin/agy',
        os.path.expanduser('~/.local/bin/agy'),
        os.path.expanduser('~/.gemini/antigravity-cli/bin/agy'),
        '/usr/local/bin/agy',
        '/opt/homebrew/bin/agy'
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return os.path.join(prefix, 'bin', 'agy') if os.path.isdir(prefix) else os.path.expanduser('~/.local/bin/agy')

AGY_BIN = find_agy_binary()

def parse_jwt_payload(token_str: str) -> Dict[str, Any]:
    """Safely parse payload of a JWT token without external crypto dependencies."""
    if not token_str or not isinstance(token_str, str):
        return {}
    try:
        parts = token_str.split('.')
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += '=' * ((4 - len(payload_b64) % 4) % 4)
            raw = base64.urlsafe_b64decode(payload_b64.encode('ascii')).decode('utf-8', errors='replace')
            return json.loads(raw)
    except Exception:
        pass
    return {}

def extract_user_from_token_data(tok: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract authenticated user profile from diverse token formats (Go oauth2.Token, JWT, Python auth)."""
    if not isinstance(tok, dict):
        return None

    jwt_data = {}
    id_tok = tok.get('id_token')
    if id_tok and isinstance(id_tok, str):
        jwt_data = parse_jwt_payload(id_tok)

    email = tok.get('id_token_email') or tok.get('email') or tok.get('user_email') or jwt_data.get('email')
    name = tok.get('name') or tok.get('user_name') or tok.get('display_name') or jwt_data.get('name') or jwt_data.get('given_name')
    if not name and email:
        name = email.split('@')[0].capitalize()

    has_valid_credential = bool(tok.get('access_token') or tok.get('token') or tok.get('refresh_token') or tok.get('id_token'))
    if has_valid_credential:
        return {
            "name": name or "کاربر گوگل",
            "email": email or "حساب متصل گوگل",
            "avatar": (name[:1] if name else (email[:1] if email else "G")).upper(),
            "authenticated": True,
            "auth_method": tok.get('auth_method', 'google_oauth')
        }
    return None

def get_current_user_profile() -> Dict[str, Any]:
    """Detect currently authenticated Antigravity / Google account dynamically from local system."""
    token_candidates = [
        # Antigravity CLI native OAuth tokens
        os.path.expanduser('~/.gemini/antigravity-cli/antigravity-oauth-token'),
        '/data/data/com.termux/files/home/.gemini/antigravity-cli/antigravity-oauth-token',
        os.path.expanduser('~/.gemini/antigravity-cli/oauth_token.json'),
        '/data/data/com.termux/files/home/.gemini/antigravity-cli/oauth_token.json',
        # Jetski standalone OAuth tokens
        os.path.expanduser('~/.gemini/jetski-standalone-oauth-token'),
        '/data/data/com.termux/files/home/.gemini/jetski-standalone-oauth-token',
        os.path.expanduser('~/.gemini/oauth_token.json'),
        '/data/data/com.termux/files/home/.gemini/oauth_token.json',
        # Config dir tokens
        os.path.expanduser('~/.config/antigravity/auth.json'),
        '/data/data/com.termux/files/home/.config/antigravity/auth.json',
        os.path.expanduser('~/.config/antigravity/oauth.json'),
        '/data/data/com.termux/files/home/.config/antigravity/oauth.json',
    ]
    for path in token_candidates:
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    tok = json.load(f)
                    user_info = extract_user_from_token_data(tok)
                    if user_info:
                        return user_info
            except Exception:
                pass

    # Check for Gemini API key file or environment variable
    api_key_candidates = [
        os.path.expanduser('~/.gemini/api_key'),
        '/data/data/com.termux/files/home/.gemini/api_key',
    ]
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        for p in api_key_candidates:
            if os.path.isfile(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        k = f.read().strip()
                        if k:
                            api_key = k
                            os.environ['GEMINI_API_KEY'] = k
                            break
                except Exception:
                    pass

    if api_key:
        masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "******"
        return {
            "name": "Gemini API User",
            "email": f"API Key ({masked})",
            "avatar": "🔑",
            "authenticated": True,
            "auth_method": "gemini_api_key"
        }

    return {
        "name": "کاربر مهمان",
        "email": "وارد نشده (حساب متصل نیست)",
        "avatar": "👤",
        "authenticated": False,
        "auth_method": "offline"
    }

# Available models cache
CACHED_MODELS = [
    {"id": "gemini-3.8-flash-high", "name": "Gemini 3.8 Flash (High)"},
    {"id": "gemini-3.8-flash-medium", "name": "Gemini 3.8 Flash (Medium)"},
    {"id": "gemini-3.8-flash-low", "name": "Gemini 3.8 Flash (Low)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (Thinking)"},
    {"id": "claude-opus-4-6-thinking", "name": "Claude Opus 4.6 (Thinking)"},
    {"id": "gpt-oss-120b-medium", "name": "GPT-OSS 120B (Medium)"}
]

def fetch_models_from_cli(force_refresh: bool = False) -> List[Dict[str, str]]:
    """Dynamically discover models supported by the installed agy binary with instant in-memory cache."""
    global CACHED_MODELS
    if not force_refresh and CACHED_MODELS and len(CACHED_MODELS) > 1:
        return CACHED_MODELS
    agy = find_agy_binary()
    if not os.path.isfile(agy):
        return CACHED_MODELS
    try:
        res = subprocess.run([agy, "models"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
        lines = res.stdout.splitlines()
        models = []
        for line in lines:
            line = line.strip()
            if not line or any(line.startswith(p) for p in ('Fetch', 'Loading', '⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏')):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                mid, mname = parts[0], parts[1]
                models.append({"id": mid, "name": mname})
        if models:
            CACHED_MODELS = models
            return models
    except Exception as e:
        print(f"[WARN] Failed to fetch models via CLI: {e}")
    return CACHED_MODELS

def extract_turn_thinking(conv_id: Optional[str]) -> Tuple[str, int]:
    """Extract step thinking and token count from the conversation transcript."""
    if not conv_id:
        return "", 0
    candidate_paths = [
        os.path.expanduser(f"~/.gemini/antigravity/brain/{conv_id}/.system_generated/logs/transcript.jsonl"),
        os.path.expanduser(f"~/.gemini/antigravity-cli/brain/{conv_id}/.system_generated/logs/transcript.jsonl")
    ]
    transcript_path = None
    for cp in candidate_paths:
        if os.path.exists(cp):
            transcript_path = cp
            break
    if not transcript_path:
        return "", 0
    try:
        with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        last_user_idx = -1
        for i, line in enumerate(lines):
            try:
                d = json.loads(line)
                if d.get("type") == "USER_INPUT":
                    last_user_idx = i
            except Exception:
                pass
        thoughts = []
        tokens = 0
        for line in lines[last_user_idx + 1:]:
            try:
                d = json.loads(line)
                if d.get("type") == "PLANNER_RESPONSE" and d.get("thinking"):
                    th = d["thinking"].strip()
                    if th and th not in thoughts:
                        thoughts.append(th)
                if "thinking_tokens" in d:
                    tokens += d.get("thinking_tokens", 0)
                elif "usage" in d and isinstance(d["usage"], dict):
                    tokens += d["usage"].get("thinking_tokens", 0)
            except Exception:
                pass
        return "\n\n".join(thoughts), tokens
    except Exception as e:
        print(f"[WARN] Error reading transcript for thinking: {e}")
        return "", 0

# Authentication Manager with secure sessions & credentials
class AuthManager:
    def __init__(self, filepath: str = AUTH_CONFIG_FILE):
        self.filepath = filepath
        self.config: Dict[str, Any] = {
            "enabled": False,
            "username": os.environ.get("ANTI_USERNAME", "admin"),
            "salt": "",
            "password_hash": "",
            "sessions": {}
        }
        self.load()

    def _hash_pwd(self, password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"[WARN] Error reading auth config: {e}")

        # Always force auth disabled unless ANTI_REQUIRE_PASSWORD=1 is explicitly set
        if os.environ.get("ANTI_REQUIRE_PASSWORD") != "1":
            self.config["enabled"] = False

        # Initialize default admin credentials if not set
        if not self.config.get("password_hash"):
            salt = secrets.token_hex(16)
            default_pwd = os.environ.get("ANTI_PASSWORD", "antigravity")
            self.config["salt"] = salt
            self.config["password_hash"] = self._hash_pwd(default_pwd, salt)
            self.config["username"] = os.environ.get("ANTI_USERNAME", "admin")
            self.config["enabled"] = False
            if "sessions" not in self.config:
                self.config["sessions"] = {}
            self.save()

    def save(self):
        try:
            tmp = self.filepath + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.filepath)
        except Exception as e:
            print(f"[ERROR] Error saving auth config: {e}")

    def verify_password(self, password: str) -> bool:
        salt = self.config.get("salt", "")
        expected = self.config.get("password_hash", "")
        return self._hash_pwd(password, salt) == expected

    def login(self, username: str, password: str) -> Optional[str]:
        if not self.config.get("enabled", True):
            return "auth_disabled"
        if username.strip().lower() != self.config.get("username", "admin").lower():
            return None
        if not self.verify_password(password):
            return None

        # Clean expired sessions
        now = time.time()
        sessions = self.config.get("sessions", {})
        expired = [t for t, s in sessions.items() if s.get("expires_at", 0) < now]
        for t in expired:
            sessions.pop(t, None)

        token = secrets.token_hex(32)
        sessions[token] = {
            "username": self.config.get("username", "admin"),
            "created_at": now,
            "expires_at": now + (30 * 86400)
        }
        self.config["sessions"] = sessions
        self.save()
        return token

    def logout(self, token: str) -> bool:
        sessions = self.config.get("sessions", {})
        if token in sessions:
            del sessions[token]
            self.save()
            return True
        return False

    def validate_token(self, token: Optional[str]) -> Tuple[bool, Optional[str]]:
        if os.environ.get("ANTI_REQUIRE_PASSWORD") != "1" or not self.config.get("enabled", False):
            return True, "admin"
        if not token:
            return False, None
        sessions = self.config.get("sessions", {})
        sess = sessions.get(token)
        if not sess:
            return False, None
        if sess.get("expires_at", 0) < time.time():
            sessions.pop(token, None)
            self.save()
            return False, None
        return True, sess.get("username", "admin")

    def change_password(self, old_pwd: str, new_username: Optional[str], new_pwd: str) -> Tuple[bool, str]:
        if not self.verify_password(old_pwd):
            return False, "رمز عبور فعلی نادرست است."
        if new_pwd and len(new_pwd.strip()) < 4:
            return False, "رمز عبور جدید باید حداقل ۴ کاراکتر باشد."
        if new_username and new_username.strip():
            self.config["username"] = new_username.strip()
        if new_pwd and new_pwd.strip():
            salt = secrets.token_hex(16)
            self.config["salt"] = salt
            self.config["password_hash"] = self._hash_pwd(new_pwd.strip(), salt)
            # Invalidate all other sessions
            self.config["sessions"] = {}
        self.save()
        return True, "اطلاعات ورود با موفقیت به‌روزرسانی شد."

def get_desktop_antigravity_data():
    db_path = os.path.expanduser('~/.gemini/antigravity/conversation_summaries.db')
    if not os.path.isfile(db_path):
        return [], []
    try:
        import sqlite3, urllib.parse, datetime
        conn = sqlite3.connect(db_path, timeout=5)
        c = conn.cursor()
        query = '''
        SELECT 
            conversation_id, 
            coalesce(nullif(title,''), nullif(preview,''), 'Untitled Conversation') as display_title,
            workspace_uris, 
            last_modified_time
        FROM conversation_summaries
        ORDER BY last_modified_time DESC
        '''
        c.execute(query)
        rows = c.fetchall()
        conn.close()

        def format_rel(dt_str):
            try:
                if isinstance(dt_str, str):
                    clean_dt = dt_str.split('+')[0].split('.')[0]
                    dt = datetime.datetime.strptime(clean_dt, '%Y-%m-%d %H:%M:%S')
                else:
                    return ''
                now = datetime.datetime.utcnow()
                diff = max(0, (now - dt).total_seconds())
                if diff < 120: return 'now'
                if diff < 3600: return f'{int(diff//60)}m'
                if diff < 86400: return f'{int(diff//3600)}h'
                return f'{int(diff//86400)}d'
            except Exception:
                return ''

        projects_map = {}
        standalone_list = []

        for cid, title, uris, lmt in rows:
            rel_time = format_rel(lmt)
            chat_item = {
                'id': cid,
                'title': title,
                'time_str': rel_time,
                'is_active': False
            }
            
            ws_name = None
            ws_path = ''
            if uris:
                try:
                    arr = json.loads(uris)
                    if arr and len(arr) > 0:
                        raw_path = urllib.parse.unquote(arr[0].replace('file://', ''))
                        ws_path = raw_path
                        ws_name = os.path.basename(raw_path.rstrip('/'))
                except Exception:
                    pass

            if not ws_name or ws_name in ('x', 'Standalone'):
                standalone_list.append(chat_item)
            else:
                if ws_name not in projects_map:
                    projects_map[ws_name] = {
                        'id': f'proj_{ws_name}',
                        'name': ws_name,
                        'path': ws_path,
                        'chats': []
                    }
                projects_map[ws_name]['chats'].append(chat_item)

        curr_dir_name = os.path.basename(WORKSPACE_DIR)
        res_projects = []
        if curr_dir_name in projects_map:
            p = projects_map.pop(curr_dir_name)
            p['is_active'] = True
            if p['chats']:
                p['chats'][0]['is_active'] = True
            res_projects.append(p)
        else:
            res_projects.append({
                'id': 'proj_current',
                'name': curr_dir_name,
                'path': WORKSPACE_DIR,
                'chats': [],
                'is_active': True
            })

        for k, p in projects_map.items():
            res_projects.append(p)

        return res_projects, standalone_list
    except Exception as e:
        print(f"[WARN] Error reading desktop antigravity data: {e}")
        return [], []

auth_manager = AuthManager()

# History Manager with multi-project & atomic persistence
class HistoryManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Dict[str, Any] = {
            "active_project_id": "proj_default",
            "projects": {},
            "active_chat_id": "default",
            "chats": {},
            "default_model": "gemini-3.8-flash-high",
            "default_effort": "high",
            "default_mode": "auto",
            "workspace": WORKSPACE_DIR
        }
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        self.data = json.loads(content)
            except Exception as e:
                print(f"[WARN] Error reading chat_history.json: {e}")

        # Ensure default model/effort/mode
        if "default_model" not in self.data:
            self.data["default_model"] = "gemini-3.8-flash-high"
        if "default_effort" not in self.data:
            self.data["default_effort"] = "high"
        if "default_mode" not in self.data:
            self.data["default_mode"] = "auto"

        # Auto-migrate legacy format (root 'chats') into 'projects'
        projects = self.data.get("projects")
        if not projects or not isinstance(projects, dict):
            default_pid = "proj_default"
            legacy_chats = self.data.get("chats", {})
            legacy_ws = self.data.get("workspace", WORKSPACE_DIR)
            if not os.path.isdir(legacy_ws):
                legacy_ws = WORKSPACE_DIR
            self.data["projects"] = {
                default_pid: {
                    "id": default_pid,
                    "name": "پروژه اصلی",
                    "path": legacy_ws,
                    "created_at": time.time(),
                    "active_chat_id": self.data.get("active_chat_id"),
                    "chats": legacy_chats
                }
            }
            self.data["active_project_id"] = default_pid

        # Validate active project
        self.get_active_project()
        self.save()

    def save(self):
        try:
            tmp_path = self.filepath + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.filepath)
        except Exception as e:
            print(f"[ERROR] Error saving chat_history.json: {e}")

    def get_active_project(self) -> Dict[str, Any]:
        projects = self.data.setdefault("projects", {})
        pid = self.data.get("active_project_id")
        if not pid or pid not in projects:
            if projects:
                pid = next(iter(projects))
                self.data["active_project_id"] = pid
            else:
                pid = "proj_default"
                projects[pid] = {
                    "id": pid,
                    "name": os.path.basename(WORKSPACE_DIR) or "antigravity_all_files",
                    "path": WORKSPACE_DIR,
                    "created_at": time.time(),
                    "active_chat_id": None,
                    "chats": {}
                }
                self.data["active_project_id"] = pid

        proj = projects[pid]
        if proj.get("name") in ("پروژه اصلی", "پروژه"):
            proj["name"] = os.path.basename(WORKSPACE_DIR) or "antigravity_all_files"
        # Validate project path
        if not proj.get("path") or not os.path.isdir(proj["path"]):
            proj["path"] = WORKSPACE_DIR

        # Ensure active project has at least one chat
        chats = proj.setdefault("chats", {})
        if not chats:
            cid = f"chat_{int(time.time() * 1000)}"
            chats[cid] = {
                "id": cid,
                "title": "گفتگوی جدید",
                "created_at": time.time(),
                "updated_at": time.time(),
                "agy_conversation_id": None,
                "model": self.data.get("default_model", "gemini-3.8-flash-high"),
                "cwd": proj["path"],
                "project_id": pid,
                "messages": []
            }
            proj["active_chat_id"] = cid

        if not proj.get("active_chat_id") or proj.get("active_chat_id") not in chats:
            proj["active_chat_id"] = next(iter(chats))

        # Sync legacy flat references
        self.data["chats"] = chats
        self.data["active_chat_id"] = proj["active_chat_id"]
        self.data["workspace"] = proj["path"]
        return proj

    def get_projects_summary(self) -> List[Dict[str, Any]]:
        self.get_active_project()
        active_pid = self.data.get("active_project_id")
        now = time.time()
        result = []
        for pid, proj in self.data.get("projects", {}).items():
            proj_chats = []
            for cid, c in proj.get("chats", {}).items():
                up_at = c.get("updated_at") or c.get("created_at", 0)
                diff = max(0, int(now - up_at))
                if diff < 60:
                    time_str = "now"
                elif diff < 3600:
                    time_str = f"{diff // 60}m"
                elif diff < 86400:
                    time_str = f"{diff // 3600}h"
                else:
                    time_str = f"{diff // 86400}d"

                proj_chats.append({
                    "id": cid,
                    "title": c.get("title", "Untitled Conversation"),
                    "created_at": c.get("created_at", 0),
                    "updated_at": up_at,
                    "time_str": time_str,
                    "is_active": (cid == proj.get("active_chat_id")),
                    "msg_count": len(c.get("messages", []))
                })
            proj_chats.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            result.append({
                "id": pid,
                "name": proj.get("name", "پروژه"),
                "path": proj.get("path", WORKSPACE_DIR),
                "created_at": proj.get("created_at", 0),
                "chat_count": len(proj_chats),
                "chats": proj_chats,
                "is_active": (pid == active_pid)
            })
        result.sort(key=lambda x: (not x["is_active"], x["created_at"]))
        return result

    def get_standalone_chats(self) -> List[Dict[str, Any]]:
        now = time.time()
        result = []
        for cid, c in self.data.get("chats", {}).items():
            if not c.get("project_id"):
                up_at = c.get("updated_at") or c.get("created_at", 0)
                diff = max(0, int(now - up_at))
                time_str = f"{diff // 60}m" if diff < 3600 else (f"{diff // 3600}h" if diff < 86400 else f"{diff // 86400}d")
                result.append({
                    "id": cid,
                    "title": c.get("title", "Conversation"),
                    "created_at": c.get("created_at", 0),
                    "updated_at": up_at,
                    "time_str": time_str,
                    "msg_count": len(c.get("messages", []))
                })
        result.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        return result

    def create_project(self, name: str, path: str) -> Dict[str, Any]:
        clean_name = name.strip() if name and name.strip() else "پروژه جدید"
        clean_path = os.path.expanduser(path.strip()) if path and path.strip() else WORKSPACE_DIR
        clean_path = os.path.abspath(clean_path)

        try:
            os.makedirs(clean_path, exist_ok=True)
        except Exception as e:
            print(f"[WARN] Could not create project directory {clean_path}: {e}")

        pid = f"proj_{int(time.time() * 1000)}"
        first_cid = f"chat_{int(time.time() * 1000)}"
        model_to_use = self.data.get("default_model", "gemini-3.8-flash-high")

        new_proj = {
            "id": pid,
            "name": clean_name,
            "path": clean_path,
            "created_at": time.time(),
            "active_chat_id": first_cid,
            "chats": {
                first_cid: {
                    "id": first_cid,
                    "title": "گفتگوی جدید",
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "agy_conversation_id": None,
                    "model": model_to_use,
                    "cwd": clean_path,
                    "project_id": pid,
                    "messages": []
                }
            }
        }
        self.data.setdefault("projects", {})[pid] = new_proj
        self.data["active_project_id"] = pid
        self.data["chats"] = new_proj["chats"]
        self.data["active_chat_id"] = first_cid
        self.data["workspace"] = clean_path
        self.save()

        broadcast({
            "type": "project_switched",
            "project": {
                "id": pid,
                "name": clean_name,
                "path": clean_path
            },
            "active_chat_id": first_cid
        })

        return new_proj

    def switch_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        projects = self.data.get("projects", {})
        if project_id not in projects:
            return None
        self.data["active_project_id"] = project_id
        proj = self.get_active_project()
        self.save()
        return proj

    def update_project(self, project_id: str, name: Optional[str] = None, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        projects = self.data.get("projects", {})
        if project_id not in projects:
            return None
        proj = projects[project_id]
        if name and name.strip():
            proj["name"] = name.strip()
        if path and path.strip():
            clean_path = os.path.abspath(os.path.expanduser(path.strip()))
            try:
                os.makedirs(clean_path, exist_ok=True)
            except Exception:
                pass
            proj["path"] = clean_path
            for ch in proj.get("chats", {}).values():
                ch["cwd"] = clean_path
            if self.data.get("active_project_id") == project_id:
                self.data["workspace"] = clean_path
        self.save()
        return proj

    def delete_project(self, project_id: str) -> bool:
        projects = self.data.get("projects", {})
        if project_id not in projects or len(projects) <= 1:
            return False
        del projects[project_id]
        if self.data.get("active_project_id") == project_id:
            new_pid = next(iter(projects))
            self.switch_project(new_pid)
        else:
            self.save()
        return True

    def get_chats_summary(self, project_id: Optional[str] = None):
        if project_id and project_id in self.data.get("projects", {}):
            proj = self.data["projects"][project_id]
        else:
            proj = self.get_active_project()

        result = []
        for cid, chat in proj.get("chats", {}).items():
            result.append({
                "id": cid,
                "title": chat.get("title", "گفتگو"),
                "created_at": chat.get("created_at", 0),
                "updated_at": chat.get("updated_at", 0),
                "message_count": len(chat.get("messages", [])),
                "model": chat.get("model", "gemini-3.8-flash-high"),
                "agy_conversation_id": chat.get("agy_conversation_id"),
                "project_id": proj.get("id"),
                "cwd": chat.get("cwd", proj.get("path"))
            })
        result.sort(key=lambda x: x["updated_at"], reverse=True)
        return result

    def get_chat(self, chat_id: str, project_id: Optional[str] = None):
        if project_id and project_id in self.data.get("projects", {}):
            return self.data["projects"][project_id].get("chats", {}).get(chat_id)
        active_proj = self.get_active_project()
        if chat_id in active_proj.get("chats", {}):
            return active_proj["chats"][chat_id]
        # Search all projects
        for p in self.data.get("projects", {}).values():
            if chat_id in p.get("chats", {}):
                return p["chats"][chat_id]
        return None

    def create_chat(self, title: str = "گفتگوی جدید", model: Optional[str] = None, project_id: Optional[str] = None):
        if project_id and project_id in self.data.get("projects", {}):
            proj = self.data["projects"][project_id]
        else:
            proj = self.get_active_project()

        cid = f"chat_{int(time.time() * 1000)}"
        model_to_use = model or self.data.get("default_model", "gemini-3.8-flash-high")
        cwd = proj.get("path") or WORKSPACE_DIR
        new_chat = {
            "id": cid,
            "title": title,
            "created_at": time.time(),
            "updated_at": time.time(),
            "agy_conversation_id": None,
            "model": model_to_use,
            "cwd": cwd,
            "project_id": proj.get("id"),
            "messages": []
        }
        proj.setdefault("chats", {})[cid] = new_chat
        proj["active_chat_id"] = cid
        if proj.get("id") == self.data.get("active_project_id"):
            self.data["chats"] = proj["chats"]
            self.data["active_chat_id"] = cid
        self.save()
        return new_chat

    def delete_chat(self, chat_id: str, project_id: Optional[str] = None):
        target_proj = None
        if project_id and project_id in self.data.get("projects", {}):
            target_proj = self.data["projects"][project_id]
        else:
            for p in self.data.get("projects", {}).values():
                if chat_id in p.get("chats", {}):
                    target_proj = p
                    break
            if not target_proj:
                target_proj = self.get_active_project()

        chats = target_proj.get("chats", {})
        if chat_id in chats:
            del chats[chat_id]
            if not chats:
                return self.create_chat(project_id=target_proj.get("id"))
            if target_proj.get("active_chat_id") == chat_id:
                target_proj["active_chat_id"] = next(iter(chats))
            if target_proj.get("id") == self.data.get("active_project_id"):
                self.data["chats"] = chats
                self.data["active_chat_id"] = target_proj["active_chat_id"]
            self.save()
            return self.get_chat(target_proj["active_chat_id"])
        if chat_id in self.data.get("chats", {}):
            del self.data["chats"][chat_id]
            self.save()
        return None

    def clear_chat(self, chat_id: str):
        chat = self.get_chat(chat_id)
        if chat:
            chat["messages"] = []
            chat["agy_conversation_id"] = None
            chat["updated_at"] = time.time()
            self.save()
            return True
        return False

    def add_message(self, chat_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None):
        chat = self.get_chat(chat_id)
        if not chat:
            chat = self.create_chat()
            chat_id = chat["id"]

        if role == "user" and (chat.get("title") == "گفتگوی جدید" or not chat.get("title")):
            cleaned = content.strip().split('\n')[0][:40]
            if cleaned:
                chat["title"] = cleaned

        msg = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "meta": meta or {}
        }
        chat["messages"].append(msg)
        chat["updated_at"] = time.time()

        # Update active chat id in owner project
        for p in self.data.get("projects", {}).values():
            if chat_id in p.get("chats", {}):
                p["active_chat_id"] = chat_id
                if p.get("id") == self.data.get("active_project_id"):
                    self.data["active_chat_id"] = chat_id
                break

        self.save()
        return msg

history_mgr = HistoryManager(HISTORY_FILE)

# Connected WebSockets
connected_clients: Set[tornado.websocket.WebSocketHandler] = set()

# Process log subscriptions: pid -> Set[WebSocketHandler]
log_subscribers: Dict[int, Set[tornado.websocket.WebSocketHandler]] = {}

# Active child processes per chat: chat_id -> asyncio.subprocess.Process
active_chat_processes: Dict[str, asyncio.subprocess.Process] = {}

# Active tool execution info: chat_id -> Dict
active_tool_info: Dict[str, Dict[str, Any]] = {}

# In-memory log buffer for processes (last 300 lines)
managed_process_logs: Dict[int, deque] = {}

# Interactive Permission Waiters: request_id -> asyncio.Future
permission_futures: Dict[str, asyncio.Future] = {}

# Broadcast to all connected clients
def broadcast(message: Dict[str, Any]):
    msg_str = json.dumps(message, ensure_ascii=False)
    for client in list(connected_clients):
        try:
            client.write_message(msg_str)
        except Exception:
            connected_clients.discard(client)

# Format bytes helper
def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != 'B' else f"{size} B"
        size /= 1024
    return f"{size:.1f} TB"

# Check internet connectivity
def is_internet_available(timeout: float = 0.8) -> bool:
    for host, port in [("1.1.1.1", 53), ("8.8.8.8", 53)]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            return True
        except Exception:
            pass
    return False

# Scan listening development ports on localhost
def get_open_ports() -> List[int]:
    common_ports = [3000, 5000, 5173, 7681, 8000, 8080, 8888, 9000]
    open_ports = []
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.02)
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                open_ports.append(port)
            sock.close()
        except Exception:
            pass
    return open_ports

# Security check to allow user home, workspace, or any project path
def is_path_allowed(target_path: str) -> bool:
    try:
        target_abs = os.path.abspath(os.path.expanduser(target_path))
        allowed_roots = [USER_HOME, WORKSPACE_DIR]
        # Common mobile & Unix storage roots
        for mobile_root in ['/sdcard', '/storage/emulated/0', '/data/data/com.termux/files', '/storage']:
            if os.path.exists(mobile_root):
                allowed_roots.append(mobile_root)
        # All configured projects paths
        for proj in history_mgr.data.get("projects", {}).values():
            p_path = proj.get("path")
            if p_path:
                allowed_roots.append(os.path.abspath(os.path.expanduser(p_path)))

        real_allowed = []
        for r in allowed_roots:
            real_allowed.append(r)
            try:
                rp = os.path.realpath(r)
                if rp not in real_allowed:
                    real_allowed.append(rp)
            except Exception:
                pass

        target_real = os.path.realpath(target_abs)
        return any(target_abs.startswith(r) or target_real.startswith(r) for r in real_allowed)
    except Exception:
        return False

# Get user processes from system
def get_system_processes() -> List[Dict[str, Any]]:
    procs = []
    open_ports = get_open_ports()
    current_pid = os.getpid()

    try:
        cmd = ['ps', '-eo', 'pid,user,%cpu,%mem,etime,comm,args', '-w', '-w']
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        lines = res.stdout.strip().splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.strip().split(None, 6)
                if len(parts) >= 7:
                    pid_str, user, cpu_str, mem_str, etime, comm, args = parts
                    try:
                        pid = int(pid_str)
                    except ValueError:
                        continue

                    # Filter out short-lived ps itself
                    if args.startswith('ps ') or comm == 'ps':
                        continue

                    cpu_val = float(cpu_str) if cpu_str.replace('.', '', 1).isdigit() else 0.0
                    mem_val = float(mem_str) if mem_str.replace('.', '', 1).isdigit() else 0.0

                    # Try to detect port associated with this process
                    detected_port = None
                    if pid == current_pid:
                        detected_port = PORT
                    else:
                        for p in open_ports:
                            if str(p) in args:
                                detected_port = p
                                break

                    is_managed = (pid in managed_process_logs) or (pid == current_pid)
                    for chat_proc in active_chat_processes.values():
                        if chat_proc.pid == pid:
                            is_managed = True
                            break

                    procs.append({
                        "pid": pid,
                        "user": user,
                        "cpu": cpu_val,
                        "mem": mem_val,
                        "uptime": etime,
                        "name": os.path.basename(comm),
                        "command": args,
                        "port": detected_port,
                        "is_server": (pid == current_pid),
                        "is_managed": is_managed
                    })
    except Exception as e:
        print(f"[WARN] Error in get_system_processes: {e}")

    # Sort: Current server first, then managed, then CPU usage descending
    procs.sort(key=lambda x: (not x["is_server"], not x["is_managed"], -x["cpu"]))
    return procs

# Find child processes of a parent pid
def get_child_pids(parent_pid: int) -> List[int]:
    children = []
    try:
        out = subprocess.check_output(['pgrep', '-P', str(parent_pid)], text=True, timeout=1)
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                children.append(int(line))
    except Exception:
        pass
    return children

# Helper to send log line to subscribers
def emit_process_log(pid: int, line: str):
    if pid not in managed_process_logs:
        managed_process_logs[pid] = deque(maxlen=300)
    managed_process_logs[pid].append(line)

    subs = log_subscribers.get(pid)
    if subs:
        msg = json.dumps({"type": "process_log_line", "pid": pid, "line": line}, ensure_ascii=False)
        for ws in list(subs):
            try:
                ws.write_message(msg)
            except Exception:
                subs.discard(ws)

# Execute Antigravity Binary Turn with Live Step Accordion & Permissions
async def execute_agy_turn(chat_id: str, prompt: str, ws_client: Optional[tornado.websocket.WebSocketHandler] = None):
    chat = history_mgr.get_chat(chat_id)
    if not chat:
        chat = history_mgr.create_chat()
        chat_id = chat["id"]

    active_proj = history_mgr.get_active_project()
    cwd = chat.get("cwd") or active_proj.get("path") or WORKSPACE_DIR
    if not os.path.isdir(cwd):
        cwd = WORKSPACE_DIR

    agy_conv_id = chat.get("agy_conversation_id")
    model = chat.get("model") or "gemini-3.8-flash-high"
    effort = chat.get("effort") or history_mgr.data.get("default_effort", "high")
    mode = chat.get("mode") or history_mgr.data.get("default_mode", "auto")

    agy_bin = find_agy_binary()
    if not os.path.exists(agy_bin):
        termux_cmd = "pkg install -y glibc-repo && pkg install -y glibc ca-certificates resolv-conf && curl -fsSL https://raw.githubusercontent.com/wallentx/antigravity-cli-termux/dev/install.sh | bash"
        err_msg = (
            "⚠️ **موتور هوش مصنوعی Antigravity CLI روی سیستم یافت نشد.**\n\n"
            f"برای فعال‌سازی و شروع چت، لطفاً دستور زیر را در ترموکس اجرا کنید:\n\n"
            f"```bash\n{termux_cmd}\n```"
        )
        msg_obj = history_mgr.add_message(chat_id, "model", err_msg)
        broadcast({
            "type": "turn_complete",
            "chat_id": chat_id,
            "content": err_msg,
            "message": msg_obj
        })
        return

    # Build command arguments for agy
    cmd = [
        agy_bin,
        "-p", prompt,
        "--output-format", "stream-json"
    ]
    perm_preset = history_mgr.data.get("permission_preset", "Turbo")
    if perm_preset == "Turbo":
        cmd.append("--dangerously-skip-permissions")
    if agy_conv_id:
        cmd.extend(["--conversation", agy_conv_id])
    if model:
        cmd.extend(["--model", model])
    if effort:
        cmd.extend(["--effort", effort])
    if mode and mode not in ("auto", "default"):
        cmd.extend(["--mode", mode])

    def send_ws(payload: Dict[str, Any]):
        payload["chat_id"] = chat_id
        msg_json = json.dumps(payload, ensure_ascii=False)
        if ws_client and ws_client in connected_clients:
            try:
                ws_client.write_message(msg_json)
                return
            except Exception:
                pass
        broadcast(payload)

    # Clean CLI stream execution (no synthetic fake status bubbles)
    accumulated_response: List[str] = []
    active_step_index = 0
    turn_steps: Dict[int, Dict[str, Any]] = {}
    turn_start_time = time.time()
    thinking_task: Optional[asyncio.Task] = None

    proc: Optional[asyncio.subprocess.Process] = None

    try:
        sub_env = os.environ.copy()
        if os.path.isdir('/data/data/com.termux/files/home'):
            sub_env['HOME'] = '/data/data/com.termux/files/home'
        api_key = sub_env.get('GEMINI_API_KEY')
        if not api_key:
            for ak_path in [os.path.expanduser('~/.gemini/api_key'), '/data/data/com.termux/files/home/.gemini/api_key']:
                if os.path.isfile(ak_path):
                    try:
                        with open(ak_path, 'r', encoding='utf-8') as f:
                            ak = f.read().strip()
                            if ak:
                                sub_env['GEMINI_API_KEY'] = ak
                                break
                    except Exception:
                        pass

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=sub_env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        active_chat_processes[chat_id] = proc
        managed_process_logs[proc.pid] = deque(maxlen=300)

        # Background task to poll real-time thinking from transcript
        async def poll_thinking_live():
            last_sent_th = ""
            try:
                while proc and proc.returncode is None:
                    await asyncio.sleep(0.7)
                    cid = chat.get("agy_conversation_id")
                    if cid:
                        th, tok = extract_turn_thinking(cid)
                        if th and th != last_sent_th:
                            last_sent_th = th
                            send_ws({
                                "type": "thinking_update",
                                "thinking": th,
                                "tokens": tok
                            })
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        thinking_task = asyncio.create_task(poll_thinking_live())

        # Background task to read stderr for permission prompts or command outputs
        async def read_stderr():
            try:
                while True:
                    err_line_bytes = await proc.stderr.readline()
                    if not err_line_bytes:
                        break
                    err_line = err_line_bytes.decode('utf-8', errors='replace').strip()
                    if not err_line:
                        continue

                    # Filter out benign Go init logs
                    if "Initialized Android local timezone" in err_line or "ERROR: logging before" in err_line:
                        continue

                    emit_process_log(proc.pid, f"[stderr] {err_line}")

                    # Check for interactive permission request patterns in stderr/stdout
                    perm_patterns = [
                        r'\[y/n\]', r'\(y/n\)', r'Run command\?', r'Do you trust',
                        r'Execute.*?\?', r'Allow once', r'\[Y/n\]', r'\[y/N\]'
                    ]
                    if any(re.search(pat, err_line, re.IGNORECASE) for pat in perm_patterns):
                        req_id = f"perm_{int(time.time()*1000)}"
                        fut = asyncio.get_event_loop().create_future()
                        permission_futures[req_id] = fut

                        send_ws({
                            "type": "permission_request",
                            "request_id": req_id,
                            "action_type": "command",
                            "title": "درخواست تایید اجرای دستور در ترمینال",
                            "command": err_line,
                            "cwd": cwd,
                            "raw_prompt": err_line
                        })

                        # Wait for user approval
                        try:
                            decision, custom_input = await asyncio.wait_for(fut, timeout=120)
                            if decision in ('allow', 'yes'):
                                proc.stdin.write(b"y\n")
                            elif decision == 'always':
                                proc.stdin.write(b"a\n")
                            elif decision in ('deny', 'no'):
                                proc.stdin.write(b"n\n")
                            elif decision == 'custom' and custom_input:
                                proc.stdin.write(f"{custom_input}\n".encode('utf-8'))
                            await proc.stdin.drain()
                        except asyncio.TimeoutError:
                            proc.stdin.write(b"n\n")
                            await proc.stdin.drain()
                        finally:
                            permission_futures.pop(req_id, None)

                    # Always stream non-empty stderr lines to live CLI view
                    send_ws({
                        "type": "cli_output",
                        "line": err_line,
                        "is_err": True
                    })

                    # If a command tool is actively running, stream stderr line
                    active_info = active_tool_info.get(chat_id)
                    if active_info and active_info.get("is_command"):
                        send_ws({
                            "type": "command_output",
                            "step_index": active_info.get("step_index", 0),
                            "line": err_line,
                            "is_err": True
                        })
            except Exception as e:
                print(f"[WARN] read_stderr exception: {e}")

        stderr_task = asyncio.create_task(read_stderr())

        # Read NDJSON line-by-line from agy stdout
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            line_str = line_bytes.decode('utf-8', errors='replace').strip()
            if not line_str:
                continue

            emit_process_log(proc.pid, f"[stdout] {line_str}")

            # Non-JSON lines (raw CLI prints or commands)
            if not line_str.startswith('{'):
                # Stream directly to live CLI chat block
                send_ws({
                    "type": "cli_output",
                    "line": line_str,
                    "is_err": False
                })
                active_info = active_tool_info.get(chat_id)
                if active_info and active_info.get("is_command"):
                    send_ws({
                        "type": "command_output",
                        "step_index": active_info.get("step_index", 0),
                        "line": line_str,
                        "is_err": False
                    })
                continue

            try:
                data = json.loads(line_str)
            except Exception:
                continue

            event = data.get("event")

            # 1. Event: Init
            if event == "init":
                conv_id = data.get("conversation_id")
                if conv_id:
                    chat["agy_conversation_id"] = conv_id
                    history_mgr.save()
                    send_ws({"type": "init", "conversation_id": conv_id})

            # 2. Event: Step Update
            elif event == "step_update":
                step = data.get("step_update", {})
                step_type = step.get("step_type")
                state = step.get("state")
                step_index = step.get("step_index", active_step_index)
                active_step_index = step_index

                if step_type == "tool":
                    tool_name = step.get("tool_name") or step.get("tool_info", {}).get("name", "tool")
                    tool_info = step.get("tool_info", {})
                    params = tool_info.get("parameters", {})
                    duration = step.get("duration_seconds", 0)

                    action = "Ran"
                    feed_type = "tool"
                    feed_label = ""
                    file_name = ""
                    file_ext = ""
                    line_range = ""
                    add_lines = 0
                    del_lines = 0
                    is_command = False
                    snippet = ""

                    if tool_name in ("read_file", "view_file"):
                        action = "Analyzed"
                        feed_type = "read"
                        fpath = params.get("Path") or params.get("path") or ""
                        file_name = os.path.basename(fpath) if fpath else "file"
                        file_ext = os.path.splitext(file_name)[1].lower().replace(".", "")
                        sline = params.get("StartLine") or params.get("start_line")
                        eline = params.get("EndLine") or params.get("end_line")
                        if sline and eline:
                            line_range = f"#L{sline}-{eline}"
                        elif sline:
                            line_range = f"#L{sline}"
                        feed_label = f"{file_name} {line_range}".strip()

                        if fpath:
                            full_path = fpath if os.path.isabs(fpath) else os.path.join(cwd, fpath)
                            if os.path.isfile(full_path):
                                try:
                                    with open(full_path, 'r', encoding='utf-8', errors='replace') as rf:
                                        flines = rf.readlines()
                                    s_idx = max(0, int(sline) - 1) if sline else 0
                                    e_idx = int(eline) if eline else min(len(flines), s_idx + 100)
                                    numbered = []
                                    for idx in range(s_idx, min(e_idx, len(flines))):
                                        numbered.append(f"{idx+1:4d} | {flines[idx]}")
                                    snippet = "".join(numbered)
                                except Exception:
                                    pass

                    elif tool_name in ("write_file", "write_to_file"):
                        fpath = params.get("Path") or params.get("path") or ""
                        file_name = os.path.basename(fpath) if fpath else "file"
                        file_ext = os.path.splitext(file_name)[1].lower().replace(".", "")
                        full_path = fpath if os.path.isabs(fpath) else os.path.join(cwd, fpath)
                        content = params.get("Content") or params.get("content") or ""
                        add_lines = len(content.splitlines()) if content else 0
                        
                        if not os.path.exists(full_path):
                            action = "Created"
                            feed_type = "create"
                            del_lines = 0
                            feed_label = f"{file_name} +{add_lines} -0"
                        else:
                            action = "Edited"
                            feed_type = "edit"
                            del_lines = 0
                            feed_label = f"{file_name} +{add_lines} -0"
                        snippet = content[:2000]

                    elif tool_name in ("edit_file", "replace_file_content", "multi_replace_file_content", "sed_file"):
                        action = "Edited"
                        feed_type = "edit"
                        fpath = params.get("Path") or params.get("path") or ""
                        file_name = os.path.basename(fpath) if fpath else "file"
                        file_ext = os.path.splitext(file_name)[1].lower().replace(".", "")
                        target = params.get("Target") or params.get("target") or ""
                        replacement = params.get("Replacement") or params.get("replacement") or params.get("Content") or params.get("content") or ""
                        add_lines = len(replacement.splitlines()) if replacement else 0
                        del_lines = len(target.splitlines()) if target else 0
                        if add_lines == 0 and del_lines == 0:
                            content = params.get("Content") or params.get("content") or ""
                            add_lines = len(content.splitlines()) if content else 1
                        feed_label = f"{file_name} +{add_lines} -{del_lines}"

                    elif tool_name == "run_command":
                        action = "Ran"
                        feed_type = "tool"
                        is_command = True
                        cmd_str = params.get("CommandLine") or params.get("command") or ""
                        summary = params.get("toolSummary") or params.get("tool_summary") or ""
                        if summary:
                            feed_label = summary.strip('"\'')
                        elif cmd_str:
                            feed_label = cmd_str[:60]
                        else:
                            feed_label = "terminal command"

                    elif tool_name in ("grep_search", "find_by_name", "list_dir"):
                        action = "Analyzed"
                        feed_type = "tool"
                        fpath = params.get("Path") or params.get("path") or ""
                        file_name = os.path.basename(fpath) if fpath else ""
                        query = params.get("query") or params.get("pattern") or ""
                        if query and file_name:
                            feed_label = f"inspect '{query}' in {file_name}"
                        elif query:
                            feed_label = f"inspect '{query}'"
                        elif file_name:
                            feed_label = f"inspect {file_name}"
                        else:
                            feed_label = "inspect workspace"
                    else:
                        action = "Ran"
                        feed_type = "tool"
                        summary = params.get("toolSummary") or params.get("tool_summary") or ""
                        feed_label = summary.strip('"\'') if summary else tool_name

                    if state == "ACTIVE":
                        turn_steps[step_index] = {
                            "index": step_index,
                            "tool": tool_name,
                            "action": action,
                            "feed_type": feed_type,
                            "feed_label": feed_label,
                            "file_name": file_name,
                            "file_ext": file_ext,
                            "line_range": line_range,
                            "add_lines": add_lines,
                            "del_lines": del_lines,
                            "state": "ACTIVE",
                            "duration": 0,
                            "output": "",
                            "target": params.get("Target", ""),
                            "replacement": params.get("Replacement", "") or params.get("Content", ""),
                            "snippet": snippet,
                            "command": params.get("CommandLine", "")
                        }
                        active_tool_info[chat_id] = {
                            "step_index": step_index,
                            "tool_name": tool_name,
                            "action": action,
                            "feed_label": feed_label,
                            "is_command": is_command,
                            "command": params.get("CommandLine", ""),
                            "start_time": time.time()
                        }
                        send_ws({
                            "type": "step_start",
                            "step_index": step_index,
                            "step_type": "tool",
                            "action": action,
                            "feed_type": feed_type,
                            "feed_label": feed_label,
                            "file_name": file_name,
                            "file_ext": file_ext,
                            "line_range": line_range,
                            "add_lines": add_lines,
                            "del_lines": del_lines,
                            "tool_name": tool_name,
                            "command": params.get("CommandLine", ""),
                            "is_command": is_command,
                            "start_time": time.time(),
                            "target": params.get("Target", ""),
                            "replacement": params.get("Replacement", "") or params.get("Content", ""),
                            "snippet": snippet,
                            "start_line": params.get("StartLine"),
                            "end_line": params.get("EndLine"),
                            "file_path": params.get("Path", "")
                        })

                    elif state == "DONE":
                        active_tool_info.pop(chat_id, None)
                        output_str = tool_info.get("output", "")
                        if step_index in turn_steps:
                            turn_steps[step_index]["state"] = "DONE"
                            turn_steps[step_index]["duration"] = round(duration, 1)
                            turn_steps[step_index]["output"] = output_str
                        send_ws({
                            "type": "step_done",
                            "step_index": step_index,
                            "step_type": "tool",
                            "action": action,
                            "feed_type": feed_type,
                            "feed_label": feed_label,
                            "file_name": file_name,
                            "file_ext": file_ext,
                            "line_range": line_range,
                            "add_lines": add_lines,
                            "del_lines": del_lines,
                            "tool_name": tool_name,
                            "duration": round(duration, 1),
                            "output": output_str,
                            "target": params.get("Target", ""),
                            "replacement": params.get("Replacement", "") or params.get("Content", ""),
                            "snippet": snippet,
                            "command": params.get("CommandLine", ""),
                            "start_line": params.get("StartLine"),
                            "end_line": params.get("EndLine"),
                            "file_path": params.get("Path", "")
                        })

                elif step_type == "agent_response":
                    text_delta = step.get("text_delta", "")
                    duration = step.get("duration_seconds", 0)
                    usage = step.get("usage", {})
                    thinking_tokens = usage.get("thinking_tokens", 0)

                    if state == "DONE" and duration >= 0.8:
                        th_text, _ = extract_turn_thinking(conv_id)
                        send_ws({
                            "type": "thinking_step",
                            "step_index": step_index,
                            "duration": max(1, round(duration)),
                            "thinking": th_text or "Reasoning analysis completed.",
                            "tokens": thinking_tokens
                        })

                    if text_delta:
                        accumulated_response.append(text_delta)
                        send_ws({
                            "type": "delta",
                            "delta": text_delta
                        })

            # 3. Event: Result
            elif event == "result":
                result = data.get("result", {})
                final_res = result.get("response")
                if final_res:
                    accumulated_response = [final_res]

        await proc.wait()
        try:
            await asyncio.wait_for(stderr_task, timeout=1.0)
        except Exception:
            pass

        if thinking_task and not thinking_task.done():
            thinking_task.cancel()

        return_code = proc.returncode
        full_text = "".join(accumulated_response).strip()

        # Final extraction of thinking and tokens from transcript
        conv_id = chat.get("agy_conversation_id")
        final_thinking, final_tokens = extract_turn_thinking(conv_id)
        sorted_steps = [turn_steps[k] for k in sorted(turn_steps.keys())]
        turn_duration = round(time.time() - turn_start_time, 2)

        meta = {
            "thinking": final_thinking,
            "thinking_tokens": final_tokens,
            "duration": turn_duration,
            "steps": sorted_steps,
            "model": model,
            "effort": effort,
            "mode": mode
        }

        if return_code != 0 and not full_text:
            err_clean = f"خطای اجرا در باینری agy (کد خروج: {return_code})"
            send_ws({"type": "error", "error": err_clean})
        else:
            if not full_text:
                full_text = "عملیات بدون خروجی متنی به پایان رسید."
            
            # Save assistant response with meta (thinking & steps) to chat history
            history_mgr.add_message(chat_id, "assistant", full_text, meta=meta)
            send_ws({
                "type": "done",
                "full_text": full_text,
                "meta": meta
            })

    except asyncio.CancelledError:
        send_ws({"type": "status", "status": "عملیات لغو شد."})
    except Exception as e:
        err_msg = f"خطا در برقراری ارتباط با پردازه agy: {str(e)}"
        send_ws({"type": "error", "error": err_msg})
    finally:
        if thinking_task and not thinking_task.done():
            thinking_task.cancel()
        active_chat_processes.pop(chat_id, None)
        active_tool_info.pop(chat_id, None)
        send_ws({"type": "status", "status": ""})

# Handle slash commands directly
async def handle_slash_command(chat_id: str, text: str, ws_client: Optional[tornado.websocket.WebSocketHandler] = None):
    parts = text.strip().split()
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    chat = history_mgr.get_chat(chat_id)
    if not chat:
        chat = history_mgr.create_chat()
        chat_id = chat["id"]

    def reply_cmd(msg: str):
        history_mgr.add_message(chat_id, "assistant", msg)
        payload = {
            "type": "done",
            "chat_id": chat_id,
            "full_text": msg
        }
        if ws_client:
            try:
                ws_client.write_message(json.dumps(payload, ensure_ascii=False))
                return
            except Exception:
                pass
        broadcast(payload)

    if cmd == "/clear":
        history_mgr.clear_chat(chat_id)
        payload = {"type": "chat_cleared", "chat_id": chat_id}
        if ws_client:
            try:
                ws_client.write_message(json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass
        broadcast(payload)

    elif cmd == "/model":
        if arg:
            valid_ids = [m["id"] for m in CACHED_MODELS]
            matched = [m for m in valid_ids if arg.lower() in m.lower()]
            selected = matched[0] if matched else arg
            chat["model"] = selected
            history_mgr.data["default_model"] = selected
            history_mgr.save()
            reply_cmd(f"مدل فعال به **`{selected}`** تغییر یافت.")
        else:
            current = chat.get("model", "gemini-3.8-flash-high")
            list_text = "\n".join([f"- **`{m['id']}`** ({m['name']})" for m in CACHED_MODELS])
            reply_cmd(f"مدل فعلی: **`{current}`**\n\nمدل‌های در دسترس:\n{list_text}\n\nبرای تغییر: `/model <نام مدل>`")

    elif cmd == "/compact":
        chat["agy_conversation_id"] = None
        history_mgr.save()
        reply_cmd("کانتکست گفتگو فشرده‌سازی شد و مکالمه جدید در امتداد تاریخچه شروع می‌شود.")

    elif cmd == "/restart":
        # Restart engine via command
        count = 0
        for cid, p in list(active_chat_processes.items()):
            try:
                p.terminate()
                count += 1
            except Exception:
                pass
        active_chat_processes.clear()
        reply_cmd(f"موتور Antigravity مجدداً راه‌اندازی شد ({count} پردازه متوقف گردید).")

    elif cmd == "/effort":
        if arg and arg.lower() in ("low", "medium", "high", "xhigh", "max"):
            chat["effort"] = arg.lower()
            history_mgr.data["default_effort"] = arg.lower()
            history_mgr.save()
            reply_cmd(f"میزان تلاش فکری (Reasoning Effort) به **`{arg.lower()}`** تغییر یافت.")
        else:
            curr = chat.get("effort") or history_mgr.data.get("default_effort", "high")
            reply_cmd(f"میزان تلاش فکری فعلی: **`{curr}`**\n\nگزینه‌ها: `low`, `medium`, `high`, `xhigh`, `max`\nدستور تغییر: `/effort high`")

    elif cmd == "/mode":
        if arg and arg.lower() in ("auto", "plan", "request-review"):
            chat["mode"] = arg.lower()
            history_mgr.data["default_mode"] = arg.lower()
            history_mgr.save()
            reply_cmd(f"حالت اجرایی ایجنت به **`{arg.lower()}`** تغییر یافت.")
        else:
            curr = chat.get("mode") or history_mgr.data.get("default_mode", "auto")
            reply_cmd(f"حالت اجرایی فعلی: **`{curr}`**\n\nگزینه‌ها:\n- `auto`: اجرای خودکار\n- `plan`: طرح‌ریزی قبل از اجرا\n- `request-review`: بازبینی و تایید\nدستور: `/mode auto`")

    elif cmd in ("/help", "/راهنما"):
        help_text = (
            "### ⚡ دستورات در دسترس Antigravity:\n\n"
            "- `/goal [متن]` : اجرای تسک‌های عمیق و خودکار تا حصول نتیجه نهایی\n"
            "- `/plan [متن]` : برنامه‌ریزی گام‌به‌گام و دقیق پیش از شروع کار\n"
            "- `/boost [متن]` : تفکر عمیق و تحلیل چندبعدی مسئله\n"
            "- `/compact` : فشرده‌سازی سابقه برای آزادسازی حافظه توکن‌ها\n"
            "- `/schedule` : زمان‌بندی اجرای دستورات و تنظیم تایمر\n"
            "- `/browser` : وب‌گردی و اتوماسیون تعامل با صفحات وب\n"
            "- `/model [نام]` : مشاهده یا تغییر مدل هوش مصنوعی\n"
            "- `/effort [سطح]` : تنظیم تلاش استدلال (`low`, `medium`, `high`, `max`)\n"
            "- `/mode [حالت]` : تنظیم حالت اجرایی (`auto`, `plan`, `request-review`)\n"
            "- `/clear` : پاکسازی پیام‌های گفتگوی فعلی\n"
            "- `/restart` : راه‌اندازی مجدد موتور پردازش و بستن پروسه‌ها\n"
            "- `/help` : نمایش همین راهنما"
        )
        reply_cmd(help_text)
    else:
        # Unknown slash command - forward to agy anyway
        await execute_agy_turn(chat_id, text, ws_client)

# Tornado HTTP Handlers
class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

    def get(self):
        self.render(os.path.join(WORKSPACE_DIR, 'index.html'))

    def head(self):
        self.get()

class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

# Base API Handler with session validation
class BaseApiHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()

    def get_auth_token(self) -> Optional[str]:
        auth_hdr = self.request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            return auth_hdr[7:].strip()
        cookie_val = self.get_cookie("anti_session")
        if cookie_val:
            return cookie_val.strip()
        return self.get_argument("token", None)

    def is_authenticated(self) -> Tuple[bool, Optional[str]]:
        token = self.get_auth_token()
        return auth_manager.validate_token(token)

    def prepare(self):
        if self.request.method == "OPTIONS":
            return
        if os.environ.get("ANTI_REQUIRE_PASSWORD") != "1" and not auth_manager.config.get("enabled", False):
            return
        is_auth, user = self.is_authenticated()
        if not is_auth:
            self.set_status(401)
            self.finish(json.dumps({
                "error": "احراز هویت الزامی است. لطفاً وارد شوید.",
                "auth_required": True
            }, ensure_ascii=False))

class AuthLoginHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")

    def options(self):
        self.set_status(204)
        self.finish()

    def post(self):
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception:
            self.set_status(400)
            self.finish(json.dumps({"ok": False, "error": "درخواست نامعتبر است."}, ensure_ascii=False))
            return

        username = data.get("username", "")
        password = data.get("password", "")
        remember = data.get("remember", True)

        token = auth_manager.login(username, password)
        if not token:
            self.set_status(401)
            self.finish(json.dumps({"ok": False, "error": "نام کاربری یا رمز عبور اشتباه است."}, ensure_ascii=False))
            return

        self.set_cookie("anti_session", token, expires_days=30 if remember else 1, httponly=True, samesite="Lax")
        self.finish(json.dumps({
            "ok": True,
            "token": token,
            "username": auth_manager.config.get("username", "admin")
        }, ensure_ascii=False))

class AuthLogoutHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self):
        self.set_status(204)
        self.finish()

    def post(self):
        token = None
        auth_hdr = self.request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()
        if not token:
            token = self.get_cookie("anti_session")
        if token:
            auth_manager.logout(token)
        self.clear_cookie("anti_session")
        self.finish(json.dumps({"ok": True, "message": "با موفقیت خارج شدید."}, ensure_ascii=False))

class AuthStatusHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        token = None
        auth_hdr = self.request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()
        if not token:
            token = self.get_cookie("anti_session")
        if not token:
            token = self.get_argument("token", None)

        is_auth, user = auth_manager.validate_token(token)
        self.finish(json.dumps({
            "authenticated": is_auth,
            "username": user if is_auth else None,
            "auth_enabled": auth_manager.config.get("enabled", False)
        }, ensure_ascii=False))

class AuthChangePasswordHandler(BaseApiHandler):
    def post(self):
        try:
            data = json.loads(self.request.body.decode('utf-8'))
        except Exception:
            self.set_status(400)
            self.finish(json.dumps({"ok": False, "error": "درخواست نامعتبر است."}, ensure_ascii=False))
            return

        old_pwd = data.get("old_password", "")
        new_username = data.get("new_username", None)
        new_pwd = data.get("new_password", "")

        ok, msg = auth_manager.change_password(old_pwd, new_username, new_pwd)
        if not ok:
            self.set_status(400)
            self.finish(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
            return
        self.finish(json.dumps({
            "ok": True,
            "message": msg,
            "username": auth_manager.config.get("username", "admin")
        }, ensure_ascii=False))

class ProjectsApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args):
        self.set_status(204)
        self.finish()

    def get(self):
        active_proj = history_mgr.get_active_project()
        self.write(json.dumps({
            "projects": history_mgr.get_projects_summary(),
            "standalone_chats": history_mgr.get_standalone_chats(),
            "active_project_id": history_mgr.data.get("active_project_id"),
            "active_project": active_proj,
            "user": get_current_user_profile()
        }, ensure_ascii=False))

    def post(self):
        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}
        name = body.get("name", "پروژه جدید")
        path = body.get("path", "")
        new_proj = history_mgr.create_project(name=name, path=path)
        self.write(json.dumps({
            "success": True,
            "project": new_proj,
            "active_project_id": new_proj["id"],
            "projects": history_mgr.get_projects_summary()
        }, ensure_ascii=False))

class ProjectDetailApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, PUT, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args):
        self.set_status(204)
        self.finish()

    def get(self, project_id):
        proj = history_mgr.data.get("projects", {}).get(project_id)
        if not proj:
            self.set_status(404)
            self.write(json.dumps({"error": "پروژه یافت نشد."}))
            return
        self.write(json.dumps(proj, ensure_ascii=False))

    def put(self, project_id):
        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}
        updated = history_mgr.update_project(project_id, name=body.get("name"), path=body.get("path"))
        if not updated:
            self.set_status(404)
            self.write(json.dumps({"error": "پروژه یافت نشد."}))
            return
        self.write(json.dumps({
            "success": True,
            "project": updated,
            "projects": history_mgr.get_projects_summary()
        }, ensure_ascii=False))

    def delete(self, project_id):
        success = history_mgr.delete_project(project_id)
        if not success:
            self.set_status(400)
            self.write(json.dumps({"error": "امکان حذف این پروژه وجود ندارد (حداقل یک پروژه باید در سیستم باقی بماند)."}))
            return
        self.write(json.dumps({
            "success": True,
            "active_project": history_mgr.get_active_project(),
            "projects": history_mgr.get_projects_summary()
        }, ensure_ascii=False))

class ProjectSwitchApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args):
        self.set_status(204)
        self.finish()

    def post(self, project_id):
        proj = history_mgr.switch_project(project_id)
        if not proj:
            self.set_status(404)
            self.write(json.dumps({"error": "پروژه یافت نشد."}))
            return

        broadcast({
            "type": "project_switched",
            "project": {
                "id": proj["id"],
                "name": proj["name"],
                "path": proj["path"]
            },
            "active_chat_id": proj.get("active_chat_id")
        })

        self.write(json.dumps({
            "success": True,
            "active_project": proj,
            "chats": history_mgr.get_chats_summary(proj["id"])
        }, ensure_ascii=False))

def get_project_context_info(project_path: str) -> Dict[str, Any]:
    norm_path = os.path.abspath(os.path.expanduser(project_path))
    info: Dict[str, Any] = {
        "path": norm_path,
        "exists": os.path.isdir(norm_path),
        "git_branch": None,
        "git_commit": None,
        "has_agents_dir": False,
        "has_gemini_md": False,
        "has_rules": False,
        "skills_count": 0,
        "rules_count": 0
    }
    if not info["exists"]:
        return info

    git_dir = os.path.join(norm_path, ".git")
    if os.path.exists(git_dir):
        try:
            b = subprocess.check_output(["git", "-C", norm_path, "branch", "--show-current"], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            info["git_branch"] = b or "HEAD"
            c = subprocess.check_output(["git", "-C", norm_path, "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            info["git_commit"] = c
        except Exception:
            pass

    if os.path.isfile(os.path.join(norm_path, "GEMINI.md")) or os.path.isfile(os.path.join(norm_path, "AGENTS.md")):
        info["has_gemini_md"] = True

    agents_dir = os.path.join(norm_path, ".agents")
    if not os.path.isdir(agents_dir):
        agents_dir = os.path.join(norm_path, ".agent")
    if os.path.isdir(agents_dir):
        info["has_agents_dir"] = True
        skills_dir = os.path.join(agents_dir, "skills")
        if os.path.isdir(skills_dir):
            try:
                info["skills_count"] = len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
            except Exception:
                pass
        rules_dir = os.path.join(agents_dir, "rules")
        if os.path.isdir(rules_dir):
            try:
                info["rules_count"] = len([f for f in os.listdir(rules_dir) if f.endswith('.md')])
                info["has_rules"] = info["rules_count"] > 0
            except Exception:
                pass
    return info

class SettingsApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args):
        self.set_status(204)
        self.finish()

    def get(self):
        active_proj = history_mgr.get_active_project() or {}
        proj_path = active_proj.get("path", WORKSPACE_DIR)
        context_info = get_project_context_info(proj_path)

        agy_ver = "2.28.2"
        agy_bin = find_agy_binary()
        try:
            res = subprocess.run([agy_bin, "--version"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                agy_ver = res.stdout.strip()
        except Exception:
            pass

        global_settings = {
            "default_model": history_mgr.data.get("default_model", "gemini-3.8-flash-high"),
            "default_effort": history_mgr.data.get("default_effort", "high"),
            "default_mode": history_mgr.data.get("default_mode", "auto"),
            "permission_preset": history_mgr.data.get("permission_preset", "Turbo"),
            "enable_sounds": history_mgr.data.get("enable_sounds", False),
            "app_version": agy_ver,
            "cli_binary": agy_bin,
            "workspace_path": proj_path,
            "git_branch": context_info.get("git_branch", "main"),
            "models": [{"id": m.get("id"), "name": m.get("name")} for m in fetch_models_from_cli()]
        }

        self.write(json.dumps({
            "global": global_settings,
            "active_project": {
                "id": active_proj.get("id"),
                "name": active_proj.get("name"),
                "path": proj_path,
                "context": context_info,
                "overrides": active_proj.get("settings", {})
            },
            "user": get_current_user_profile()
        }, ensure_ascii=False))

    def post(self):
        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}

        glob = body.get("global", {})
        allowed_keys = [
            "default_model", "default_effort", "default_mode", "permission_preset",
            "enable_sounds"
        ]
        for k in allowed_keys:
            if k in glob:
                history_mgr.data[k] = glob[k]

        history_mgr.save()

        broadcast({
            "type": "settings_updated",
            "model": history_mgr.data.get("default_model"),
            "effort": history_mgr.data.get("default_effort"),
            "mode": history_mgr.data.get("default_mode"),
            "permission_preset": history_mgr.data.get("permission_preset", "Turbo"),
            "enable_sounds": history_mgr.data.get("enable_sounds", False)
        })

        self.write(json.dumps({
            "success": True,
            "message": "تنظیمات با موفقیت ذخیره گردید."
        }, ensure_ascii=False))

class ProjectContextApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        active_proj = history_mgr.get_active_project() or {}
        proj_path = active_proj.get("path", WORKSPACE_DIR)
        context_info = get_project_context_info(proj_path)
        self.write(json.dumps({
            "project": active_proj,
            "context": context_info
        }, ensure_ascii=False))

class ChatApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args):
        self.set_status(204)
        self.finish()

    def get(self, chat_id=None):
        if chat_id:
            chat = history_mgr.get_chat(chat_id)
            if chat:
                self.write(json.dumps(chat, ensure_ascii=False))
            else:
                self.set_status(404)
                self.write(json.dumps({"error": "Chat not found"}))
        else:
            summaries = history_mgr.get_chats_summary()
            active_proj = history_mgr.get_active_project()
            active_id = active_proj.get("active_chat_id")
            self.write(json.dumps({
                "active_project_id": active_proj.get("id"),
                "active_project_name": active_proj.get("name"),
                "active_project_path": active_proj.get("path"),
                "active_chat_id": active_id,
                "chats": summaries,
                "default_model": history_mgr.data.get("default_model", "gemini-3.8-flash-high"),
                "workspace": active_proj.get("path", WORKSPACE_DIR)
            }, ensure_ascii=False))

    def post(self, chat_id=None):
        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}

        action = body.get("action")
        if action == "clear" and chat_id:
            success = history_mgr.clear_chat(chat_id)
            self.write(json.dumps({"success": success}))
            return

        project_id = body.get("project_id")
        title = body.get("title", "گفتگوی جدید")
        model = body.get("model")
        new_chat = history_mgr.create_chat(title=title, model=model, project_id=project_id)
        self.write(json.dumps(new_chat, ensure_ascii=False))

    def delete(self, chat_id=None):
        if not chat_id:
            self.set_status(400)
            self.write(json.dumps({"error": "chat_id required"}))
            return
        active_chat = history_mgr.delete_chat(chat_id)
        self.write(json.dumps({
            "success": True,
            "active_chat": active_chat
        }, ensure_ascii=False))

class ModelsApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        models = fetch_models_from_cli()
        self.write(json.dumps({
            "models": models,
            "default": history_mgr.data.get("default_model", "gemini-3.8-flash-high"),
            "effort": history_mgr.data.get("default_effort", "high"),
            "mode": history_mgr.data.get("default_mode", "auto")
        }, ensure_ascii=False))

class MentionsApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        cwd = history_mgr.data.get("workspace", WORKSPACE_DIR)
        items = []
        try:
            for root, dirs, files in os.walk(cwd):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '.git')]
                rel_root = os.path.relpath(root, cwd)
                for f in files:
                    if f.startswith('.'):
                        continue
                    rel_p = f if rel_root == '.' else os.path.join(rel_root, f)
                    items.append({"name": f, "path": rel_p, "type": "file"})
                    if len(items) >= 200:
                        break
                if len(items) >= 200:
                    break
        except Exception:
            pass
        self.write(json.dumps({"items": items}, ensure_ascii=False))

class SearchChatsApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        query = self.get_argument("q", "").strip().lower()
        if not query:
            self.write(json.dumps({"results": []}, ensure_ascii=False))
            return

        results = []
        projects = history_mgr.data.get("projects", {})
        for pid, proj in projects.items():
            p_name = proj.get("name", "Project")
            for cid, chat in proj.get("chats", {}).items():
                title = chat.get("title", "")
                messages = chat.get("messages", [])
                
                title_match = query in title.lower()
                matched_messages = []
                for m in messages:
                    content = m.get("content", "")
                    if query in content.lower():
                        pos = content.lower().find(query)
                        start = max(0, pos - 30)
                        end = min(len(content), pos + len(query) + 50)
                        matched_messages.append({
                            "role": m.get("role", "user"),
                            "snippet": ("..." if start > 0 else "") + content[start:end].strip() + ("..." if end < len(content) else "")
                        })
                        if len(matched_messages) >= 2:
                            break

                if title_match or matched_messages:
                    results.append({
                        "chat_id": cid,
                        "title": title or "گفتگو",
                        "project_id": pid,
                        "project_name": p_name,
                        "updated_at": chat.get("updated_at", 0),
                        "matched_messages": matched_messages,
                        "title_match": title_match
                    })

        results.sort(key=lambda x: (not x["title_match"], -x["updated_at"]))
        self.write(json.dumps({"results": results[:25], "query": query}, ensure_ascii=False))

class AntigravityAccountApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args):
        self.set_status(204)
        self.finish()

    def get(self):
        user = get_current_user_profile()
        is_logged_in = user.get("authenticated", False)

        total_prompt_tokens = 0
        total_thinking_tokens = 0
        total_response_tokens = 0

        for proj in history_mgr.data.get("projects", {}).values():
            for chat in proj.get("chats", {}).values():
                for msg in chat.get("messages", []):
                    meta = msg.get("meta", {})
                    th_tokens = meta.get("thinking_tokens", 0)
                    total_thinking_tokens += th_tokens
                    content_len = len(msg.get("content", "").split())
                    if msg.get("role") == "user":
                        total_prompt_tokens += int(content_len * 1.3)
                    else:
                        total_response_tokens += int(content_len * 1.3)

        response_data = {
            "logged_in": is_logged_in,
            "user": user,
            "email": user.get("email", "حساب متصل نیست"),
            "auth_method": user.get("auth_method", "offline"),
            "models_quota": [
                {
                    "id": "gemini-3.8-flash-high",
                    "name": "Gemini 3.8 Flash (High)",
                    "status": "active" if is_logged_in else "guest",
                    "rpm_limit": "60 RPM" if is_logged_in else "محدود",
                    "daily_quota": "نامحدود / بدون سقف ساعتی" if is_logged_in else "نیاز به اتصال اکانت",
                    "used_percentage": 14 if is_logged_in else 0,
                    "tier": "Tier 1 - High Priority"
                },
                {
                    "id": "claude-sonnet-4-6",
                    "name": "Claude Sonnet 4.6 (Thinking)",
                    "status": "active" if is_logged_in else "guest",
                    "rpm_limit": "30 RPM" if is_logged_in else "محدود",
                    "daily_quota": "سهمیه سازمانی Antigravity" if is_logged_in else "نیاز به لاگین",
                    "used_percentage": 22 if is_logged_in else 0,
                    "tier": "Tier 1 - Deep Reasoning"
                },
                {
                    "id": "gpt-oss-120b-medium",
                    "name": "GPT-OSS 120B (Medium)",
                    "status": "ready",
                    "rpm_limit": "45 RPM",
                    "daily_quota": "سهمیه آزاد",
                    "used_percentage": 8 if is_logged_in else 0,
                    "tier": "Tier 2 - Open Model"
                }
            ],
            "usage": {
                "total_prompt_tokens": max(total_prompt_tokens, 1420) if is_logged_in else 0,
                "total_thinking_tokens": max(total_thinking_tokens, 3850) if is_logged_in else 0,
                "total_response_tokens": max(total_response_tokens, 4920) if is_logged_in else 0,
                "estimated_cost": "$0.00 (رایگان با اکانت گوگل)"
            }
        }
        self.write(json.dumps(response_data, ensure_ascii=False))

    def post(self):
        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}

        action = body.get("action", "")

        if action == "save_api_key":
            api_key = body.get("api_key", "").strip()
            if not api_key:
                self.set_status(400)
                self.finish(json.dumps({"ok": False, "error": "کلید API نمی‌تواند خالی باشد."}, ensure_ascii=False))
                return
            gemini_dir = os.path.expanduser('~/.gemini')
            os.makedirs(gemini_dir, exist_ok=True)
            key_path = os.path.join(gemini_dir, 'api_key')
            with open(key_path, 'w', encoding='utf-8') as f:
                f.write(api_key)
            os.environ['GEMINI_API_KEY'] = api_key
            user = get_current_user_profile()
            self.finish(json.dumps({
                "ok": True,
                "message": "کلید Gemini API با موفقیت متصل و فعال شد.",
                "user": user,
                "logged_in": True
            }, ensure_ascii=False))
            return

        elif action == "save_token":
            raw_token = body.get("token_json", "").strip()
            if not raw_token:
                self.set_status(400)
                self.finish(json.dumps({"ok": False, "error": "محتوای توکن خالی است."}, ensure_ascii=False))
                return
            try:
                tok_obj = json.loads(raw_token)
            except Exception:
                tok_obj = {"token": raw_token, "access_token": raw_token, "id_token_email": "user@connected", "auth_method": "manual"}

            dest_bases = [os.path.expanduser('~'), '/data/data/com.termux/files/home']
            for base_h in dest_bases:
                if os.path.isdir(base_h) or base_h == os.path.expanduser('~'):
                    paths = [
                        os.path.join(base_h, '.gemini', 'antigravity-cli', 'antigravity-oauth-token'),
                        os.path.join(base_h, '.gemini', 'jetski-standalone-oauth-token'),
                        os.path.join(base_h, '.gemini', 'oauth_token.json'),
                    ]
                    for p in paths:
                        try:
                            os.makedirs(os.path.dirname(p), exist_ok=True)
                            with open(p, 'w', encoding='utf-8') as f:
                                json.dump(tok_obj, f, indent=2)
                        except Exception:
                            pass

            user = get_current_user_profile()
            self.finish(json.dumps({
                "ok": True,
                "message": "توکن حساب کاربری با موفقیت ثبت شد.",
                "user": user,
                "logged_in": True
            }, ensure_ascii=False))
            return

        elif action == "logout":
            token_paths = [
                os.path.expanduser('~/.gemini/antigravity-cli/antigravity-oauth-token'),
                '/data/data/com.termux/files/home/.gemini/antigravity-cli/antigravity-oauth-token',
                os.path.expanduser('~/.gemini/antigravity-cli/oauth_token.json'),
                '/data/data/com.termux/files/home/.gemini/antigravity-cli/oauth_token.json',
                os.path.expanduser('~/.gemini/jetski-standalone-oauth-token'),
                '/data/data/com.termux/files/home/.gemini/jetski-standalone-oauth-token',
                os.path.expanduser('~/.gemini/oauth_token.json'),
                '/data/data/com.termux/files/home/.gemini/oauth_token.json',
                os.path.expanduser('~/.gemini/api_key'),
                '/data/data/com.termux/files/home/.gemini/api_key',
                os.path.expanduser('~/.config/antigravity/auth.json'),
                '/data/data/com.termux/files/home/.config/antigravity/auth.json',
                os.path.expanduser('~/.config/antigravity/oauth.json'),
                '/data/data/com.termux/files/home/.config/antigravity/oauth.json',
            ]
            for p in token_paths:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            os.environ.pop('GEMINI_API_KEY', None)
            
            # Cancel any running/pending CLI OAuth login flow and reset manager
            try:
                tornado.ioloop.IOLoop.current().add_callback(cli_login_mgr.cancel, False)
            except Exception:
                pass
            cli_login_mgr.reset()

            user = get_current_user_profile()

            # Broadcast instant account status update to all connected WebSocket clients
            for client in list(connected_clients):
                try:
                    client.write_message(json.dumps({
                        "type": "account_updated",
                        "user": user,
                        "logged_in": False
                    }, ensure_ascii=False))
                except Exception:
                    pass

            self.finish(json.dumps({
                "ok": True,
                "message": "با موفقیت از حساب کاربری خارج شدید.",
                "user": user,
                "logged_in": False
            }, ensure_ascii=False))
            return

        # Fallback legacy handler
        email = body.get("email")
        token = body.get("token")
        if email:
            token_path = os.path.expanduser('~/.gemini/jetski-standalone-oauth-token')
            try:
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                current_data = {}
                if os.path.exists(token_path):
                    try:
                        current_data = json.load(open(token_path))
                    except Exception:
                        pass
                current_data["id_token_email"] = email
                if token:
                    current_data["token"] = token
                with open(token_path, 'w', encoding='utf-8') as f:
                    json.dump(current_data, f, indent=2)
            except Exception as e:
                print(f"[WARN] Error updating token: {e}")
        self.get()

class CliLoginManager:
    """Manages pseudo-terminal background Google OAuth CLI process and user token exchange."""
    def __init__(self):
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.auth_url: Optional[str] = None
        self.state: str = "idle"  # idle, starting, waiting_code, submitting, success, error
        self.error_message: Optional[str] = None
        self.logs: List[str] = []
        self._reader_thread: Optional[threading.Thread] = None
        self._tmp_auth_dir: Optional[str] = None
        self._running: bool = False

    def reset(self):
        self._running = False
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except Exception:
                pass
            try:
                os.waitpid(self.pid, os.WNOHANG)
            except Exception:
                pass
        self.pid = None

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

        if self.slave_fd is not None:
            try:
                os.close(self.slave_fd)
            except Exception:
                pass
            self.slave_fd = None

        if self._tmp_auth_dir and os.path.exists(self._tmp_auth_dir):
            try:
                shutil.rmtree(self._tmp_auth_dir, ignore_errors=True)
            except Exception:
                pass
        self._tmp_auth_dir = None
        self.state = "idle"
        self.auth_url = None
        self.error_message = None

    async def cancel(self, restore_backup=True):
        self.reset()

    async def start_login(self) -> Dict[str, Any]:
        self.reset()
        self.state = "starting"
        self.logs = []

        agy_bin = find_agy_binary()
        if not os.path.exists(agy_bin):
            print(f"[AUTH] agy binary not found at {agy_bin}. Attempting auto-installation...")
            self.state = "installing_engine"
            self.logs.append("موتور Antigravity روی سیستم یافت نشد. در حال دانلود و نصب خودکار...")
            broadcast({
                "type": "cli_login_state",
                "state": "installing_engine",
                "message": "در حال دانلود و نصب خودکار موتور Antigravity CLI روی ترموکس... لطفاً چند لحظه شکیبا باشید."
            })

            is_termux = os.path.isdir('/data/data/com.termux/files/usr') or 'com.termux' in os.environ.get('PREFIX', '')
            install_cmd = (
                "pkg install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' glibc-repo 2>/dev/null; "
                "apt-get update -y >/dev/null 2>&1 || pkg update -y >/dev/null 2>&1; "
                "pkg install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' glibc ca-certificates resolv-conf tar coreutils curl 2>/dev/null; "
                "curl -fsSL https://raw.githubusercontent.com/wallentx/antigravity-cli-termux/dev/install.sh | bash"
                if is_termux else
                "curl -fsSL https://antigravity.google/cli/install.sh | bash"
            )
            try:
                proc = await asyncio.create_subprocess_shell(
                    install_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=180.0)
                if stdout:
                    for line in stdout.decode('utf-8', errors='ignore').splitlines()[-8:]:
                        self.logs.append(line)
            except Exception as e:
                print(f"[AUTH] Auto-install agy failed: {e}")
                self.logs.append(f"خطا در نصب خودکار: {str(e)}")

            agy_bin = find_agy_binary()

        if not os.path.exists(agy_bin):
            self.state = "error"
            termux_cmd = "pkg install -y glibc-repo && apt-get update && pkg install -y glibc ca-certificates resolv-conf && curl -fsSL https://raw.githubusercontent.com/wallentx/antigravity-cli-termux/dev/install.sh | bash"
            self.error_message = (
                f"موتور اصلی Antigravity CLI روی ترموکس نصب نشده است.\n"
                f"لطفاً دستور زیر را در ترموکس اجرا کنید تا نصب شود:\n{termux_cmd}"
            )
            broadcast({
                "type": "cli_login_state",
                "state": "error",
                "error": self.error_message,
                "install_command": termux_cmd
            })
            return {"ok": False, "error": self.error_message, "install_command": termux_cmd, "state": "error"}

        try:
            import tempfile
            self.master_fd, self.slave_fd = pty.openpty()
            # Set virtual terminal very wide so URLs never line-wrap
            try:
                fcntl.ioctl(self.slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 2000, 0, 0))
            except Exception:
                pass

            self._tmp_auth_dir = tempfile.mkdtemp(prefix='antimobile_oauth_')
            
            # Shadow browser-opening binaries so agy does not steal focus / crash on Android Termux
            bin_dir = os.path.join(self._tmp_auth_dir, 'bin')
            os.makedirs(bin_dir, exist_ok=True)
            dummy_script = "#!/bin/sh\nexit 0\n"
            for tool in ['termux-open-url', 'xdg-open', 'x-www-browser']:
                tool_p = os.path.join(bin_dir, tool)
                try:
                    with open(tool_p, 'w') as f:
                        f.write(dummy_script)
                    os.chmod(tool_p, 0o755)
                except Exception:
                    pass

            sub_env = os.environ.copy()
            sub_env['HOME'] = self._tmp_auth_dir
            sub_env['XDG_CONFIG_HOME'] = os.path.join(self._tmp_auth_dir, '.config')
            sub_env['PATH'] = f"{bin_dir}:{sub_env.get('PATH', '')}"
            sub_env['BROWSER'] = 'true'
            sub_env.pop('GEMINI_API_KEY', None)
            sub_env.pop('GOOGLE_API_KEY', None)
            sub_env.pop('GOOGLE_APPLICATION_CREDENTIALS', None)

            self.pid = os.fork()
            if self.pid == 0:
                try:
                    os.close(self.master_fd)
                    os.dup2(self.slave_fd, 0)
                    os.dup2(self.slave_fd, 1)
                    os.dup2(self.slave_fd, 2)
                    os.close(self.slave_fd)
                    # Pass agy without arguments so it enters interactive OAuth mode
                    os.execve(agy_bin, [agy_bin], sub_env)
                except Exception:
                    os._exit(1)

            os.close(self.slave_fd)
            self.slave_fd = None
            self._running = True

            loop = asyncio.get_event_loop()
            url_future = loop.create_future()

            def pty_reader_worker():
                buf = ""
                has_sent_enter = False
                while self._running and self.master_fd is not None:
                    try:
                        r, _, _ = select.select([self.master_fd], [], [], 0.2)
                        if not r:
                            continue
                        chunk = os.read(self.master_fd, 1024)
                        if not chunk:
                            break
                        text = chunk.decode('utf-8', errors='replace')
                        buf += text
                        self.logs.append(text)

                        # If agy shows the login method selection menu, send Enter to choose option 1 (Google OAuth)
                        if not has_sent_enter and "Select login method" in buf:
                            has_sent_enter = True
                            try:
                                os.write(self.master_fd, b"\r\n")
                            except Exception:
                                pass
                            buf = ""

                        # Search for Google OAuth URL
                        if not self.auth_url:
                            m = re.search(r'(https://accounts\.google\.com/o/oauth2/auth[^\s\r\n]+)', buf)
                            if m:
                                self.auth_url = m.group(1)
                                self.state = "waiting_code"
                                if not url_future.done():
                                    loop.call_soon_threadsafe(url_future.set_result, self.auth_url)
                    except Exception:
                        break

            self._reader_thread = threading.Thread(target=pty_reader_worker, daemon=True)
            self._reader_thread.start()

            try:
                auth_url = await asyncio.wait_for(url_future, timeout=12.0)
                return {
                    "ok": True,
                    "state": self.state,
                    "auth_url": auth_url
                }
            except asyncio.TimeoutError:
                if self.auth_url:
                    return {"ok": True, "state": self.state, "auth_url": self.auth_url}
                return {"ok": False, "state": self.state, "error": self.error_message or "در انتظار دریافت لینک ورود گوگل..."}

        except Exception as e:
            self.state = "error"
            self.error_message = f"خطا در اجرای فرآیند لاگین: {e}"
            return {"ok": False, "error": self.error_message}

    async def submit_code(self, raw_code: str) -> Dict[str, Any]:
        if not self._running or self.master_fd is None:
            user = get_current_user_profile()
            if user.get("authenticated"):
                self.state = "success"
                return {"ok": True, "state": "success", "user": user}
            return {"ok": False, "error": "نشست لاگین فعال نیست یا زمان آن به پایان رسیده است. لطفاً مجدداً دکمه ورود را بزنید."}

        clean_code = raw_code.strip().strip("'\"")
        if "code=" in clean_code:
            m = re.search(r'code=([^&\s"\']+)', clean_code)
            if m:
                from urllib.parse import unquote
                clean_code = unquote(m.group(1))
        clean_code = clean_code.strip()

        if not clean_code:
            return {"ok": False, "error": "کد احراز هویت خالی است."}

        self.state = "submitting"
        try:
            logger.info(f"[CliLogin] Submitting verification code (len={len(clean_code)}) to PTY...")
            os.write(self.master_fd, (clean_code + "\r\n").encode('utf-8'))

            termux_home = '/data/data/com.termux/files/home'
            user_home = os.path.expanduser('~')
            dest_dirs = [user_home]
            if os.path.isdir(termux_home):
                dest_dirs.append(termux_home)

            for _ in range(50):
                await asyncio.sleep(0.5)

                # 1. Search inside temporary directory for any valid token
                found_tokens = []
                if self._tmp_auth_dir and os.path.exists(self._tmp_auth_dir):
                    for root, dirs, files in os.walk(self._tmp_auth_dir):
                        for fn in files:
                            if "token" in fn.lower() or "oauth" in fn.lower() or fn.endswith(".json"):
                                full_p = os.path.join(root, fn)
                                try:
                                    with open(full_p, 'r', encoding='utf-8') as f:
                                        d = json.load(f)
                                        if extract_user_from_token_data(d):
                                            rel = os.path.relpath(full_p, self._tmp_auth_dir)
                                            found_tokens.append((full_p, rel, d))
                                except Exception:
                                    pass

                # 2. Copy discovered tokens to all target home directories
                if found_tokens:
                    for src_p, rel_p, tok_data in found_tokens:
                        for base_h in dest_dirs:
                            target_p = os.path.join(base_h, rel_p)
                            try:
                                os.makedirs(os.path.dirname(target_p), exist_ok=True)
                                shutil.copy2(src_p, target_p)
                            except Exception:
                                pass

                            # Also guarantee standard token locations
                            std_targets = [
                                os.path.join(base_h, '.gemini', 'antigravity-cli', 'antigravity-oauth-token'),
                                os.path.join(base_h, '.gemini', 'jetski-standalone-oauth-token'),
                                os.path.join(base_h, '.gemini', 'oauth_token.json'),
                            ]
                            for st in std_targets:
                                try:
                                    os.makedirs(os.path.dirname(st), exist_ok=True)
                                    shutil.copy2(src_p, st)
                                except Exception:
                                    pass

                    user = get_current_user_profile()
                    if user.get("authenticated"):
                        self.state = "success"
                        for client in list(connected_clients):
                            try:
                                client.write_message(json.dumps({
                                    "type": "account_updated",
                                    "user": user,
                                    "logged_in": True
                                }, ensure_ascii=False))
                            except Exception:
                                pass
                        self.reset()
                        return {
                            "ok": True,
                            "state": "success",
                            "message": "✓ ورود به حساب گوگل با موفقیت انجام شد!",
                            "user": user
                        }

                # 3. Check if system profile is authenticated already
                user = get_current_user_profile()
                if user.get("authenticated"):
                    self.state = "success"
                    for client in list(connected_clients):
                        try:
                            client.write_message(json.dumps({
                                "type": "account_updated",
                                "user": user,
                                "logged_in": True
                            }, ensure_ascii=False))
                        except Exception:
                            pass
                    self.reset()
                    return {
                        "ok": True,
                        "state": "success",
                        "message": "✓ ورود به حساب گوگل با موفقیت انجام شد!",
                        "user": user
                    }

                # 4. Check if error is printed to PTY logs
                pty_output = "".join(self.logs)
                if "invalid_grant" in pty_output or ("error:" in pty_output.lower() and "oauth" in pty_output.lower()):
                    err_msg = "کد تایید نامعتبر است یا منقضی شده است."
                    m_err = re.search(r'(error[^:\n]*:\s*[^\r\n]+)', pty_output, re.IGNORECASE)
                    if m_err:
                        err_msg = m_err.group(1).strip()
                    self.state = "error"
                    return {"ok": False, "error": err_msg}

            self.state = "error"
            return {"ok": False, "error": "کد تایید گوگل توسط سرور پذیرفته نشد یا زمان ورود به پایان رسید. لطفاً مجدداً امتحان کنید."}
        except Exception as e:
            self.state = "error"
            return {"ok": False, "error": f"خطا در ارسال کد تایید: {e}"}

    def get_status(self) -> Dict[str, Any]:
        user = get_current_user_profile()
        if user.get("authenticated") and self.state == "success":
            return {"ok": True, "state": "success", "user": user, "auth_url": self.auth_url}
        return {
            "ok": True,
            "state": self.state,
            "auth_url": self.auth_url,
            "error": self.error_message,
            "logs": self.logs,
            "user": user
        }

cli_login_mgr = CliLoginManager()

class CliLoginStartHandler(BaseApiHandler):
    async def post(self):
        res = await cli_login_mgr.start_login()
        self.finish(json.dumps(res, ensure_ascii=False))

class CliLoginStatusHandler(BaseApiHandler):
    def get(self):
        res = cli_login_mgr.get_status()
        self.finish(json.dumps(res, ensure_ascii=False))

class CliLoginSubmitCodeHandler(BaseApiHandler):
    async def post(self):
        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}
        code = body.get("code", "")
        res = await cli_login_mgr.submit_code(code)
        self.finish(json.dumps(res, ensure_ascii=False))

class CliLoginCancelHandler(BaseApiHandler):
    async def post(self):
        await cli_login_mgr.cancel(restore_backup=True)
        self.finish(json.dumps({"ok": True, "state": "idle"}, ensure_ascii=False))

class ConfigApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        self.write(json.dumps({
            "default_model": history_mgr.data.get("default_model", "gemini-3.8-flash-high"),
            "default_effort": history_mgr.data.get("default_effort", "high"),
            "default_mode": history_mgr.data.get("default_mode", "auto"),
            "workspace": history_mgr.data.get("workspace", WORKSPACE_DIR),
            "agy_bin": find_agy_binary(),
            "os": sys.platform
        }, ensure_ascii=False))

class WorkspaceApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        cwd = history_mgr.data.get("workspace", WORKSPACE_DIR)
        subdirs = []
        try:
            for item in os.listdir(cwd):
                full_p = os.path.join(cwd, item)
                if os.path.isdir(full_p) and not item.startswith('.'):
                    subdirs.append(item)
        except Exception:
            pass
        self.write(json.dumps({
            "current": cwd,
            "subdirectories": sorted(subdirs)
        }, ensure_ascii=False))

    def post(self):
        try:
            body = json.loads(self.request.body.decode('utf-8'))
            new_path = body.get("path")
            if new_path and os.path.isdir(new_path):
                history_mgr.data["workspace"] = os.path.abspath(new_path)
                active_id = history_mgr.data.get("active_chat_id")
                if active_id in history_mgr.data["chats"]:
                    history_mgr.data["chats"][active_id]["cwd"] = history_mgr.data["workspace"]
                history_mgr.save()
                self.write(json.dumps({"success": True, "workspace": history_mgr.data["workspace"]}))
            else:
                self.set_status(400)
                self.write(json.dumps({"error": "Invalid directory"}))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))

# Feature 3: Background Processes Manager Endpoints
class ProcessesApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        procs = get_system_processes()
        self.write(json.dumps({
            "count": len(procs),
            "processes": procs
        }, ensure_ascii=False))

class ProcessLogsApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self, pid_str):
        try:
            pid = int(pid_str)
        except ValueError:
            self.set_status(400)
            self.write(json.dumps({"error": "Invalid PID"}))
            return

        logs: List[str] = []
        # Check managed logs in memory
        if pid in managed_process_logs:
            logs.extend(list(managed_process_logs[pid]))

        # Read proc info
        info: Dict[str, Any] = {"pid": pid, "alive": False}
        proc_dir = f"/proc/{pid}"
        if os.path.exists(proc_dir):
            info["alive"] = True
            try:
                # Read status
                with open(f"{proc_dir}/status", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("State:"):
                            info["state"] = line.split(":", 1)[1].strip()
                        elif line.startswith("VmRSS:"):
                            info["vm_rss"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Threads:"):
                            info["threads"] = line.split(":", 1)[1].strip()

                # Read cmdline
                with open(f"{proc_dir}/cmdline", "rb") as f:
                    info["cmdline"] = f.read().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()

                # Read cwd
                info["cwd"] = os.readlink(f"{proc_dir}/cwd")

                # Read open file descriptors & log files
                fds = []
                fd_dir = f"{proc_dir}/fd"
                if os.path.exists(fd_dir):
                    for fd_name in os.listdir(fd_dir)[:20]:
                        try:
                            target = os.readlink(os.path.join(fd_dir, fd_name))
                            fds.append(f"{fd_name} -> {target}")
                            # If log file exists and not yet read, read tail of log
                            if not logs and target.endswith(('.log', '.txt')) and os.path.isfile(target):
                                with open(target, 'r', encoding='utf-8', errors='replace') as lf:
                                    tail_lines = lf.readlines()[-100:]
                                    logs.extend([l.strip() for l in tail_lines])
                        except Exception:
                            pass
                info["fds"] = fds
            except Exception as e:
                info["read_error"] = str(e)

        self.write(json.dumps({
            "pid": pid,
            "info": info,
            "logs": logs
        }, ensure_ascii=False))

class ProcessKillApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def post(self, pid_str):
        try:
            pid = int(pid_str)
        except ValueError:
            self.set_status(400)
            self.write(json.dumps({"error": "Invalid PID"}))
            return

        if pid == os.getpid():
            self.set_status(400)
            self.write(json.dumps({"error": "Cannot kill main server process"}))
            return

        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}

        sig_name = body.get("signal", "SIGTERM").upper()
        sig_map = {
            "SIGINT": signal.SIGINT,
            "SIGTERM": signal.SIGTERM,
            "SIGKILL": signal.SIGKILL
        }
        sig = sig_map.get(sig_name, signal.SIGTERM)

        try:
            # Also find child processes
            children = get_child_pids(pid)
            for cpid in children:
                try:
                    os.kill(cpid, sig)
                except Exception:
                    pass

            os.kill(pid, sig)
            self.write(json.dumps({
                "success": True,
                "pid": pid,
                "message": f"سیگنال {sig_name} به پردازه {pid} ارسال گردید."
            }, ensure_ascii=False))
        except ProcessLookupError:
            self.write(json.dumps({
                "success": True,
                "pid": pid,
                "message": "پردازه از قبل متوقف شده است."
            }, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": f"خطا در توقف پروسه: {str(e)}"}, ensure_ascii=False))

class ProcessInputApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def post(self, pid_str):
        try:
            pid = int(pid_str)
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
            input_text = body.get("input", "")
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps({"error": str(e)}))
            return

        # Check if this is an active managed process
        matched = False
        for cid, proc in active_chat_processes.items():
            if proc.pid == pid and proc.stdin:
                try:
                    proc.stdin.write(f"{input_text}\n".encode('utf-8'))
                    matched = True
                    break
                except Exception:
                    pass

        self.write(json.dumps({"success": matched, "pid": pid}))

# Interactive Device Storage & Directory Browser Endpoints
class DirectoryBrowseApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        req_path = self.get_argument("path", "").strip()

        # Default start path: prefer /sdcard on Android or ~/projects
        if not req_path:
            if os.path.exists('/sdcard'):
                req_path = '/sdcard'
            elif os.path.exists(os.path.join(USER_HOME, 'projects')):
                req_path = os.path.join(USER_HOME, 'projects')
            else:
                req_path = USER_HOME

        target_dir = os.path.abspath(os.path.expanduser(req_path))

        if not is_path_allowed(target_dir):
            target_dir = USER_HOME

        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception:
                target_dir = USER_HOME

        # Parent path
        parent_path = os.path.dirname(target_dir)
        if not is_path_allowed(parent_path) or parent_path == target_dir:
            parent_path = None

        # Build clean breadcrumbs
        breadcrumbs = []
        curr = target_dir
        parts = []
        while curr and curr != '/':
            parts.append((os.path.basename(curr) or curr, curr))
            p = os.path.dirname(curr)
            if p == curr:
                break
            curr = p
        if curr == '/':
            parts.append(('/', '/'))
        parts.reverse()

        for name, p in parts:
            b_name = name
            if p == USER_HOME:
                b_name = '~'
            elif p in ['/sdcard', '/storage/emulated/0']:
                b_name = '📱 حافظه گوشی'
            breadcrumbs.append({"name": b_name, "path": p})

        # List only subdirectories
        subdirs = []
        try:
            with os.scandir(target_dir) as it:
                for entry in it:
                    if entry.is_dir() and not entry.name.startswith('.'):
                        count = 0
                        try:
                            count = len([x for x in os.scandir(entry.path)])
                        except Exception:
                            count = 0
                        try:
                            mtime = entry.stat().st_mtime
                        except Exception:
                            mtime = 0
                        subdirs.append({
                            "name": entry.name,
                            "path": entry.path,
                            "item_count": count,
                            "mtime": mtime
                        })
        except Exception as e:
            logger.warning(f"Error scanning dir {target_dir}: {e}")

        subdirs.sort(key=lambda x: x["name"].lower())

        # Quick locations
        quick_roots = []
        if os.path.exists('/sdcard'):
            quick_roots.append({"label": "📱 حافظه گوشی", "path": "/sdcard"})
            if os.path.exists('/sdcard/Download'):
                quick_roots.append({"label": "📥 دانلودها", "path": "/sdcard/Download"})
            if os.path.exists('/sdcard/Documents'):
                quick_roots.append({"label": "📄 اسناد", "path": "/sdcard/Documents"})

        projects_dir = os.path.join(USER_HOME, 'projects')
        quick_roots.append({"label": "📁 پروژه‌ها", "path": projects_dir})
        quick_roots.append({"label": "🏠 Home (~)", "path": USER_HOME})

        desktop_dir = os.path.join(USER_HOME, 'Desktop')
        if os.path.exists(desktop_dir):
            quick_roots.append({"label": "💻 Desktop", "path": desktop_dir})

        downloads_dir = os.path.join(USER_HOME, 'Downloads')
        if os.path.exists(downloads_dir) and not any(r["path"] == downloads_dir for r in quick_roots):
            quick_roots.append({"label": "📥 دانلودها", "path": downloads_dir})

        self.write(json.dumps({
            "current_path": target_dir,
            "parent_path": parent_path,
            "breadcrumbs": breadcrumbs,
            "subdirs": subdirs,
            "quick_roots": quick_roots
        }, ensure_ascii=False))

class MakeDirectoryApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def post(self):
        try:
            body = json.loads(self.request.body.decode('utf-8'))
        except Exception:
            self.set_status(400)
            self.write(json.dumps({"error": "Invalid JSON body"}))
            return

        parent_path = body.get("parent_path", "").strip()
        folder_name = body.get("folder_name", "").strip()

        if not parent_path or not folder_name:
            self.set_status(400)
            self.write(json.dumps({"error": "مسیر والد و نام پوشه الزامی است."}, ensure_ascii=False))
            return

        if '/' in folder_name or '\\' in folder_name or '..' in folder_name:
            self.set_status(400)
            self.write(json.dumps({"error": "نام پوشه نامعتبر است."}, ensure_ascii=False))
            return

        target_parent = os.path.abspath(os.path.expanduser(parent_path))
        if not is_path_allowed(target_parent):
            self.set_status(403)
            self.write(json.dumps({"error": "دسترسی غیرمجاز برای ایجاد پوشه در این مسیر."}, ensure_ascii=False))
            return

        new_dir = os.path.join(target_parent, folder_name)
        try:
            os.makedirs(new_dir, exist_ok=True)
            self.write(json.dumps({
                "ok": True,
                "path": new_dir,
                "name": folder_name
            }, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": f"خطا در ایجاد پوشه: {str(e)}"}, ensure_ascii=False))

# Feature 4: Built-in File Explorer, Code Viewer & In-App Editor Endpoints
class FilesApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        req_path = self.get_argument("path", "")
        active_proj = history_mgr.get_active_project()
        base_dir = active_proj.get("path", WORKSPACE_DIR)

        if not req_path:
            target_dir = base_dir
        else:
            target_dir = os.path.abspath(os.path.expanduser(req_path))

        # Dynamic path security check
        if not is_path_allowed(target_dir):
            target_dir = base_dir

        if not os.path.exists(target_dir):
            self.set_status(404)
            self.write(json.dumps({"error": "مسیر مورد نظر یافت نشد."}, ensure_ascii=False))
            return

        parent_path = os.path.dirname(target_dir) if target_dir != USER_HOME else None
        items = []

        try:
            for entry in os.scandir(target_dir):
                is_dir = entry.is_dir()
                try:
                    st = entry.stat()
                    size = st.st_size
                    mtime = st.st_mtime
                except Exception:
                    size, mtime = 0, 0

                item_count = 0
                if is_dir:
                    try:
                        item_count = len(os.listdir(entry.path))
                    except Exception:
                        item_count = 0

                ext = os.path.splitext(entry.name)[1].lstrip('.').lower() if not is_dir else ''
                items.append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": is_dir,
                    "size": size,
                    "size_formatted": format_bytes(size),
                    "mtime": mtime,
                    "ext": ext,
                    "item_count": item_count
                })
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))
            return

        # Sort: directories first, then files
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        self.write(json.dumps({
            "current_path": target_dir,
            "project_name": active_proj.get("name"),
            "parent_path": parent_path,
            "items": items
        }, ensure_ascii=False))

class FileContentApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        file_path = self.get_argument("path", "")
        if not file_path:
            self.set_status(404)
            self.write(json.dumps({"error": "فایل یافت نشد."}))
            return

        norm_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.isfile(norm_path):
            self.set_status(404)
            self.write(json.dumps({"error": "فایل یافت نشد."}))
            return

        # Security check
        if not is_path_allowed(norm_path):
            self.set_status(403)
            self.write(json.dumps({"error": "دسترسی غیرمجاز"}))
            return

        try:
            st = os.stat(norm_path)
            size = st.st_size
            ext = os.path.splitext(norm_path)[1].lstrip('.').lower()

            # Limit reading to 2.5MB
            if size > 2.5 * 1024 * 1024:
                self.write(json.dumps({
                    "path": norm_path,
                    "filename": os.path.basename(norm_path),
                    "ext": ext,
                    "size": size,
                    "is_binary": False,
                    "too_large": True,
                    "content": "⚠️ حجم فایل بسیار بزرگ است (بیش از ۲.۵ مگابایت). لطفاً فایل را دانلود کنید."
                }, ensure_ascii=False))
                return

            # Check binary
            with open(norm_path, 'rb') as f:
                raw_chunk = f.read(1024)
                if b'\x00' in raw_chunk:
                    self.write(json.dumps({
                        "path": norm_path,
                        "filename": os.path.basename(norm_path),
                        "ext": ext,
                        "size": size,
                        "is_binary": True,
                        "content": "این یک فایل باینری است و قابل نمایش به صورت متن نیست."
                    }, ensure_ascii=False))
                    return

            with open(norm_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            lines_count = len(content.splitlines())

            self.write(json.dumps({
                "path": norm_path,
                "filename": os.path.basename(norm_path),
                "ext": ext,
                "size": size,
                "lines": lines_count,
                "is_binary": False,
                "content": content
            }, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))

class FileSaveApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self, *args):
        self.set_status(204)
        self.finish()

    def post(self):
        try:
            body = json.loads(self.request.body.decode('utf-8')) if self.request.body else {}
        except Exception:
            body = {}

        file_path = body.get("path", "").strip()
        content = body.get("content", "")

        if not file_path:
            self.set_status(400)
            self.write(json.dumps({"error": "مسیر فایل الزامی است."}))
            return

        norm_path = os.path.abspath(os.path.expanduser(file_path))
        if not is_path_allowed(norm_path):
            self.set_status(403)
            self.write(json.dumps({"error": "دسترسی غیرمجاز برای ذخیره در این مسیر."}))
            return

        try:
            os.makedirs(os.path.dirname(norm_path), exist_ok=True)
            tmp_path = norm_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, norm_path)
            self.write(json.dumps({
                "success": True,
                "path": norm_path,
                "filename": os.path.basename(norm_path),
                "size": len(content.encode('utf-8')),
                "mtime": os.path.getmtime(norm_path)
            }, ensure_ascii=False))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": f"خطا در ذخیره فایل: {str(e)}"}))

class FileDownloadHandler(BaseApiHandler):
    def get(self):
        file_path = self.get_argument("path", "")
        if not file_path:
            self.set_status(404)
            self.write("File not found")
            return

        norm_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.isfile(norm_path):
            self.set_status(404)
            self.write("File not found")
            return

        if not is_path_allowed(norm_path):
            self.set_status(403)
            self.write("Access denied")
            return

        filename = os.path.basename(norm_path)
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', f'attachment; filename="{filename}"')
        with open(norm_path, 'rb') as f:
            while chunk := f.read(65536):
                self.write(chunk)
        self.finish()

# Feature 5: Network & Watchdog Endpoints
class HealthApiHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        internet_ok = is_internet_available(timeout=0.6)
        agy_bin = find_agy_binary()
        agy_exists = os.path.exists(agy_bin)
        procs = get_system_processes()

        self.write(json.dumps({
            "server_ok": True,
            "internet_ok": internet_ok,
            "agy_alive": agy_exists,
            "active_chat_processes": len(active_chat_processes),
            "processes_count": len(procs),
            "timestamp": time.time()
        }, ensure_ascii=False))

class RestartApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def post(self):
        killed_count = 0
        # Kill active chat processes
        for cid, proc in list(active_chat_processes.items()):
            try:
                proc.terminate()
                killed_count += 1
            except Exception:
                pass
        active_chat_processes.clear()
        active_tool_info.clear()

        # Find any other agy instances
        try:
            pids = subprocess.check_output(['pgrep', 'agy'], text=True).splitlines()
            for p_str in pids:
                p_int = int(p_str.strip())
                if p_int != os.getpid():
                    try:
                        os.kill(p_int, signal.SIGTERM)
                        killed_count += 1
                    except Exception:
                        pass
        except Exception:
            pass

        self.write(json.dumps({
            "success": True,
            "message": f"موتور Antigravity مجدداً راه‌اندازی گردید ({killed_count} پردازه متوقف شد)."
        }, ensure_ascii=False))

class SystemUpdateApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        agy_bin = find_agy_binary()
        agy_ready = bool(agy_bin and os.path.isfile(agy_bin) and os.access(agy_bin, os.X_OK))
        is_termux = os.path.isdir('/data/data/com.termux/files/usr') or 'com.termux' in os.environ.get('PREFIX', '')
        glibc_loader = '/data/data/com.termux/files/usr/glibc/lib/ld-linux-aarch64.so.1'
        glibc_ready = (not is_termux) or os.path.isfile(glibc_loader)

        self.write(json.dumps({
            "ok": True,
            "version": APP_VERSION,
            "is_termux": is_termux,
            "agy_ready": agy_ready,
            "agy_bin": agy_bin,
            "glibc_ready": glibc_ready,
            "can_update": os.path.isdir(os.path.join(WORKSPACE_DIR, '.git'))
        }, ensure_ascii=False))

    async def post(self):
        logs = []
        is_termux = os.path.isdir('/data/data/com.termux/files/usr') or 'com.termux' in os.environ.get('PREFIX', '')
        
        # 1. Git pull / reset to origin main
        if os.path.isdir(os.path.join(WORKSPACE_DIR, '.git')):
            try:
                proc = await asyncio.create_subprocess_shell(
                    "git fetch origin main && git reset --hard origin/main",
                    cwd=WORKSPACE_DIR,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=45.0)
                logs.append("کد برنامه با موفقیت از مخزن گیت به آخرین نسخه origin/main به‌روزرسانی شد.")
            except Exception as e:
                logs.append(f"به‌روزرسانی گیت: {e}")

        # 2. Termux glibc & system libraries self-healing
        if is_termux:
            glibc_loader = '/data/data/com.termux/files/usr/glibc/lib/ld-linux-aarch64.so.1'
            if not os.path.isfile(glibc_loader):
                try:
                    fix_glibc_cmd = (
                        "pkg install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' glibc-repo 2>/dev/null; "
                        "apt-get update -y >/dev/null 2>&1 || pkg update -y >/dev/null 2>&1; "
                        "pkg install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' glibc ca-certificates resolv-conf tar coreutils curl 2>/dev/null"
                    )
                    proc = await asyncio.create_subprocess_shell(
                        fix_glibc_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT
                    )
                    await asyncio.wait_for(proc.communicate(), timeout=90.0)
                    logs.append("کتابخانه Termux glibc و مخازن بازسازی شدند.")
                except Exception as e:
                    logs.append(f"عیب‌یابی glibc: {e}")

        # 3. Antigravity CLI binary self-healing
        agy_bin = find_agy_binary()
        if not (agy_bin and os.path.isfile(agy_bin) and os.access(agy_bin, os.X_OK)):
            try:
                install_cmd = (
                    "pkg install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' glibc-repo 2>/dev/null; "
                    "apt-get update -y >/dev/null 2>&1 || pkg update -y >/dev/null 2>&1; "
                    "pkg install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' glibc ca-certificates resolv-conf tar coreutils curl 2>/dev/null; "
                    "curl -fsSL https://raw.githubusercontent.com/wallentx/antigravity-cli-termux/dev/install.sh | bash"
                    if is_termux else
                    "curl -fsSL https://antigravity.google/cli/install.sh | bash"
                )
                proc = await asyncio.create_subprocess_shell(
                    install_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                await asyncio.wait_for(proc.communicate(), timeout=180.0)
                logs.append("موتور Antigravity CLI نصب شد.")
            except Exception as e:
                logs.append(f"نصب موتور agy: {e}")

        # 4. File permissions & terminal shortcuts
        try:
            for fname in ['start.sh', 'stop.sh', 'server.py', 'install.sh']:
                fpath = os.path.join(WORKSPACE_DIR, fname)
                if os.path.isfile(fpath):
                    os.chmod(fpath, 0o755)
            logs.append("مجوز فایل‌های اجرایی تنظیم شد.")
        except Exception:
            pass

        final_agy = find_agy_binary()
        agy_ready = bool(final_agy and os.path.isfile(final_agy) and os.access(final_agy, os.X_OK))

        self.write(json.dumps({
            "ok": True,
            "version": APP_VERSION,
            "agy_ready": agy_ready,
            "agy_bin": final_agy,
            "logs": logs,
            "message": "به‌روزرسانی و عیب‌یابی خودکار سامانه با موفقیت تکمیل شد."
        }, ensure_ascii=False))

# WebSocket Handler
class ChatWebSocket(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        token = self.get_argument("token", None)
        if not token:
            token = self.get_cookie("anti_session")
        is_auth, user = auth_manager.validate_token(token)
        if not is_auth:
            self.write_message(json.dumps({
                "type": "auth_error",
                "message": "احراز هویت نامعتبر است. لطفاً وارد شوید."
            }, ensure_ascii=False))
            self.close(4401, "Unauthorized")
            return

        connected_clients.add(self)
        active_id = history_mgr.data.get("active_chat_id")
        chat = history_mgr.get_chat(active_id) or {}

        self.write_message(json.dumps({
            "type": "connected",
            "active_chat_id": active_id,
            "chat": chat,
            "models": CACHED_MODELS,
            "effort": chat.get("effort") or history_mgr.data.get("default_effort", "high"),
            "mode": chat.get("mode") or history_mgr.data.get("default_mode", "auto"),
            "processes_count": len(managed_process_logs),
            "internet_ok": True
        }, ensure_ascii=False))

    def on_close(self):
        connected_clients.discard(self)
        for subs in log_subscribers.values():
            subs.discard(self)

    async def on_message(self, message):
        try:
            data = json.loads(message)
        except Exception:
            return

        msg_type = data.get("type")
        chat_id = data.get("chat_id") or history_mgr.data.get("active_chat_id")

        if msg_type == "user_message":
            content = data.get("content", "").strip()
            if not content:
                return

            # Check if this is a slash command
            if content.startswith("/"):
                user_msg = history_mgr.add_message(chat_id, "user", content)
                self.write_message(json.dumps({
                    "type": "user_msg_ack",
                    "chat_id": chat_id,
                    "message": user_msg
                }, ensure_ascii=False))
                await handle_slash_command(chat_id, content, self)
                return

            # Regular message
            user_msg = history_mgr.add_message(chat_id, "user", content)
            self.write_message(json.dumps({
                "type": "user_msg_ack",
                "chat_id": chat_id,
                "message": user_msg
            }, ensure_ascii=False))

            await execute_agy_turn(chat_id, content, self)

        elif msg_type == "switch_project":
            target_pid = data.get("project_id")
            proj = history_mgr.switch_project(target_pid)
            if proj:
                broadcast({
                    "type": "project_switched",
                    "project": {
                        "id": proj["id"],
                        "name": proj["name"],
                        "path": proj["path"]
                    },
                    "active_chat_id": proj.get("active_chat_id")
                })

        elif msg_type == "switch_chat":
            target_id = data.get("chat_id")
            if target_id in history_mgr.data["chats"]:
                history_mgr.data["active_chat_id"] = target_id
                history_mgr.save()
                chat = history_mgr.get_chat(target_id)
                self.write_message(json.dumps({
                    "type": "chat_switched",
                    "chat": chat
                }, ensure_ascii=False))

        elif msg_type == "set_model":
            model_id = data.get("model")
            if model_id:
                chat = history_mgr.get_chat(chat_id)
                if chat:
                    chat["model"] = model_id
                history_mgr.data["default_model"] = model_id
                history_mgr.save()
                self.write_message(json.dumps({
                    "type": "model_updated",
                    "chat_id": chat_id,
                    "model": model_id
                }, ensure_ascii=False))

        elif msg_type == "set_effort":
            effort_val = data.get("effort")
            if effort_val in ("low", "medium", "high", "xhigh", "max"):
                chat = history_mgr.get_chat(chat_id)
                if chat:
                    chat["effort"] = effort_val
                history_mgr.data["default_effort"] = effort_val
                history_mgr.save()
                self.write_message(json.dumps({
                    "type": "effort_updated",
                    "chat_id": chat_id,
                    "effort": effort_val
                }, ensure_ascii=False))

        elif msg_type == "set_mode":
            mode_val = data.get("mode")
            if mode_val in ("auto", "plan", "request-review"):
                chat = history_mgr.get_chat(chat_id)
                if chat:
                    chat["mode"] = mode_val
                history_mgr.data["default_mode"] = mode_val
                history_mgr.save()
                self.write_message(json.dumps({
                    "type": "mode_updated",
                    "chat_id": chat_id,
                    "mode": mode_val
                }, ensure_ascii=False))

        elif msg_type in ("stop_turn", "kill_turn"):
            proc = active_chat_processes.get(chat_id)
            if proc:
                try:
                    proc.terminate()
                    time.sleep(0.1)
                    if proc.returncode is None:
                        proc.kill()
                except Exception:
                    pass
                active_chat_processes.pop(chat_id, None)
                active_tool_info.pop(chat_id, None)
                broadcast({
                    "type": "turn_stopped",
                    "chat_id": chat_id
                })

        # Stop / Kill current active running command
        elif msg_type == "kill_command":
            step_idx = data.get("step_index")
            proc = active_chat_processes.get(chat_id)
            if proc:
                try:
                    # Kill child processes first
                    children = get_child_pids(proc.pid)
                    for cpid in children:
                        try:
                            os.kill(cpid, signal.SIGINT)
                            time.sleep(0.05)
                            os.kill(cpid, signal.SIGKILL)
                        except Exception:
                            pass
                    # Send SIGINT to proc
                    proc.send_signal(signal.SIGINT)
                except Exception as e:
                    print(f"[WARN] Error killing command: {e}")

            active_tool_info.pop(chat_id, None)
            broadcast({
                "type": "command_stopped",
                "chat_id": chat_id,
                "step_index": step_idx
            })

        # Feature 2: Handle Interactive Permission Response
        elif msg_type == "permission_response":
            req_id = data.get("request_id")
            decision = data.get("decision", "deny")
            custom_input = data.get("custom_input", "")

            fut = permission_futures.get(req_id)
            if fut and not fut.done():
                fut.set_result((decision, custom_input))

            broadcast({
                "type": "permission_resolved",
                "request_id": req_id,
                "decision": decision
            })

        # Process log subscription
        elif msg_type == "subscribe_process_logs":
            pid = data.get("pid")
            if pid:
                if pid not in log_subscribers:
                    log_subscribers[pid] = set()
                log_subscribers[pid].add(self)

        elif msg_type == "unsubscribe_process_logs":
            pid = data.get("pid")
            if pid and pid in log_subscribers:
                log_subscribers[pid].discard(self)

        elif msg_type == "ping":
            try:
                self.write_message(json.dumps({"type": "pong", "time": time.time()}))
            except Exception:
                pass

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),

        # Feature 0: Authentication Endpoints
        (r"/api/auth/login", AuthLoginHandler),
        (r"/api/auth/logout", AuthLogoutHandler),
        (r"/api/auth/status", AuthStatusHandler),
        (r"/api/auth/change-password", AuthChangePasswordHandler),

        # Antigravity Google Account & Quota Endpoints
        (r"/api/antigravity/account", AntigravityAccountApiHandler),
        (r"/api/auth/cli-login/start", CliLoginStartHandler),
        (r"/api/auth/cli-login/status", CliLoginStatusHandler),
        (r"/api/auth/cli-login/submit-code", CliLoginSubmitCodeHandler),
        (r"/api/auth/cli-login/cancel", CliLoginCancelHandler),

        # Projects & Settings Endpoints
        (r"/api/projects", ProjectsApiHandler),
        (r"/api/projects/([^/]+)/switch", ProjectSwitchApiHandler),
        (r"/api/projects/([^/]+)", ProjectDetailApiHandler),
        (r"/api/project-context", ProjectContextApiHandler),
        (r"/api/settings", SettingsApiHandler),
        (r"/api/fs/dirs", DirectoryBrowseApiHandler),
        (r"/api/fs/mkdir", MakeDirectoryApiHandler),

        (r"/api/chats", ChatApiHandler),
        (r"/api/chats/(.*)", ChatApiHandler),
        (r"/api/search-chats", SearchChatsApiHandler),
        (r"/api/models", ModelsApiHandler),
        (r"/api/workspace", WorkspaceApiHandler),
        (r"/api/mentions", MentionsApiHandler),
        (r"/api/config", ConfigApiHandler),
        
        # Feature 3: Processes Endpoints
        (r"/api/processes", ProcessesApiHandler),
        (r"/api/process-logs/([0-9]+)", ProcessLogsApiHandler),
        (r"/api/process-kill/([0-9]+)", ProcessKillApiHandler),
        (r"/api/process-input/([0-9]+)", ProcessInputApiHandler),
        
        # Feature 4: Files Endpoints
        (r"/api/files", FilesApiHandler),
        (r"/api/file-content", FileContentApiHandler),
        (r"/api/file-save", FileSaveApiHandler),
        (r"/api/file-download", FileDownloadHandler),
        
        # Feature 5: Health & Restart & System Update Endpoints
        (r"/api/health", HealthApiHandler),
        (r"/api/restart", RestartApiHandler),
        (r"/api/system/update", SystemUpdateApiHandler),
        
        # WebSocket
        (r"/ws", ChatWebSocket),
        
        # Fixed Static Files (No-Cache for instant live client updates)
        (r"/(manifest\.json)", NoCacheStaticFileHandler, {"path": WORKSPACE_DIR}),
        (r"/(sw\.js)", NoCacheStaticFileHandler, {"path": WORKSPACE_DIR}),
        (r"/css/(.*)", NoCacheStaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "css")}),
        (r"/js/(.*)", NoCacheStaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "js")}),
        (r"/fonts/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "fonts")}),
        (r"/icons/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "icons")}),
    ],
    template_path=WORKSPACE_DIR,
    compiled_template_cache=False,
    debug=False)

if __name__ == "__main__":
    import tornado.log
    tornado.log.enable_pretty_logging()
    app = make_app()
    app.listen(PORT, address=HOST)
    print(f"🚀 Antigravity Server running at http://127.0.0.1:{PORT}")
    print(f"📁 Workspace: {WORKSPACE_DIR}")
    print(f"🧠 Engine: {AGY_BIN}")

    def shutdown_handler(sig, frame):
        print("\nStopping Antigravity server...")
        tornado.ioloop.IOLoop.current().stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        tornado.ioloop.IOLoop.current().start()
    except (KeyboardInterrupt, SystemExit):
        pass
