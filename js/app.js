/**
 * Antigravity Desktop-Style Mobile Web PWA Client
 * Pure JavaScript, Offline Ready, Markdown Streaming, Code Copy
 * Full Implementation of 5 Core Features
 */

(function () {
  'use strict';

  // State
  let ws = null;
  let activeChatId = null;
  let chats = {};
  let currentModel = 'gemini-3.8-flash-medium';
  let currentEffort = 'high';
  let currentMode = 'auto';
  let availableModels = [
    { id: 'gemini-3.8-flash-medium', name: 'Gemini 3.8 Flash (Medium)' },
    { id: 'gemini-3.8-flash-high', name: 'Gemini 3.8 Flash (High)' },
    { id: 'gemini-3.8-flash-low', name: 'Gemini 3.8 Flash (Low)' },
    { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6 (Thinking)' },
    { id: 'claude-opus-4-6-thinking', name: 'Claude Opus 4.6 (Thinking)' },
    { id: 'gpt-oss-120b-medium', name: 'GPT-OSS 120B (Medium)' }
  ];
  let workspaceDir = '~';
  let isWsConnected = false;
  let isInternetOnline = navigator.onLine !== false;
  let activeStreamingBubble = null;
  let currentStreamText = '';

  // Auth State
  let authToken = localStorage.getItem('anti_auth_token') || sessionStorage.getItem('anti_auth_token') || null;
  let currentUser = localStorage.getItem('anti_username') || sessionStorage.getItem('anti_username') || 'admin';
  let isAuthenticated = true;

  // Active Turn Steps, Thinking & Timers
  let currentAccordionEl = null;
  let currentMiniTerminals = {}; // step_index -> { element, timerInterval, startTime }
  let activeTurnStepIndices = new Set();
  let liveThinkingEl = null;
  let liveThinkingTimer = null;
  let liveThinkingStartTime = 0;
  let liveTurnMeta = null;
  let cachedMentions = [];
  let slashSelectedIdx = 0;
  let mentionSelectedIdx = 0;

  // Inspect Process State
  let currentInspectingPid = null;

  // File Explorer State
  let currentFilesPath = '';

  // Real-Time CLI Stream Element
  let activeLiveCliEl = null;

  // DOM Elements
  const authLoginModal = document.getElementById('authLoginModal');
  const authLoginForm = document.getElementById('authLoginForm');
  const authUsername = document.getElementById('authUsername');
  const authPassword = document.getElementById('authPassword');
  const authRememberMe = document.getElementById('authRememberMe');
  const authAlertBanner = document.getElementById('authAlertBanner');
  const btnAuthSubmit = document.getElementById('btnAuthSubmit');
  const authBtnText = document.getElementById('authBtnText');
  const authSubmitSpinner = document.getElementById('authSubmitSpinner');
  const btnToggleAuthPassword = document.getElementById('btnToggleAuthPassword');
  const drawerUserCard = document.getElementById('drawerUserCard');
  const drawerUserName = document.getElementById('drawerUserName');
  const drawerUserAvatar = document.getElementById('drawerUserAvatar');
  const btnDrawerLogout = document.getElementById('btnDrawerLogout');
  const btnOpenChangePassword = document.getElementById('btnOpenChangePassword');
  const changePasswordModal = document.getElementById('changePasswordModal');
  const btnCloseChangePassword = document.getElementById('btnCloseChangePassword');
  const changePasswordForm = document.getElementById('changePasswordForm');
  const changePwdAlert = document.getElementById('changePwdAlert');
  const cpCurrentPassword = document.getElementById('cpCurrentPassword');
  const cpNewUsername = document.getElementById('cpNewUsername');
  const cpNewPassword = document.getElementById('cpNewPassword');

  const headerStatusDot = document.getElementById('headerStatusDot');
  const headerModelText = document.getElementById('headerModelText');
  const pillModel = document.getElementById('pillModel');
  const pillModelText = document.getElementById('pillModelText');
  const pillEffort = document.getElementById('pillEffort');
  const pillEffortText = document.getElementById('pillEffortText');
  const pillMode = document.getElementById('pillMode');
  const pillModeText = document.getElementById('pillModeText');
  const pingValText = document.getElementById('pingValText');
  const pingDot = document.getElementById('pingDot');
  const btnMic = document.getElementById('btnMic');
  const slashPopover = document.getElementById('slashPopover');
  const mentionsPopover = document.getElementById('mentionsPopover');
  const modelSheetBackdrop = document.getElementById('modelSheetBackdrop');
  const modelSheetBody = document.getElementById('modelSheetBody');
  const btnCloseModelSheet = document.getElementById('btnCloseModelSheet');

  const btnNewChat = document.getElementById('btnNewChat');
  const btnMenu = document.getElementById('btnMenu');
  const btnCloseDrawer = document.getElementById('btnCloseDrawer');
  const drawerBackdrop = document.getElementById('drawerBackdrop');
  const btnDrawerNewChat = document.getElementById('btnDrawerNewChat');
  const chatsList = document.getElementById('chatsList');
  const modelSelect = document.getElementById('modelSelect');
  const workspacePathText = document.getElementById('workspacePathText');
  const chatScrollArea = document.getElementById('chatScrollArea');
  const chatInner = document.getElementById('chatInner');
  const emptyState = document.getElementById('emptyState');
  const thinkingRow = document.getElementById('thinkingRow');
  const thinkingText = document.getElementById('thinkingText');
  const inputMessage = document.getElementById('inputMessage');
  const btnSend = document.getElementById('btnSend');
  const btnToggleKeys = document.getElementById('btnToggleKeys');
  const extraKeysRow = document.getElementById('extraKeysRow');

  // Network Banners
  const networkWarningBanner = document.getElementById('networkWarningBanner');
  const serverErrorBanner = document.getElementById('serverErrorBanner');
  const btnBannerRestart = document.getElementById('btnBannerRestart');

  // Header and Drawer Navigation
  const btnOpenFiles = document.getElementById('btnOpenFiles');
  const btnOpenProcesses = document.getElementById('btnOpenProcesses');
  const procBadgeHeader = document.getElementById('procBadgeHeader');
  const procBadgeDrawer = document.getElementById('procBadgeDrawer');
  const btnDrawerProcesses = document.getElementById('btnDrawerProcesses');
  const btnDrawerFiles = document.getElementById('btnDrawerFiles');
  const btnDrawerGuide = document.getElementById('btnDrawerGuide');
  const btnDrawerRestart = document.getElementById('btnDrawerRestart');
  const systemGuideModal = document.getElementById('systemGuideModal');
  const btnCloseSystemGuide = document.getElementById('btnCloseSystemGuide');

  // Processes Modal Elements
  const processesModal = document.getElementById('processesModal');
  const procModalBadge = document.getElementById('procModalBadge');
  const btnRefreshProcesses = document.getElementById('btnRefreshProcesses');
  const btnCloseProcesses = document.getElementById('btnCloseProcesses');
  const processesListContainer = document.getElementById('processesListContainer');

  // Inspect Process Modal Elements
  const inspectProcessModal = document.getElementById('inspectProcessModal');
  const inspectTitle = document.getElementById('inspectTitle');
  const btnCloseInspect = document.getElementById('btnCloseInspect');
  const inspectInfoBar = document.getElementById('inspectInfoBar');
  const inspectTerminalScreen = document.getElementById('inspectTerminalScreen');
  const inspectTerminalOutput = document.getElementById('inspectTerminalOutput');
  const inspectStdinInput = document.getElementById('inspectStdinInput');
  const btnSendInspectStdin = document.getElementById('btnSendInspectStdin');
  const btnSignalSigint = document.getElementById('btnSignalSigint');
  const btnSignalSigterm = document.getElementById('btnSignalSigterm');
  const btnSignalSigkill = document.getElementById('btnSignalSigkill');

  // Files Modal Elements
  const filesModal = document.getElementById('filesModal');
  const btnCloseFiles = document.getElementById('btnCloseFiles');
  const btnFilesUp = document.getElementById('btnFilesUp');
  const filesBreadcrumbs = document.getElementById('filesBreadcrumbs');
  const filesListContainer = document.getElementById('filesListContainer');

  // Code Viewer Modal Elements
  const codeViewerModal = document.getElementById('codeViewerModal');
  const codeViewerTitle = document.getElementById('codeViewerTitle');
  const codeViewerLang = document.getElementById('codeViewerLang');
  const btnCodeCopy = document.getElementById('btnCodeCopy');
  const btnCodeDownload = document.getElementById('btnCodeDownload');
  const btnCodeMention = document.getElementById('btnCodeMention');
  const btnCloseCodeViewer = document.getElementById('btnCloseCodeViewer');
  const codeLineNumbers = document.getElementById('codeLineNumbers');
  const codeHighlighted = document.getElementById('codeHighlighted');
  let currentViewedFilePath = '';
  let currentViewedFileContent = '';

  // In-App Code Editor Elements & State
  const btnCodeEditToggle = document.getElementById('btnCodeEditToggle');
  const btnCodeSave = document.getElementById('btnCodeSave');
  const codeEditorInput = document.getElementById('codeEditorInput');
  let isCodeEditing = false;

  // Multi-Project Workspaces State & DOM Elements
  let projects = {};
  let activeProjectId = null;
  let activeProject = null;

  const headerProjectText = document.getElementById('headerProjectText');
  const headerCenterBtn = document.getElementById('headerCenterBtn');
  const drawerProjectName = document.getElementById('drawerProjectName');
  const drawerProjectPath = document.getElementById('drawerProjectPath');
  const projectActiveCard = document.getElementById('projectActiveCard');
  const btnActiveProjectInfo = document.getElementById('btnActiveProjectInfo');
  const btnDrawerNewProject = document.getElementById('btnDrawerNewProject');
  const btnDrawerOpenProjects = document.getElementById('btnDrawerOpenProjects');
  const btnDrawerProjects = document.getElementById('btnDrawerProjects');
  const projectsBadgeDrawer = document.getElementById('projectsBadgeDrawer');
  const drawerChatCount = document.getElementById('drawerChatCount');

  const projectsModal = document.getElementById('projectsModal');
  const btnCloseProjects = document.getElementById('btnCloseProjects');
  const projectsModalBadge = document.getElementById('projectsModalBadge');
  const btnToggleCreateProject = document.getElementById('btnToggleCreateProject');
  const createProjectPanel = document.getElementById('createProjectPanel');
  const newProjectName = document.getElementById('newProjectName');
  const newProjectPath = document.getElementById('newProjectPath');
  const btnSubmitCreateProject = document.getElementById('btnSubmitCreateProject');
  const btnCancelCreateProject = document.getElementById('btnCancelCreateProject');
  const projectsListContainer = document.getElementById('projectsListContainer');

  // Configure Marked with Highlight.js
  if (typeof marked !== 'undefined') {
    const renderer = new marked.Renderer();

    renderer.code = function (code, lang) {
      const language = lang || 'text';
      let highlighted = code;
      if (typeof hljs !== 'undefined') {
        try {
          if (lang && hljs.getLanguage(lang)) {
            highlighted = hljs.highlight(code, { language: lang }).value;
          } else {
            highlighted = hljs.highlightAuto(code).value;
          }
        } catch (e) {
          highlighted = code;
        }
      }

      const escapedCode = encodeURIComponent(code);

      return `
        <div class="code-container">
          <div class="code-header">
            <span class="code-lang">${language}</span>
            <button class="code-copy-btn" data-code="${escapedCode}" onclick="window.copyCode(this)">کپی</button>
          </div>
          <pre><code class="hljs language-${language}">${highlighted}</code></pre>
        </div>
      `;
    };

    renderer.blockquote = function (quote) {
      const str = (typeof quote === 'string') ? quote : (quote?.text || '');
      const clean = str.trim();
      const alertMap = [
        { tag: '[!NOTE]', type: 'note', title: 'یادداشت', icon: 'ℹ️' },
        { tag: '[!TIP]', type: 'tip', title: 'نکته', icon: '💡' },
        { tag: '[!IMPORTANT]', type: 'important', title: 'مهم', icon: '⚡' },
        { tag: '[!WARNING]', type: 'warning', title: 'هشدار', icon: '⚠️' },
        { tag: '[!CAUTION]', type: 'caution', title: 'احتیاط', icon: '🛑' }
      ];
      for (const a of alertMap) {
        if (clean.includes(a.tag)) {
          const content = clean.replace(a.tag, '').replace(/<p>\s*<\/p>/g, '');
          return `
            <div class="antigravity-alert ${a.type}">
              <div class="alert-title">${a.icon} ${a.title}</div>
              <div class="alert-content">${content}</div>
            </div>
          `;
        }
      }
      return `<blockquote>${str}</blockquote>`;
    };

    renderer.link = function (href, title, text) {
      if (typeof href === 'object' && href !== null) {
        text = href.text || (href.tokens && href.tokens.map(t => t.text || '').join('')) || '';
        title = href.title || '';
        href = href.href || '';
      }
      const hrefStr = String(href || '');
      if (hrefStr.startsWith('file://')) {
        const filePath = hrefStr.replace('file://', '');
        const fName = filePath.split('/').pop();
        return `<a href="#" class="file-mention-link" data-path="${filePath}" onclick="window.handleFileLinkClick(event, this)">📄 ${text || fName}</a>`;
      }
      return `<a href="${hrefStr}" target="_blank" rel="noopener noreferrer">${text || hrefStr}</a>`;
    };

    marked.setOptions({
      renderer: renderer,
      breaks: true,
      gfm: true
    });
  }

  // Global File Link Handler
  window.handleFileLinkClick = function (e, el) {
    e.preventDefault();
    const path = el.getAttribute('data-path');
    if (path) {
      openCodeViewer(path);
    }
  };

  // Global Code Copy Function
  window.copyCode = function (button) {
    const raw = button.getAttribute('data-code');
    const text = decodeURIComponent(raw);
    navigator.clipboard.writeText(text).then(() => {
      const orig = button.innerText;
      button.innerText = 'کپی شد';
      button.style.color = '#10b981';
      setTimeout(() => {
        button.innerText = orig;
        button.style.color = '';
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy', err);
    });
  };

  // LocalStorage Helpers
  function saveToLocalStorage() {
    try {
      localStorage.setItem('agy_chats_v2', JSON.stringify(chats));
      localStorage.setItem('agy_active_chat_id', activeChatId || '');
      localStorage.setItem('agy_current_model', currentModel || '');
    } catch (e) {
      console.warn('LocalStorage save failed:', e);
    }
  }

  function loadFromLocalStorage() {
    try {
      const storedChats = localStorage.getItem('agy_chats_v2');
      if (storedChats) {
        chats = JSON.parse(storedChats);
      }
      activeChatId = localStorage.getItem('agy_active_chat_id') || activeChatId;
      currentModel = localStorage.getItem('agy_current_model') || currentModel;
    } catch (e) {
      console.warn('LocalStorage load failed:', e);
    }
  }

  // Format Persian / Relative Time
  function formatTimestamp(ts) {
    if (!ts) return '';
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
  }

  // Auto-scroll chat area
  function scrollToBottom(force = false) {
    if (!chatScrollArea) return;
    const isNearBottom = chatScrollArea.scrollHeight - chatScrollArea.scrollTop - chatScrollArea.clientHeight < 350;
    if (force || isNearBottom) {
      chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
    }
  }

  // =========================================================================
  // Feature 5: Network Status Indicator & Watchdog
  // =========================================================================
  function updateNetworkStatus() {
    if (!isWsConnected) {
      // Red: Disconnected from local server
      if (headerStatusDot) {
        headerStatusDot.className = 'status-dot disconnected';
        headerStatusDot.title = 'ارتباط با سرور ترموکس قطع است';
      }
      if (serverErrorBanner) serverErrorBanner.classList.add('show');
      if (networkWarningBanner) networkWarningBanner.classList.remove('show');
    } else if (!isInternetOnline) {
      // Yellow: Local server connected, but internet offline
      if (headerStatusDot) {
        headerStatusDot.className = 'status-dot warning';
        headerStatusDot.title = 'سرور متصل است، اما اینترنت قطع است';
      }
      if (networkWarningBanner) networkWarningBanner.classList.add('show');
      if (serverErrorBanner) serverErrorBanner.classList.remove('show');
    } else {
      // Green: Local server connected and internet online
      if (headerStatusDot) {
        headerStatusDot.className = 'status-dot connected';
        headerStatusDot.title = 'اتصال برقرار است (سرور و اینترنت فعال)';
      }
      if (networkWarningBanner) networkWarningBanner.classList.remove('show');
      if (serverErrorBanner) serverErrorBanner.classList.remove('show');
    }
  }

  // Listen to browser online/offline events
  window.addEventListener('online', () => {
    isInternetOnline = true;
    updateNetworkStatus();
  });

  window.addEventListener('offline', () => {
    isInternetOnline = false;
    updateNetworkStatus();
  });

  // Auth Fetch Wrapper with automatic bearer header and 401 interception
  async function authFetch(url, options = {}) {
    options.headers = options.headers || {};
    if (authToken) {
      if (options.headers instanceof Headers) {
        options.headers.set('Authorization', `Bearer ${authToken}`);
      } else {
        options.headers['Authorization'] = `Bearer ${authToken}`;
      }
    }
    const res = await fetch(url, options);
    if (res.status === 401) {
      console.warn('[Auth] 401 Unauthorized for', url);
      return res;
    }
    return res;
  }

  // Feature 0: Authentication UI Handlers (Disabled)
  function showLoginModal(errorMsg = '') {
    return;
  }

  function hideLoginModal() {
    return;
  }

  function updateUserInfoUI(username) {
    currentUser = username || 'admin';
  }

  async function checkAuthStatus() {
    try {
      const headers = {};
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
      const res = await fetch('/api/auth/status', { headers });
      const data = await res.json();
      if (data && (data.authenticated || data.auth_enabled === false)) {
        isAuthenticated = true;
        hideLoginModal();
        fetchAccountQuota();
        return true;
      } else {
        isAuthenticated = true;
        hideLoginModal();
        return true;
      }
    } catch (err) {
      console.warn('[Auth] Status check bypass:', err);
      isAuthenticated = true;
      hideLoginModal();
      return true;
    }
  }

  async function handleLoginSubmit() {
    const user = authUsername ? authUsername.value.trim() : 'admin';
    const pwd = authPassword ? authPassword.value : '';
    const remember = authRememberMe ? authRememberMe.checked : true;

    if (!user || !pwd) {
      if (authAlertBanner) {
        authAlertBanner.textContent = 'لطفاً نام کاربری و رمز عبور را وارد کنید.';
        authAlertBanner.className = 'auth-alert';
        authAlertBanner.style.display = 'block';
      }
      return;
    }

    if (btnAuthSubmit) btnAuthSubmit.disabled = true;
    if (authSubmitSpinner) authSubmitSpinner.style.display = 'block';
    if (authBtnText) authBtnText.textContent = 'در حال بررسی...';
    if (authAlertBanner) authAlertBanner.style.display = 'none';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pwd, remember })
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        authToken = data.token;
        currentUser = data.username || user;
        isAuthenticated = true;

        if (remember) {
          localStorage.setItem('anti_auth_token', authToken);
          localStorage.setItem('anti_username', currentUser);
        } else {
          sessionStorage.setItem('anti_auth_token', authToken);
          sessionStorage.setItem('anti_username', currentUser);
        }

        updateUserInfoUI(currentUser);
        hideLoginModal();

        // Connect and load user data
        connectWebSocket();
        fetchServerChats();
        fetchModels();
        fetchWorkspace();
        fetchProcesses();
        fetchMentions();
      } else {
        if (authAlertBanner) {
          authAlertBanner.textContent = data.error || 'نام کاربری یا رمز عبور نامعتبر است.';
          authAlertBanner.className = 'auth-alert';
          authAlertBanner.style.display = 'block';
        }
        if (authPassword) authPassword.focus();
      }
    } catch (err) {
      if (authAlertBanner) {
        authAlertBanner.textContent = 'خطا در ارتباط با سرور. لطفاً اتصال را بررسی کنید.';
        authAlertBanner.className = 'auth-alert';
        authAlertBanner.style.display = 'block';
      }
    } finally {
      if (btnAuthSubmit) btnAuthSubmit.disabled = false;
      if (authSubmitSpinner) authSubmitSpinner.style.display = 'none';
      if (authBtnText) authBtnText.textContent = 'ورود به سیستم';
    }
  }

  async function handleLogout() {
    if (!confirm('آیا مایلید از حساب کاربری خود خارج شوید؟')) return;

    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      });
    } catch (e) {}

    authToken = null;
    isAuthenticated = false;
    localStorage.removeItem('anti_auth_token');
    localStorage.removeItem('anti_username');
    sessionStorage.removeItem('anti_auth_token');
    sessionStorage.removeItem('anti_username');

    if (ws) {
      try { ws.close(); } catch (e) {}
    }

    closeDrawer();
    showLoginModal('با موفقیت از سیستم خارج شدید.');
  }

  // Periodic Health Check
  async function checkHealth() {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        isInternetOnline = (data.internet_ok || navigator.onLine);
        if (data.processes_count !== undefined) {
          updateProcessBadge(data.processes_count);
        }
      }
    } catch (e) {
      // Server might be down
    }
    updateNetworkStatus();
  }

  // Restart Engine Function
  async function restartEngine() {
    if (btnBannerRestart) btnBannerRestart.disabled = true;
    if (btnDrawerRestart) btnDrawerRestart.disabled = true;

    try {
      const res = await authFetch('/api/restart', { method: 'POST' });
      const data = await res.json();
      appendMessageBubble('assistant', `🔄 **راه‌اندازی مجدد:** ${data.message || 'موتور با موفقیت ریستارت شد.'}`, Date.now() / 1000, true);
    } catch (e) {
      appendMessageBubble('assistant', `⚠️ **خطا در راه‌اندازی مجدد:** ${e.message}`, Date.now() / 1000, true);
    } finally {
      if (btnBannerRestart) btnBannerRestart.disabled = false;
      if (btnDrawerRestart) btnDrawerRestart.disabled = false;
      closeDrawer();
      fetchProcesses();
    }
  }

  // =========================================================================
  // Antigravity Google Account & Model Quota Tracker
  // =========================================================================
  const pillQuota = document.getElementById('pillQuota');
  const quotaModal = document.getElementById('quotaModal');
  const btnCloseQuota = document.getElementById('btnCloseQuota');
  const quotaModalEmail = document.getElementById('quotaModalEmail');
  const quotaModalAuthMethod = document.getElementById('quotaModalAuthMethod');
  const btnOpenCliLoginGuide = document.getElementById('btnOpenCliLoginGuide');
  const cliLoginBox = document.getElementById('cliLoginBox');
  const modelsQuotaList = document.getElementById('modelsQuotaList');
  const meterPromptTokens = document.getElementById('meterPromptTokens');
  const meterThinkingTokens = document.getElementById('meterThinkingTokens');
  const meterResponseTokens = document.getElementById('meterResponseTokens');
  const btnDrawerQuota = document.getElementById('btnDrawerQuota');
  const btnDrawerOpenQuota = document.getElementById('btnDrawerOpenQuota');
  const btnOpenAccountQuota = document.getElementById('btnOpenAccountQuota');

  let accountQuotaData = null;

  async function fetchAccountQuota() {
    try {
      const res = await authFetch('/api/antigravity/account');
      if (res.ok) {
        accountQuotaData = await res.json();
        updateAccountQuotaUI();
      }
    } catch (e) {
      console.warn('Could not fetch account quota:', e);
    }
  }

  function updateAccountQuotaUI() {
    if (!accountQuotaData) return;
    const email = accountQuotaData.email || 'حساب گوگل Antigravity';

    if (drawerUserName) drawerUserName.textContent = email;
    if (quotaModalEmail) quotaModalEmail.textContent = email;
    if (quotaModalAuthMethod) {
      quotaModalAuthMethod.textContent = accountQuotaData.logged_in
        ? 'متصل به سرورهای رسمی Google Antigravity'
        : 'حالت آفلاین / بدون توکن OAuth';
    }

    if (accountQuotaData.usage) {
      if (meterPromptTokens) meterPromptTokens.textContent = Number(accountQuotaData.usage.total_prompt_tokens).toLocaleString();
      if (meterThinkingTokens) meterThinkingTokens.textContent = Number(accountQuotaData.usage.total_thinking_tokens).toLocaleString();
      if (meterResponseTokens) meterResponseTokens.textContent = Number(accountQuotaData.usage.total_response_tokens).toLocaleString();
    }

    if (modelsQuotaList && accountQuotaData.models_quota) {
      modelsQuotaList.innerHTML = '';
      accountQuotaData.models_quota.forEach(m => {
        const card = document.createElement('div');
        card.className = 'model-quota-card';
        card.innerHTML = `
          <div class="model-quota-header">
            <span class="model-quota-title">${m.name}</span>
            <span class="model-quota-tier">${m.tier}</span>
          </div>
          <div class="model-progress-bar-wrap">
            <div class="model-progress-bar-fill" style="width: ${m.used_percentage}%;"></div>
          </div>
          <div class="model-quota-footer">
            <span>سقف درخواست: ${m.rpm_limit}</span>
            <span>وضعیت: ${m.daily_quota}</span>
          </div>
        `;
        modelsQuotaList.appendChild(card);
      });
    }
  }

  function openQuotaModal() {
    if (quotaModal) quotaModal.classList.add('open');
    if (cliLoginBox) cliLoginBox.style.display = 'none';
    fetchAccountQuota();
  }

  function closeQuotaModal() {
    if (quotaModal) quotaModal.classList.remove('open');
  }

  // Update Badge in header and drawer
  function updateProcessBadge(count) {
    const val = count || 0;
    if (procBadgeHeader) procBadgeHeader.textContent = val;
    if (procBadgeDrawer) procBadgeDrawer.textContent = val;
    if (procModalBadge) procModalBadge.textContent = val;
  }

  // Utility: HTML Escaping
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Utility: Haptic Feedback on supported mobile browsers
  function triggerHaptic(ms = 15) {
    if (navigator.vibrate) {
      try { navigator.vibrate(ms); } catch (e) {}
    }
  }

  // Lightweight Toast Notification System
  function showToast(msg, type = 'info') {
    if (!msg) return;
    try {
      let container = document.getElementById('agyToastContainer');
      if (!container) {
        container = document.createElement('div');
        container.id = 'agyToastContainer';
        container.style.cssText = `
          position: fixed;
          top: 20px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 999999;
          display: flex;
          flex-direction: column;
          gap: 8px;
          pointer-events: none;
          max-width: 90vw;
          width: max-content;
        `;
        document.body.appendChild(container);
      }

      const toast = document.createElement('div');
      toast.className = `agy-toast agy-toast-${type}`;
      
      const colors = {
        success: { bg: '#064e3b', border: '#059669', text: '#ecfdf5' },
        error: { bg: '#7f1d1d', border: '#dc2626', text: '#fef2f2' },
        warn: { bg: '#78350f', border: '#d97706', text: '#fffbeb' },
        info: { bg: '#1e293b', border: '#3b82f6', text: '#f8fafc' }
      };
      const theme = colors[type] || colors.info;

      toast.style.cssText = `
        background: ${theme.bg};
        border: 1px solid ${theme.border};
        color: ${theme.text};
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
        box-shadow: 0 4px 16px rgba(0,0,0,0.5);
        opacity: 0;
        transform: translateY(-8px);
        transition: opacity 0.2s ease, transform 0.2s ease;
        pointer-events: auto;
        direction: rtl;
        text-align: right;
      `;
      toast.textContent = msg;
      container.appendChild(toast);

      requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
      });

      triggerHaptic(15);

      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-8px)';
        setTimeout(() => {
          if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 250);
      }, 3500);
    } catch (e) {
      console.log('[Toast]', type, msg);
    }
  }

  window.showToast = showToast;

  // Create Antigravity 2.0 Minimal Thinking Accordion Element
  function createThinkingAccordion(thinkingText, duration, tokens, isLive = false) {
    const card = document.createElement('div');
    card.className = `agy-thinking-card ${isLive ? 'active expanded' : ''}`;
    
    let durStr = duration ? `${duration}s` : (isLive ? '0.0s' : '');
    const tokStr = tokens ? ` • ${tokens} tokens` : '';
    const badgeText = `${durStr}${tokStr}`;
    const titleText = isLive ? 'Thinking...' : 'Thought';

    card.innerHTML = `
      <div class="agy-thinking-header">
        <div class="agy-thinking-title">
          <span>🧠</span>
          <span class="thinking-title-label">${titleText}</span>
        </div>
        <span class="agy-thinking-time">${badgeText}</span>
      </div>
      <div class="agy-thinking-body">${escapeHtml(thinkingText || '')}</div>
    `;

    const header = card.querySelector('.agy-thinking-header');
    header.addEventListener('click', () => {
      triggerHaptic(10);
      card.classList.toggle('expanded');
    });

    return card;
  }

  // Create Antigravity Action Steps Accordion
  function createStepsAccordion(steps) {
    const accordion = document.createElement('div');
    accordion.className = 'activity-accordion';
    const count = Array.isArray(steps) ? steps.length : 0;

    accordion.innerHTML = `
      <div class="accordion-header">
        <div class="accordion-summary">
          <span class="accordion-icon">⚡</span>
          <span class="accordion-title">عملیات و ابزارهای اجرا شده (${count} گام)</span>
        </div>
        <div class="accordion-meta-wrap">
          <span class="accordion-badge">تکمیل شده</span>
          <svg class="accordion-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
      <div class="accordion-content"></div>
    `;

    const content = accordion.querySelector('.accordion-content');
    if (Array.isArray(steps)) {
      steps.forEach(step => {
        const stepEl = document.createElement('div');
        stepEl.className = 'step-item';
        stepEl.innerHTML = `
          <div class="step-row">
            <div class="step-title-wrap">
              <span class="step-status-icon">✓</span>
              <span class="step-text">${step.icon || '•'} ${escapeHtml(step.title || step.tool)}</span>
            </div>
            <span class="step-duration">${step.duration || 0}s</span>
          </div>
        `;
        if (step.output) {
          const outBox = document.createElement('div');
          outBox.className = 'mini-terminal';
          outBox.innerHTML = `
            <div class="mini-terminal-header">
              <span class="mini-terminal-cmd">${escapeHtml(step.command || step.tool)}</span>
            </div>
            <div class="mini-terminal-body" style="max-height: 180px;">${escapeHtml(step.output)}</div>
          `;
          stepEl.appendChild(outBox);
        }
        content.appendChild(stepEl);
      });
    }

    const header = accordion.querySelector('.accordion-header');
    header.addEventListener('click', () => {
      triggerHaptic(10);
      accordion.classList.toggle('expanded');
    });

    return accordion;
  }

  // =========================================================================
  // Render Messages for Current Chat
  // =========================================================================
  function renderMessages() {
    if (!chatInner) return;
    currentAccordionEl = null;
    currentMiniTerminals = {};
    activeTurnStepIndices.clear();

    const chat = chats[activeChatId];
    if (!chat || !chat.messages || chat.messages.length === 0) {
      chatInner.innerHTML = '';
      return;
    }

    chatInner.innerHTML = '';

    chat.messages.forEach(msg => {
      appendMessageBubble(msg.role, msg.content, msg.timestamp, false, false, msg.meta);
    });

    scrollToBottom(true);
  }

  // Append a single message bubble to DOM
  function appendMessageBubble(role, content, timestamp, shouldScroll = true, isError = false, meta = null) {
    if (emptyState) emptyState.style.display = 'none';

    const row = document.createElement('div');
    row.className = `msg-row ${role}`;

    if (role === 'user') {
      const bubble = document.createElement('div');
      bubble.className = 'bubble user-bubble';
      bubble.setAttribute('dir', 'auto');

      const p = document.createElement('p');
      p.style.whiteSpace = 'pre-wrap';
      p.textContent = content;
      bubble.appendChild(p);

      if (timestamp) {
        const metaSpan = document.createElement('span');
        metaSpan.className = 'msg-meta';
        metaSpan.textContent = formatTimestamp(timestamp);
        bubble.appendChild(metaSpan);
      }

      row.appendChild(bubble);
    } else {
      row.className = 'msg-row assistant minimal-turn';

      // Antigravity 2.0 Live Feed (if meta has thinking or steps)
      if (meta && (meta.thinking || (meta.steps && meta.steps.length > 0))) {
        const feed = document.createElement('div');
        feed.className = 'agy-live-feed';

        if (meta.thinking) {
          const thinkItem = document.createElement('div');
          thinkItem.className = 'agy-feed-item thinking';
          const dur = meta.duration ? `${Math.round(meta.duration)}s` : '30s';
          thinkItem.innerHTML = `
            <div class="agy-feed-header">
              <span class="agy-feed-label">Thought for ${dur}</span>
              <span class="agy-feed-chevron">›</span>
            </div>
            <div class="agy-feed-body">${escapeHtml(meta.thinking)}</div>
          `;
          thinkItem.querySelector('.agy-feed-header').addEventListener('click', () => {
            triggerHaptic(10);
            thinkItem.classList.toggle('expanded');
          });
          feed.appendChild(thinkItem);
        }

        if (meta.steps && Array.isArray(meta.steps)) {
          meta.steps.forEach(st => {
            const item = document.createElement('div');
            item.className = `agy-feed-item ${(st.action || st.feed_type || 'tool').toLowerCase()}`;
            item._stepData = st;
            item.innerHTML = buildFeedItemHeaderHtml(st);
            const body = item.querySelector('.agy-feed-body');
            renderFeedPreview(body, st);
            item.querySelector('.agy-feed-header').addEventListener('click', () => {
              triggerHaptic(10);
              item.classList.toggle('expanded');
            });
            feed.appendChild(item);
          });
        }

        row.appendChild(feed);
      }

      // Message Bubble Body (Pure Typography on pitch-black background)
      const bubble = document.createElement('div');
      bubble.className = 'bubble ai-bubble';
      bubble.setAttribute('dir', 'auto');

      if (typeof marked !== 'undefined') {
        bubble.innerHTML = marked.parse(content || '');
      } else {
        bubble.textContent = content || '';
      }

      if (isError) {
        const retryBtn = document.createElement('button');
        retryBtn.className = 'msg-retry-btn';
        retryBtn.innerHTML = `↻ تلاش مجدد`;
        retryBtn.onclick = () => {
          const chat = chats[activeChatId];
          if (chat && chat.messages.length > 1) {
            const lastUserMsg = [...chat.messages].reverse().find(m => m.role === 'user');
            if (lastUserMsg) retryMessage(lastUserMsg.content);
          }
        };
        bubble.appendChild(retryBtn);
      }

      row.appendChild(bubble);
    }

    chatInner.appendChild(row);

    if (shouldScroll) {
      scrollToBottom(true);
    }

    return row.querySelector('.ai-bubble') || row;
  }

  // Retry Message Function (Feature 5.3)
  function retryMessage(promptText) {
    if (!promptText) return;
    if (inputMessage) {
      inputMessage.value = promptText;
      inputMessage.dispatchEvent(new Event('input'));
      sendMessage();
    }
  }

  // =========================================================================
  // Feature 1: Live Step-by-Step Activity Accordion & Real-time Command Preview
  // =========================================================================
  function getOrCreateAccordion() {
    if (currentAccordionEl && document.body.contains(currentAccordionEl)) {
      return currentAccordionEl;
    }

    const row = document.createElement('div');
    row.className = 'msg-row assistant';
    row.style.marginBottom = '4px';

    const accordion = document.createElement('div');
    accordion.className = 'activity-accordion expanded';

    accordion.innerHTML = `
      <div class="accordion-header">
        <div class="accordion-summary">
          <span class="accordion-icon">⚙️</span>
          <span class="accordion-title">مراحل پردازش هوش مصنوعی...</span>
        </div>
        <div class="accordion-meta-wrap">
          <span class="accordion-badge">زنده</span>
          <svg class="accordion-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
      <div class="accordion-content"></div>
    `;

    // Click header to toggle collapse
    accordion.querySelector('.accordion-header').addEventListener('click', () => {
      accordion.classList.toggle('expanded');
    });

    row.appendChild(accordion);
    chatInner.appendChild(row);
    currentAccordionEl = accordion;
    scrollToBottom();

    return currentAccordionEl;
  }

    // =========================================================================
  // Antigravity 2.0 Minimalist Live Feed Handlers (Exact match to reference)
  // =========================================================================
  let currentLiveFeedEl = null;
  let currentFeedStatusEl = null;
  let lastTurnThinkingText = '';

  // File Badges for Antigravity 2.0 Feed Items (Image 7)
  function getFileBadge(ext) {
    const e = (ext || '').toLowerCase().replace(/^\./, '');
    if (e === 'tsx' || e === 'jsx') {
      return { text: '⚛', cls: 'icon-react' };
    }
    if (e === 'ts') {
      return { text: 'TS', cls: 'icon-ts' };
    }
    if (e === 'js') {
      return { text: 'JS', cls: 'icon-js' };
    }
    if (e === 'py') {
      return { text: 'PY', cls: 'icon-py' };
    }
    if (['html', 'xml', 'svg'].includes(e)) {
      return { text: '</>', cls: 'icon-html' };
    }
    if (['css', 'scss', 'sass', 'less'].includes(e)) {
      return { text: '{}', cls: 'icon-css' };
    }
    if (e === 'json') {
      return { text: '{}', cls: 'icon-json' };
    }
    if (['md', 'txt'].includes(e)) {
      return { text: 'MD', cls: 'icon-md' };
    }
    if (['sh', 'bash', 'zsh'].includes(e)) {
      return { text: '$_', cls: 'icon-sh' };
    }
    return { text: '{}', cls: 'icon-code' };
  }

  function buildFeedItemHeaderHtml(data) {
    const action = data.action || (data.feed_type === 'edit' ? 'Edited' : (data.feed_type === 'create' ? 'Created' : (data.feed_type === 'read' ? 'Analyzed' : 'Ran')));
    const fname = data.file_name || 'file';
    const badge = getFileBadge(data.file_ext);

    if (action === 'Analyzed') {
      const lineRange = data.line_range ? `<span class="agy-feed-linerange">${escapeHtml(data.line_range)}</span>` : '';
      return `
        <div class="agy-feed-header">
          <span class="agy-feed-verb">Analyzed</span>
          <span class="agy-feed-badge ${badge.cls}">${badge.text}</span>
          <span class="agy-feed-filename">${escapeHtml(fname)}</span>
          ${lineRange}
          <span class="agy-feed-chevron">›</span>
        </div>
        <div class="agy-feed-body"></div>
      `;
    }

    if (action === 'Created') {
      return `
        <div class="agy-feed-header">
          <span class="agy-feed-verb">Created</span>
          <span class="agy-feed-badge ${badge.cls}">${badge.text}</span>
          <span class="agy-feed-filename">${escapeHtml(fname)}</span>
          <span class="agy-feed-diff-add">+${data.add_lines || 0}</span>
          <span class="agy-feed-diff-del">-0</span>
          <span class="agy-feed-chevron">›</span>
        </div>
        <div class="agy-feed-body"></div>
      `;
    }

    if (action === 'Edited') {
      return `
        <div class="agy-feed-header">
          <span class="agy-feed-verb">Edited</span>
          <span class="agy-feed-badge ${badge.cls}">${badge.text}</span>
          <span class="agy-feed-filename">${escapeHtml(fname)}</span>
          <span class="agy-feed-diff-add">+${data.add_lines || 0}</span>
          <span class="agy-feed-diff-del">-${data.del_lines || 0}</span>
          <span class="agy-feed-chevron">›</span>
        </div>
        <div class="agy-feed-body"></div>
      `;
    }

    // Default: Ran <command / summary>
    const labelText = data.feed_label || data.command || data.title || data.tool_name || 'terminal command';
    return `
      <div class="agy-feed-header">
        <span class="agy-feed-verb">Ran</span>
        <span class="agy-feed-cmd">${escapeHtml(labelText)}</span>
        <span class="agy-feed-chevron">›</span>
      </div>
      <div class="agy-feed-body"></div>
    `;
  }

  function renderFeedPreview(body, data) {
    if (!body || !data) return;

    // 1. Edit / Diff Preview
    if (data.action === 'Edited' || data.feed_type === 'edit') {
      const target = data.target || '';
      const replacement = data.replacement || '';
      const fname = data.file_name || 'file';
      const addCount = data.add_lines || 0;
      const delCount = data.del_lines || 0;

      let diffHtml = `
        <div class="agy-preview-diff">
          <div class="agy-diff-header">
            <span class="agy-diff-file">${escapeHtml(fname)}</span>
            <span class="agy-diff-stats"><span class="add">+${addCount}</span> <span class="del">-${delCount}</span></span>
          </div>
          <div class="agy-diff-content">
      `;
      if (target) {
        target.split('\n').forEach(line => {
          diffHtml += `<div class="agy-diff-line del"><span class="marker">-</span><span class="code">${escapeHtml(line)}</span></div>`;
        });
      }
      if (replacement) {
        replacement.split('\n').forEach(line => {
          diffHtml += `<div class="agy-diff-line add"><span class="marker">+</span><span class="code">${escapeHtml(line)}</span></div>`;
        });
      }
      if (!target && !replacement && data.output) {
        diffHtml += `<div class="agy-diff-line"><span class="code">${escapeHtml(data.output)}</span></div>`;
      }
      diffHtml += `</div></div>`;
      body.innerHTML = diffHtml;
      return;
    }

    // 2. Created File Preview
    if (data.action === 'Created' || data.feed_type === 'create') {
      const fname = data.file_name || 'file';
      const snip = data.snippet || data.replacement || data.output || '';
      const addCount = data.add_lines || (snip ? snip.split('\n').length : 0);
      let createHtml = `
        <div class="agy-preview-diff">
          <div class="agy-diff-header">
            <span class="agy-diff-file">${escapeHtml(fname)}</span>
            <span class="agy-diff-stats"><span class="add">+${addCount}</span> <span class="del">-0</span></span>
          </div>
          <div class="agy-diff-content">
      `;
      if (snip) {
        snip.split('\n').forEach(line => {
          createHtml += `<div class="agy-diff-line add"><span class="marker">+</span><span class="code">${escapeHtml(line)}</span></div>`;
        });
      }
      createHtml += `</div></div>`;
      body.innerHTML = createHtml;
      return;
    }

    // 3. File Read / Analyzed Snippet Preview
    if (data.action === 'Analyzed' || data.feed_type === 'read' || data.snippet || data.tool_name === 'read_file' || data.tool_name === 'view_file') {
      const fname = data.file_name || 'file';
      const range = data.line_range || (data.start_line ? `line ${data.start_line}` : 'file');
      const snip = data.snippet || data.output || '';
      body.innerHTML = `
        <div class="agy-preview-code">
          <div class="agy-code-header">
            <span class="agy-code-file">${escapeHtml(fname)}</span>
            <span class="agy-code-range">${escapeHtml(range)}</span>
          </div>
          <pre class="agy-code-content">${escapeHtml(snip)}</pre>
        </div>
      `;
      return;
    }

    // 4. Command Preview
    if (data.action === 'Ran' || data.is_command || data.tool_name === 'run_command' || data.command) {
      const cmd = data.command || data.feed_label || 'command';
      const out = data.output || body.textContent || 'Running...';
      const dur = data.duration ? `${data.duration}s` : '';
      body.innerHTML = `
        <div class="agy-preview-terminal">
          <div class="agy-terminal-header">
            <span class="agy-terminal-cmd">$ ${escapeHtml(cmd)}</span>
            ${dur ? `<span class="agy-terminal-badge">${dur}</span>` : ''}
          </div>
          <pre class="agy-terminal-output">${escapeHtml(out)}</pre>
        </div>
      `;
      return;
    }

    // 5. Default / Output
    if (data.output) {
      body.innerHTML = `<pre class="agy-feed-generic-output">${escapeHtml(data.output)}</pre>`;
    }
  }

  function handleStepStart(data) {
    if (!currentLiveFeedEl) return;
    const stepIndex = data.step_index;
    let item = currentLiveFeedEl.querySelector(`[data-step="${stepIndex}"]`);
    if (!item) {
      item = document.createElement('div');
      item.setAttribute('data-step', stepIndex);
      item._stepData = Object.assign({}, data);
      const actionCls = (data.action || data.feed_type || 'tool').toLowerCase();
      item.className = `agy-feed-item ${actionCls}`;
      item.innerHTML = buildFeedItemHeaderHtml(data);

      const body = item.querySelector('.agy-feed-body');
      renderFeedPreview(body, item._stepData);

      item.querySelector('.agy-feed-header').addEventListener('click', () => {
        triggerHaptic(10);
        item.classList.toggle('expanded');
      });

      if (currentFeedStatusEl && currentFeedStatusEl.parentNode === currentLiveFeedEl) {
        currentLiveFeedEl.insertBefore(item, currentFeedStatusEl);
      } else {
        currentLiveFeedEl.appendChild(item);
      }
    } else {
      item._stepData = Object.assign(item._stepData || {}, data);
      const body = item.querySelector('.agy-feed-body');
      renderFeedPreview(body, item._stepData);
    }
    scrollToBottom();
  }

  function handleCommandOutput(data) {
    if (!currentLiveFeedEl) return;
    const stepIndex = data.step_index;
    const item = currentLiveFeedEl.querySelector(`[data-step="${stepIndex}"]`);
    if (item) {
      if (!item._stepData) item._stepData = {};
      item._stepData.output = (item._stepData.output ? item._stepData.output + '\n' : '') + data.line;
      const body = item.querySelector('.agy-feed-body');
      if (body) {
        const outPre = body.querySelector('.agy-terminal-output');
        if (outPre) {
          outPre.textContent = item._stepData.output;
        } else {
          renderFeedPreview(body, item._stepData);
        }
      }
    }
  }

  function handleStepDone(data) {
    if (!currentLiveFeedEl) return;
    const stepIndex = data.step_index;
    let item = currentLiveFeedEl.querySelector(`[data-step="${stepIndex}"]`);
    if (!item) {
      handleStepStart(data);
      item = currentLiveFeedEl.querySelector(`[data-step="${stepIndex}"]`);
    }
    if (item) {
      item._stepData = Object.assign(item._stepData || {}, data);
      item.innerHTML = buildFeedItemHeaderHtml(item._stepData);
      const body = item.querySelector('.agy-feed-body');
      if (body) {
        renderFeedPreview(body, item._stepData);
      }
      item.querySelector('.agy-feed-header').addEventListener('click', () => {
        triggerHaptic(10);
        item.classList.toggle('expanded');
      });
    }
    scrollToBottom();
  }

  function handleThinkingStep(data) {
    if (!currentLiveFeedEl) return;
    const dur = Math.round(data.duration || 1);
    const item = document.createElement('div');
    item.className = 'agy-feed-item thinking';
    const thText = data.thinking || lastTurnThinkingText || '';
    item.innerHTML = `
      <div class="agy-feed-header">
        <span class="agy-feed-verb">Thought for ${dur}s</span>
        <span class="agy-feed-chevron">›</span>
      </div>
      <div class="agy-feed-body">
        <div class="agy-preview-thought">${escapeHtml(thText || 'Reasoning analysis completed.')}</div>
      </div>
    `;
    item.querySelector('.agy-feed-header').addEventListener('click', () => {
      triggerHaptic(10);
      item.classList.toggle('expanded');
    });

    if (currentFeedStatusEl && currentFeedStatusEl.parentNode === currentLiveFeedEl) {
      currentLiveFeedEl.insertBefore(item, currentFeedStatusEl);
    } else {
      currentLiveFeedEl.appendChild(item);
    }
    scrollToBottom();
  }

  // Kill Command via WebSocket
  function killCommand(stepIndex) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'kill_command',
        chat_id: activeChatId,
        step_index: stepIndex
      }));
    }
    const tTimer = document.getElementById(`termTimer_${stepIndex}`);
    if (tTimer) tTimer.textContent += ' (توقف)';
  }

  // =========================================================================
  // Feature 2: Interactive Command & Permission Approval UI
  // =========================================================================
  function handlePermissionRequest(data) {
    if (emptyState) emptyState.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'msg-row assistant';
    row.id = `permCard_${data.request_id}`;

    const card = document.createElement('div');
    card.className = 'action-approval-card';
    card.setAttribute('dir', 'auto');

    card.innerHTML = `
      <div class="approval-card-header">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <span>${data.title || 'درخواست تایید اجرای دستور در ترمینال'}</span>
      </div>

      <div class="approval-card-cmd">$ ${data.command || data.raw_prompt || ''}</div>
      <div class="approval-card-path">مسیر اجرا: ${data.cwd || workspaceDir}</div>

      <div class="approval-card-actions">
        <button class="btn-approval allow" data-action="allow">✓ تایید و اجرا (Allow / Yes)</button>
        <button class="btn-approval always" data-action="always">✓✓ تایید همیشگی (Always Allow)</button>
        <button class="btn-approval deny" data-action="deny">✕ رد کردن (Deny / No)</button>
      </div>

      <div class="approval-custom-input-row">
        <input type="text" class="approval-custom-input" placeholder="ورودی یا پاسخ سفارشی..." dir="auto">
        <button class="btn-approval custom">ارسال پاسخ</button>
      </div>
    `;

    // Handle button clicks
    const btnAllow = card.querySelector('.btn-approval.allow');
    const btnAlways = card.querySelector('.btn-approval.always');
    const btnDeny = card.querySelector('.btn-approval.deny');
    const btnCustom = card.querySelector('.btn-approval.custom');
    const customInput = card.querySelector('.approval-custom-input');

    function resolveCard(decision, customVal = '') {
      // Disable all inputs
      card.querySelectorAll('button, input').forEach(el => el.disabled = true);
      
      const badge = document.createElement('div');
      if (decision === 'allow' || decision === 'always') {
        badge.className = 'approval-status-badge allowed';
        badge.textContent = `✓ مجوز تایید شد (${decision === 'always' ? 'همیشگی' : 'تک‌بار'})`;
      } else if (decision === 'custom') {
        badge.className = 'approval-status-badge allowed';
        badge.textContent = `✓ پاسخ سفارشی ارسال شد: ${customVal}`;
      } else {
        badge.className = 'approval-status-badge denied';
        badge.textContent = '✕ مجوز رد شد';
      }
      card.appendChild(badge);

      // Send to WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'permission_response',
          request_id: data.request_id,
          decision: decision,
          custom_input: customVal
        }));
      }
    }

    btnAllow.addEventListener('click', () => resolveCard('allow'));
    btnAlways.addEventListener('click', () => resolveCard('always'));
    btnDeny.addEventListener('click', () => resolveCard('deny'));
    btnCustom.addEventListener('click', () => {
      const val = customInput.value.trim();
      if (val) resolveCard('custom', val);
    });

    row.appendChild(card);
    chatInner.appendChild(row);
    scrollToBottom(true);
  }

  // =========================================================================
  // Feature 3: Background Processes Manager
  // =========================================================================
  async function fetchProcesses() {
    try {
      const res = await authFetch('/api/processes');
      if (res.ok) {
        const data = await res.json();
        updateProcessBadge(data.count || 0);
        renderProcessesList(data.processes || []);
      }
    } catch (e) {
      console.warn('Could not fetch processes:', e);
    }
  }

  function renderProcessesList(procs) {
    if (!processesListContainer) return;
    processesListContainer.innerHTML = '';

    if (!procs || procs.length === 0) {
      processesListContainer.innerHTML = '<div style="color: #666; text-align: center; padding: 20px;">هیچ پروسه‌ای یافت نشد.</div>';
      return;
    }

    procs.forEach(p => {
      const card = document.createElement('div');
      card.className = 'proc-card';

      card.innerHTML = `
        <div class="proc-header-row">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="proc-pid-badge">PID ${p.pid}</span>
            <span style="font-weight: 600; font-size: 13px; color: #fff;">${p.name}</span>
            ${p.is_server ? '<span style="font-size: 10px; background: #262626; color: #10b981; padding: 1px 6px; border-radius: 4px;">سرور اصلی</span>' : ''}
          </div>
          ${p.port ? `<span class="proc-port-badge">پورت :${p.port}</span>` : ''}
        </div>

        <div class="proc-cmd-text">${p.command}</div>

        <div class="proc-meta-row">
          <span>مصرف پردازنده: ${p.cpu}%</span>
          <span>حافظه رم: ${p.mem}%</span>
          <span>مدت فعالیت: ${p.uptime}</span>
        </div>

        <div class="proc-actions-row">
          <button class="proc-btn btn-inspect" data-pid="${p.pid}">👁 مشاهده زنده (Inspect)</button>
          ${!p.is_server ? `<button class="proc-btn danger btn-kill" data-pid="${p.pid}">🗑 بستن پروسه (Kill)</button>` : ''}
        </div>
      `;

      card.querySelector('.btn-inspect').addEventListener('click', () => {
        openInspectModal(p);
      });

      const killBtn = card.querySelector('.btn-kill');
      if (killBtn) {
        killBtn.addEventListener('click', () => {
          killProcess(p.pid);
        });
      }

      processesListContainer.appendChild(card);
    });
  }

  async function killProcess(pid, signal = 'SIGTERM') {
    try {
      const res = await authFetch(`/api/process-kill/${pid}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signal: signal })
      });
      const data = await res.json();
      if (data.success) {
        fetchProcesses();
      }
    } catch (e) {
      console.error('Kill error:', e);
    }
  }

  function openProcessesModal() {
    closeDrawer();
    fetchProcesses();
    if (processesModal) processesModal.classList.add('open');
  }

  function closeProcessesModal() {
    if (processesModal) processesModal.classList.remove('open');
  }

  // Feature 3.2: Inspect Process Modal
  async function openInspectModal(proc) {
    currentInspectingPid = proc.pid;
    if (inspectTitle) inspectTitle.textContent = `مشاهده زنده: ${proc.name} (PID ${proc.pid})`;
    if (inspectInfoBar) {
      inspectInfoBar.innerHTML = `
        <span>PID: <b>${proc.pid}</b></span>
        <span>دستور: <b>${proc.name}</b></span>
        <span>Uptime: <b>${proc.uptime}</b></span>
      `;
    }
    if (inspectTerminalOutput) inspectTerminalOutput.textContent = 'در حال دریافت اطلاعات پروسه...';
    if (inspectProcessModal) inspectProcessModal.classList.add('open');

    // Subscribe to logs via WS
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'subscribe_process_logs', pid: proc.pid }));
    }

    try {
      const res = await authFetch(`/api/process-logs/${proc.pid}`);
      if (res.ok) {
        const data = await res.json();
        if (data.info && inspectInfoBar) {
          inspectInfoBar.innerHTML = `
            <span>وضعیت: <b>${data.info.state || 'اجرا'}</b></span>
            <span>حافظه: <b>${data.info.vm_rss || '-'}</b></span>
            <span>مسیر: <b>${data.info.cwd || '-'}</b></span>
            <span>رشته‌ها: <b>${data.info.threads || '1'}</b></span>
          `;
        }
        if (inspectTerminalOutput) {
          if (data.logs && data.logs.length > 0) {
            inspectTerminalOutput.textContent = data.logs.join('\n');
          } else {
            inspectTerminalOutput.textContent = `[پروسه فعال است اما خروجی لاگ ثبت نگردیده است]\nCommand: ${proc.command}\nPID: ${proc.pid}`;
          }
          if (inspectTerminalScreen) inspectTerminalScreen.scrollTop = inspectTerminalScreen.scrollHeight;
        }
      }
    } catch (e) {
      if (inspectTerminalOutput) inspectTerminalOutput.textContent = `خطا در دریافت لاگ: ${e.message}`;
    }
  }

  function closeInspectModal() {
    if (currentInspectingPid && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'unsubscribe_process_logs', pid: currentInspectingPid }));
    }
    currentInspectingPid = null;
    if (inspectProcessModal) inspectProcessModal.classList.remove('open');
  }

  // Send Stdin to Inspected Process
  async function sendInspectStdin() {
    if (!currentInspectingPid || !inspectStdinInput) return;
    const text = inspectStdinInput.value;
    if (!text) return;

    try {
      await authFetch(`/api/process-input/${currentInspectingPid}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: text })
      });
      if (inspectTerminalOutput) {
        inspectTerminalOutput.textContent += `\n> ${text}\n`;
        if (inspectTerminalScreen) inspectTerminalScreen.scrollTop = inspectTerminalScreen.scrollHeight;
      }
      inspectStdinInput.value = '';
    } catch (e) {
      console.warn('Failed to send stdin:', e);
    }
  }

  // =========================================================================
  // Feature 4: Built-in File Explorer & Code Viewer
  // =========================================================================
  async function fetchFiles(path = '') {
    try {
      const url = path ? `/api/files?path=${encodeURIComponent(path)}` : '/api/files';
      const res = await authFetch(url);
      if (res.ok) {
        const data = await res.json();
        currentFilesPath = data.current_path;
        renderBreadcrumbs(data.current_path);
        renderFilesList(data.items || [], data.parent_path);
      }
    } catch (e) {
      console.warn('Could not fetch files:', e);
    }
  }

  function renderBreadcrumbs(fullPath) {
    if (!filesBreadcrumbs) return;
    filesBreadcrumbs.innerHTML = '';

    const parts = fullPath.split('/').filter(Boolean);
    let accum = '';

    const rootBtn = document.createElement('button');
    rootBtn.className = 'breadcrumb-segment';
    rootBtn.textContent = '/';
    rootBtn.onclick = () => fetchFiles('/');
    filesBreadcrumbs.appendChild(rootBtn);

    parts.forEach((p, idx) => {
      accum += '/' + p;
      const target = accum;
      const sep = document.createElement('span');
      sep.textContent = '/';
      sep.style.color = '#444';
      filesBreadcrumbs.appendChild(sep);

      const segBtn = document.createElement('button');
      segBtn.className = `breadcrumb-segment ${idx === parts.length - 1 ? 'active' : ''}`;
      segBtn.textContent = p;
      segBtn.onclick = () => fetchFiles(target);
      filesBreadcrumbs.appendChild(segBtn);
    });

    filesBreadcrumbs.scrollLeft = filesBreadcrumbs.scrollWidth;
  }

  function getFileIcon(ext, isDir) {
    if (isDir) return '📁';
    const map = {
      py: '🐍',
      js: '🟨',
      json: '📦',
      html: '🌐',
      css: '🎨',
      md: '📝',
      sh: '⚡',
      txt: '📄',
      svg: '🖼️',
      png: '🖼️',
      jpg: '🖼️',
      log: '📜'
    };
    return map[ext] || '📄';
  }

  function renderFilesList(items, parentPath) {
    if (!filesListContainer) return;
    filesListContainer.innerHTML = '';

    if (btnFilesUp) {
      btnFilesUp.onclick = () => {
        if (parentPath) fetchFiles(parentPath);
      };
      btnFilesUp.disabled = !parentPath;
    }

    if (items.length === 0) {
      filesListContainer.innerHTML = '<div style="color: #666; text-align: center; padding: 20px;">این پوشه خالی است.</div>';
      return;
    }

    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'file-item';

      row.innerHTML = `
        <div class="file-item-left">
          <span class="file-icon">${getFileIcon(item.ext, item.is_dir)}</span>
          <span class="file-name">${item.name}</span>
        </div>
        <div class="file-meta-right">
          ${item.is_dir ? `<span>${item.item_count} مورد</span>` : `<span>${item.size_formatted}</span>`}
        </div>
      `;

      row.onclick = () => {
        if (item.is_dir) {
          fetchFiles(item.path);
        } else {
          viewCodeFile(item.path);
        }
      };

      filesListContainer.appendChild(row);
    });
  }

  function openFilesModal() {
    closeDrawer();
    fetchFiles(currentFilesPath || workspaceDir);
    if (filesModal) filesModal.classList.add('open');
  }

  function closeFilesModal() {
    if (filesModal) filesModal.classList.remove('open');
  }

  // Feature 4.2: Built-in Code Viewer
  async function viewCodeFile(filePath) {
    currentViewedFilePath = filePath;
    currentViewedFileContent = '';
    const filename = filePath.split('/').pop();
    const ext = filename.split('.').pop().toLowerCase();

    if (codeViewerTitle) codeViewerTitle.textContent = filename;
    if (codeViewerLang) codeViewerLang.textContent = ext;
    if (codeLineNumbers) codeLineNumbers.textContent = '1';
    if (codeHighlighted) codeHighlighted.textContent = 'در حال بارگذاری فایل...';
    if (codeViewerModal) codeViewerModal.classList.add('open');
    toggleCodeEditMode(false);

    try {
      const res = await authFetch(`/api/file-content?path=${encodeURIComponent(filePath)}`);
      if (res.ok) {
        const data = await res.json();
        currentViewedFileContent = data.content || '';

        // Generate line numbers
        const linesCount = data.lines || (data.content.split('\n').length);
        let numStr = '';
        for (let i = 1; i <= linesCount; i++) {
          numStr += i + '\n';
        }
        if (codeLineNumbers) codeLineNumbers.textContent = numStr;

        // Syntax Highlighting
        if (typeof hljs !== 'undefined') {
          try {
            if (ext && hljs.getLanguage(ext)) {
              codeHighlighted.innerHTML = hljs.highlight(data.content, { language: ext }).value;
            } else {
              codeHighlighted.innerHTML = hljs.highlightAuto(data.content).value;
            }
          } catch (e) {
            codeHighlighted.textContent = data.content;
          }
        } else {
          codeHighlighted.textContent = data.content;
        }
      }
    } catch (e) {
      if (codeHighlighted) codeHighlighted.textContent = `خطا در باز کردن فایل: ${e.message}`;
    }
  }

  function closeCodeViewer() {
    toggleCodeEditMode(false);
    if (codeViewerModal) codeViewerModal.classList.remove('open');
  }

  // Toggle In-App Code Editor Mode
  function toggleCodeEditMode(force) {
    if (typeof force === 'boolean') {
      isCodeEditing = force;
    } else {
      isCodeEditing = !isCodeEditing;
    }
    if (isCodeEditing) {
      if (codeEditorInput) {
        codeEditorInput.value = currentViewedFileContent;
        codeEditorInput.style.display = 'block';
        codeEditorInput.focus();
      }
      if (codeHighlighted && codeHighlighted.parentElement) codeHighlighted.parentElement.style.display = 'none';
      if (codeLineNumbers) codeLineNumbers.style.display = 'none';
      if (btnCodeSave) btnCodeSave.style.display = 'inline-flex';
      if (btnCodeEditToggle) {
        btnCodeEditToggle.classList.add('active');
        btnCodeEditToggle.textContent = '👁️ پیش‌نمایش';
      }
    } else {
      if (codeEditorInput) codeEditorInput.style.display = 'none';
      if (codeHighlighted && codeHighlighted.parentElement) codeHighlighted.parentElement.style.display = 'block';
      if (codeLineNumbers) codeLineNumbers.style.display = 'block';
      if (btnCodeSave) btnCodeSave.style.display = 'none';
      if (btnCodeEditToggle) {
        btnCodeEditToggle.classList.remove('active');
        btnCodeEditToggle.textContent = '✏️ ویرایش';
      }
    }
  }

  // Save File Content from In-App Code Editor
  async function saveCurrentFileCode() {
    if (!currentViewedFilePath || !codeEditorInput) return;
    const newContent = codeEditorInput.value;
    const origBtnText = btnCodeSave ? btnCodeSave.innerText : 'ذخیره';
    if (btnCodeSave) {
      btnCodeSave.innerText = 'در حال ذخیره...';
      btnCodeSave.disabled = true;
    }

    try {
      const res = await authFetch('/api/file-save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: currentViewedFilePath, content: newContent })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        currentViewedFileContent = newContent;
        if (btnCodeSave) {
          btnCodeSave.innerText = '✅ ذخیره شد';
          btnCodeSave.style.color = '#10b981';
        }

        // Re-highlight preview
        const ext = currentViewedFilePath.split('.').pop().toLowerCase();
        if (typeof hljs !== 'undefined') {
          try {
            if (ext && hljs.getLanguage(ext)) {
              codeHighlighted.innerHTML = hljs.highlight(newContent, { language: ext }).value;
            } else {
              codeHighlighted.innerHTML = hljs.highlightAuto(newContent).value;
            }
          } catch (e) {
            codeHighlighted.textContent = newContent;
          }
        } else {
          codeHighlighted.textContent = newContent;
        }

        setTimeout(() => {
          if (btnCodeSave) {
            btnCodeSave.innerText = origBtnText;
            btnCodeSave.disabled = false;
            btnCodeSave.style.color = '';
          }
        }, 1500);
      } else {
        alert(data.error || 'خطا در ذخیره فایل');
        if (btnCodeSave) {
          btnCodeSave.innerText = origBtnText;
          btnCodeSave.disabled = false;
        }
      }
    } catch (err) {
      alert(`خطا در ارتباط با سرور: ${err.message}`);
      if (btnCodeSave) {
        btnCodeSave.innerText = origBtnText;
        btnCodeSave.disabled = false;
      }
    }
  }

  // =========================================================================
  // Multi-Project Workspaces Management
  // =========================================================================
  async function fetchProjects() {
    try {
      const res = await authFetch('/api/projects');
      if (res.ok) {
        const data = await res.json();
        activeProjectId = data.active_project_id;
        activeProject = data.active_project;
        projects = {};
        if (data.projects) {
          data.projects.forEach(p => {
            projects[p.id] = p;
          });
        }
        updateProjectUI();
      }
    } catch (e) {
      console.warn('Could not fetch projects:', e);
    }
  }

  function updateProjectUI() {
    if (activeProject) {
      if (drawerProjectName) drawerProjectName.textContent = activeProject.name || 'پروژه اصلی';
      if (drawerProjectPath) {
        drawerProjectPath.textContent = activeProject.path || '~';
        drawerProjectPath.title = activeProject.path || '~';
      }
      if (headerProjectText) {
        headerProjectText.textContent = `📁 ${activeProject.name || 'پروژه اصلی'}`;
      }
      if (workspacePathText) {
        workspacePathText.textContent = activeProject.path || '~';
      }
    }

    const pCount = Object.keys(projects).length;
    if (projectsBadgeDrawer) projectsBadgeDrawer.textContent = pCount;
    if (projectsModalBadge) projectsModalBadge.textContent = pCount;

    renderProjectsModalList();
  }

  function renderProjectsModalList() {
    if (!projectsListContainer) return;
    projectsListContainer.innerHTML = '';

    const pList = Object.values(projects);
    if (!pList.length && activeProject) {
      pList.push(activeProject);
    }

    pList.forEach(p => {
      const isCurrent = (p.id === activeProjectId);
      const card = document.createElement('div');
      card.className = `project-item-card ${isCurrent ? 'active' : ''}`;

      const info = document.createElement('div');
      info.className = 'project-item-info';
      info.onclick = () => {
        if (!isCurrent) switchProject(p.id);
      };

      const header = document.createElement('div');
      header.className = 'project-item-header';

      const name = document.createElement('span');
      name.className = 'project-item-name';
      name.textContent = p.name || 'پروژه';
      header.appendChild(name);

      if (isCurrent) {
        const activeTag = document.createElement('span');
        activeTag.className = 'project-active-tag';
        activeTag.textContent = 'فعال';
        header.appendChild(activeTag);
      }

      const meta = document.createElement('div');
      meta.className = 'project-item-meta';

      const count = document.createElement('span');
      count.textContent = `${p.chat_count !== undefined ? p.chat_count : 1} گفتگو`;

      const path = document.createElement('span');
      path.className = 'project-item-path';
      path.textContent = p.path || '~';
      path.title = p.path || '~';

      meta.appendChild(count);
      meta.appendChild(path);

      info.appendChild(header);
      info.appendChild(meta);

      const actions = document.createElement('div');
      actions.className = 'project-item-actions';

      if (!isCurrent) {
        const switchBtn = document.createElement('button');
        switchBtn.className = 'project-btn-switch';
        switchBtn.textContent = 'انتخاب';
        switchBtn.onclick = (e) => {
          e.stopPropagation();
          switchProject(p.id);
        };
        actions.appendChild(switchBtn);

        const delBtn = document.createElement('button');
        delBtn.className = 'project-btn-delete';
        delBtn.title = 'حذف پروژه';
        delBtn.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        `;
        delBtn.onclick = (e) => {
          e.stopPropagation();
          deleteProject(p.id);
        };
        actions.appendChild(delBtn);
      }

      card.appendChild(info);
      card.appendChild(actions);
      projectsListContainer.appendChild(card);
    });
  }

  async function switchProject(projectId) {
    if (activeProjectId === projectId) {
      closeProjectsModal();
      return;
    }
    try {
      const res = await authFetch(`/api/projects/${projectId}/switch`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        activeProjectId = data.active_project.id;
        activeProject = data.active_project;
        chats = {};
        if (data.chats) {
          data.chats.forEach(summary => {
            chats[summary.id] = {
              id: summary.id,
              title: summary.title,
              created_at: summary.created_at,
              updated_at: summary.updated_at,
              model: summary.model,
              messages: []
            };
          });
        }
        activeChatId = data.active_project.active_chat_id || (data.chats && data.chats[0] ? data.chats[0].id : null);
        if (activeChatId) {
          const chatRes = await authFetch(`/api/chats/${activeChatId}`);
          if (chatRes.ok) {
            chats[activeChatId] = await chatRes.json();
          }
        }
        updateProjectUI();
        renderMessages();
        updateDrawerChatList();
        closeProjectsModal();
        closeDrawer();

        currentFilesPath = '';
      }
    } catch (e) {
      console.error('Failed to switch project:', e);
    }
  }

  async function createNewProject(name, path) {
    if (!name || !name.trim()) {
      alert('لطفاً نام پروژه را وارد نمایید.');
      return;
    }
    try {
      const res = await authFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), path: (path || '').trim() })
      });
      if (res.ok) {
        const data = await res.json();
        if (createProjectPanel) createProjectPanel.style.display = 'none';
        if (newProjectName) newProjectName.value = '';
        if (newProjectPath) newProjectPath.value = '';
        await fetchProjects();
        await switchProject(data.active_project_id);
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.error || 'خطا در ایجاد پروژه');
      }
    } catch (e) {
      alert('خطا در ارتباط با سرور: ' + e.message);
    }
  }

  async function deleteProject(projectId) {
    if (!confirm('آیا از حذف این پروژه مطمئن هستید؟ (فایل‌های داخل پوشه دست‌نخورده باقی می‌مانند اما نشست گفتگوهای آن پاک می‌شود)')) {
      return;
    }
    try {
      const res = await authFetch(`/api/projects/${projectId}`, { method: 'DELETE' });
      if (res.ok) {
        const data = await res.json();
        await fetchProjects();
        if (data.active_project) {
          await switchProject(data.active_project.id);
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.error || 'امکان حذف این پروژه وجود ندارد.');
      }
    } catch (e) {
      alert('خطا: ' + e.message);
    }
  }

  function openProjectsModal() {
    if (projectsModal) projectsModal.classList.add('open');
    if (createProjectPanel) createProjectPanel.style.display = 'none';
    renderProjectsModalList();
  }

  function closeProjectsModal() {
    if (projectsModal) projectsModal.classList.remove('open');
  }

  // Copy Code in Viewer
  function copyCurrentFileCode() {
    if (!currentViewedFileContent) return;
    navigator.clipboard.writeText(currentViewedFileContent).then(() => {
      const orig = btnCodeCopy.innerText;
      btnCodeCopy.innerText = 'کپی شد';
      btnCodeCopy.style.color = '#10b981';
      setTimeout(() => {
        btnCodeCopy.innerText = orig;
        btnCodeCopy.style.color = '';
      }, 2000);
    });
  }

  // Download File
  function downloadCurrentFile() {
    if (!currentViewedFilePath) return;
    const downloadUrl = `/api/file-download?path=${encodeURIComponent(currentViewedFilePath)}`;
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = currentViewedFilePath.split('/').pop();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  // Mention File in Chat Input (@filename)
  function mentionCurrentFile() {
    if (!currentViewedFilePath) return;
    const filename = currentViewedFilePath.split('/').pop();
    closeCodeViewer();
    closeFilesModal();
    if (inputMessage) {
      inputMessage.value += (inputMessage.value ? ' ' : '') + `@${filename} `;
      inputMessage.dispatchEvent(new Event('input'));
      inputMessage.focus();
    }
  }

  // =========================================================================
  // Antigravity 2.0 Sidebar Projects Tree & Real Workspace Chats (Image 1)
  // =========================================================================
  const expandedProjectFolders = new Set();
  let cachedProjectsData = null;

  async function updateDrawerChatList() {
    const projectsContainer = document.getElementById('sidebarProjectsTree');
    const standaloneContainer = document.getElementById('sidebarStandaloneChats');

    try {
      const res = await fetch('/api/projects');
      if (!res.ok) return;
      const data = await res.json();
      cachedProjectsData = data;

      if (data.active_project_id) {
        activeProjectId = data.active_project_id;
        expandedProjectFolders.add(data.active_project_id);
      }

      // Update User profile in sidebar and settings
      if (data.user) {
        const nameEl = document.getElementById('sidebarUserName');
        const emailEl = document.getElementById('sidebarUserEmail');
        const avatarEl = document.getElementById('userAvatarText');
        if (nameEl) nameEl.textContent = data.user.name || 'کاربر مهمان';
        if (emailEl) emailEl.textContent = data.user.email || 'حساب متصل نیست';
        if (avatarEl) avatarEl.textContent = data.user.avatar || '👤';

        const sName = document.getElementById('settingsUserName');
        const sEmail = document.getElementById('settingsUserEmail');
        const sAvatar = document.getElementById('settingsUserAvatar');
        if (sName) sName.textContent = data.user.name || 'کاربر مهمان';
        if (sEmail) sEmail.textContent = data.user.email ? (data.user.email.length > 20 ? data.user.email.substring(0, 18) + '...' : data.user.email) : 'حساب متصل نیست';
        if (sAvatar) sAvatar.textContent = data.user.avatar || '👤';
      }

      // Populate Projects Tree with Real User Projects
      renderDrawerProjectsTree(data.projects);

      // Populate Standalone Chats
      if (standaloneContainer) {
        standaloneContainer.innerHTML = '';
        if (Array.isArray(data.standalone_chats) && data.standalone_chats.length > 0) {
          data.standalone_chats.forEach(c => {
            const item = document.createElement('div');
            item.className = `agy-chat-item ${c.id === activeChatId ? 'active' : ''}`;
            item.onclick = () => {
              switchChat(c.id);
              closeDrawer();
            };

            const titleEl = document.createElement('span');
            titleEl.className = 'agy-chat-title';
            titleEl.textContent = c.title || 'Conversation';
            item.appendChild(titleEl);

            const timeEl = document.createElement('span');
            timeEl.className = 'agy-chat-time';
            timeEl.textContent = c.time_str || '';
            item.appendChild(timeEl);

            standaloneContainer.appendChild(item);
          });
        }
      }

    } catch (e) {
      console.warn('[Drawer] Error loading projects tree:', e);
    }
  }

  function renderDrawerProjectsTree(projectsList, filterQuery = '') {
    const projectsContainer = document.getElementById('sidebarProjectsTree');
    if (!projectsContainer || !Array.isArray(projectsList)) return;
    projectsContainer.innerHTML = '';

    const q = (filterQuery || '').toLowerCase().trim();

    projectsList.forEach(p => {
      const isFiltered = q.length > 0;
      let matchedChats = p.chats || [];
      if (isFiltered) {
        const pNameMatch = (p.name || '').toLowerCase().includes(q);
        if (!pNameMatch) {
          matchedChats = matchedChats.filter(c => (c.title || '').toLowerCase().includes(q));
          if (matchedChats.length === 0) return;
        }
      }

      const isProjectActive = (p.id === activeProjectId);
      const isOpen = isFiltered || expandedProjectFolders.has(p.id) || isProjectActive;
      const folder = document.createElement('div');
      folder.className = `agy-project-folder ${isOpen ? 'open' : ''} ${isProjectActive ? 'active-project' : ''}`;
      folder.setAttribute('data-proj-id', p.id);

      const header = document.createElement('div');
      header.className = 'agy-project-header';
      header.innerHTML = `
        <div class="agy-project-header-left">
          <div class="agy-project-title-row">
            <span>📁</span>
            <span class="agy-project-name">${escapeHtml(p.name)}</span>
          </div>
          ${p.path ? `<span class="agy-project-path-sub">${escapeHtml(p.path)}</span>` : ''}
        </div>
        <div class="agy-project-header-right">
          <span class="agy-project-count-badge">${matchedChats.length}</span>
          <button class="agy-project-add-btn" title="گفتگوی جدید در این پروژه" onclick="window.createNewChatInProject(event, '${escapeHtml(p.id)}')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          </button>
          <svg class="agy-project-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>
      `;

      header.onclick = async (e) => {
        if (e.target.closest('.agy-project-add-btn')) return;
        if (folder.classList.contains('open')) {
          folder.classList.remove('open');
          expandedProjectFolders.delete(p.id);
        } else {
          folder.classList.add('open');
          expandedProjectFolders.add(p.id);
          if (p.id !== activeProjectId) {
            await switchProject(p.id);
          }
        }
      };
      folder.appendChild(header);

      const folderChatsList = document.createElement('div');
      folderChatsList.className = 'agy-project-chats';

      if (matchedChats && matchedChats.length > 0) {
        matchedChats.forEach(c => {
          const isChatActive = (c.id === activeChatId);
          const item = document.createElement('div');
          item.className = `agy-chat-item ${isChatActive ? 'active' : ''}`;
          item.onclick = async (e) => {
            e.stopPropagation();
            if (p.id !== activeProjectId) {
              await authFetch(`/api/projects/${p.id}/switch`, { method: 'POST' });
              activeProjectId = p.id;
            }
            switchChat(c.id);
            closeDrawer();
          };

          const titleEl = document.createElement('span');
          titleEl.className = 'agy-chat-title';
          titleEl.textContent = c.title || 'Untitled Conversation';
          item.appendChild(titleEl);

          const rightWrap = document.createElement('div');
          rightWrap.className = 'agy-chat-item-right';

          const delBtn = document.createElement('button');
          delBtn.className = 'agy-chat-delete-btn';
          delBtn.title = 'حذف این گفتگو';
          delBtn.innerHTML = '✕';
          delBtn.onclick = (e) => {
            e.stopPropagation();
            handleDeleteChat(e, c.id);
          };
          rightWrap.appendChild(delBtn);

          if (isChatActive) {
            const timeEl = document.createElement('span');
            timeEl.className = 'agy-chat-time';
            timeEl.textContent = c.time_str || 'now';
            rightWrap.appendChild(timeEl);
          } else {
            const dot = document.createElement('span');
            dot.className = 'agy-chat-dot';
            rightWrap.appendChild(dot);
          }

          item.appendChild(rightWrap);
          folderChatsList.appendChild(item);
        });
      } else {
        const empty = document.createElement('div');
        empty.className = 'agy-empty-chats';
        empty.textContent = 'No conversations yet';
        folderChatsList.appendChild(empty);
      }

      folder.appendChild(folderChatsList);
      projectsContainer.appendChild(folder);
    });
  }

  function filterDrawerProjects(query) {
    if (cachedProjectsData && cachedProjectsData.projects) {
      renderDrawerProjectsTree(cachedProjectsData.projects, query);
    }
  }

  let isProjectFilterVisible = false;
  function toggleProjectFilter() {
    const input = document.getElementById('projectFilterInput');
    if (!input) return;
    isProjectFilterVisible = !isProjectFilterVisible;
    input.style.display = isProjectFilterVisible ? 'block' : 'none';
    if (isProjectFilterVisible) {
      input.focus();
    } else {
      input.value = '';
      filterDrawerProjects('');
    }
  }

  // Device Storage Browser & Folder Picker
  let fpCurrentDirectory = '';
  let fpParentDirectory = null;

  async function promptNewProject() {
    closeDrawer();
    closeSettingsModal();
    const modal = document.getElementById('folderPickerModal');
    if (modal) {
      modal.classList.add('open');
      toggleFpMkdir(false);
      await loadFpDirectory(fpCurrentDirectory || '');
    }
  }

  function closeFolderPickerModal() {
    const modal = document.getElementById('folderPickerModal');
    if (modal) modal.classList.remove('open');
  }

  async function loadFpDirectory(path) {
    const dirListEl = document.getElementById('fpDirList');
    const pathDisplay = document.getElementById('fpCurrentPathDisplay');
    const crumbsEl = document.getElementById('fpBreadcrumbs');
    const rootsEl = document.getElementById('fpQuickRoots');
    const btnParent = document.getElementById('fpBtnParent');

    if (dirListEl) dirListEl.innerHTML = '<div class="agy-fp-loading">در حال خواندن پوشه‌های حافظه...</div>';

    try {
      const url = path ? `/api/fs/dirs?path=${encodeURIComponent(path)}` : '/api/fs/dirs';
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to load directory');
      const data = await res.json();

      fpCurrentDirectory = data.current_path;
      fpParentDirectory = data.parent_path;

      if (pathDisplay) pathDisplay.textContent = fpCurrentDirectory;

      // Auto-suggest project name if empty
      const nameIn = document.getElementById('fpProjectName');
      if (nameIn && !nameIn.value.trim()) {
        const parts = fpCurrentDirectory.split('/').filter(Boolean);
        const folderName = parts.pop() || 'Project';
        if (folderName !== 'projects' && folderName !== 'sdcard') {
          nameIn.value = folderName;
        }
      }

      // Render Parent Button state
      if (btnParent) {
        btnParent.disabled = !fpParentDirectory;
      }

      // Render Quick Roots
      if (rootsEl && data.quick_roots) {
        rootsEl.innerHTML = data.quick_roots.map(r => {
          const isAct = r.path === fpCurrentDirectory;
          return `<button type="button" class="agy-fp-root-chip ${isAct ? 'active' : ''}" onclick="window.navigateFpDir('${escapeHtml(r.path)}')">${escapeHtml(r.label)}</button>`;
        }).join('');
      }

      // Render Breadcrumbs
      if (crumbsEl && data.breadcrumbs) {
        crumbsEl.innerHTML = data.breadcrumbs.map((b, idx) => {
          const isLast = idx === data.breadcrumbs.length - 1;
          return `
            <span class="agy-fp-crumb ${isLast ? 'active' : ''}" onclick="window.navigateFpDir('${escapeHtml(b.path)}')">${escapeHtml(b.name)}</span>
            ${!isLast ? '<span class="agy-fp-crumb-sep">/</span>' : ''}
          `;
        }).join('');
        crumbsEl.scrollLeft = crumbsEl.scrollWidth;
      }

      // Render Subdirectories List
      if (dirListEl) {
        const subdirs = data.subdirs || [];
        if (subdirs.length === 0) {
          dirListEl.innerHTML = `
            <div class="agy-fp-empty">
              <div style="font-size:24px;margin-bottom:6px;">📂</div>
              <div>این پوشه خالی است.</div>
              <div style="font-size:11px;color:#52525b;margin-top:4px;">می‌توانید با دکمه بالا یک پوشه جدید بسازید یا همین مسیر را برای پروژه انتخاب کنید.</div>
            </div>
          `;
        } else {
          dirListEl.innerHTML = subdirs.map(d => {
            const countStr = d.item_count ? `(${d.item_count})` : '';
            return `
              <div class="agy-fp-folder-item" onclick="window.navigateFpDir('${escapeHtml(d.path)}')">
                <div class="agy-fp-folder-info">
                  <span class="agy-fp-folder-icon">📁</span>
                  <span class="agy-fp-folder-name">${escapeHtml(d.name)}</span>
                  <span class="agy-fp-folder-count">${countStr}</span>
                </div>
                <span class="agy-fp-folder-chevron">›</span>
              </div>
            `;
          }).join('');
        }
      }
    } catch (e) {
      if (dirListEl) {
        dirListEl.innerHTML = `<div class="agy-fp-empty" style="color:#ef4444;">خطا در خواندن پوشه: ${escapeHtml(e.message)}</div>`;
      }
    }
  }

  function navigateFpDir(path) {
    if (path) {
      loadFpDirectory(path);
    }
  }

  function navigateFpParent() {
    if (fpParentDirectory) {
      loadFpDirectory(fpParentDirectory);
    }
  }

  function refreshFpDir() {
    loadFpDirectory(fpCurrentDirectory);
  }

  function toggleFpMkdir(force) {
    const panel = document.getElementById('fpMkdirPanel');
    const input = document.getElementById('fpNewFolderName');
    if (!panel) return;
    const isShowing = typeof force === 'boolean' ? force : (panel.style.display === 'none');
    panel.style.display = isShowing ? 'block' : 'none';
    if (isShowing && input) {
      input.value = '';
      input.focus();
    }
  }

  async function submitFpMkdir() {
    const input = document.getElementById('fpNewFolderName');
    const folderName = input ? input.value.trim() : '';

    if (!folderName) {
      alert('لطفاً نام پوشه جدید را وارد نمایید.');
      if (input) input.focus();
      return;
    }

    try {
      const res = await authFetch('/api/fs/mkdir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parent_path: fpCurrentDirectory,
          folder_name: folderName
        })
      });

      const data = await res.json();
      if (res.ok && data.ok) {
        toggleFpMkdir(false);
        // Automatically set project name to this new folder
        const nameIn = document.getElementById('fpProjectName');
        if (nameIn) nameIn.value = folderName;
        // Enter the newly created folder
        await loadFpDirectory(data.path);
      } else {
        alert(data.error || 'خطا در ایجاد پوشه جدید.');
      }
    } catch (err) {
      alert('خطا در ارسال درخواست ایجاد پوشه: ' + err.message);
    }
  }

  function setFpPath(path) {
    navigateFpDir(path);
  }

  async function submitFolderPicker() {
    const nameIn = document.getElementById('fpProjectName');
    let pName = nameIn ? nameIn.value.trim() : '';
    const pPath = fpCurrentDirectory;

    if (!pPath) {
      alert('لطفاً پوشه‌ای از حافظه دستگاه انتخاب نمایید.');
      return;
    }

    if (!pName) {
      const parts = pPath.split('/').filter(Boolean);
      pName = parts.pop() || 'Project';
    }

    try {
      const res = await authFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: pName, path: pPath })
      });
      if (res.ok) {
        const data = await res.json();
        closeFolderPickerModal();
        expandedProjectFolders.add(data.active_project_id);
        await fetchProjects();
        await switchProject(data.active_project_id);
        updateDrawerChatList();
        renderSettingsProjectsList();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.error || 'خطا در ایجاد پروژه');
      }
    } catch (e) {
      alert('خطا در ارتباط: ' + e.message);
    }
  }

  async function handleDeleteChat(e, chatId) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!confirm('آیا از حذف این گفتگو اطمینان دارید؟ پیام‌ها و سوابق آن پاک خواهند شد.')) {
      return;
    }
    triggerHaptic(15);
    try {
      const res = await authFetch(`/api/chats/${chatId}`, { method: 'DELETE' });
      if (res.ok) {
        delete chats[chatId];
        if (activeChatId === chatId) {
          const remainingIds = Object.keys(chats);
          if (remainingIds.length > 0) {
            await switchChat(remainingIds[0]);
          } else {
            await createNewChat();
          }
        } else {
          renderMessages();
          updateDrawerChatList();
          renderSettingsProjectsList();
        }
      }
    } catch (err) {
      alert('خطا در حذف گفتگو: ' + err.message);
    }
  }

  // Universal Chat Search Engine
  let chatSearchDebounceTimer = null;
  function openChatSearchModal() {
    closeDrawer();
    const modal = document.getElementById('chatSearchModal');
    const input = document.getElementById('chatSearchInput');
    const results = document.getElementById('chatSearchResults');
    if (modal) {
      modal.classList.add('open');
      if (input) {
        input.value = '';
        input.focus();
      }
      if (results) {
        results.innerHTML = '<div class="agy-search-hint">عبارت مورد نظر خود را برای جستجو در متن پیام‌ها و چت‌ها وارد کنید...</div>';
      }
    }
  }

  function closeChatSearchModal() {
    const modal = document.getElementById('chatSearchModal');
    if (modal) modal.classList.remove('open');
  }

  async function performChatSearch(query) {
    const resultsContainer = document.getElementById('chatSearchResults');
    if (!resultsContainer) return;

    const q = (query || '').trim();
    if (!q) {
      resultsContainer.innerHTML = '<div class="agy-search-hint">عبارت مورد نظر خود را برای جستجو در متن پیام‌ها و چت‌ها وارد کنید...</div>';
      return;
    }

    resultsContainer.innerHTML = '<div class="agy-search-hint">در حال جستجو در میان تمام گفتگوها...</div>';

    try {
      const res = await fetch(`/api/search-chats?q=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error('Search request failed');
      const data = await res.json();
      const results = data.results || [];

      if (results.length === 0) {
        resultsContainer.innerHTML = `<div class="agy-search-hint">هیچ نتیجه‌ای برای «${escapeHtml(q)}» یافت نشد.</div>`;
        return;
      }

      const qRegex = new RegExp(`(${escapeRegex(q)})`, 'gi');

      resultsContainer.innerHTML = results.map(item => {
        const highlightedTitle = escapeHtml(item.title).replace(qRegex, '<mark>$1</mark>');
        const snippetHtml = item.matched_messages && item.matched_messages.length > 0 
          ? item.matched_messages.map(m => {
              const hlSnippet = escapeHtml(m.snippet).replace(qRegex, '<mark>$1</mark>');
              return `<div class="agy-search-snippet"><strong>${m.role === 'user' ? 'شما:' : 'هوش مصنوعی:'}</strong> ${hlSnippet}</div>`;
            }).join('')
          : '';

        return `
          <div class="agy-search-item" onclick="window.selectSearchResult('${escapeHtml(item.project_id)}', '${escapeHtml(item.chat_id)}')">
            <div class="agy-search-item-top">
              <span class="agy-search-item-title">${highlightedTitle}</span>
              <span class="agy-search-item-proj">📁 ${escapeHtml(item.project_name)}</span>
            </div>
            ${snippetHtml}
          </div>
        `;
      }).join('');
    } catch (e) {
      resultsContainer.innerHTML = `<div class="agy-search-hint" style="color:#ef4444;">خطا در جستجو: ${escapeHtml(e.message)}</div>`;
    }
  }

  async function selectSearchResult(projectId, chatId) {
    closeChatSearchModal();
    if (projectId && projectId !== activeProjectId) {
      await authFetch(`/api/projects/${projectId}/switch`, { method: 'POST' });
      activeProjectId = projectId;
      expandedProjectFolders.add(projectId);
    }
    await switchChat(chatId);
  }

  function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // Settings Projects & Chats Manager Pane
  async function renderSettingsProjectsList() {
    const container = document.getElementById('settingsProjectsMgmtList');
    if (!container) return;
    container.innerHTML = '<div style="color:#71717a;font-size:12px;padding:10px;">در حال بارگذاری لیست پروژه‌ها و گفتگوها...</div>';

    try {
      const res = await fetch('/api/projects');
      if (!res.ok) return;
      const data = await res.json();
      const projList = data.projects || [];
      if (projList.length === 0) {
        container.innerHTML = '<div style="color:#71717a;font-size:12px;padding:10px;">هیچ پروژه‌ای یافت نشد.</div>';
        return;
      }

      container.innerHTML = projList.map(p => {
        const isAct = p.id === activeProjectId;
        const chatsList = p.chats || [];
        return `
          <div class="agy-pm-card ${isAct ? 'active-proj' : ''}">
            <div class="agy-pm-header">
              <div>
                <div class="agy-pm-title">📁 ${escapeHtml(p.name)} ${isAct ? '<span class="agy-active-badge">فضای کاری فعال</span>' : ''}</div>
                <div class="agy-pm-path">${escapeHtml(p.path || '')}</div>
              </div>
              <div class="agy-pm-actions">
                ${!isAct ? `<button type="button" class="agy-btn-ghost" onclick="window.switchProjectFromSettings('${escapeHtml(p.id)}')">فعال‌سازی</button>` : ''}
                ${projList.length > 1 ? `<button type="button" class="agy-btn-danger-ghost" onclick="window.deleteProjectFromSettings('${escapeHtml(p.id)}')">حذف پروژه</button>` : ''}
              </div>
            </div>
            
            <div class="agy-pm-chats-table">
              <div style="font-size:11px;color:#71717a;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;">
                <span>گفتگوهای این پروژه (${chatsList.length}):</span>
                <button type="button" style="background:none;border:none;color:#e4e4e7;cursor:pointer;font-size:11px;font-weight:500;" onclick="window.createNewChatInProject(null, '${escapeHtml(p.id)}'); window.closeSettingsModal();">+ چت جدید</button>
              </div>
              ${chatsList.length > 0 ? chatsList.map(c => `
                <div class="agy-pm-chat-row">
                  <span class="agy-pm-chat-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title || 'گفتگو')}</span>
                  <div class="agy-pm-chat-actions">
                    <span style="font-size:10px;color:#71717a;font-family:var(--font-mono);">${c.time_str || ''}</span>
                    <button type="button" class="agy-btn-ghost" style="padding:2px 8px;font-size:10.5px;" onclick="window.openChatFromSettings('${escapeHtml(p.id)}', '${escapeHtml(c.id)}')">باز کردن</button>
                    <button type="button" class="agy-btn-danger-ghost" style="padding:2px 8px;font-size:10.5px;" title="حذف چت" onclick="window.handleDeleteChat(event, '${escapeHtml(c.id)}')">✕</button>
                  </div>
                </div>
              `).join('') : '<div style="font-size:11px;color:#71717a;padding:4px;">بدون گفتگو</div>'}
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.warn('Error loading settings projects list:', e);
    }
  }

  async function switchProjectFromSettings(projectId) {
    await switchProject(projectId);
    renderSettingsProjectsList();
    updateDrawerChatList();
  }

  async function deleteProjectFromSettings(projectId) {
    if (!confirm('آیا از حذف این پروژه مطمئن هستید؟ فایل‌های پروژه روی دیسک باقی می‌مانند اما گفتگوهای آن حذف خواهند شد.')) {
      return;
    }
    try {
      const res = await authFetch(`/api/projects/${projectId}`, { method: 'DELETE' });
      if (res.ok) {
        await fetchProjects();
        renderSettingsProjectsList();
        updateDrawerChatList();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.error || 'خطا در حذف پروژه');
      }
    } catch (e) {
      alert('خطا: ' + e.message);
    }
  }

  async function openChatFromSettings(projectId, chatId) {
    closeSettingsModal();
    if (projectId !== activeProjectId) {
      await authFetch(`/api/projects/${projectId}/switch`, { method: 'POST' });
      activeProjectId = projectId;
      expandedProjectFolders.add(projectId);
    }
    await switchChat(chatId);
  }

  async function switchChat(chatId) {
    if (activeChatId === chatId && chats[chatId] && chats[chatId].messages && chats[chatId].messages.length > 0) {
      closeDrawer();
      return;
    }
    activeChatId = chatId;
    saveToLocalStorage();

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'switch_chat', chat_id: chatId }));
    }

    try {
      const res = await authFetch(`/api/chats/${chatId}`);
      if (res.ok) {
        const fullChat = await res.json();
        chats[chatId] = fullChat;
        if (fullChat.model) {
          currentModel = fullChat.model;
          const found = availableModels.find(m => m.id === currentModel);
          const dockModelName = document.getElementById('dockModelName');
          if (dockModelName && found) dockModelName.textContent = found.name;
          if (headerModelText) headerModelText.textContent = currentModel;
        }
      }
    } catch (e) {
      console.warn('Could not fetch full chat:', e);
    }

    renderMessages();
    updateDrawerChatList();
    closeDrawer();
  }

  async function createNewChat() {
    return createNewChatInProject(null, activeProjectId);
  }

  async function createNewChatInProject(e, projectId) {
    if (e) e.stopPropagation();
    closeDrawer();
    triggerHaptic(15);
    const pid = projectId || activeProjectId || 'proj_default';

    if (pid !== activeProjectId) {
      try {
        await authFetch(`/api/projects/${pid}/switch`, { method: 'POST' });
        activeProjectId = pid;
      } catch (err) {
        console.warn('Project switch error:', err);
      }
    }

    const newId = `chat_${Date.now()}`;
    const newChatObj = {
      id: newId,
      title: 'گفتگوی جدید',
      created_at: Date.now() / 1000,
      updated_at: Date.now() / 1000,
      model: currentModel,
      effort: currentEffort,
      mode: currentMode,
      cwd: workspaceDir,
      project_id: pid,
      messages: []
    };
    chats[newId] = newChatObj;
    activeChatId = newId;
    saveToLocalStorage();
    renderMessages();
    updateDrawerChatList();
    if (inputMessage) inputMessage.focus();

    try {
      const res = await authFetch('/api/chats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: newId, title: 'گفتگوی جدید', model: currentModel, project_id: pid })
      });
      if (res.ok) {
        const serverChat = await res.json();
        if (serverChat && serverChat.id) {
          chats[serverChat.id] = { ...newChatObj, ...serverChat };
          activeChatId = serverChat.id;
          saveToLocalStorage();
          updateDrawerChatList();
        }
      }
    } catch (e) {
      console.warn('Backend chat sync notice:', e);
    }
  }

  async function deleteChat(chatId) {
    if (Object.keys(chats).length <= 1) {
      chats[chatId].messages = [];
      saveToLocalStorage();
      renderMessages();
      updateDrawerChatList();
      return;
    }

    try {
      const res = await authFetch(`/api/chats/${chatId}`, { method: 'DELETE' });
      const data = await res.json();
      delete chats[chatId];
      if (data.active_chat) {
        chats[data.active_chat.id] = data.active_chat;
        activeChatId = data.active_chat.id;
      } else {
        activeChatId = Object.keys(chats)[0];
      }
      saveToLocalStorage();
      renderMessages();
      updateDrawerChatList();
    } catch (e) {
      console.error('Failed to delete chat:', e);
    }
  }

  async function fetchServerChats() {
    try {
      await fetchProjects();
      const res = await authFetch('/api/chats');
      const data = await res.json();
      if (data && data.chats) {
        data.chats.forEach(summary => {
          if (!chats[summary.id]) {
            chats[summary.id] = {
              id: summary.id,
              title: summary.title,
              created_at: summary.created_at,
              updated_at: summary.updated_at,
              model: summary.model,
              messages: []
            };
          } else {
            chats[summary.id].title = summary.title;
            chats[summary.id].updated_at = summary.updated_at;
            chats[summary.id].model = summary.model;
          }
        });

        if (data.active_chat_id && !activeChatId) {
          activeChatId = data.active_chat_id;
        }

        if (activeChatId) {
          const chatRes = await authFetch(`/api/chats/${activeChatId}`);
          if (chatRes.ok) {
            const fullChat = await chatRes.json();
            chats[activeChatId] = fullChat;
            if (fullChat.model) currentModel = fullChat.model;
          }
        }

        if (headerModelText) headerModelText.textContent = currentModel;
        saveToLocalStorage();
        renderMessages();
        updateDrawerChatList();
      }
    } catch (e) {
      console.warn('Could not fetch chats:', e);
    }
  }

  async function fetchModels() {
    try {
      const res = await authFetch('/api/models');
      const data = await res.json();
      if (data && data.models) {
        availableModels = data.models;
        renderModelDropdownList();
        const found = availableModels.find(m => m.id === currentModel);
        if (found) {
          const dockModelName = document.getElementById('dockModelName');
          if (dockModelName) dockModelName.textContent = found.name;
        }
        if (modelSelect) {
          modelSelect.innerHTML = '';
          availableModels.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.name;
            if (m.id === currentModel) opt.selected = true;
            modelSelect.appendChild(opt);
          });
        }
      }
    } catch (e) {
      console.warn('Could not fetch models:', e);
    }
  }

  async function fetchInitialSettings() {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data = await res.json();
        if (data && data.global) {
          if (data.global.permission_preset) {
            const dockPolicyName = document.getElementById('dockPolicyName');
            if (dockPolicyName) dockPolicyName.textContent = data.global.permission_preset;
          }
          if (data.global.default_model) {
            currentModel = data.global.default_model;
            const found = availableModels.find(m => m.id === currentModel);
            const dockModelName = document.getElementById('dockModelName');
            if (dockModelName && found) dockModelName.textContent = found.name;
          }
        }
      }
    } catch (e) {
      console.warn('Could not fetch initial settings:', e);
    }
  }

  async function fetchWorkspace() {
    try {
      const res = await authFetch('/api/workspace');
      const data = await res.json();
      if (data && data.current) {
        workspaceDir = data.current;
        if (workspacePathText) workspacePathText.textContent = workspaceDir;
      }
    } catch (e) {
      console.warn('Could not fetch workspace:', e);
    }
  }

  // =========================================================================
  // WebSocket Connection & Real-Time Handler
  // =========================================================================
  function connectWebSocket() {
    if (!isAuthenticated) return;
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws?token=${encodeURIComponent(authToken || '')}`;

    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      try { ws.close(); } catch (e) {}
    }

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isWsConnected = true;
      updateNetworkStatus();
    };

    ws.onclose = (e) => {
      isWsConnected = false;
      updateNetworkStatus();
      if (e && e.code === 4401) {
        isAuthenticated = false;
        showLoginModal('احراز هویت نامعتبر است. لطفاً وارد شوید.');
        return;
      }
      // Auto-reconnect every 2 seconds if authenticated
      if (isAuthenticated) {
        setTimeout(connectWebSocket, 2000);
      }
    };

    ws.onerror = (err) => {
      console.error('WS Error:', err);
      isWsConnected = false;
      updateNetworkStatus();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data) return;
        handleWsMessage(data);
      } catch (err) {
        console.error('WS Message handle error:', err);
      }
    };
  }

  function resetSendBtnState() {
    if (!btnSend) return;
    btnSend.classList.remove('stop-mode');
    btnSend.title = 'ارسال پیام';
    if (inputMessage && inputMessage.value.trim().length > 0) {
      btnSend.classList.remove('btn-disabled');
    } else {
      btnSend.classList.add('btn-disabled');
    }
  }

  function handleWsMessage(data) {
    const type = data.type;

    if (type === 'account_updated') {
      refreshAccountStatus();
      if (typeof fetchAccountQuota === 'function') {
        fetchAccountQuota();
      }
      return;
    }

    if (type === 'auth_error') {
      isAuthenticated = false;
      showLoginModal(data.message || 'احراز هویت نامعتبر است. لطفاً وارد شوید.');
      return;
    }

    if (type === 'project_switched') {
      if (data.project) {
        fetchProjects();
        fetchServerChats();
      }
      return;
    }

    if (type === 'connected') {
      if (data.chat) {
        chats[data.chat.id] = data.chat;
        activeChatId = data.chat.id;
        if (data.chat.model) currentModel = data.chat.model;
        if (data.chat.effort) currentEffort = data.chat.effort;
        if (data.chat.mode) currentMode = data.chat.mode;
        if (headerModelText) headerModelText.textContent = currentModel;
        if (pillModelText) pillModelText.textContent = currentModel;
        updateEffortPill(currentEffort);
        updateModePill(currentMode);
        renderMessages();
        updateDrawerChatList();
      }
      if (data.models) {
        availableModels = data.models;
        renderModelDropdownList();
        const found = availableModels.find(m => m.id === currentModel);
        if (found) {
          const dockModelName = document.getElementById('dockModelName');
          if (dockModelName) dockModelName.textContent = found.name;
        }
      }
      if (data.effort) {
        currentEffort = data.effort;
        updateEffortPill(currentEffort);
      }
      if (data.mode) {
        currentMode = data.mode;
        updateModePill(currentMode);
      }
      if (data.processes_count !== undefined) {
        updateProcessBadge(data.processes_count);
      }
      if (data.internet_ok !== undefined) {
        isInternetOnline = data.internet_ok;
        updateNetworkStatus();
      }
    } else if (type === 'pong') {
      if (pingStartTime > 0) {
        const latency = Math.round(performance.now() - pingStartTime);
        if (pingValText) pingValText.textContent = `${latency}ms`;
        if (pingDot) {
          pingDot.className = `ping-dot ${latency > 250 ? 'slow' : ''}`;
        }
      }
    } else if (type === 'status') {
      const text = data.status;
      if (text) {
        if (!liveThinkingEl) {
          if (thinkingRow) thinkingRow.classList.add('active');
          if (thinkingText) thinkingText.textContent = text;
        }
        scrollToBottom();
      } else {
        if (thinkingRow) thinkingRow.classList.remove('active');
      }
    } else if (type === 'thinking_update') {
      lastTurnThinkingText = data.thinking || '';
      if (currentLiveFeedEl) {
        const thinkingBodies = currentLiveFeedEl.querySelectorAll('.agy-feed-item.thinking .agy-feed-body');
        thinkingBodies.forEach(b => {
          if (!b.textContent || b.textContent.length < lastTurnThinkingText.length) {
            b.textContent = lastTurnThinkingText;
          }
        });
      }
    } else if (type === 'thinking_step') {
      handleThinkingStep(data);
    } else if (type === 'effort_updated') {
      currentEffort = data.effort;
      updateEffortPill(currentEffort);
      if (chats[data.chat_id]) {
        chats[data.chat_id].effort = currentEffort;
        saveToLocalStorage();
      }
    } else if (type === 'mode_updated') {
      currentMode = data.mode;
      updateModePill(currentMode);
      if (chats[data.chat_id]) {
        chats[data.chat_id].mode = currentMode;
        saveToLocalStorage();
      }
    } else if (type === 'turn_stopped') {
      if (currentFeedStatusEl) {
        currentFeedStatusEl.remove();
        currentFeedStatusEl = null;
      }
      resetSendBtnState();
      if (activeStreamingBubble) {
        activeStreamingBubble.innerHTML += '<br><em style="color:#ef4444;font-size:11px;">[عملیات متوقف گردید]</em>';
      }
      activeStreamingBubble = null;
      currentLiveFeedEl = null;
      currentStreamText = '';
    } else if (type === 'cli_output') {
      if (activeLiveCliEl && data.line) {
        const lineEl = document.createElement('div');
        const text = data.line;
        if (text.startsWith('$') || text.startsWith('>')) {
          lineEl.className = 'cli-cmd';
        } else if (data.is_err) {
          lineEl.className = 'cli-err';
        } else {
          lineEl.className = 'cli-out';
        }
        lineEl.textContent = text;
        activeLiveCliEl.appendChild(lineEl);
        activeLiveCliEl.scrollTop = activeLiveCliEl.scrollHeight;
        scrollToBottom();
      }
    } else if (type === 'step_start') {
      handleStepStart(data);
    } else if (type === 'command_output') {
      handleCommandOutput(data);
    } else if (type === 'step_done') {
      handleStepDone(data);
    } else if (type === 'command_stopped') {
      handleStepDone({ step_index: data.step_index, duration: 0, output: 'دستور متوقف گردید.' });
    } else if (type === 'permission_request') {
      handlePermissionRequest(data);
    } else if (type === 'delta') {
      if (currentFeedStatusEl) {
        currentFeedStatusEl.remove();
        currentFeedStatusEl = null;
      }
      if (!activeStreamingBubble) {
        currentStreamText = '';
        activeStreamingBubble = appendMessageBubble('assistant', '', null, true);
      }
      if (activeStreamingBubble) {
        activeStreamingBubble.style.display = '';
      }

      currentStreamText += data.delta;
      if (typeof marked !== 'undefined') {
        activeStreamingBubble.innerHTML = marked.parse(currentStreamText);
      } else {
        activeStreamingBubble.textContent = currentStreamText;
      }
      scrollToBottom();
    } else if (type === 'done') {
      if (currentFeedStatusEl) {
        currentFeedStatusEl.remove();
        currentFeedStatusEl = null;
      }
      resetSendBtnState();
      playCompletionSound();
      if (activeStreamingBubble) {
        activeStreamingBubble.style.display = '';
      }
      resetSendBtnState();

      const fullText = data.full_text || currentStreamText;
      const targetChatId = data.chat_id || activeChatId;

      if (!chats[targetChatId]) {
        chats[targetChatId] = { id: targetChatId, messages: [] };
      }

      const msgObj = {
        role: 'assistant',
        content: fullText,
        timestamp: Date.now() / 1000,
        meta: data.meta || {}
      };
      chats[targetChatId].messages.push(msgObj);
      chats[targetChatId].updated_at = Date.now() / 1000;

      saveToLocalStorage();

      if (activeStreamingBubble) {
        if (typeof marked !== 'undefined') {
          activeStreamingBubble.innerHTML = marked.parse(fullText);
        } else {
          activeStreamingBubble.textContent = fullText;
        }
      } else {
        renderMessages();
      }

      activeStreamingBubble = null;
      activeLiveCliEl = null;
      currentStreamText = '';
      currentAccordionEl = null;
      liveThinkingEl = null;
      currentMiniTerminals = {};
      activeTurnStepIndices.clear();

      updateDrawerChatList();
      scrollToBottom(true);
    } else if (type === 'error') {
      if (thinkingRow) thinkingRow.classList.remove('active');
      resetSendBtnState();
      appendMessageBubble('assistant', `⚠️ **خطا:**\n${data.error}`, Date.now() / 1000, true, true);
      activeStreamingBubble = null;
      activeLiveCliEl = null;
      currentStreamText = '';
      currentAccordionEl = null;
      liveThinkingEl = null;
    } else if (type === 'chat_cleared') {
      if (chats[data.chat_id]) {
        chats[data.chat_id].messages = [];
        saveToLocalStorage();
        renderMessages();
        updateDrawerChatList();
      }
    } else if (type === 'model_updated') {
      currentModel = data.model;
      if (headerModelText) headerModelText.textContent = currentModel;
      if (pillModelText) pillModelText.textContent = currentModel;
      if (modelSelect) modelSelect.value = currentModel;
      if (chats[data.chat_id]) {
        chats[data.chat_id].model = currentModel;
        saveToLocalStorage();
      }
    } else if (type === 'process_log_line') {
      if (currentInspectingPid === data.pid && inspectTerminalOutput) {
        inspectTerminalOutput.textContent += `\n${data.line}`;
        if (inspectTerminalScreen) inspectTerminalScreen.scrollTop = inspectTerminalScreen.scrollHeight;
      }
    }
  }

  // Send User Message
  function sendMessage() {
    if (!inputMessage) return;

    // Check if turn is currently running -> Stop turn
    if (btnSend && btnSend.classList.contains('stop-mode')) {
      triggerHaptic(20);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'stop_turn', chat_id: activeChatId }));
      }
      return;
    }

    const text = inputMessage.value.trim();
    if (!text) {
      triggerHaptic(10);
      inputMessage.focus();
      return;
    }

    triggerHaptic(15);
    closeSlashPopover();
    closeMentionsPopover();

    if (!activeChatId || !chats[activeChatId]) {
      const newId = `chat_${Date.now()}`;
      chats[newId] = {
        id: newId,
        title: text.slice(0, 35),
        created_at: Date.now() / 1000,
        updated_at: Date.now() / 1000,
        model: currentModel,
        effort: currentEffort,
        mode: currentMode,
        messages: []
      };
      activeChatId = newId;
    }

    const userMsg = {
      role: 'user',
      content: text,
      timestamp: Date.now() / 1000
    };
    chats[activeChatId].messages.push(userMsg);
    chats[activeChatId].updated_at = Date.now() / 1000;

    if (chats[activeChatId].title === 'گفتگوی جدید' || !chats[activeChatId].title) {
      chats[activeChatId].title = text.slice(0, 36);
    }

    saveToLocalStorage();
    appendMessageBubble('user', text, userMsg.timestamp, true);
    updateDrawerChatList();

    // Clear input & reset height
    inputMessage.value = '';
    inputMessage.style.height = 'auto';
    btnSend.classList.remove('btn-disabled');
    btnSend.classList.add('stop-mode');
    btnSend.title = 'توقف پردازش (Stop)';

    // Start Live Turn UI Container (Antigravity 2.0 Minimalist Live Feed)
    const row = document.createElement('div');
    row.className = 'msg-row assistant minimal-turn';

    const feed = document.createElement('div');
    feed.className = 'agy-live-feed';

    const statusEl = document.createElement('div');
    statusEl.className = 'agy-feed-status';
    statusEl.innerHTML = '<span class="agy-feed-status-text">Working</span>';
    feed.appendChild(statusEl);

    row.appendChild(feed);

    // Live Assistant Bubble (Pure typography, no borders, rendered directly on pitch-black canvas)
    const bubble = document.createElement('div');
    bubble.className = 'bubble ai-bubble';
    bubble.setAttribute('dir', 'auto');
    bubble.style.display = 'none';
    row.appendChild(bubble);

    chatInner.appendChild(row);
    currentLiveFeedEl = feed;
    currentFeedStatusEl = statusEl;
    activeStreamingBubble = bubble;
    currentStreamText = '';
    lastTurnThinkingText = '';
    liveThinkingStartTime = Date.now();
    scrollToBottom(true);

    // Send to WebSocket
    const msgPayload = JSON.stringify({
      type: 'user_message',
      content: text,
      chat_id: activeChatId,
      model: currentModel,
      effort: currentEffort,
      mode: currentMode
    });

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(msgPayload);
    } else if (ws && ws.readyState === WebSocket.CONNECTING) {
      const waitInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          clearInterval(waitInterval);
          ws.send(msgPayload);
        } else if (!ws || ws.readyState !== WebSocket.CONNECTING) {
          clearInterval(waitInterval);
          appendMessageBubble('assistant', '⚠️ خطا در برقراری ارتباط با سرور. لطفاً دوباره تلاش کنید.', Date.now() / 1000, true, true);
          resetSendBtnState();
        }
      }, 100);
    } else {
      connectWebSocket();
      setTimeout(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(msgPayload);
        } else {
          appendMessageBubble('assistant', '⚠️ در حال برقراری مجدد ارتباط با سرور... لطفاً دوباره تلاش کنید.', Date.now() / 1000, true, true);
          resetSendBtnState();
        }
      }, 500);
    }
  }

  // =========================================================================
  // Antigravity Quick Control Pills & Options
  // =========================================================================
  const EFFORT_LEVELS = ['low', 'medium', 'high', 'max'];
  const EFFORT_LABELS = {
    'low': 'تلاش: کم',
    'medium': 'تلاش: متوسط',
    'high': 'تلاش: زیاد',
    'max': 'تلاش: حداکثر'
  };

  function cycleEffort() {
    triggerHaptic(15);
    const currIdx = EFFORT_LEVELS.indexOf(currentEffort);
    const nextIdx = (currIdx + 1) % EFFORT_LEVELS.length;
    currentEffort = EFFORT_LEVELS[nextIdx];
    updateEffortPill(currentEffort);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_effort', chat_id: activeChatId, effort: currentEffort }));
    }
  }

  function updateEffortPill(effort) {
    if (pillEffortText) pillEffortText.textContent = EFFORT_LABELS[effort] || `تلاش: ${effort}`;
  }

  const MODE_LEVELS = ['auto', 'plan', 'request-review'];
  const MODE_LABELS = {
    'auto': 'خودکار',
    'plan': 'طرح‌ریزی',
    'request-review': 'نیاز به تایید'
  };

  function cycleMode() {
    triggerHaptic(15);
    const currIdx = MODE_LEVELS.indexOf(currentMode);
    const nextIdx = (currIdx + 1) % MODE_LEVELS.length;
    currentMode = MODE_LEVELS[nextIdx];
    updateModePill(currentMode);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_mode', chat_id: activeChatId, mode: currentMode }));
    }
  }

  function updateModePill(mode) {
    if (pillModeText) pillModeText.textContent = MODE_LABELS[mode] || mode;
  }

  // Ping Watchdog
  let pingStartTime = 0;
  function startPingWatchdog() {
    setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        pingStartTime = performance.now();
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 6000);
  }

  // =========================================================================
  // Antigravity 2.0 Dock Dropdowns (Model Picker & Policy Preset)
  // =========================================================================
  function renderModelDropdownList() {
    const list = document.getElementById('dockModelDropdownList');
    if (!list) return;
    list.innerHTML = availableModels.map(m => {
      const isSel = (m.id === currentModel);
      return `
        <div class="agy-dropdown-item ${isSel ? 'selected' : ''}" onclick="window.selectModel('${escapeHtml(m.id)}')">
          <div class="agy-dropdown-item-info">
            <span class="agy-dropdown-item-title">${escapeHtml(m.name)}</span>
            <span class="agy-dropdown-item-desc">${escapeHtml(m.id)}</span>
          </div>
          <span class="agy-dropdown-check">✓</span>
        </div>
      `;
    }).join('');
  }

  function toggleModelDropdown(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    triggerHaptic(10);
    const menu = document.getElementById('dockModelDropdown');
    const policyMenu = document.getElementById('dockPolicyDropdown');
    if (policyMenu) policyMenu.classList.remove('active');

    if (menu) {
      const willOpen = !menu.classList.contains('active');
      if (willOpen) {
        renderModelDropdownList();
        menu.classList.add('active');
      } else {
        menu.classList.remove('active');
      }
    }
  }

  function togglePolicyDropdown(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    triggerHaptic(10);
    const menu = document.getElementById('dockPolicyDropdown');
    const modelMenu = document.getElementById('dockModelDropdown');
    if (modelMenu) modelMenu.classList.remove('active');

    if (menu) {
      const willOpen = !menu.classList.contains('active');
      if (willOpen) {
        const dockPolicyName = document.getElementById('dockPolicyName');
        const cur = dockPolicyName ? dockPolicyName.textContent.trim() : 'Auto';
        const items = menu.querySelectorAll('.agy-dropdown-item');
        items.forEach(el => {
          if (el.getAttribute('data-preset') === cur) {
            el.classList.add('selected');
          } else {
            el.classList.remove('selected');
          }
        });
        menu.classList.add('active');
      } else {
        menu.classList.remove('active');
      }
    }
  }

  function selectPolicyPreset(preset) {
    triggerHaptic(15);
    const dockPolicyName = document.getElementById('dockPolicyName');
    if (dockPolicyName) dockPolicyName.textContent = preset;

    const items = document.querySelectorAll('#dockPolicyDropdownList .agy-dropdown-item');
    items.forEach(el => {
      if (el.getAttribute('data-preset') === preset) {
        el.classList.add('selected');
      } else {
        el.classList.remove('selected');
      }
    });

    closeAllDockDropdowns();

    // Sync settings UI selector if present
    const sel = document.getElementById('settingPermissionPreset');
    if (sel) sel.value = preset;

    autoSaveSetting('permission_preset', preset);
  }

  function closeAllDockDropdowns() {
    const modelMenu = document.getElementById('dockModelDropdown');
    const policyMenu = document.getElementById('dockPolicyDropdown');
    if (modelMenu) modelMenu.classList.remove('active');
    if (policyMenu) policyMenu.classList.remove('active');
  }

  function selectModel(modelId) {
    triggerHaptic(15);
    currentModel = modelId;
    const found = availableModels.find(m => m.id === modelId);
    const displayName = found ? found.name : modelId;

    const dockModelName = document.getElementById('dockModelName');
    if (dockModelName) dockModelName.textContent = displayName;
    if (pillModelText) pillModelText.textContent = displayName;
    if (headerModelText) headerModelText.textContent = displayName;
    if (modelSelect) modelSelect.value = modelId;

    renderModelDropdownList();
    closeAllDockDropdowns();

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_model', chat_id: activeChatId, model: modelId }));
    }
    if (chats[activeChatId]) {
      chats[activeChatId].model = modelId;
      saveToLocalStorage();
    }
    autoSaveSetting('default_model', modelId);
  }

  // Backwards compatibility
  function openModelSheet() {
    toggleModelDropdown();
  }

  function closeModelSheet() {
    closeAllDockDropdowns();
  }

  // =========================================================================
  // Slash Commands & @ Mentions Autocomplete
  // =========================================================================
  const SLASH_COMMANDS = [
    { cmd: '/goal', desc: 'اجرای تسک‌های عمیق و خودکار تا حصول نتیجه نهایی' },
    { cmd: '/plan', desc: 'برنامه‌ریزی گام‌به‌گام و دقیق پیش از شروع کار' },
    { cmd: '/boost', desc: 'تفکر عمیق و بررسی با چندین چشم‌انداز' },
    { cmd: '/compact', desc: 'فشرده‌سازی سابقه و بازنشانی کانتکست' },
    { cmd: '/schedule', desc: 'زمان‌بندی اجرای دستورات و کارهای دوره‌ای' },
    { cmd: '/browser', desc: 'وب‌گردی و اتوماسیون تعامل با صفحات وب' },
    { cmd: '/model', desc: 'مشاهده یا تغییر مدل هوش مصنوعی' },
    { cmd: '/effort', desc: 'تنظیم تلاش استدلال (low, medium, high, max)' },
    { cmd: '/mode', desc: 'تنظیم حالت اجرایی (auto, plan, request-review)' },
    { cmd: '/clear', desc: 'پاکسازی پیام‌های گفتگوی فعلی' },
    { cmd: '/restart', desc: 'راه‌اندازی مجدد موتور پردازش و بستن پروسه‌ها' },
    { cmd: '/help', desc: 'نمایش راهنمای کامل دستورات' }
  ];

  function handleInputPopovers() {
    if (!inputMessage) return;
    const val = inputMessage.value;
    
    // 1. Slash Commands
    if (val.startsWith('/')) {
      const q = val.toLowerCase().trim();
      const matched = SLASH_COMMANDS.filter(c => c.cmd.startsWith(q));
      renderSlashPopover(matched);
      closeMentionsPopover();
      return;
    } else {
      closeSlashPopover();
    }

    // 2. @ Mentions
    const atIdx = val.lastIndexOf('@');
    if (atIdx !== -1 && (atIdx === 0 || /\s/.test(val[atIdx - 1]))) {
      const q = val.slice(atIdx + 1).toLowerCase();
      renderMentionsPopover(q);
      return;
    } else {
      closeMentionsPopover();
    }
  }

  function renderSlashPopover(list) {
    if (!slashPopover) return;
    if (list.length === 0) {
      closeSlashPopover();
      return;
    }
    slashPopover.innerHTML = '';
    slashSelectedIdx = 0;

    list.forEach((item, index) => {
      const div = document.createElement('div');
      div.className = `slash-item ${index === 0 ? 'selected' : ''}`;
      div.innerHTML = `
        <span class="slash-cmd-name">${item.cmd}</span>
        <span class="slash-cmd-desc">${item.desc}</span>
      `;
      div.onclick = () => {
        triggerHaptic(15);
        inputMessage.value = item.cmd + ' ';
        closeSlashPopover();
        inputMessage.focus();
        inputMessage.dispatchEvent(new Event('input'));
      };
      slashPopover.appendChild(div);
    });

    slashPopover.classList.add('active');
  }

  function closeSlashPopover() {
    if (slashPopover) slashPopover.classList.remove('active');
  }

  async function fetchMentions() {
    try {
      const res = await authFetch('/api/mentions');
      const data = await res.json();
      if (data && data.items) {
        cachedMentions = data.items;
      }
    } catch (e) {}
  }

  function renderMentionsPopover(query) {
    if (!mentionsPopover) return;
    const filtered = cachedMentions.filter(item => 
      item.name.toLowerCase().includes(query) || item.path.toLowerCase().includes(query)
    ).slice(0, 8);

    if (filtered.length === 0) {
      closeMentionsPopover();
      return;
    }

    mentionsPopover.innerHTML = '';
    mentionSelectedIdx = 0;

    filtered.forEach((item, index) => {
      const div = document.createElement('div');
      div.className = `mention-item ${index === 0 ? 'selected' : ''}`;
      div.innerHTML = `
        <span class="mention-name">📄 ${escapeHtml(item.name)}</span>
        <span class="mention-path">${escapeHtml(item.path)}</span>
      `;
      div.onclick = () => {
        triggerHaptic(15);
        const atIdx = inputMessage.value.lastIndexOf('@');
        inputMessage.value = inputMessage.value.slice(0, atIdx) + item.path + ' ';
        closeMentionsPopover();
        inputMessage.focus();
        inputMessage.dispatchEvent(new Event('input'));
      };
      mentionsPopover.appendChild(div);
    });

    mentionsPopover.classList.add('active');
  }

  function closeMentionsPopover() {
    if (mentionsPopover) mentionsPopover.classList.remove('active');
  }

  function updatePopoverSelection(items, selectedIdx) {
    items.forEach((it, idx) => {
      it.classList.toggle('selected', idx === selectedIdx);
      if (idx === selectedIdx) it.scrollIntoView({ block: 'nearest' });
    });
  }

  // =========================================================================
  // Voice Input (Speech-to-Text via Web Speech API)
  // =========================================================================
  function initVoiceInput() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      if (btnMic) btnMic.style.display = 'none';
      return;
    }
    const recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'fa-IR';

    let isRecording = false;

    recognition.onresult = (e) => {
      const text = e.results[0][0].transcript;
      if (inputMessage) {
        inputMessage.value = (inputMessage.value + ' ' + text).trim();
        inputMessage.dispatchEvent(new Event('input'));
        inputMessage.focus();
      }
    };

    recognition.onend = () => {
      isRecording = false;
      if (btnMic) btnMic.classList.remove('recording');
    };

    recognition.onerror = () => {
      isRecording = false;
      if (btnMic) btnMic.classList.remove('recording');
    };

    if (btnMic) {
      btnMic.addEventListener('click', () => {
        triggerHaptic(20);
        if (isRecording) {
          recognition.stop();
        } else {
          try {
            recognition.start();
            isRecording = true;
            btnMic.classList.add('recording');
          } catch (err) {
            isRecording = false;
            btnMic.classList.remove('recording');
          }
        }
      });
    }
  }

  // Drawer Controls
  function openDrawer() {
    triggerHaptic(10);
    updateDrawerChatList();
    if (drawerBackdrop) {
      drawerBackdrop.classList.add('open');
      drawerBackdrop.style.display = 'block';
    }
  }

  function closeDrawer() {
    triggerHaptic(10);
    if (drawerBackdrop) {
      drawerBackdrop.classList.remove('open');
      setTimeout(() => {
        if (!drawerBackdrop.classList.contains('open')) {
          drawerBackdrop.style.display = 'none';
        }
      }, 250);
    }
  }

  // =========================================================================
  // Antigravity 2.0 Official Settings & Architecture Controller (Images 3, 4, 5)
  // =========================================================================
  const settingsModal = document.getElementById('settingsModal');

  async function openSettingsModal(tabName = null) {
    closeDrawer();
    if (settingsModal) settingsModal.classList.add('open', 'active');
    
    const targetTab = tabName || 'account';
    switchSettingsTab(targetTab);

    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data = await res.json();
        applySettingsToForm(data);
      }
    } catch (e) {
      console.warn('[Settings] Failed to fetch server settings:', e);
    }
    refreshAccountStatus();
    checkSystemUpdateStatus();
  }

  function closeSettingsModal() {
    if (settingsModal) settingsModal.classList.remove('open', 'active');
  }

  function switchSettingsTab(tabName) {
    triggerHaptic(10);
    document.querySelectorAll('.agy-settings-nav-item').forEach(btn => {
      const isActive = btn.getAttribute('data-tab') === tabName;
      btn.classList.toggle('active', isActive);
      if (isActive && window.innerWidth <= 768) {
        btn.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
      }
    });
    document.querySelectorAll('.agy-settings-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === `pane-${tabName}`);
    });
    if (tabName === 'projects') {
      renderSettingsProjectsList();
    } else if (tabName === 'account') {
      refreshAccountStatus();
      checkCliLoginSession();
    } else if (tabName === 'general') {
      checkSystemUpdateStatus();
    }
  }

  async function refreshAccountStatus(forceToast = false) {
    try {
      const res = await fetch('/api/antigravity/account');
      if (res.ok) {
        const data = await res.json();
        const user = data.user || {};
        const isLoggedIn = Boolean(data.logged_in && user.authenticated);

        // Update Account Hero Card
        const heroAvatar = document.getElementById('accountHeroAvatar');
        const heroName = document.getElementById('accountHeroName');
        const heroEmail = document.getElementById('accountHeroEmail');
        const heroStatusDot = document.getElementById('accountHeroStatusDot');
        const heroStatusText = document.getElementById('accountHeroStatusText');
        const loggedInSection = document.getElementById('accountLoggedInSection');
        const heroQuickLogout = document.getElementById('btnHeroQuickLogout');

        if (heroAvatar) heroAvatar.textContent = user.avatar || (isLoggedIn ? '👤' : '👤');
        if (heroName) heroName.textContent = user.name || (isLoggedIn ? 'کاربر متصل' : 'کاربر مهمان');
        if (heroEmail) heroEmail.textContent = user.email || (isLoggedIn ? 'حساب فعال' : 'وارد نشده (حساب متصل نیست)');
        
        if (heroStatusDot) {
          heroStatusDot.className = `status-indicator-dot ${isLoggedIn ? 'online' : 'offline'}`;
        }
        if (heroStatusText) {
          heroStatusText.textContent = isLoggedIn ? `متصل (${data.auth_method || 'آنلاین'})` : 'حالت مهمان / آفلاین';
        }
        const heroVerifiedBadge = document.getElementById('accountHeroVerifiedBadge');
        if (heroVerifiedBadge) {
          heroVerifiedBadge.style.display = isLoggedIn ? 'inline-flex' : 'none';
        }
        if (loggedInSection) {
          loggedInSection.style.display = isLoggedIn ? 'block' : 'none';
        }
        if (heroQuickLogout) {
          heroQuickLogout.style.display = isLoggedIn ? 'inline-flex' : 'none';
        }
        const btnGoogleLoginText = document.getElementById('btnGoogleLoginText');
        if (btnGoogleLoginText) {
          btnGoogleLoginText.textContent = isLoggedIn ? 'تعویض یا اتصال مجدد با اکانت گوگل' : 'ورود با حساب کاربری گوگل';
        }

        // Sync Sidebar & Settings Footer
        const sidebarName = document.getElementById('sidebarUserName');
        const sidebarEmail = document.getElementById('sidebarUserEmail');
        const sidebarAvatar = document.getElementById('userAvatarText');
        const btnSidebarLogout = document.getElementById('btnSidebarLogout');
        if (sidebarName) sidebarName.textContent = user.name || (isLoggedIn ? 'کاربر متصل' : 'کاربر مهمان');
        if (sidebarEmail) sidebarEmail.textContent = user.email || (isLoggedIn ? 'متصل' : 'حساب متصل نیست');
        if (sidebarAvatar) sidebarAvatar.textContent = user.avatar || '👤';
        if (btnSidebarLogout) {
          btnSidebarLogout.style.display = isLoggedIn ? 'inline-flex' : 'none';
        }

        const sName = document.getElementById('settingsUserName');
        const sEmail = document.getElementById('settingsUserEmail');
        const sAvatar = document.getElementById('settingsUserAvatar');
        if (sName) sName.textContent = user.name || (isLoggedIn ? 'کاربر متصل' : 'کاربر مهمان');
        if (sEmail) sEmail.textContent = user.email ? (user.email.length > 20 ? user.email.substring(0, 18) + '...' : user.email) : 'حساب متصل نیست';
        if (sAvatar) sAvatar.textContent = user.avatar || '👤';

        // Sync Quota Modal Elements
        const qEmail = document.getElementById('quotaModalEmail');
        const qStatus = document.getElementById('quotaModalAuthMethod');
        const btnQuotaLogout = document.getElementById('btnQuotaLogout');
        if (qEmail) qEmail.textContent = user.email || 'حساب متصل نیست';
        if (qStatus) {
          qStatus.textContent = isLoggedIn ? `متصل به Antigravity (${data.auth_method || 'آنلاین'})` : 'وضعیت: حساب متصل نیست (مهمان)';
        }
        if (btnQuotaLogout) {
          btnQuotaLogout.style.display = isLoggedIn ? 'inline-flex' : 'none';
        }

        // Render Quotas with Antigravity Design
        const quotasContainer = document.getElementById('accountSettingsQuotasList');
        if (quotasContainer && data.models_quota) {
          quotasContainer.innerHTML = '';
          data.models_quota.forEach(m => {
            const card = document.createElement('div');
            card.className = 'agy-setting-card';
            card.style.flexDirection = 'column';
            card.style.alignItems = 'stretch';
            card.style.gap = '8px';
            const tierColor = m.id.includes('flash') ? '#38bdf8' : (m.id.includes('claude') ? '#c084fc' : '#34d399');
            const progressBg = m.id.includes('flash') 
              ? 'linear-gradient(90deg, #38bdf8, #818cf8)' 
              : (m.id.includes('claude') ? 'linear-gradient(90deg, #818cf8, #c084fc)' : 'linear-gradient(90deg, #10b981, #34d399)');
            card.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; font-size: 13.5px; color: #f8fafc;">${m.name}</span>
                <span style="font-size: 10.5px; font-weight: 600; color: ${isLoggedIn ? tierColor : '#9ca3af'}; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); padding: 2px 8px; border-radius: 999px;">${m.tier || ''}</span>
              </div>
              <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden;">
                <div style="width: ${m.used_percentage || 0}%; height: 100%; background: ${isLoggedIn ? progressBg : '#6b7280'}; border-radius: 999px;"></div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: #94a3b8;">
                <span>سقف مجاز: ${m.rpm_limit}</span>
                <span>سهمیه: ${m.daily_quota}</span>
              </div>
            `;
            quotasContainer.appendChild(card);
          });
        }

        if (forceToast) {
          showToast(isLoggedIn ? `✓ متصل به حساب: ${user.name || user.email}` : 'وضعیت: حساب کاربری متصل نیست');
        }

        if (isLoggedIn) {
          resetCliLoginUI();
        } else {
          checkCliLoginSession();
        }
      }
    } catch (e) {
      console.warn('[Account] Failed to fetch account status:', e);
      if (forceToast) showToast('خطا در دریافت وضعیت حساب', 'error');
    }
  }

  async function saveGeminiApiKey() {
    const input = document.getElementById('inputGeminiApiKey');
    if (!input) return;
    const key = input.value.trim();
    if (!key) {
      showToast('لطفاً کلید Gemini API Key را وارد کنید.', 'warn');
      return;
    }

    try {
      showToast('در حال ثبت کلید...', 'info');
      const res = await fetch('/api/antigravity/account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'save_api_key', api_key: key })
      });
      const data = await res.json();
      if (data.ok) {
        input.value = '';
        showToast(data.message || '✓ کلید Gemini با موفقیت فعال شد.');
        await refreshAccountStatus();
      } else {
        showToast(data.error || 'خطا در ثبت کلید.', 'error');
      }
    } catch (e) {
      showToast('خطا در برقراری ارتباط با سرور.', 'error');
    }
  }

  async function saveCustomOAuthToken() {
    const input = document.getElementById('inputCustomTokenJson');
    if (!input) return;
    const token = input.value.trim();
    if (!token) {
      showToast('لطفاً محتوای توکن را وارد کنید.', 'warn');
      return;
    }

    try {
      showToast('در حال ثبت توکن...', 'info');
      const res = await fetch('/api/antigravity/account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'save_token', token_json: token })
      });
      const data = await res.json();
      if (data.ok) {
        input.value = '';
        showToast(data.message || '✓ توکن حساب با موفقیت ثبت شد.');
        await refreshAccountStatus();
      } else {
        showToast(data.error || 'خطا در ثبت توکن.', 'error');
      }
    } catch (e) {
      showToast('خطا در برقراری ارتباط با سرور.', 'error');
    }
  }

  async function logoutAccount(skipConfirm = false) {
    if (!skipConfirm) {
      if (!confirm('آیا از خروج از حساب کاربری اطمینان دارید؟ تمام توکن‌ها و نشست‌های متصل غیرفعال خواهند شد.')) {
        return;
      }
    }

    try {
      showToast('در حال خروج از حساب کاربری...', 'info');
      const res = await fetch('/api/antigravity/account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'logout' })
      });
      const data = await res.json();

      // Clear any stored client tokens
      authToken = null;
      isAuthenticated = false;
      localStorage.removeItem('anti_auth_token');
      localStorage.removeItem('anti_username');
      sessionStorage.removeItem('anti_auth_token');
      sessionStorage.removeItem('anti_username');

      // Clear all login input fields in settings
      const apiKeyInput = document.getElementById('inputGeminiApiKey');
      if (apiKeyInput) apiKeyInput.value = '';
      const oauthJsonInput = document.getElementById('inputOauthTokenJson');
      if (oauthJsonInput) oauthJsonInput.value = '';
      const authCodeInput = document.getElementById('inputCliAuthCode');
      if (authCodeInput) authCodeInput.value = '';

      // Reset CLI Login state and UI
      if (typeof resetCliLoginUI === 'function') {
        resetCliLoginUI();
      }

      showToast(data.message || '✓ با موفقیت از حساب کاربری خارج شدید.', 'success');

      // Refresh UI everywhere
      await refreshAccountStatus();
      if (typeof fetchAccountQuota === 'function') {
        await fetchAccountQuota();
      }
      if (typeof fetchModels === 'function') {
        fetchModels();
      }
    } catch (e) {
      console.error('[Logout] Error:', e);
      showToast('خطا در خروج از حساب کاربری.', 'error');
    }
  }

  function copyCliAuthCommand() {
    const cmdEl = document.getElementById('cliAuthCommandText');
    const text = cmdEl ? cmdEl.textContent : 'agy --prompt "login"';
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        showToast('✓ دستور در کلیپ‌بورد کپی شد: ' + text);
      }).catch(() => {
        fallbackCopyText(text);
      });
    } else {
      fallbackCopyText(text);
    }
  }

  function fallbackCopyText(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      showToast('✓ دستور کپی شد: ' + text);
    } catch (e) {
      showToast('خطا در کپی دستور.', 'warn');
    }
    document.body.removeChild(ta);
  }

  // =========================================================================
  // In-App Background Google CLI OAuth Bridge Flow
  // =========================================================================
  let cliAuthUrl = '';
  let cliLoginPollTimer = null;

  async function checkCliLoginSession() {
    try {
      const res = await fetch('/api/auth/cli-login/status');
      if (!res.ok) return;
      const data = await res.json();
      if (data.ok && data.state === 'waiting_code' && data.auth_url) {
        cliAuthUrl = data.auth_url;
        setupCliLoginActiveUI(data.auth_url);
      } else if (data.ok && data.state === 'running') {
        const idleBox = document.getElementById('cliLoginIdleBox');
        const loadingBox = document.getElementById('cliLoginLoadingBox');
        const activeBox = document.getElementById('cliLoginActiveBox');
        if (idleBox) idleBox.style.display = 'none';
        if (loadingBox) loadingBox.style.display = 'block';
        if (activeBox) activeBox.style.display = 'none';
        pollCliLoginStatus();
      } else if (data.ok && data.state === 'idle') {
        const activeBox = document.getElementById('cliLoginActiveBox');
        const loadingBox = document.getElementById('cliLoginLoadingBox');
        if ((activeBox && activeBox.style.display === 'block') || (loadingBox && loadingBox.style.display === 'block')) {
          resetCliLoginUI();
        }
      }
    } catch (e) {
      console.warn('[CliLogin] check error:', e);
    }
  }

  async function startCliLoginFlow() {
    const idleBox = document.getElementById('cliLoginIdleBox');
    const loadingBox = document.getElementById('cliLoginLoadingBox');
    const activeBox = document.getElementById('cliLoginActiveBox');

    if (idleBox) idleBox.style.display = 'none';
    if (loadingBox) loadingBox.style.display = 'block';
    if (activeBox) activeBox.style.display = 'none';

    try {
      showToast('در حال شروع نشست ورود گوگل در پس‌زمینه...', 'info');
      const res = await fetch('/api/auth/cli-login/start', { method: 'POST' });
      const data = await res.json();

      if (data.ok && data.auth_url) {
        cliAuthUrl = data.auth_url;
        setupCliLoginActiveUI(data.auth_url);
        showToast('لینک ورود گوگل آماده شد. لطفاً مرحله ۱ را باز کنید.', 'success');
      } else if (data.ok && data.state === 'success') {
        showToast('✓ حساب گوگل متصل شد.', 'success');
        resetCliLoginUI();
        await refreshAccountStatus();
      } else {
        pollCliLoginStatus();
      }
    } catch (e) {
      showToast('خطا در شروع نشست ورود گوگل.', 'error');
      resetCliLoginUI();
    }
  }

  function setupCliLoginActiveUI(url) {
    const idleBox = document.getElementById('cliLoginIdleBox');
    const loadingBox = document.getElementById('cliLoginLoadingBox');
    const activeBox = document.getElementById('cliLoginActiveBox');
    const linkBtn = document.getElementById('btnOpenAuthUrlLink');
    const codeInput = document.getElementById('inputCliAuthCode');

    if (idleBox) idleBox.style.display = 'none';
    if (loadingBox) loadingBox.style.display = 'none';
    if (activeBox) {
      activeBox.style.display = 'block';
      try {
        activeBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } catch (err) {}
    }
    if (linkBtn) {
      linkBtn.href = url;
      linkBtn.setAttribute('target', '_blank');
      linkBtn.setAttribute('rel', 'noopener noreferrer');
    }
    if (codeInput) {
      if (!codeInput.value) codeInput.value = '';
      setTimeout(() => {
        try { codeInput.focus(); } catch (e) {}
      }, 300);
    }
  }

  function pollCliLoginStatus() {
    let attempts = 0;
    if (cliLoginPollTimer) clearInterval(cliLoginPollTimer);
    cliLoginPollTimer = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch('/api/auth/cli-login/status');
        const data = await res.json();
        if (data.auth_url) {
          clearInterval(cliLoginPollTimer);
          cliAuthUrl = data.auth_url;
          setupCliLoginActiveUI(data.auth_url);
          showToast('لینک ورود گوگل آماده شد.', 'success');
        } else if (data.state === 'installing_engine') {
          const loadingDesc = document.querySelector('#cliLoginLoadingBox .login-card-desc');
          if (loadingDesc) {
            loadingDesc.textContent = data.message || 'در حال دانلود و نصب خودکار موتور Antigravity CLI روی ترموکس... لطفاً چند ثانیه شکیبا باشید.';
          }
        } else if (data.state === 'error' || attempts > 100) {
          clearInterval(cliLoginPollTimer);
          showToast(data.error || 'خطا در دریافت لینک لاگین.', 'error');
          resetCliLoginUI();
        }
      } catch (e) {
        if (attempts > 12) {
          clearInterval(cliLoginPollTimer);
          resetCliLoginUI();
        }
      }
    }, 1000);
  }

  function copyGoogleAuthUrl() {
    if (!cliAuthUrl) return;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(cliAuthUrl).then(() => {
        showToast('✓ لینک ورود در کلیپ‌بورد کپی شد.', 'success');
      }).catch(() => fallbackCopyText(cliAuthUrl));
    } else {
      fallbackCopyText(cliAuthUrl);
    }
  }

  async function submitCliAuthCode() {
    const input = document.getElementById('inputCliAuthCode');
    const btn = document.getElementById('btnSubmitAuthCode');
    if (!input) return;
    let code = input.value.trim();
    if (!code) {
      showToast('لطفاً کد تایید گوگل را وارد کنید.', 'warn');
      return;
    }

    // Extract code if user pasted full redirect URL
    if (code.includes('code=')) {
      try {
        const urlParams = new URL(code.startsWith('http') ? code : `https://example.com/?${code}`).searchParams;
        const extracted = urlParams.get('code');
        if (extracted) code = extracted;
      } catch (err) {
        const m = code.match(/code=([^&]+)/);
        if (m) code = decodeURIComponent(m[1]);
      }
    }

    if (btn) {
      btn.disabled = true;
      btn.textContent = 'در حال اعتبارسنجی...';
    }

    try {
      showToast('در حال اعتبارسنجی کد با سرورهای گوگل...', 'info');
      const res = await fetch('/api/auth/cli-login/submit-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code })
      });
      const data = await res.json();

      if (data.ok) {
        showToast(data.message || '✓ ورود موفقیت‌آمیز بود! حساب شما متصل شد.', 'success');
        resetCliLoginUI();
        await refreshAccountStatus(true);
      } else {
        showToast(data.error || 'کد واردشده معتبر نیست.', 'error');
      }
    } catch (e) {
      showToast('خطا در برقراری ارتباط با سرور.', 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = '✓ تایید و فعال‌سازی';
      }
    }
  }

  async function cancelCliLoginFlow() {
    if (cliLoginPollTimer) clearInterval(cliLoginPollTimer);
    try {
      await fetch('/api/auth/cli-login/cancel', { method: 'POST' });
    } catch (e) {}
    resetCliLoginUI();
    showToast('نشست ورود لغو شد.');
  }

  function resetCliLoginUI() {
    if (cliLoginPollTimer) clearInterval(cliLoginPollTimer);
    const idleBox = document.getElementById('cliLoginIdleBox');
    const loadingBox = document.getElementById('cliLoginLoadingBox');
    const activeBox = document.getElementById('cliLoginActiveBox');
    if (idleBox) idleBox.style.display = 'block';
    if (loadingBox) loadingBox.style.display = 'none';
    if (activeBox) activeBox.style.display = 'none';
  }

  let audioToneEnabled = false;

  function playCompletionSound() {
    if (!audioToneEnabled) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12);
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.22);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.22);
    } catch (e) {
      console.warn('[Audio] Feedback chime error:', e);
    }
  }

  function applySettingsToForm(data) {
    if (!data) return;
    const glob = data.global || {};

    // General Tab
    const selPreset = document.getElementById('settingPermissionPreset');
    if (selPreset && glob.permission_preset) {
      selPreset.value = glob.permission_preset;
      if (!selPreset.value) selPreset.value = 'Turbo';
    }

    const selPlan = document.getElementById('settingPlanPolicy');
    if (selPlan && glob.artifact_review) {
      selPlan.value = glob.artifact_review;
    }

    if (glob.queued_messages) {
      setSegmentedValue('ctrlQueuedMessages', glob.queued_messages);
    }

    // Audio Chime Settings
    const chkSound = document.getElementById('settingEnableSounds');
    if (chkSound) {
      chkSound.checked = !!glob.enable_sounds;
      audioToneEnabled = !!glob.enable_sounds;
    }

    const rngVolume = document.getElementById('settingSoundVolume');
    const lblVolume = document.getElementById('settingVolumeLabel');
    if (rngVolume && glob.sound_volume !== undefined) {
      rngVolume.value = glob.sound_volume;
      if (lblVolume) lblVolume.textContent = glob.sound_volume + '%';
    }

    // Models Tab
    const modelsContainer = document.getElementById('settingsModelsListContainer');
    const modelList = (Array.isArray(glob.models) && glob.models.length > 0) ? glob.models : (availableModels || []);
    if (modelsContainer && modelList.length > 0) {
      modelsContainer.innerHTML = modelList.map(m => {
        const isSelected = m.id === (glob.default_model || currentModel);
        return `
          <div class="agy-model-card ${isSelected ? 'selected' : ''}" onclick="selectModelOption('${escapeHtml(m.id)}')">
            <div class="agy-row-info">
              <div class="agy-row-label">${escapeHtml(m.name)}</div>
              <div class="agy-row-desc">${escapeHtml(m.id)}</div>
            </div>
            <div class="agy-model-radio-indicator">
              <input type="radio" name="settings_active_model" value="${escapeHtml(m.id)}" ${isSelected ? 'checked' : ''}>
              <span class="agy-radio-custom"></span>
            </div>
          </div>
        `;
      }).join('');
    }

    // Sync to Dock policy chip & model chip
    const dockPolicyName = document.getElementById('dockPolicyName');
    if (dockPolicyName && glob.permission_preset) dockPolicyName.textContent = glob.permission_preset;

    const dockModelName = document.getElementById('dockModelName');
    if (dockModelName && glob.default_model) {
      const found = (glob.models || []).find(m => m.id === glob.default_model);
      dockModelName.textContent = found ? found.name : glob.default_model;
    }
  }

  function selectModelOption(id) {
    triggerHaptic(10);
    autoSaveSetting('default_model', id);
    document.querySelectorAll('.agy-model-card').forEach(card => {
      const radio = card.querySelector('input[type="radio"]');
      const isThis = radio && radio.value === id;
      card.classList.toggle('selected', isThis);
      if (radio) radio.checked = isThis;
    });
  }
  window.selectModelOption = selectModelOption;

  function setSegmentedValue(containerId, value, settingKey) {
    const container = document.getElementById(containerId);
    if (container) {
      container.querySelectorAll('.agy-seg-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.trim().toLowerCase() === String(value).trim().toLowerCase());
      });
    }
    if (settingKey) autoSaveSetting(settingKey, value);
  }
  window.setSegmentedValue = setSegmentedValue;

  async function autoSaveSetting(key, value) {
    triggerHaptic(10);
    if (key === 'enable_sounds') {
      audioToneEnabled = !!value;
    }
    try {
      const payload = { global: {} };
      payload.global[key] = value;
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (key === 'permission_preset') {
        const dockPolicyName = document.getElementById('dockPolicyName');
        if (dockPolicyName) dockPolicyName.textContent = value;
      } else if (key === 'default_model') {
        currentModel = value;
        const dockModelName = document.getElementById('dockModelName');
        if (dockModelName) dockModelName.textContent = value;
        if (headerModelText) headerModelText.textContent = value;
        if (pillModelText) pillModelText.textContent = value;
      }
    } catch (e) {
      console.warn('[Settings] Error auto-saving setting:', e);
    }
  }

  function cyclePolicyPreset() {
    triggerHaptic(10);
    const presets = ['Turbo', 'Accept Edits', 'Auto', 'Request Review', 'Strict'];
    const dockPolicyName = document.getElementById('dockPolicyName');
    const current = dockPolicyName ? dockPolicyName.textContent.trim() : 'Turbo';
    let nextIdx = (presets.indexOf(current) + 1) % presets.length;
    if (nextIdx < 0) nextIdx = 0;
    const nextVal = presets[nextIdx];
    if (dockPolicyName) dockPolicyName.textContent = nextVal;
    const sel = document.getElementById('settingPermissionPreset');
    if (sel) sel.value = nextVal;
    autoSaveSetting('permission_preset', nextVal);
  }

  function applyAppTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    autoSaveSetting('theme', theme);
  }

  async function saveSettingsForm() {
    closeSettingsModal();
  }

  async function initProjectAgentsDir() {
    triggerHaptic(10);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_overrides: {
            has_agents_dir: true
          }
        })
      });
      alert('ساختار استاندارد .agents/ برای این پروژه در حافظه ثبت گردید.');
    } catch (e) {
      alert('خطا: ' + e.message);
    }
  }

  // System Update & Self-Repair Actions
  async function checkSystemUpdateStatus() {
    const desc = document.getElementById('systemVersionDesc');
    const badge = document.getElementById('systemStatusBadge');
    if (!desc) return;
    try {
      const res = await fetch('/api/system/update');
      if (res.ok) {
        const data = await res.json();
        const agyStatus = data.agy_ready ? '✅ موتور آماده' : '⚠️ موتور CLI یافت نشد';
        const glibcStatus = data.is_termux ? (data.glibc_ready ? ' | glibc: OK' : ' | ❌ glibc ناقص') : '';
        desc.textContent = `نسخه فعلی: v${data.version || '3.2.1'} | ${agyStatus}${glibcStatus}`;
        if (badge) {
          if (data.agy_ready && data.glibc_ready) {
            badge.className = 'agy-status-pill verified';
            badge.textContent = 'بروز و آماده';
          } else {
            badge.className = 'agy-status-pill warning';
            badge.textContent = 'نیاز به عیب‌یابی';
          }
        }
      }
    } catch (e) {
      console.warn('[Update] Failed to check status:', e);
    }
  }

  async function triggerSystemUpdate() {
    const btn = document.getElementById('btnSystemUpdate');
    const logBox = document.getElementById('updateLogBox');
    const badge = document.getElementById('systemStatusBadge');
    const desc = document.getElementById('systemVersionDesc');

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="spin-anim" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10"></path>
        </svg>
        در حال به‌روزرسانی و عیب‌یابی خودکار سامانه...
      `;
    }
    if (logBox) {
      logBox.style.display = 'block';
      logBox.textContent = '⏳ در حال شروع عیب‌یابی خودکار، بررسی گیت و بسته‌های سیستم...\n';
    }
    showToast('در حال به‌روزرسانی و عیب‌یابی خودکار سامانه... لطفاً صبور باشید.', 'info', 6000);

    try {
      const res = await fetch('/api/system/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();

      if (logBox && Array.isArray(data.logs)) {
        logBox.textContent = data.logs.join('\n') + '\n\n' + (data.message || 'پایان عملیات.');
        logBox.scrollTop = logBox.scrollHeight;
      }

      if (data.ok) {
        showToast(data.message || 'سامانه با موفقیت به‌روزرسانی و عیب‌یابی شد!', 'success', 5000);
        if (badge) {
          badge.className = 'agy-status-pill verified';
          badge.textContent = 'بروز و آماده';
        }
        if (desc) {
          desc.textContent = `نسخه فعلی: v${data.version || '3.2.1'} | ✅ موتور آماده (${data.agy_bin || 'agy'})`;
        }
      } else {
        showToast(data.error || 'خطا در عملیات به‌روزرسانی.', 'error', 6000);
      }
    } catch (e) {
      console.error('[Update] Error:', e);
      if (logBox) logBox.textContent += '\n❌ خطا در ارتباط با سرور: ' + e.message;
      showToast('خطا در ارتباط با سرور: ' + e.message, 'error', 6000);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
          </svg>
          بررسی، به‌روزرسانی و عیب‌یابی خودکار سامانه
        `;
      }
      checkSystemUpdateStatus();
    }
  }

  // Expose global window actions for direct HTML onclick triggers
  window.triggerSystemUpdate = triggerSystemUpdate;
  window.checkSystemUpdateStatus = checkSystemUpdateStatus;
  window.toggleModelDropdown = toggleModelDropdown;
  window.togglePolicyDropdown = togglePolicyDropdown;
  window.selectModel = selectModel;
  window.selectPolicyPreset = selectPolicyPreset;
  window.closeAllDockDropdowns = closeAllDockDropdowns;
  window.openModelSheet = openModelSheet;
  window.closeModelSheet = closeModelSheet;
  window.openSettingsModal = openSettingsModal;
  window.closeSettingsModal = closeSettingsModal;
  window.switchSettingsTab = switchSettingsTab;
  window.saveSettingsForm = saveSettingsForm;
  window.initProjectAgentsDir = initProjectAgentsDir;
  window.autoSaveSetting = autoSaveSetting;
  window.setSegmentedValue = setSegmentedValue;
  window.cyclePolicyPreset = cyclePolicyPreset;
  window.applyAppTheme = applyAppTheme;
  window.openDrawer = openDrawer;
  window.closeDrawer = closeDrawer;
  window.createNewChat = createNewChat;
  window.createNewChatInProject = createNewChatInProject;
  window.switchChat = switchChat;
  window.switchProject = switchProject;
  window.promptNewProject = promptNewProject;
  window.toggleProjectFilter = toggleProjectFilter;
  window.filterDrawerProjects = filterDrawerProjects;
  window.sendMessage = sendMessage;
  window.openChatSearchModal = openChatSearchModal;
  window.closeChatSearchModal = closeChatSearchModal;
  window.performChatSearch = performChatSearch;
  window.selectSearchResult = selectSearchResult;
  window.setFpPath = setFpPath;
  window.submitFolderPicker = submitFolderPicker;
  window.closeFolderPickerModal = closeFolderPickerModal;
  window.navigateFpDir = navigateFpDir;
  window.navigateFpParent = navigateFpParent;
  window.refreshFpDir = refreshFpDir;
  window.toggleFpMkdir = toggleFpMkdir;
  window.submitFpMkdir = submitFpMkdir;
  window.handleDeleteChat = handleDeleteChat;
  window.renderSettingsProjectsList = renderSettingsProjectsList;
  window.switchProjectFromSettings = switchProjectFromSettings;
  window.deleteProjectFromSettings = deleteProjectFromSettings;
  window.openChatFromSettings = openChatFromSettings;
  window.refreshAccountStatus = refreshAccountStatus;
  window.saveGeminiApiKey = saveGeminiApiKey;
  window.saveCustomOAuthToken = saveCustomOAuthToken;
  window.logoutAccount = logoutAccount;
  window.copyCliAuthCommand = copyCliAuthCommand;
  window.startCliLoginFlow = startCliLoginFlow;
  window.copyGoogleAuthUrl = copyGoogleAuthUrl;
  window.submitCliAuthCode = submitCliAuthCode;
  window.cancelCliLoginFlow = cancelCliLoginFlow;
  window.checkCliLoginSession = checkCliLoginSession;
  window.openQuotaModal = openQuotaModal;
  window.closeQuotaModal = closeQuotaModal;

  // Helper to bind guaranteed tap/click events
  function bindAction(el, handler) {
    if (!el) return;
    el.addEventListener('click', (e) => {
      e.preventDefault();
      handler(e);
    });
  }

  // Setup Event Listeners
  function setupEvents() {
    // Input Auto-Resize, Popovers & Send
    inputMessage.addEventListener('input', () => {
      inputMessage.style.height = 'auto';
      inputMessage.style.height = Math.min(inputMessage.scrollHeight, 140) + 'px';
      if (btnSend) {
        if (inputMessage.value.trim().length > 0 || btnSend.classList.contains('stop-mode')) {
          btnSend.classList.remove('btn-disabled');
        } else {
          btnSend.classList.add('btn-disabled');
        }
      }
      handleInputPopovers();
    });

    inputMessage.addEventListener('keydown', (e) => {
      // Popover keyboard navigation
      if (slashPopover && slashPopover.classList.contains('active')) {
        const items = slashPopover.querySelectorAll('.slash-item');
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          slashSelectedIdx = (slashSelectedIdx + 1) % items.length;
          updatePopoverSelection(items, slashSelectedIdx);
          return;
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          slashSelectedIdx = (slashSelectedIdx - 1 + items.length) % items.length;
          updatePopoverSelection(items, slashSelectedIdx);
          return;
        } else if (e.key === 'Enter' || e.key === 'Tab') {
          e.preventDefault();
          if (items[slashSelectedIdx]) items[slashSelectedIdx].click();
          return;
        } else if (e.key === 'Escape') {
          e.preventDefault();
          closeSlashPopover();
          return;
        }
      }

      if (mentionsPopover && mentionsPopover.classList.contains('active')) {
        const items = mentionsPopover.querySelectorAll('.mention-item');
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          mentionSelectedIdx = (mentionSelectedIdx + 1) % items.length;
          updatePopoverSelection(items, mentionSelectedIdx);
          return;
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          mentionSelectedIdx = (mentionSelectedIdx - 1 + items.length) % items.length;
          updatePopoverSelection(items, mentionSelectedIdx);
          return;
        } else if (e.key === 'Enter' || e.key === 'Tab') {
          e.preventDefault();
          if (items[mentionSelectedIdx]) items[mentionSelectedIdx].click();
          return;
        } else if (e.key === 'Escape') {
          e.preventDefault();
          closeMentionsPopover();
          return;
        }
      }

      if (e.key === 'Enter' && !e.shiftKey) {
        if (window.innerWidth > 640 || !('ontouchstart' in window)) {
          e.preventDefault();
          sendMessage();
        }
      }
    });

    // Close popovers and dock dropdowns on click outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.input-container')) {
        closeSlashPopover();
        closeMentionsPopover();
      }
      if (!e.target.closest('#dockModelWrapper') && !e.target.closest('#dockPolicyWrapper')) {
        closeAllDockDropdowns();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeAllDockDropdowns();
      }
    });

    bindAction(btnSend, sendMessage);

    // Quick Control Pills
    if (pillModel) bindAction(pillModel, openModelSheet);
    if (pillEffort) bindAction(pillEffort, cycleEffort);
    if (pillMode) bindAction(pillMode, cycleMode);
    if (btnCloseModelSheet) bindAction(btnCloseModelSheet, closeModelSheet);
    if (modelSheetBackdrop) {
      modelSheetBackdrop.addEventListener('click', (e) => {
        if (e.target === modelSheetBackdrop) closeModelSheet();
      });
    }

    // Header buttons
    if (btnNewChat) bindAction(btnNewChat, createNewChat);
    if (btnMenu) bindAction(btnMenu, openDrawer);
    if (btnCloseDrawer) bindAction(btnCloseDrawer, closeDrawer);
    if (drawerBackdrop) {
      drawerBackdrop.addEventListener('click', (e) => {
        if (e.target === drawerBackdrop) closeDrawer();
      });
    }
    if (btnDrawerNewChat) bindAction(btnDrawerNewChat, createNewChat);

    // Header quick tools
    if (btnOpenFiles) btnOpenFiles.addEventListener('click', openFilesModal);
    if (btnOpenProcesses) btnOpenProcesses.addEventListener('click', openProcessesModal);

    // Drawer tool buttons
    if (btnDrawerProcesses) btnDrawerProcesses.addEventListener('click', openProcessesModal);
    if (btnDrawerFiles) btnDrawerFiles.addEventListener('click', openFilesModal);
    if (btnDrawerGuide && systemGuideModal) {
      btnDrawerGuide.addEventListener('click', () => {
        closeDrawer();
        systemGuideModal.classList.add('active');
      });
    }
    if (btnCloseSystemGuide && systemGuideModal) {
      btnCloseSystemGuide.addEventListener('click', () => {
        systemGuideModal.classList.remove('active');
      });
    }
    if (systemGuideModal) {
      systemGuideModal.addEventListener('click', (e) => {
        if (e.target === systemGuideModal) systemGuideModal.classList.remove('active');
      });
    }
    if (btnDrawerRestart) btnDrawerRestart.addEventListener('click', restartEngine);
    if (btnBannerRestart) btnBannerRestart.addEventListener('click', restartEngine);

    // Processes modal buttons
    if (btnCloseProcesses) btnCloseProcesses.addEventListener('click', closeProcessesModal);
    if (btnRefreshProcesses) btnRefreshProcesses.addEventListener('click', fetchProcesses);
    if (processesModal) {
      processesModal.addEventListener('click', (e) => {
        if (e.target === processesModal) closeProcessesModal();
      });
    }

    // Inspect modal buttons
    if (btnCloseInspect) btnCloseInspect.addEventListener('click', closeInspectModal);
    if (inspectProcessModal) {
      inspectProcessModal.addEventListener('click', (e) => {
        if (e.target === inspectProcessModal) closeInspectModal();
      });
    }
    if (btnSendInspectStdin) btnSendInspectStdin.addEventListener('click', sendInspectStdin);
    if (inspectStdinInput) {
      inspectStdinInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendInspectStdin();
      });
    }
    if (btnSignalSigint) btnSignalSigint.addEventListener('click', () => {
      if (currentInspectingPid) killProcess(currentInspectingPid, 'SIGINT');
    });
    if (btnSignalSigterm) btnSignalSigterm.addEventListener('click', () => {
      if (currentInspectingPid) killProcess(currentInspectingPid, 'SIGTERM');
    });
    if (btnSignalSigkill) btnSignalSigkill.addEventListener('click', () => {
      if (currentInspectingPid) killProcess(currentInspectingPid, 'SIGKILL');
    });

    // Files modal buttons
    if (btnCloseFiles) btnCloseFiles.addEventListener('click', closeFilesModal);
    if (filesModal) {
      filesModal.addEventListener('click', (e) => {
        if (e.target === filesModal) closeFilesModal();
      });
    }

    // Code viewer modal buttons & In-App Editor
    if (btnCloseCodeViewer) btnCloseCodeViewer.addEventListener('click', closeCodeViewer);
    if (btnCodeCopy) btnCodeCopy.addEventListener('click', copyCurrentFileCode);
    if (btnCodeDownload) btnCodeDownload.addEventListener('click', downloadCurrentFile);
    if (btnCodeMention) btnCodeMention.addEventListener('click', mentionCurrentFile);
    if (btnCodeEditToggle) btnCodeEditToggle.addEventListener('click', () => toggleCodeEditMode());
    if (btnCodeSave) btnCodeSave.addEventListener('click', saveCurrentFileCode);
    if (codeViewerModal) {
      codeViewerModal.addEventListener('click', (e) => {
        if (e.target === codeViewerModal) closeCodeViewer();
      });
    }

    // Projects Manager Modal & Triggers
    if (headerCenterBtn) headerCenterBtn.addEventListener('click', openProjectsModal);
    if (btnDrawerOpenProjects) btnDrawerOpenProjects.addEventListener('click', openProjectsModal);
    if (btnDrawerProjects) btnDrawerProjects.addEventListener('click', openProjectsModal);
    if (btnActiveProjectInfo) btnActiveProjectInfo.addEventListener('click', openProjectsModal);
    if (btnDrawerNewProject) {
      btnDrawerNewProject.addEventListener('click', () => {
        openProjectsModal();
        if (createProjectPanel) {
          createProjectPanel.style.display = 'block';
          if (newProjectName) newProjectName.focus();
        }
      });
    }
    if (btnCloseProjects) btnCloseProjects.addEventListener('click', closeProjectsModal);
    if (projectsModal) {
      projectsModal.addEventListener('click', (e) => {
        if (e.target === projectsModal) closeProjectsModal();
      });
    }
    if (btnToggleCreateProject) {
      btnToggleCreateProject.addEventListener('click', () => {
        if (createProjectPanel) {
          const isHidden = (createProjectPanel.style.display === 'none');
          createProjectPanel.style.display = isHidden ? 'block' : 'none';
          if (isHidden && newProjectName) newProjectName.focus();
        }
      });
    }
    if (btnCancelCreateProject) {
      btnCancelCreateProject.addEventListener('click', () => {
        if (createProjectPanel) createProjectPanel.style.display = 'none';
      });
    }
    if (btnSubmitCreateProject) {
      btnSubmitCreateProject.addEventListener('click', () => {
        const pName = newProjectName ? newProjectName.value : '';
        const pPath = newProjectPath ? newProjectPath.value : '';
        createNewProject(pName, pPath);
      });
    }

    // Quick Path Chips for Projects
    document.querySelectorAll('.quick-path-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        if (newProjectPath) {
          newProjectPath.value = chip.getAttribute('data-path') || '';
          newProjectPath.focus();
        }
      });
    });

    // Quota Modal & Triggers
    if (pillQuota) pillQuota.addEventListener('click', openQuotaModal);
    if (btnDrawerQuota) btnDrawerQuota.addEventListener('click', openQuotaModal);
    if (btnDrawerOpenQuota) btnDrawerOpenQuota.addEventListener('click', openQuotaModal);
    if (btnOpenAccountQuota) btnOpenAccountQuota.addEventListener('click', openQuotaModal);
    if (btnCloseQuota) btnCloseQuota.addEventListener('click', closeQuotaModal);
    if (quotaModal) {
      quotaModal.addEventListener('click', (e) => {
        if (e.target === quotaModal) closeQuotaModal();
      });
    }
    if (btnOpenCliLoginGuide) {
      btnOpenCliLoginGuide.addEventListener('click', () => {
        if (cliLoginBox) {
          cliLoginBox.style.display = (cliLoginBox.style.display === 'none' ? 'block' : 'none');
        }
      });
    }

    // Settings Modal backdrop click
    if (settingsModal) {
      settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettingsModal();
      });
    }

    // Attach File / Image
    const btnAttachFile = document.getElementById('btnAttachFile');
    const fileAttachmentInput = document.getElementById('fileAttachmentInput');
    if (btnAttachFile && fileAttachmentInput) {
      btnAttachFile.addEventListener('click', () => fileAttachmentInput.click());
      fileAttachmentInput.addEventListener('change', () => {
        const files = fileAttachmentInput.files;
        if (files && files.length > 0) {
          let names = [];
          for (let i = 0; i < files.length; i++) {
            names.push(`@${files[i].name}`);
          }
          inputMessage.value += (inputMessage.value ? ' ' : '') + names.join(' ') + ' ';
          inputMessage.dispatchEvent(new Event('input'));
          inputMessage.focus();
        }
      });
    }

    // Model Change
    if (modelSelect) {
      modelSelect.addEventListener('change', () => {
        const selected = modelSelect.value;
        selectModel(selected);
      });
    }

    // Extra Keys Toggle
    if (btnToggleKeys && extraKeysRow) {
      btnToggleKeys.addEventListener('click', () => {
        extraKeysRow.classList.toggle('show');
      });
    }

    // Extra key clicks
    document.querySelectorAll('.key-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.getAttribute('data-key');
        if (key === 'CLEAR') {
          inputMessage.value = '/clear';
          sendMessage();
        } else if (key === '/restart') {
          restartEngine();
        } else if (key === 'TAB') {
          inputMessage.value += '  ';
          inputMessage.dispatchEvent(new Event('input'));
          inputMessage.focus();
        } else if (key === 'ESC') {
          inputMessage.value = '';
          inputMessage.style.height = 'auto';
          btnSend.disabled = true;
          closeSlashPopover();
          closeMentionsPopover();
        } else {
          inputMessage.value += key + ' ';
          inputMessage.dispatchEvent(new Event('input'));
          inputMessage.focus();
        }
      });
    });

    // Quick Suggestions
    document.querySelectorAll('.chip-btn').forEach(chip => {
      chip.addEventListener('click', () => {
        const text = chip.getAttribute('data-prompt') || chip.innerText.trim();
        inputMessage.value = text;
        inputMessage.dispatchEvent(new Event('input'));
        sendMessage();
      });
    });

    // Chat Search Engine Input & Modals
    const chatSearchInput = document.getElementById('chatSearchInput');
    if (chatSearchInput) {
      chatSearchInput.addEventListener('input', (e) => {
        clearTimeout(chatSearchDebounceTimer);
        chatSearchDebounceTimer = setTimeout(() => {
          performChatSearch(e.target.value);
        }, 200);
      });
      chatSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeChatSearchModal();
      });
    }

    const chatSearchModal = document.getElementById('chatSearchModal');
    if (chatSearchModal) {
      chatSearchModal.addEventListener('click', (e) => {
        if (e.target === chatSearchModal) closeChatSearchModal();
      });
    }

    const folderPickerModal = document.getElementById('folderPickerModal');
    if (folderPickerModal) {
      folderPickerModal.addEventListener('click', (e) => {
        if (e.target === folderPickerModal) closeFolderPickerModal();
      });
    }

    const fpNewFolderName = document.getElementById('fpNewFolderName');
    if (fpNewFolderName) {
      fpNewFolderName.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          submitFpMkdir();
        } else if (e.key === 'Escape') {
          toggleFpMkdir(false);
        }
      });
    }

    // Global keyboard shortcut Ctrl+K / Cmd+K
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        openChatSearchModal();
      }
      if (e.key === 'Escape') {
        closeChatSearchModal();
        closeFolderPickerModal();
      }
    });

    // Enter key submit on CLI auth code input
    const inputCliCode = document.getElementById('inputCliAuthCode');
    if (inputCliCode) {
      inputCliCode.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          submitCliAuthCode();
        }
      });
    }

    // Tab focus / visibility change sync
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        refreshAccountStatus();
        checkCliLoginSession();
      }
    });

    window.addEventListener('focus', () => {
      refreshAccountStatus();
      checkCliLoginSession();
    });
  }

  // Setup Auth Events
  function setupAuthEvents() {
    if (authLoginForm) {
      authLoginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleLoginSubmit();
      });
    }

    if (btnToggleAuthPassword && authPassword) {
      btnToggleAuthPassword.addEventListener('click', () => {
        const isPwd = authPassword.type === 'password';
        authPassword.type = isPwd ? 'text' : 'password';
        const eye = document.getElementById('pwdEyeIcon');
        if (eye) {
          eye.innerHTML = isPwd
            ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>'
            : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
        }
      });
    }

    if (btnDrawerLogout) {
      btnDrawerLogout.addEventListener('click', handleLogout);
    }

    // Change Password Modal Events
    if (btnOpenChangePassword && changePasswordModal) {
      btnOpenChangePassword.addEventListener('click', () => {
        closeDrawer();
        if (changePwdAlert) changePwdAlert.style.display = 'none';
        if (cpCurrentPassword) cpCurrentPassword.value = '';
        if (cpNewUsername) cpNewUsername.value = currentUser;
        if (cpNewPassword) cpNewPassword.value = '';
        changePasswordModal.classList.add('active');
      });
    }

    if (btnCloseChangePassword && changePasswordModal) {
      btnCloseChangePassword.addEventListener('click', () => {
        changePasswordModal.classList.remove('active');
      });
    }

    if (changePasswordForm) {
      changePasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const oldPwd = cpCurrentPassword ? cpCurrentPassword.value : '';
        const newUsr = cpNewUsername ? cpNewUsername.value.trim() : '';
        const newPwd = cpNewPassword ? cpNewPassword.value : '';

        if (!oldPwd || !newPwd) {
          if (changePwdAlert) {
            changePwdAlert.textContent = 'لطفاً رمز عبور فعلی و جدید را وارد کنید.';
            changePwdAlert.className = 'auth-alert';
            changePwdAlert.style.display = 'block';
          }
          return;
        }

        try {
          const res = await authFetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password: oldPwd, new_username: newUsr, new_password: newPwd })
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            if (changePwdAlert) {
              changePwdAlert.textContent = 'رمز عبور با موفقیت تغییر کرد!';
              changePwdAlert.className = 'auth-alert success';
              changePwdAlert.style.display = 'block';
            }
            if (data.username) updateUserInfoUI(data.username);
            setTimeout(() => {
              if (changePasswordModal) changePasswordModal.classList.remove('active');
            }, 1200);
          } else {
            if (changePwdAlert) {
              changePwdAlert.textContent = data.error || 'خطا در تغییر رمز عبور.';
              changePwdAlert.className = 'auth-alert';
              changePwdAlert.style.display = 'block';
            }
          }
        } catch (err) {
          if (changePwdAlert) {
            changePwdAlert.textContent = 'خطا در برقراری ارتباط با سرور.';
            changePwdAlert.className = 'auth-alert';
            changePwdAlert.style.display = 'block';
          }
        }
      });
    }
  }

  // Clear any legacy Service Worker caches to ensure fresh code
  function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        for (const reg of registrations) {
          reg.unregister();
        }
      }).catch(() => {});
    }
  }

  // Initialize
  async function init() {
    loadFromLocalStorage();
    connectWebSocket();

    const foundModel = availableModels.find(m => m.id === currentModel);
    const dockModelName = document.getElementById('dockModelName');
    if (dockModelName && foundModel) dockModelName.textContent = foundModel.name;
    renderModelDropdownList();

    if (headerModelText) headerModelText.textContent = currentModel;
    if (pillModelText) pillModelText.textContent = currentModel;
    updateEffortPill(currentEffort);
    updateModePill(currentMode);

    try {
      renderMessages();
    } catch (err) {
      console.error('[App] renderMessages error:', err);
    }
    updateDrawerChatList();

    setupEvents();
    setupAuthEvents();
    initVoiceInput();
    startPingWatchdog();

    fetchInitialSettings();
    fetchAccountQuota();
    fetchServerChats();
    fetchModels();
    fetchWorkspace();
    fetchProcesses();
    fetchMentions();

    registerServiceWorker();

    // Regular health & network polling (every 10s)
    setInterval(checkHealth, 10000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
