/**
 * Antigravity PWA - Central Reactive State Management
 */

class AppState {
  constructor() {
    this.connected = false;
    this.ping = 0;
    this.activeModel = localStorage.getItem('agy_model') || 'gemini-3.8-flash-high';
    this.models = [];
    this.cwd = '~';
    this.history = JSON.parse(localStorage.getItem('agy_cmd_history') || '[]');
    this.historyIndex = -1;
    this.isRunning = false;
    this.ctrlActive = false;
    this.altActive = false;

    // Preferences
    this.settings = {
      fontSize: parseInt(localStorage.getItem('agy_font_size') || '14', 10),
      haptics: localStorage.getItem('agy_haptics') !== 'false',
      scanlines: localStorage.getItem('agy_scanlines') === 'true',
      theme: localStorage.getItem('agy_theme') || 'oled'
    };

    this.listeners = new Map();
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(cb => {
        try { cb(data); } catch (e) { console.error('State listener error:', e); }
      });
    }
  }

  setConnected(status, ping = 0) {
    this.connected = status;
    this.ping = ping;
    this.emit('connectionChange', { connected: status, ping });
  }

  setActiveModel(modelId) {
    this.activeModel = modelId;
    localStorage.setItem('agy_model', modelId);
    this.emit('modelChange', modelId);
  }

  setModels(modelsList) {
    this.models = modelsList;
    this.emit('modelsLoaded', modelsList);
  }

  setCwd(newPath) {
    this.cwd = newPath;
    this.emit('cwdChange', newPath);
  }

  setRunning(running) {
    this.isRunning = running;
    this.emit('runningChange', running);
  }

  addHistory(cmd) {
    if (!cmd || !cmd.trim()) return;
    const trimmed = cmd.trim();
    // Remove if already present, push to end
    this.history = this.history.filter(c => c !== trimmed);
    this.history.push(trimmed);
    if (this.history.length > 100) this.history.shift();
    localStorage.setItem('agy_cmd_history', JSON.stringify(this.history));
    this.historyIndex = this.history.length;
  }

  updateSetting(key, value) {
    this.settings[key] = value;
    localStorage.setItem(`agy_${key}`, value);
    this.emit('settingChange', { key, value });
  }

  triggerHaptic(ms = 15) {
    if (this.settings.haptics && 'vibrate' in navigator) {
      try { navigator.vibrate(ms); } catch (e) {}
    }
  }
}

export const state = new AppState();
