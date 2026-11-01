/**
 * Antigravity PWA - Smart Input Bar & Slash Command Autocomplete
 * Auto RTL/LTR Detection + Seamless Enter Handling + Execution Dispatch
 */

import { state } from './state.js';
import { ws } from './ws.js';
import { api } from './api.js';
import { terminal } from './terminal.js';

class SmartInputBar {
  constructor() {
    this.textarea = null;
    this.sendBtn = null;
    this.stopBtn = null;
    this.slashPopover = null;
    this.slashIndex = 0;

    this.slashCommands = [
      { cmd: '/goal', desc: 'اجرای تسک‌های عمیق و بدون توقف تا حصول نتیجه' },
      { cmd: '/plan', desc: 'برنامه‌ریزی دقیق مرحله‌به‌مرحله قبل از اجرا' },
      { cmd: '/schedule', desc: 'زمان‌بندی دستورات و تنظیم تایمر' },
      { cmd: '/compact', desc: 'فشرده‌سازی تاریخچه و آزادسازی حافظه کانتکست' },
      { cmd: '/learn', desc: 'ذخیره دائم رفتارها و دستورالعمل‌های جدید' },
      { cmd: '/boost', desc: 'تفکر عمیق، تحلیل چندبعدی و راستی‌آزمایی دقیق' },
      { cmd: '/grill-me', desc: 'مصاحبه تعاملی برای حل چالش‌های طراحی' },
      { cmd: '/teamwork', desc: 'همکاری هماهنگ گروهی از ایجنت‌های خودمختار' },
      { cmd: 'agy models', desc: 'نمایش مدل‌های هوش مصنوعی موجود' },
      { cmd: 'agy --help', desc: 'راهنمای پارامترها و ابزارهای CLI' },
      { cmd: 'clear', desc: 'پاکسازی محیط ترمینال' },
      { cmd: 'ls -la', desc: 'مشاهده لیست تمام فایل‌ها و پوشه‌ها' },
      { cmd: 'git status', desc: 'بررسی وضعیت مخزن و فایل‌های تغییریافته' }
    ];
  }

  init() {
    this.textarea = document.getElementById('commandInput');
    this.sendBtn = document.getElementById('btnSend');
    this.stopBtn = document.getElementById('btnStop');
    this.slashPopover = document.getElementById('slashPopover');

    if (!this.textarea) return;

    // Detect RTL / LTR dynamically on typing
    this.textarea.addEventListener('input', () => {
      this.handleInputDirection();
      this.adjustHeight();
      this.handleSlashAutocomplete();
    });

    // Keyboard navigation & Submission
    this.textarea.addEventListener('keydown', (e) => {
      this.handleKeydown(e);
    });

    // Send Button Click
    this.sendBtn.addEventListener('click', () => {
      this.submit();
    });

    // Stop Button Click
    this.stopBtn.addEventListener('click', () => {
      state.triggerHaptic(25);
      ws.kill();
      terminal.appendSystemNotice('دستور توقف ارسال شد (SIGINT).', 'info');
      state.setRunning(false);
    });

    // Listen to state running changes to toggle Send/Stop buttons
    state.on('runningChange', (isRunning) => {
      if (this.sendBtn && this.stopBtn) {
        if (isRunning) {
          this.sendBtn.style.display = 'none';
          this.stopBtn.style.display = 'inline-flex';
        } else {
          this.sendBtn.style.display = 'inline-flex';
          this.stopBtn.style.display = 'none';
        }
      }
    });

    // Close slash popover when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('#inputDock')) {
        this.closeSlashPopover();
      }
    });
  }

  // Auto-detect Persian vs English / Code direction
  handleInputDirection() {
    const text = this.textarea.value.trim();
    if (!text) {
      this.textarea.style.direction = 'rtl';
      this.textarea.style.textAlign = 'right';
      return;
    }

    // Check first meaningful character
    const firstChar = text[0];
    const isPersian = /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]/.test(firstChar);

    if (firstChar === '/' || firstChar === '$' || firstChar === '!' || !isPersian) {
      this.textarea.style.direction = 'ltr';
      this.textarea.style.textAlign = 'left';
    } else {
      this.textarea.style.direction = 'rtl';
      this.textarea.style.textAlign = 'right';
    }
  }

  adjustHeight() {
    this.textarea.style.height = 'auto';
    this.textarea.style.height = `${Math.min(this.textarea.scrollHeight, 120)}px`;
  }

  handleKeydown(e) {
    // If CTRL active from floating key
    if (state.ctrlActive) {
      state.ctrlActive = false;
      const ctrlBtn = document.querySelector('.key-btn.key-active');
      if (ctrlBtn) ctrlBtn.classList.remove('key-active');

      if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        ws.kill();
        terminal.appendSystemNotice('سیگنال توقف CTRL+C ارسال شد.', 'info');
        state.setRunning(false);
        return;
      }
    }

    // If Slash Popover is open
    if (this.slashPopover && this.slashPopover.classList.contains('active')) {
      const items = this.slashPopover.querySelectorAll('.slash-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.slashIndex = (this.slashIndex + 1) % items.length;
        this.highlightSlashItem(items);
        return;
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.slashIndex = (this.slashIndex - 1 + items.length) % items.length;
        this.highlightSlashItem(items);
        return;
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (items[this.slashIndex]) {
          items[this.slashIndex].click();
        }
        return;
      } else if (e.key === 'Escape') {
        e.preventDefault();
        this.closeSlashPopover();
        return;
      }
    }

    // History navigation with Arrow Up/Down if cursor at boundaries
    if (e.key === 'ArrowUp' && this.textarea.selectionStart === 0) {
      e.preventDefault();
      terminal.historyPrev();
      return;
    }
    if (e.key === 'ArrowDown' && this.textarea.selectionStart === this.textarea.value.length) {
      e.preventDefault();
      terminal.historyNext();
      return;
    }

    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.submit();
    }
  }

  handleSlashAutocomplete() {
    const val = this.textarea.value;
    if (val.startsWith('/')) {
      const filter = val.toLowerCase();
      const matched = this.slashCommands.filter(c => c.cmd.toLowerCase().startsWith(filter));
      this.renderSlashPopover(matched);
    } else {
      this.closeSlashPopover();
    }
  }

  renderSlashPopover(list) {
    if (!this.slashPopover) return;
    if (list.length === 0) {
      this.closeSlashPopover();
      return;
    }

    this.slashPopover.innerHTML = '';
    this.slashIndex = 0;

    list.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = `slash-item ${index === 0 ? 'selected' : ''}`;
      row.innerHTML = `
        <span class="slash-cmd-name">${item.cmd}</span>
        <span class="slash-cmd-desc">${item.desc}</span>
      `;
      row.addEventListener('click', () => {
        state.triggerHaptic(12);
        this.textarea.value = item.cmd + ' ';
        this.closeSlashPopover();
        this.textarea.focus();
        this.handleInputDirection();
      });
      this.slashPopover.appendChild(row);
    });

    this.slashPopover.classList.add('active');
  }

  highlightSlashItem(items) {
    items.forEach((item, i) => {
      item.classList.toggle('selected', i === this.slashIndex);
      if (i === this.slashIndex) {
        item.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  closeSlashPopover() {
    if (this.slashPopover) {
      this.slashPopover.classList.remove('active');
    }
  }

  // Submit current command or query
  async submit() {
    const text = this.textarea.value.trim();
    if (!text) return;

    state.triggerHaptic(20);
    this.closeSlashPopover();

    // Clear input bar & reset height
    this.textarea.value = '';
    this.adjustHeight();
    this.handleInputDirection();

    // Add to history
    state.addHistory(text);

    // Display user command in terminal
    terminal.appendUserPrompt(text);

    // Handle local commands
    if (text === 'clear' || text === 'cls') {
      terminal.clear();
      return;
    }

    // If connected via WebSocket, send to server
    if (ws.isConnected) {
      const sent = ws.exec(text, state.activeModel);
      if (!sent) {
        // Fallback to REST
        this.executeViaRest(text);
      }
    } else {
      // Offline or REST mode
      this.executeViaRest(text);
    }
  }

  async executeViaRest(text) {
    state.setRunning(true);
    try {
      terminal.appendSystemNotice('در حال ارتباط با سرور از طریق REST API...', 'info');
      const res = await api.execCommand(text);
      if (res.stdout) {
        terminal.appendRawOutput(res.stdout, false);
      }
      if (res.stderr) {
        terminal.appendRawOutput(res.stderr, true);
      }
      if (res.code !== 0 && res.code !== null && res.code !== undefined) {
        terminal.appendSystemNotice(`پایان با کد خطا: ${res.code}`, 'error');
      }
    } catch (err) {
      terminal.appendSystemNotice(`خطا در برقراری ارتباط: ${err.message}`, 'error');
    } finally {
      state.setRunning(false);
    }
  }
}

export const inputBar = new SmartInputBar();
