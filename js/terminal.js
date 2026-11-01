/**
 * Antigravity PWA - Interactive Modern Terminal Component
 * ANSI Code Rendering + Markdown/Code Highlighting + Termux Floating Keys
 */

import { state } from './state.js';
import { ws } from './ws.js';

class TerminalComponent {
  constructor() {
    this.container = null;
    this.screen = null;
    this.currentOutputEl = null;
    this.isAutoScroll = true;
    this.extraKeysBar = null;
  }

  init() {
    this.container = document.getElementById('terminalContainer');
    this.screen = document.getElementById('terminalScreen');
    this.extraKeysBar = document.getElementById('extraKeysBar');

    if (!this.screen) return;

    // Detect user manual scroll to disable auto-scroll
    this.screen.addEventListener('scroll', () => {
      const atBottom = this.screen.scrollHeight - this.screen.scrollTop - this.screen.clientHeight < 40;
      this.isAutoScroll = atBottom;
    });

    // Setup Termux Floating Extra Keys
    this.setupExtraKeys();

    // Listen to WebSocket events
    this.setupWebSocketListeners();

    // Apply stored font size
    this.updateFontSize(state.settings.fontSize);
  }

  setupWebSocketListeners() {
    ws.on('stdout', (msg) => {
      const text = typeof msg === 'string' ? msg : msg.data;
      this.appendRawOutput(text, false);
      state.setRunning(true);
    });

    ws.on('stderr', (msg) => {
      const text = typeof msg === 'string' ? msg : msg.data;
      this.appendRawOutput(text, true);
    });

    ws.on('exit', (msg) => {
      state.setRunning(false);
      this.finalizeCurrentOutput();
      if (msg.code !== 0 && msg.code !== null && msg.code !== undefined) {
        this.appendSystemNotice(`خروج با کد ${msg.code}`, 'error');
      }
    });

    ws.on('system', (msg) => {
      this.appendSystemNotice(msg.message, msg.level || 'info');
    });
  }

  // Termux-style Floating Extra Keys
  setupExtraKeys() {
    if (!this.extraKeysBar) return;

    const keys = [
      { label: 'ESC', action: () => this.handleEsc() },
      { label: 'CTRL', action: (btn) => this.toggleCtrl(btn), toggle: true },
      { label: 'ALT', action: (btn) => this.toggleAlt(btn), toggle: true },
      { label: 'TAB', action: () => this.handleTab() },
      { label: '|', action: () => this.insertKey('|') },
      { label: '/', action: () => this.insertKey('/') },
      { label: '-', action: () => this.insertKey('-') },
      { label: '_', action: () => this.insertKey('_') },
      { label: '~', action: () => this.insertKey('~') },
      { label: '↑', action: () => this.historyPrev() },
      { label: '↓', action: () => this.historyNext() },
      { label: 'PASTE', action: () => this.handlePaste() },
      { label: 'CLEAR', action: () => this.clear() }
    ];

    this.extraKeysBar.innerHTML = '';
    keys.forEach(k => {
      const btn = document.createElement('button');
      btn.className = 'key-btn';
      btn.textContent = k.label;
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        state.triggerHaptic(18);
        k.action(btn);
      });
      this.extraKeysBar.appendChild(btn);
    });
  }

  toggleCtrl(btn) {
    state.ctrlActive = !state.ctrlActive;
    btn.classList.toggle('key-active', state.ctrlActive);
    if (state.ctrlActive) {
      this.appendSystemNotice('کلید CTRL فعال شد. کلید بعدی یا کلید C (توقف) را لمس کنید.', 'info');
    }
  }

  toggleAlt(btn) {
    state.altActive = !state.altActive;
    btn.classList.toggle('key-active', state.altActive);
  }

  handleEsc() {
    const input = document.getElementById('commandInput');
    if (input) input.blur();
    ws.sendStdin('\x1b');
  }

  handleTab() {
    const input = document.getElementById('commandInput');
    if (input) {
      const val = input.value;
      if (val.startsWith('/')) {
        // Trigger slash completion popup
        const popover = document.getElementById('slashPopover');
        if (popover) popover.classList.add('active');
      } else {
        input.value += '  ';
      }
    }
  }

  insertKey(char) {
    const input = document.getElementById('commandInput');
    if (input) {
      const start = input.selectionStart;
      const end = input.selectionEnd;
      input.value = input.value.substring(0, start) + char + input.value.substring(end);
      input.selectionStart = input.selectionEnd = start + char.length;
      input.focus();
      // trigger input event for direction detect
      input.dispatchEvent(new Event('input'));
    }
  }

  historyPrev() {
    if (state.history.length === 0) return;
    if (state.historyIndex > 0) {
      state.historyIndex--;
    } else {
      state.historyIndex = 0;
    }
    const input = document.getElementById('commandInput');
    if (input && state.history[state.historyIndex]) {
      input.value = state.history[state.historyIndex];
      input.dispatchEvent(new Event('input'));
    }
  }

  historyNext() {
    if (state.history.length === 0) return;
    const input = document.getElementById('commandInput');
    if (state.historyIndex < state.history.length - 1) {
      state.historyIndex++;
      if (input && state.history[state.historyIndex]) {
        input.value = state.history[state.historyIndex];
        input.dispatchEvent(new Event('input'));
      }
    } else {
      state.historyIndex = state.history.length;
      if (input) {
        input.value = '';
        input.dispatchEvent(new Event('input'));
      }
    }
  }

  async handlePaste() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) this.insertKey(text);
    } catch (err) {
      this.appendSystemNotice('عدم دسترسی به حافظه کلیپ‌بورد', 'error');
    }
  }

  // Clear Terminal
  clear() {
    if (this.screen) {
      this.screen.innerHTML = '';
      this.currentOutputEl = null;
      this.showWelcomeBanner();
    }
  }

  // Append user-entered command to terminal view
  appendUserPrompt(cmd) {
    this.finalizeCurrentOutput();

    const entry = document.createElement('div');
    entry.className = 'terminal-entry entry-user';

    const header = document.createElement('div');
    header.className = 'entry-user-header';
    header.innerHTML = `
      <span style="direction: ltr; font-family: var(--font-mono); color: var(--color-cyan);">${this.escapeHtml(state.cwd)}</span>
      <span>${new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
    `;

    const promptText = document.createElement('div');
    promptText.className = 'entry-user-prompt';
    promptText.innerHTML = `
      <span class="user-chevron">❯</span>
      <span style="flex:1;">${this.escapeHtml(cmd)}</span>
    `;

    entry.appendChild(header);
    entry.appendChild(promptText);
    this.screen.appendChild(entry);
    this.scrollToBottom();
  }

  // Append raw CLI stdout or stderr
  appendRawOutput(text, isError = false) {
    if (!this.currentOutputEl || this.currentOutputEl.dataset.type !== (isError ? 'stderr' : 'stdout')) {
      this.finalizeCurrentOutput();
      const el = document.createElement('pre');
      el.className = isError ? 'entry-cli-stderr' : 'entry-cli-stdout';
      el.dataset.type = isError ? 'stderr' : 'stdout';
      this.screen.appendChild(el);
      this.currentOutputEl = el;
    }

    const formatted = this.parseAnsi(text);
    this.currentOutputEl.innerHTML += formatted;
    this.scrollToBottom();
  }

  finalizeCurrentOutput() {
    this.currentOutputEl = null;
  }

  // Append AI Formatted Response
  appendAiResponse(content, modelName = '') {
    this.finalizeCurrentOutput();

    const entry = document.createElement('div');
    entry.className = 'terminal-entry entry-ai';

    const header = document.createElement('div');
    header.className = 'entry-ai-header';
    header.innerHTML = `
      <div class="ai-badge">${modelName || state.activeModel}</div>
      <div style="font-size: 11px; opacity: 0.7;">${new Date().toLocaleTimeString('fa-IR')}</div>
    `;

    const body = document.createElement('div');
    body.className = 'ai-markdown-content';
    body.innerHTML = this.renderMarkdown(content);

    entry.appendChild(header);
    entry.appendChild(body);
    this.screen.appendChild(entry);
    this.setupCodeCopyButtons(entry);
    this.scrollToBottom();
  }

  // System notice
  appendSystemNotice(msg, type = 'info') {
    const entry = document.createElement('div');
    entry.className = 'terminal-entry';
    const color = type === 'error' ? 'var(--color-coral)' : (type === 'success' ? 'var(--color-emerald)' : 'var(--color-amber)');
    const icon = type === 'error' ? '✖' : (type === 'success' ? '✔' : '✦');
    entry.innerHTML = `
      <div style="display: inline-flex; align-items: center; gap: 8px; padding: 4px 10px; border-radius: var(--radius-xs); background: rgba(255,255,255,0.04); border-right: 3px solid ${color}; font-size: 12px; color: ${color};">
        <span>${icon}</span>
        <span>${this.escapeHtml(msg)}</span>
      </div>
    `;
    this.screen.appendChild(entry);
    this.scrollToBottom();
  }

  // Welcome Banner
  showWelcomeBanner() {
    const banner = document.createElement('div');
    banner.className = 'terminal-entry';
    banner.innerHTML = `
      <div style="padding: 16px; background: rgba(0, 240, 255, 0.03); border: 1px solid rgba(0, 240, 255, 0.2); border-radius: var(--radius-md); margin-bottom: 12px; box-shadow: var(--glow-sm);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 20px;">⚡</span>
            <div>
              <div style="font-weight: 700; font-size: 15px; color: #ffffff;">Antigravity CLI Web & PWA</div>
              <div style="font-size: 11.5px; color: var(--text-secondary);">محیط تعاملی فرمان و هوش مصنوعی پیشرفته ترموکس</div>
            </div>
          </div>
          <span class="badge-version">v1.4.12</span>
        </div>
        <div style="font-size: 13px; line-height: 1.8; color: var(--text-secondary);">
          <div>✨ آماده برای دریافت دستورات CLI و درخواست‌های متنی هوش مصنوعی.</div>
          <div>💡 برای دیدن دستورات ویژه کافیست علامت <code style="color: var(--color-cyan); font-family: var(--font-mono); font-weight: bold;">/</code> را تایپ کنید.</div>
          <div>📱 در موبایل از دکمه‌های شناور بالا برای کلیدهای میانبر ترموکس (ESC، CTRL، TAB و جهت‌نما) استفاده کنید.</div>
        </div>
      </div>
    `;
    this.screen.appendChild(banner);
    this.scrollToBottom();
  }

  // Convert ANSI terminal color codes to HTML spans
  parseAnsi(input) {
    if (!input) return '';
    let text = this.escapeHtml(input);

    const ansiMap = {
      '30': 'color: var(--ansi-black);',
      '31': 'color: var(--ansi-red);',
      '32': 'color: var(--ansi-green);',
      '33': 'color: var(--ansi-yellow);',
      '34': 'color: var(--ansi-blue);',
      '35': 'color: var(--ansi-magenta);',
      '36': 'color: var(--ansi-cyan);',
      '37': 'color: var(--ansi-white);',
      '90': 'color: var(--ansi-bright-black);',
      '91': 'color: var(--ansi-bright-red);',
      '92': 'color: var(--ansi-bright-green);',
      '93': 'color: var(--ansi-bright-yellow);',
      '94': 'color: var(--ansi-bright-blue);',
      '95': 'color: var(--ansi-bright-magenta);',
      '96': 'color: var(--ansi-bright-cyan);',
      '97': 'color: var(--ansi-bright-white);',
      '1': 'font-weight: bold;',
      '2': 'opacity: 0.65;',
      '4': 'text-decoration: underline;'
    };

    // Replace ANSI codes
    text = text.replace(/\x1b\[([0-9;]+)m/g, (match, codeStr) => {
      if (codeStr === '0' || codeStr === '') {
        return '</span>';
      }
      const codes = codeStr.split(';');
      let styles = '';
      codes.forEach(c => {
        if (ansiMap[c]) styles += ansiMap[c] + ' ';
      });
      return `<span style="${styles}">`;
    });

    // Remove remaining unparsed control codes
    text = text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
    return text;
  }

  // Simple Markdown renderer
  renderMarkdown(md) {
    if (!md) return '';

    // Fenced Code Blocks with copy button
    let html = md.replace(/```([a-zA-Z0-9_\-\+]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const safeCode = this.escapeHtml(code.trim());
      const displayLang = lang || 'text';
      return `
        <div class="code-block-wrap">
          <div class="code-header">
            <span>${displayLang}</span>
            <button class="btn-copy-code" data-code="${encodeURIComponent(code.trim())}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              کپی
            </button>
          </div>
          <pre class="code-block-content"><code>${safeCode}</code></pre>
        </div>
      `;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); color: var(--color-cyan); direction: ltr; display: inline-block;">$1</code>');

    // Bold & Italic
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #ffffff;">$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Line breaks to <br> if not in tags
    html = html.replace(/\n/g, '<br>');

    return html;
  }

  setupCodeCopyButtons(container) {
    const copyBtns = container.querySelectorAll('.btn-copy-code');
    copyBtns.forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const code = decodeURIComponent(btn.dataset.code || '');
        try {
          await navigator.clipboard.writeText(code);
          btn.textContent = 'کپی شد! ✔';
          btn.style.color = 'var(--color-emerald)';
          setTimeout(() => {
            btn.innerHTML = `
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              کپی
            `;
            btn.style.color = '';
          }, 2000);
        } catch (err) {
          console.error('Failed to copy code:', err);
        }
      });
    });
  }

  scrollToBottom() {
    if (this.isAutoScroll && this.screen) {
      this.screen.scrollTop = this.screen.scrollHeight;
    }
  }

  updateFontSize(size) {
    document.documentElement.style.setProperty('--terminal-font-size', `${size}px`);
  }

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

export const terminal = new TerminalComponent();
