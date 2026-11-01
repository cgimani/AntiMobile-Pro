/**
 * Antigravity PWA - Sidebar Drawer & Management Dashboard
 * Connection Stats, Model Switcher, File Explorer, Editor Modal & Settings
 */

import { state } from './state.js';
import { api } from './api.js';
import { ws } from './ws.js';
import { terminal } from './terminal.js';

class SidebarDashboard {
  constructor() {
    this.overlay = null;
    this.drawer = null;
    this.modalOverlay = null;
    this.editorTextarea = null;
    this.modalFileTitle = null;
    this.currentEditingPath = null;
  }

  init() {
    this.overlay = document.getElementById('sidebarOverlay');
    this.drawer = document.getElementById('sidebarDrawer');
    this.modalOverlay = document.getElementById('fileModalOverlay');
    this.editorTextarea = document.getElementById('fileEditorTextarea');
    this.modalFileTitle = document.getElementById('modalFileTitle');

    this.bindEvents();
    this.renderSystemInfo();
    this.loadModels();
    this.loadFiles();
    this.applyTheme(state.settings.theme);
  }

  bindEvents() {
    // Open drawer button
    const btnOpen = document.getElementById('btnOpenSidebar');
    if (btnOpen) {
      btnOpen.addEventListener('click', () => this.open());
    }

    // Close drawer button
    const btnClose = document.getElementById('btnCloseSidebar');
    if (btnClose) {
      btnClose.addEventListener('click', () => this.close());
    }

    // Overlay backdrop click
    if (this.overlay) {
      this.overlay.addEventListener('click', (e) => {
        if (e.target === this.overlay) this.close();
      });
    }

    // Refresh files button
    const btnRefreshFiles = document.getElementById('btnRefreshFiles');
    if (btnRefreshFiles) {
      btnRefreshFiles.addEventListener('click', () => {
        state.triggerHaptic(15);
        this.loadFiles();
      });
    }

    // Close Modal button
    const btnCloseModal = document.getElementById('btnCloseModal');
    if (btnCloseModal) {
      btnCloseModal.addEventListener('click', () => this.closeModal());
    }

    // Save File button
    const btnSaveFile = document.getElementById('btnSaveFile');
    if (btnSaveFile) {
      btnSaveFile.addEventListener('click', () => this.saveCurrentFile());
    }

    // Font size slider
    const fontSlider = document.getElementById('fontSizeSlider');
    const fontVal = document.getElementById('fontSizeValue');
    if (fontSlider) {
      fontSlider.value = state.settings.fontSize;
      if (fontVal) fontVal.textContent = `${state.settings.fontSize}px`;
      fontSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        state.updateSetting('fontSize', val);
        if (fontVal) fontVal.textContent = `${val}px`;
        terminal.updateFontSize(val);
      });
    }

    // Scanlines toggle
    const chkScanlines = document.getElementById('chkScanlines');
    const overlayScanlines = document.getElementById('scanlinesOverlay');
    if (chkScanlines) {
      chkScanlines.checked = state.settings.scanlines;
      if (overlayScanlines) overlayScanlines.style.display = state.settings.scanlines ? 'block' : 'none';
      chkScanlines.addEventListener('change', (e) => {
        state.updateSetting('scanlines', e.target.checked);
        if (overlayScanlines) overlayScanlines.style.display = e.target.checked ? 'block' : 'none';
      });
    }

    // Haptics toggle
    const chkHaptics = document.getElementById('chkHaptics');
    if (chkHaptics) {
      chkHaptics.checked = state.settings.haptics;
      chkHaptics.addEventListener('change', (e) => {
        state.updateSetting('haptics', e.target.checked);
      });
    }

    // Quick Action Buttons
    const quickActions = document.querySelectorAll('.quick-action-btn[data-cmd]');
    quickActions.forEach(btn => {
      btn.addEventListener('click', () => {
        const cmd = btn.dataset.cmd;
        state.triggerHaptic(18);
        this.close();
        terminal.appendUserPrompt(cmd);
        if (ws.isConnected) {
          ws.exec(cmd);
        } else {
          api.execCommand(cmd).then(res => {
            if (res.stdout) terminal.appendRawOutput(res.stdout);
            if (res.stderr) terminal.appendRawOutput(res.stderr, true);
          });
        }
      });
    });

    // Clear history button
    const btnClearHistory = document.getElementById('btnClearHistory');
    if (btnClearHistory) {
      btnClearHistory.addEventListener('click', () => {
        state.history = [];
        state.historyIndex = -1;
        localStorage.removeItem('agy_cmd_history');
        this.showToast('سابقه فرامین با موفقیت پاکسازی شد', 'success');
      });
    }

    // Theme selector buttons
    const themeBtns = document.querySelectorAll('.theme-btn[data-theme]');
    themeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const theme = btn.dataset.theme;
        state.updateSetting('theme', theme);
        this.applyTheme(theme);
        themeBtns.forEach(b => b.classList.toggle('active', b.dataset.theme === theme));
        this.showToast(`تم ${btn.textContent.trim()} فعال شد`, 'success');
      });
    });

    // Listen to connection state updates
    state.on('connectionChange', ({ connected, ping }) => {
      this.updateConnectionPill(connected, ping);
    });

    state.on('modelChange', (modelId) => {
      this.updateActiveModelBadge(modelId);
    });
  }

  open() {
    state.triggerHaptic(15);
    if (this.overlay) this.overlay.classList.add('open');
  }

  close() {
    if (this.overlay) this.overlay.classList.remove('open');
  }

  updateConnectionPill(connected, ping) {
    const dot = document.getElementById('headerStatusDot');
    const text = document.getElementById('headerStatusText');
    const latency = document.getElementById('headerStatusLatency');

    if (dot && text && latency) {
      if (connected) {
        dot.className = 'status-dot connected';
        text.textContent = 'متصل به سرور';
        latency.textContent = `${ping}ms`;
        latency.style.display = 'inline';
      } else {
        dot.className = 'status-dot disconnected';
        text.textContent = 'قطع ارتباط';
        latency.style.display = 'none';
      }
    }
  }

  updateActiveModelBadge(modelId) {
    const badge = document.getElementById('terminalModelBadge');
    if (badge) {
      badge.textContent = modelId;
    }
    // Update active highlight in sidebar model list
    const options = document.querySelectorAll('.model-option');
    options.forEach(opt => {
      opt.classList.toggle('active', opt.dataset.modelId === modelId);
    });
  }

  renderSystemInfo() {
    api.getStatus().then(status => {
      if (status.cwd) state.setCwd(status.cwd);
      const cwdEl = document.getElementById('infoCwd');
      if (cwdEl) cwdEl.textContent = status.cwd || '~';

      const terminalPwd = document.getElementById('terminalPwd');
      if (terminalPwd) terminalPwd.textContent = status.cwd || '~';

      const verEl = document.getElementById('infoVersion');
      if (verEl) verEl.textContent = status.agy_version || '1.4.12';

      const pyEl = document.getElementById('infoPython');
      if (pyEl) pyEl.textContent = status.python_version ? status.python_version.split(' ')[0] : '3.14';
    }).catch(() => {
      // Offline fallback defaults
    });
  }

  async loadModels() {
    const container = document.getElementById('sidebarModelList');
    if (!container) return;

    const defaultModels = [
      { id: 'gemini-3.8-flash-high', name: 'Gemini 3.8 Flash (High)', provider: 'Google', desc: 'سرعت و استدلال حداکثری' },
      { id: 'gemini-3.8-flash-medium', name: 'Gemini 3.8 Flash (Medium)', provider: 'Google', desc: 'توازن بهینه سرعت و دقت' },
      { id: 'gemini-3.8-flash-low', name: 'Gemini 3.8 Flash (Low)', provider: 'Google', desc: 'فوق‌العاده سریع و سبک' },
      { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6 (Thinking)', provider: 'Anthropic', desc: 'قدرت کدنویسی و معماری عمیق' },
      { id: 'claude-opus-4-6-thinking', name: 'Claude Opus 4.6 (Thinking)', provider: 'Anthropic', desc: 'استدلال فوق پیشرفته' },
      { id: 'gpt-oss-120b-medium', name: 'GPT-OSS 120B (Medium)', provider: 'Open Source', desc: 'مدل منبع‌باز وزن بالا' }
    ];

    let models = defaultModels;
    try {
      const res = await api.getModels();
      if (res && res.models && res.models.length > 0) {
        models = res.models;
      }
    } catch (e) {
      // Use fallback models
    }

    state.setModels(models);

    container.innerHTML = '';
    models.forEach(m => {
      const isActive = m.id === state.activeModel;
      const el = document.createElement('div');
      el.className = `model-option ${isActive ? 'active' : ''}`;
      el.dataset.modelId = m.id;
      el.innerHTML = `
        <div class="model-meta">
          <div class="model-name">${m.name}</div>
          <div class="model-provider">${m.provider || 'AI'} • ${m.desc || m.id}</div>
        </div>
        <div class="model-check">${isActive ? '✔' : ''}</div>
      `;

      el.addEventListener('click', () => {
        state.triggerHaptic(18);
        state.setActiveModel(m.id);
        ws.send({ type: 'set_model', model: m.id });
        this.updateActiveModelBadge(m.id);
        this.showToast(`مدل هوش مصنوعی به ${m.name} تغییر یافت`, 'success');
      });

      container.appendChild(el);
    });

    this.updateActiveModelBadge(state.activeModel);
  }

  async loadFiles() {
    const container = document.getElementById('fileTreeContainer');
    if (!container) return;

    container.innerHTML = '<div style="font-size: 11.5px; color: var(--text-muted); padding: 8px;">در حال بارگذاری فایل‌ها...</div>';

    try {
      const res = await api.getFiles();
      const files = res.files || [];

      if (files.length === 0) {
        container.innerHTML = '<div style="font-size: 11.5px; color: var(--text-dim); padding: 8px;">هیچ فایلی یافت نشد</div>';
        return;
      }

      container.innerHTML = '';
      files.forEach(f => {
        const item = document.createElement('div');
        item.className = 'file-tree-item';
        item.title = f.path;

        const icon = f.is_dir ? '📁' : this.getFileIcon(f.name);
        const sizeStr = f.is_dir ? 'پوشه' : this.formatFileSize(f.size);

        item.innerHTML = `
          <span class="file-icon">${icon}</span>
          <span class="file-name">${f.name}</span>
          <span class="file-size">${sizeStr}</span>
        `;

        item.addEventListener('click', () => {
          state.triggerHaptic(12);
          if (f.is_dir) {
            // Browse directory
            terminal.appendUserPrompt(`cd ${f.name}`);
            ws.exec(`cd ${f.name} && pwd`);
          } else {
            this.openFileModal(f.path, f.name);
          }
        });

        container.appendChild(item);
      });
    } catch (err) {
      container.innerHTML = '<div style="font-size: 11.5px; color: var(--color-coral); padding: 8px;">خطا در دریافت لیست فایل‌ها</div>';
    }
  }

  getFileIcon(filename) {
    if (filename.endsWith('.js')) return '🟨';
    if (filename.endsWith('.css')) return '🎨';
    if (filename.endsWith('.html')) return '🌐';
    if (filename.endsWith('.json')) return '⚙️';
    if (filename.endsWith('.py')) return '🐍';
    if (filename.endsWith('.sh')) return '🐚';
    if (filename.endsWith('.md')) return '📝';
    if (filename.endsWith('.svg') || filename.endsWith('.png')) return '🖼️';
    return '📄';
  }

  formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // File Modal
  async openFileModal(path, name) {
    this.currentEditingPath = path;
    if (this.modalFileTitle) this.modalFileTitle.textContent = name || path;
    if (this.editorTextarea) this.editorTextarea.value = 'در حال بارگذاری محتوا...';
    if (this.modalOverlay) this.modalOverlay.classList.add('active');

    try {
      const res = await api.getFileContent(path);
      if (this.editorTextarea) {
        this.editorTextarea.value = res.content || '';
      }
    } catch (err) {
      if (this.editorTextarea) {
        this.editorTextarea.value = `خطا در باز کردن فایل: ${err.message}`;
      }
    }
  }

  closeModal() {
    if (this.modalOverlay) this.modalOverlay.classList.remove('active');
    this.currentEditingPath = null;
  }

  async saveCurrentFile() {
    if (!this.currentEditingPath || !this.editorTextarea) return;

    state.triggerHaptic(20);
    const content = this.editorTextarea.value;
    const btnSave = document.getElementById('btnSaveFile');
    if (btnSave) btnSave.textContent = 'در حال ذخیره...';

    try {
      await api.saveFile(this.currentEditingPath, content);
      this.showToast('فایل با موفقیت ذخیره شد ✔', 'success');
      this.closeModal();
      this.loadFiles();
    } catch (err) {
      this.showToast(`خطا در ذخیره فایل: ${err.message}`, 'error');
    } finally {
      if (btnSave) btnSave.textContent = 'ذخیره تغییرات';
    }
  }

  applyTheme(theme) {
    const root = document.documentElement;
    if (theme === 'cyberpunk') {
      root.style.setProperty('--bg-oled', '#050811');
      root.style.setProperty('--color-cyan', '#00f0ff');
      root.style.setProperty('--color-violet', '#f000ff');
    } else if (theme === 'emerald') {
      root.style.setProperty('--bg-oled', '#020b06');
      root.style.setProperty('--color-cyan', '#00ff9d');
      root.style.setProperty('--color-violet', '#10b981');
    } else if (theme === 'midnight') {
      root.style.setProperty('--bg-oled', '#070a13');
      root.style.setProperty('--color-cyan', '#38bdf8');
      root.style.setProperty('--color-violet', '#818cf8');
    } else {
      // Pure OLED Black
      root.style.setProperty('--bg-oled', '#000000');
      root.style.setProperty('--color-cyan', '#00f0ff');
      root.style.setProperty('--color-violet', '#a855f7');
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span>${type === 'error' ? '✖' : (type === 'success' ? '✔' : '✦')}</span>
      <span>${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }
}

export const sidebar = new SidebarDashboard();
