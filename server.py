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
from collections import deque
from typing import Set, Dict, Any, Optional, List, Tuple

import tornado.web
import tornado.websocket
import tornado.ioloop

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
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
    candidates = [
        os.path.expanduser('~/.local/bin/agy'),
        os.path.expanduser('~/.gemini/antigravity-cli/bin/agy'),
        '/data/data/com.termux/files/home/.local/bin/agy',
        '/data/data/com.termux/files/usr/bin/agy',
        '/usr/local/bin/agy',
        '/opt/homebrew/bin/agy'
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return os.path.expanduser('~/.local/bin/agy')

AGY_BIN = find_agy_binary()

# Available models cache
CACHED_MODELS = [
    {"id": "gemini-3.8-flash-high", "name": "Gemini 3.8 Flash (High)"},
    {"id": "gemini-3.8-flash-medium", "name": "Gemini 3.8 Flash (Medium)"},
    {"id": "gemini-3.8-flash-low", "name": "Gemini 3.8 Flash (Low)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (Thinking)"},
    {"id": "claude-opus-4-6-thinking", "name": "Claude Opus 4.6 (Thinking)"},
    {"id": "gpt-oss-120b-medium", "name": "GPT-OSS 120B (Medium)"}
]

def fetch_models_from_cli() -> List[Dict[str, str]]:
    """Dynamically discover models supported by the installed agy binary."""
    global CACHED_MODELS
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
    transcript_path = os.path.expanduser(f"~/.gemini/antigravity-cli/brain/{conv_id}/.system_generated/logs/transcript.jsonl")
    if not os.path.exists(transcript_path):
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
            "enabled": True,
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

        # Initialize default admin credentials if not set
        if not self.config.get("password_hash"):
            salt = secrets.token_hex(16)
            default_pwd = os.environ.get("ANTI_PASSWORD", "antigravity")
            self.config["salt"] = salt
            self.config["password_hash"] = self._hash_pwd(default_pwd, salt)
            self.config["username"] = os.environ.get("ANTI_USERNAME", "admin")
            self.config["enabled"] = True
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
        if not self.config.get("enabled", True):
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

auth_manager = AuthManager()

# History Manager with atomic persistence
class HistoryManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Dict[str, Any] = {
            "active_chat_id": "default",
            "chats": {},
            "default_model": "gemini-3.8-flash-high",
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

        # Validate workspace path exists, else fallback to current directory
        if not os.path.isdir(self.data.get("workspace", "")):
            self.data["workspace"] = WORKSPACE_DIR

        for chat in self.data.get("chats", {}).values():
            if not os.path.isdir(chat.get("cwd", "")):
                chat["cwd"] = WORKSPACE_DIR

        # Ensure default chat exists
        if not self.data.get("chats"):
            default_id = f"chat_{int(time.time())}"
            self.data["chats"] = {
                default_id: {
                    "id": default_id,
                    "title": "گفتگوی جدید",
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "agy_conversation_id": None,
                    "model": self.data.get("default_model", "gemini-3.8-flash-high"),
                    "cwd": self.data.get("workspace", WORKSPACE_DIR),
                    "messages": []
                }
            }
            self.data["active_chat_id"] = default_id
            self.save()
        elif self.data.get("active_chat_id") not in self.data["chats"]:
            self.data["active_chat_id"] = next(iter(self.data["chats"]))

    def save(self):
        try:
            tmp_path = self.filepath + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.filepath)
        except Exception as e:
            print(f"[ERROR] Error saving chat_history.json: {e}")

    def get_chats_summary(self):
        result = []
        for cid, chat in self.data["chats"].items():
            result.append({
                "id": cid,
                "title": chat.get("title", "گفتگو"),
                "created_at": chat.get("created_at", 0),
                "updated_at": chat.get("updated_at", 0),
                "message_count": len(chat.get("messages", [])),
                "model": chat.get("model", "gemini-3.8-flash-high"),
                "agy_conversation_id": chat.get("agy_conversation_id")
            })
        result.sort(key=lambda x: x["updated_at"], reverse=True)
        return result

    def get_chat(self, chat_id: str):
        return self.data["chats"].get(chat_id)

    def create_chat(self, title: str = "گفتگوی جدید", model: Optional[str] = None):
        cid = f"chat_{int(time.time() * 1000)}"
        model_to_use = model or self.data.get("default_model", "gemini-3.8-flash-high")
        new_chat = {
            "id": cid,
            "title": title,
            "created_at": time.time(),
            "updated_at": time.time(),
            "agy_conversation_id": None,
            "model": model_to_use,
            "cwd": self.data.get("workspace", WORKSPACE_DIR),
            "messages": []
        }
        self.data["chats"][cid] = new_chat
        self.data["active_chat_id"] = cid
        self.save()
        return new_chat

    def delete_chat(self, chat_id: str):
        if chat_id in self.data["chats"]:
            del self.data["chats"][chat_id]
            if not self.data["chats"]:
                return self.create_chat()
            if self.data.get("active_chat_id") == chat_id:
                self.data["active_chat_id"] = next(iter(self.data["chats"]))
            self.save()
        return self.get_chat(self.data["active_chat_id"])

    def clear_chat(self, chat_id: str):
        chat = self.data["chats"].get(chat_id)
        if chat:
            chat["messages"] = []
            chat["agy_conversation_id"] = None
            chat["updated_at"] = time.time()
            self.save()
            return True
        return False

    def add_message(self, chat_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None):
        chat = self.data["chats"].get(chat_id)
        if not chat:
            chat = self.create_chat()
            chat_id = chat["id"]
        
        # Auto-update title if default
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
        self.data["active_chat_id"] = chat_id
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

    cwd = chat.get("cwd") or WORKSPACE_DIR
    if not os.path.isdir(cwd):
        cwd = WORKSPACE_DIR

    agy_conv_id = chat.get("agy_conversation_id")
    model = chat.get("model") or "gemini-3.8-flash-high"
    effort = chat.get("effort") or history_mgr.data.get("default_effort", "high")
    mode = chat.get("mode") or history_mgr.data.get("default_mode", "auto")

    # Build command arguments for agy
    cmd = [
        find_agy_binary(),
        "-p", prompt,
        "--output-format", "stream-json",
        "--dangerously-skip-permissions"
    ]
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

    # Initial status
    send_ws({"type": "status", "status": "💭 در حال آماده‌سازی و تحلیل..."})

    accumulated_response: List[str] = []
    active_step_index = 0
    turn_steps: Dict[int, Dict[str, Any]] = {}
    turn_start_time = time.time()
    thinking_task: Optional[asyncio.Task] = None

    proc: Optional[asyncio.subprocess.Process] = None

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
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
                # Stream to active command preview if open
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
                    tool_name = step.get("tool_name") or step.get("tool_info", {}).get("name", "ابزار")
                    tool_info = step.get("tool_info", {})
                    params = tool_info.get("parameters", {})
                    duration = step.get("duration_seconds", 0)

                    # Determine descriptive Persian title & icon
                    if tool_name == "run_command":
                        cmd_str = params.get("CommandLine") or params.get("command") or ""
                        icon = "💻"
                        title = f"اجرای دستور: {cmd_str[:55]}" if cmd_str else "اجرای دستور در ترمینال"
                        is_command = True
                    elif tool_name in ("read_file", "view_file"):
                        fpath = params.get("Path") or params.get("path") or ""
                        fname = os.path.basename(fpath) if fpath else "فایل"
                        icon = "📂"
                        title = f"خواندن فایل: {fname}"
                        is_command = False
                    elif tool_name in ("write_file", "replace_file_content", "multi_replace_file_content", "write_to_file", "edit_file"):
                        fpath = params.get("Path") or params.get("path") or ""
                        fname = os.path.basename(fpath) if fpath else "فایل"
                        icon = "✏️"
                        title = f"ویرایش فایل: {fname}"
                        is_command = False
                    elif tool_name in ("list_dir", "find_by_name"):
                        icon = "📁"
                        title = f"بررسی مسیر: {params.get('Path') or params.get('path') or ''}"
                        is_command = False
                    elif tool_name in ("grep_search", "search_web"):
                        icon = "🔍"
                        title = f"جستجو: {params.get('query') or params.get('pattern') or ''}"
                        is_command = False
                    elif tool_name in ("ask_permission", "ask_question", "ask_custom_permission"):
                        icon = "🛡️"
                        title = "درخواست تایید دسترسی"
                        is_command = False
                    else:
                        icon = "⚙️"
                        title = f"عملیات: {tool_name}"
                        is_command = False

                    if state == "ACTIVE":
                        turn_steps[step_index] = {
                            "index": step_index,
                            "tool": tool_name,
                            "icon": icon,
                            "title": title,
                            "command": params.get("CommandLine") or params.get("command", ""),
                            "path": params.get("Path") or params.get("path", ""),
                            "query": params.get("query") or params.get("pattern", ""),
                            "is_command": is_command,
                            "state": "ACTIVE",
                            "duration": 0,
                            "output": ""
                        }
                        active_tool_info[chat_id] = {
                            "step_index": step_index,
                            "tool_name": tool_name,
                            "is_command": is_command,
                            "command": params.get("CommandLine", ""),
                            "start_time": time.time()
                        }
                        send_ws({
                            "type": "step_start",
                            "step_index": step_index,
                            "step_type": "tool",
                            "tool_name": tool_name,
                            "icon": icon,
                            "title": title,
                            "command": params.get("CommandLine", ""),
                            "is_command": is_command,
                            "start_time": time.time()
                        })
                        send_ws({
                            "type": "status",
                            "status": f"{icon} {title}..."
                        })

                    elif state == "DONE":
                        active_tool_info.pop(chat_id, None)
                        output_str = tool_info.get("output", "")
                        if step_index in turn_steps:
                            turn_steps[step_index]["state"] = "DONE"
                            turn_steps[step_index]["duration"] = round(duration, 2)
                            turn_steps[step_index]["output"] = output_str
                        send_ws({
                            "type": "step_done",
                            "step_index": step_index,
                            "step_type": "tool",
                            "tool_name": tool_name,
                            "duration": round(duration, 2),
                            "output": output_str
                        })
                        send_ws({"type": "status", "status": "💭 در حال تفکر و پردازش..."})

                elif step_type == "agent_response":
                    text_delta = step.get("text_delta", "")
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
    def get(self):
        self.render(os.path.join(WORKSPACE_DIR, 'index.html'))

    def head(self):
        self.get()

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
            "auth_enabled": auth_manager.config.get("enabled", True)
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

class ChatApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")

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
            active_id = history_mgr.data.get("active_chat_id")
            self.write(json.dumps({
                "active_chat_id": active_id,
                "chats": summaries,
                "default_model": history_mgr.data.get("default_model", "gemini-3.8-flash-high"),
                "workspace": history_mgr.data.get("workspace", WORKSPACE_DIR)
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

        title = body.get("title", "گفتگوی جدید")
        model = body.get("model")
        new_chat = history_mgr.create_chat(title=title, model=model)
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

# Feature 4: Built-in File Explorer & Code Viewer Endpoints
class FilesApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        req_path = self.get_argument("path", "")
        base_dir = history_mgr.data.get("workspace", WORKSPACE_DIR)

        if not req_path:
            target_dir = base_dir
        else:
            target_dir = os.path.abspath(req_path)

        # Basic path security check
        if not target_dir.startswith(USER_HOME) and not target_dir.startswith(WORKSPACE_DIR):
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
            "parent_path": parent_path,
            "items": items
        }, ensure_ascii=False))

class FileContentApiHandler(BaseApiHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def get(self):
        file_path = self.get_argument("path", "")
        if not file_path or not os.path.isfile(file_path):
            self.set_status(404)
            self.write(json.dumps({"error": "فایل یافت نشد."}))
            return

        # Security check: within user home
        norm_path = os.path.abspath(file_path)
        if not norm_path.startswith(USER_HOME) and not norm_path.startswith(WORKSPACE_DIR):
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

class FileDownloadHandler(BaseApiHandler):
    def get(self):
        file_path = self.get_argument("path", "")
        if not file_path or not os.path.isfile(file_path):
            self.set_status(404)
            self.write("File not found")
            return

        norm_path = os.path.abspath(file_path)
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
        agy_exists = os.path.exists(AGY_BIN)
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
        procs = get_system_processes()

        self.write_message(json.dumps({
            "type": "connected",
            "active_chat_id": active_id,
            "chat": chat,
            "models": fetch_models_from_cli(),
            "effort": chat.get("effort") or history_mgr.data.get("default_effort", "high"),
            "mode": chat.get("mode") or history_mgr.data.get("default_mode", "auto"),
            "processes_count": len(procs),
            "internet_ok": is_internet_available(0.5)
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
            self.write_message(json.dumps({"type": "pong", "time": time.time()}))

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),

        # Feature 0: Authentication Endpoints
        (r"/api/auth/login", AuthLoginHandler),
        (r"/api/auth/logout", AuthLogoutHandler),
        (r"/api/auth/status", AuthStatusHandler),
        (r"/api/auth/change-password", AuthChangePasswordHandler),

        (r"/api/chats", ChatApiHandler),
        (r"/api/chats/(.*)", ChatApiHandler),
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
        (r"/api/file-download", FileDownloadHandler),
        
        # Feature 5: Health & Restart Endpoints
        (r"/api/health", HealthApiHandler),
        (r"/api/restart", RestartApiHandler),
        
        # WebSocket
        (r"/ws", ChatWebSocket),
        
        # Fixed Static Files
        (r"/(manifest\.json)", tornado.web.StaticFileHandler, {"path": WORKSPACE_DIR}),
        (r"/(sw\.js)", tornado.web.StaticFileHandler, {"path": WORKSPACE_DIR}),
        (r"/css/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "css")}),
        (r"/js/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "js")}),
        (r"/fonts/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "fonts")}),
        (r"/icons/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(WORKSPACE_DIR, "icons")}),
    ],
    template_path=WORKSPACE_DIR,
    debug=False)

if __name__ == "__main__":
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
