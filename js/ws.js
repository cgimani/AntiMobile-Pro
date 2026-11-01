/**
 * Antigravity PWA - Real-time WebSocket Client
 * Automatic Reconnect + Latency Heartbeat + Bi-directional Terminal Streaming
 */

import { state } from './state.js';

class WebSocketManager {
  constructor() {
    this.ws = null;
    this.reconnectTimer = null;
    this.reconnectInterval = 1000;
    this.maxReconnectInterval = 8000;
    this.pingTimer = null;
    this.callbacks = new Map();
    this.isConnected = false;
  }

  init() {
    this.connect();
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.reconnectInterval = 1000;
        state.setConnected(true, 5);
        this.startHeartbeat();
        this.emit('open');
        console.log('[WebSocket] Connected to', wsUrl);
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (e) {
          // If raw text
          this.emit('stdout', event.data);
        }
      };

      this.ws.onclose = () => {
        this.handleDisconnect();
      };

      this.ws.onerror = (err) => {
        console.warn('[WebSocket] Error:', err);
        // Let onclose handle reconnect
      };
    } catch (err) {
      console.error('[WebSocket] Init failed:', err);
      this.handleDisconnect();
    }
  }

  handleDisconnect() {
    this.isConnected = false;
    this.stopHeartbeat();
    state.setConnected(false, 0);
    this.emit('close');

    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.reconnectInterval = Math.min(this.reconnectInterval * 1.5, this.maxReconnectInterval);
        this.connect();
      }, this.reconnectInterval);
    }
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.pingTimer = setInterval(() => {
      if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
        const sendTime = Date.now();
        this.send({ type: 'ping', time: sendTime });
      }
    }, 4000);
  }

  stopHeartbeat() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  handleMessage(msg) {
    if (msg.type === 'pong') {
      const latency = Math.max(1, Date.now() - (msg.time || Date.now()));
      state.setConnected(true, latency);
      return;
    }

    if (msg.type === 'status') {
      if (msg.cwd) state.setCwd(msg.cwd);
      if (msg.active_model) state.setActiveModel(msg.active_model);
      return;
    }

    // Pass event to registered listeners
    this.emit(msg.type, msg);
  }

  send(data) {
    if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws.send(payload);
      return true;
    }
    return false;
  }

  // Execute command over WebSocket
  exec(cmd, model = null) {
    return this.send({
      type: 'exec',
      cmd: cmd,
      model: model || state.activeModel
    });
  }

  // Send stdin (e.g. keypress)
  sendStdin(text) {
    return this.send({
      type: 'stdin',
      data: text
    });
  }

  // Send interrupt / kill running command (CTRL+C)
  kill() {
    return this.send({
      type: 'kill'
    });
  }

  on(event, cb) {
    if (!this.callbacks.has(event)) {
      this.callbacks.set(event, []);
    }
    this.callbacks.get(event).push(cb);
  }

  emit(event, data) {
    if (this.callbacks.has(event)) {
      this.callbacks.get(event).forEach(cb => {
        try { cb(data); } catch (e) { console.error('WS Listener error:', e); }
      });
    }
  }
}

export const ws = new WebSocketManager();
