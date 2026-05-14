// ===== State =====
let token = localStorage.getItem('token');
let pollTimer = null;
let versionTimer = null;
let currentPage = 'today';
let appVersion = null;
let lastDueTasks = [];
let lastAllTasks = [];
let filterFloor = '';
let filterRoom = '';
let allFilterFloor = '';
let allFilterRoom = '';

// ===== Toast =====
let _toastTimer = null;
function showToast(msg, type='') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.className = 'toast', 2800);
}

function showUndoToast(msg, onUndo) {
  const t = document.getElementById('toast');
  t.innerHTML = `
    <div class="toast-action">
      <span class="toast-msg">${escHtml(msg)}</span>
      <button id="undo-btn">Rückgängig</button>
    </div>`;
  t.className = 'toast show success';
  clearTimeout(_toastTimer);
  const btn = document.getElementById('undo-btn');
  btn.onclick = () => {
    clearTimeout(_toastTimer);
    t.className = 'toast';
    onUndo();
  };
  _toastTimer = setTimeout(() => { t.className = 'toast'; }, 6000);
}

function formatError(detail) {
  if (!detail) return 'Fehler aufgetreten';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(d => d.msg || JSON.stringify(d)).join(', ');
  if (typeof detail === 'object') return detail.msg || JSON.stringify(detail);
  return String(detail);
}

// ===== API =====
async function api(url, options={}) {
  const headers = options.headers || {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  try {
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) { doLogout(); return null; }
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      showToast(formatError(data && data.detail), 'error');
      return null;
    }
    return data;
  } catch (e) {
    showToast('Verbindungsfehler', 'error');
    return null;
  }
}

// ===== Auth =====
function showRegister() {
  document.getElementById('login-form').classList.add('hidden');
  document.getElementById('register-form').classList.remove('hidden');
}
function showLogin() {
  document.getElementById('register-form').classList.add('hidden');
  document.getElementById('login-form').classList.remove('hidden');
}

async function doLogin() {
  const username = document.getElementById('login-user').value.trim();
  const password = document.getElementById('login-pass').value;
  if (!username || !password) return showToast('Bitte alle Felder ausfüllen', 'error');
  const data = await api('/api/auth/login', { method: 'POST', body: { username, password } });
  if (data) {
    token = data.access_token;
    localStorage.setItem('token', token);
    showApp();
  }
}

async function doRegister() {
  const username = document.getElementById('reg-user').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-pass').value;
  if (!username || !email || !password) return showToast('Bitte alle Felder ausfüllen', 'error');
  const data = await api('/api/auth/register', { method: 'POST', body: { username, email, password } });
  if (data) {
    token = data.access_token;
    localStorage.setItem('token', token);
    showApp();
  }
}

function doOidcLogin() { window.location.href = '/api/auth/oidc/login'; }

function doLogout() {
  token = null;
  localStorage.removeItem('token');
  stopPolling();
  document.getElementById('auth-screen').classList.add('active');
  document.getElementById('main-app').classList.remove('active');
}

async function showApp() {
  document.getElementById('auth-screen').classList.remove('active');
  document.getElementById('main-app').classList.add('active');
  // Aktuelle Version festhalten -> künftiger Drift triggert Reload
  try {
    const v = await (await fetch('/api/version', { cache: 'no-store' })).json();
    appVersion = v.version;
  } catch (e) {}
  const me = await api('/api/auth/me');
  if (me) {
    document.getElementById('header-greet').textContent = `Hallo, ${me.username}!`;
    document.getElementById('profile-username').value = me.username;
    document.getElementById('profile-email').value = me.email;
  }
  navigateTo('today');
  startPolling();
}

// ===== Navigation =====
function navigateTo(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`.nav-item[data-page="${page}"]`).classList.add('active');

  if (page === 'today') loadToday();
  if (page === 'all') loadAll();
  if (page === 'stats') loadStats();
}

// ===== Polling =====
function startPolling() {
  stopPolling();
  pollTimer = setInterval(() => {
    if (currentPage === 'today') loadToday(true);
    if (currentPage === 'all') loadAll(true);
    if (currentPage === 'stats') loadStats(true);
  }, 15000);
  // Version-Check alle 30s -> hard reload bei Drift
  versionTimer = setInterval(checkVersion, 30000);
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  if (versionTimer) { clearInterval(versionTimer); versionTimer = null; }
}

async function checkVersion() {
  try {
    const r = await fetch('/api/version', { cache: 'no-store' });
    const d = await r.json();
    if (appVersion && d.version && d.version !== appVersion) {
      // Server hat neu gestartet -> Frontend neu laden
      window.location.reload();
    }
    if (d.version) appVersion = d.version;
  } catch (e) {}
}

// ===== Filter Helpers =====
function buildFloorOptions(tasks, selected) {
  const counts = {};
  const order = [];
  for (const t of tasks) {
    if (!counts[t.floor]) { counts[t.floor] = 0; order.push(t.floor); }
    counts[t.floor]++;
  }
  let html = `<option value="">🏠 Alle Etagen (${tasks.length})</option>`;
  for (const f of order) {
    const sel = selected === f ? 'selected' : '';
    html += `<option value="${escAttr(f)}" ${sel}>${escHtml(f)} (${counts[f]})</option>`;
  }
  return html;
}

function buildRoomOptions(tasks, floor, selected) {
  const counts = {};
  const icons = {};
  const order = [];
  for (const t of tasks) {
    if (t.floor !== floor) continue;
    if (!counts[t.room]) { counts[t.room] = 0; order.push(t.room); icons[t.room] = t.icon; }
    counts[t.room]++;
  }
  const total = order.reduce((s, r) => s + counts[r], 0);
  let html = `<option value="">Alle Räume (${total})</option>`;
  for (const r of order) {
    const sel = selected === r ? 'selected' : '';
    html += `<option value="${escAttr(r)}" ${sel}>${icons[r]} ${escHtml(r)} (${counts[r]})</option>`;
  }
  return html;
}

// ===== Today =====
async function loadToday(silent) {
  const [tasks, today, recent] = await Promise.all([
    api('/api/tasks/due'),
    api('/api/stats/today'),
    api('/api/tasks/recent?limit=10'),
  ]);
  if (!tasks) return;

  document.getElementById('pill-done').textContent = today ? today.completions : 0;
  document.getElementById('pill-cal').textContent = today ? today.calories : 0;

  lastDueTasks = tasks;

  // Filter validieren
  if (filterFloor && !tasks.some(t => t.floor === filterFloor)) filterFloor = '';
  if (filterRoom && !tasks.some(t => t.room === filterRoom && t.floor === filterFloor)) filterRoom = '';

  renderTodayFilters();
  renderDueList();
  renderRecent(recent || []);
}

function renderTodayFilters() {
  const floorSel = document.getElementById('filter-floor-select');
  const roomSel = document.getElementById('filter-room-select');
  floorSel.innerHTML = buildFloorOptions(lastDueTasks, filterFloor);
  floorSel.classList.toggle('active', !!filterFloor);

  if (filterFloor) {
    roomSel.innerHTML = buildRoomOptions(lastDueTasks, filterFloor, filterRoom);
    roomSel.classList.remove('hidden');
    roomSel.classList.toggle('active', !!filterRoom);
  } else {
    roomSel.classList.add('hidden');
  }
}

function onFilterChange() {
  const newFloor = document.getElementById('filter-floor-select').value;
  if (newFloor !== filterFloor) {
    filterFloor = newFloor;
    filterRoom = '';
  } else {
    filterRoom = document.getElementById('filter-room-select').value || '';
  }
  renderTodayFilters();
  renderDueList();
}

function renderDueList() {
  const list = document.getElementById('due-list');
  const title = document.getElementById('due-title');

  let filtered = lastDueTasks;
  if (filterFloor) filtered = filtered.filter(t => t.floor === filterFloor);
  if (filterRoom) filtered = filtered.filter(t => t.room === filterRoom);

  if (filterRoom) title.textContent = `${filterFloor} · ${filterRoom}`;
  else if (filterFloor) title.textContent = filterFloor;
  else title.textContent = 'Fällige Aufgaben';

  if (lastDueTasks.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="icon">✨</div>
        <div class="title">Alles glänzt!</div>
        <div class="subtitle">Aktuell ist nichts fällig. Genieß den Moment.</div>
      </div>`;
    return;
  }
  if (filtered.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="icon">🎯</div>
        <div class="title">Hier ist nichts zu tun.</div>
        <div class="subtitle">In diesem Bereich ist alles aktuell.</div>
      </div>`;
    return;
  }
  list.innerHTML = filtered.map(renderTaskCard).join('');
}

function renderRecent(entries) {
  const titleRow = document.getElementById('recent-title-row');
  const list = document.getElementById('recent-list');
  if (!entries || entries.length === 0) {
    titleRow.style.display = 'none';
    list.innerHTML = '';
    return;
  }
  titleRow.style.display = '';
  list.innerHTML = entries.map(e => `
    <div class="recent-card" data-cid="${e.completion_id}">
      <div class="recent-icon">${e.icon}</div>
      <div class="recent-info">
        <div class="recent-name">${escHtml(e.task_name)}</div>
        <div class="recent-meta">${escHtml(e.room)} · ${e.calories} kcal · ${formatRelative(e.completed_at)}</div>
      </div>
      <button class="recent-undo" onclick="undoCompletion(${e.completion_id})">Rückgängig</button>
    </div>
  `).join('');
}

function formatRelative(iso) {
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'gerade eben';
  if (diff < 3600) return `vor ${Math.floor(diff/60)} Min`;
  if (diff < 86400) return `vor ${Math.floor(diff/3600)} Std`;
  return `vor ${Math.floor(diff/86400)} T`;
}

// ===== Alle Aufgaben =====
async function loadAll(silent) {
  const tasks = await api('/api/tasks/all');
  if (!tasks) return;
  lastAllTasks = tasks;

  if (allFilterFloor && !tasks.some(t => t.floor === allFilterFloor)) allFilterFloor = '';
  if (allFilterRoom && !tasks.some(t => t.room === allFilterRoom && t.floor === allFilterFloor)) allFilterRoom = '';

  renderAllFilters();
  renderAllList();
}

function renderAllFilters() {
  const floorSel = document.getElementById('all-floor-select');
  const roomSel = document.getElementById('all-room-select');
  floorSel.innerHTML = buildFloorOptions(lastAllTasks, allFilterFloor);
  floorSel.classList.toggle('active', !!allFilterFloor);

  if (allFilterFloor) {
    roomSel.innerHTML = buildRoomOptions(lastAllTasks, allFilterFloor, allFilterRoom);
    roomSel.classList.remove('hidden');
    roomSel.classList.toggle('active', !!allFilterRoom);
  } else {
    roomSel.classList.add('hidden');
  }
}

function onAllFilterChange() {
  const newFloor = document.getElementById('all-floor-select').value;
  if (newFloor !== allFilterFloor) {
    allFilterFloor = newFloor;
    allFilterRoom = '';
  } else {
    allFilterRoom = document.getElementById('all-room-select').value || '';
  }
  renderAllFilters();
  renderAllList();
}

function renderAllList() {
  const list = document.getElementById('all-list');
  let filtered = lastAllTasks;
  if (allFilterFloor) filtered = filtered.filter(t => t.floor === allFilterFloor);
  if (allFilterRoom) filtered = filtered.filter(t => t.room === allFilterRoom);

  if (filtered.length === 0) {
    list.innerHTML = `<div class="empty-state"><div class="icon">📋</div><div class="title">Keine Tasks</div></div>`;
    return;
  }
  list.innerHTML = filtered.map(renderTaskCard).join('');
}

function renderTaskCard(t) {
  const isDue = !t.last_completed_at || t.overdue_days > 0;
  const veryOverdue = t.overdue_days > 7;
  const cls = !isDue ? 'not-due' : veryOverdue ? 'very-overdue' : (t.overdue_days > 0 ? 'overdue' : '');
  const freqClass = `freq-${t.frequency}`;
  const freqLabel = { weekly: 'Woche', monthly: 'Monat', yearly: 'Jahr' }[t.frequency] || t.frequency;

  let statusBadge = '';
  if (!isDue) {
    // Berechne wann fällig: last_completed_at + Periode - jetzt
    const freqDays = { weekly: 7, monthly: 30, yearly: 365 }[t.frequency] || 7;
    const last = new Date(t.last_completed_at + (t.last_completed_at.endsWith('Z') ? '' : 'Z'));
    const dueIn = Math.ceil((last.getTime() + freqDays*86400000 - Date.now()) / 86400000);
    statusBadge = `<span class="next-badge">fällig in ${dueIn} T</span>`;
  }
  return `
    <div class="task-card ${cls}" data-task-id="${t.id}">
      <div class="overdue-stripe"></div>
      <div class="task-checkbox" onclick="completeTask(${t.id}, event)" role="button" aria-label="Erledigen">✓</div>
      <div class="task-info">
        <div class="task-name">${escHtml(t.name)}</div>
        <div class="task-meta">
          <span class="task-room"><span class="icon">${t.icon}</span>${escHtml(t.room)}</span>
          <span class="freq-badge ${freqClass}">${freqLabel}</span>
          ${statusBadge}
        </div>
      </div>
      <div class="task-stats">
        <div class="task-cal">${t.calories} kcal</div>
        <div class="task-min">${t.minutes} Min</div>
      </div>
    </div>`;
}

async function completeTask(id, ev) {
  const card = document.querySelector(`.task-card[data-task-id="${id}"]`);
  const checkbox = card && card.querySelector('.task-checkbox');
  if (checkbox) checkbox.classList.add('checked');
  // Origin for confetti
  let x, y;
  if (ev && ev.touches && ev.touches[0]) { x = ev.touches[0].clientX; y = ev.touches[0].clientY; }
  else if (ev) { x = ev.clientX; y = ev.clientY; }
  celebrate(x, y);

  const result = await api(`/api/tasks/${id}/complete`, { method: 'POST' });
  if (!result) {
    if (checkbox) checkbox.classList.remove('checked');
    return;
  }
  showUndoToast(
    `+${result.calories} kcal · ${result.minutes} Min`,
    () => undoCompletion(result.last_completion_id)
  );
  const reload = () => {
    if (currentPage === 'all') loadAll(true);
    else loadToday(true);
  };
  if (card && currentPage === 'today') {
    card.classList.add('completing');
    setTimeout(reload, 350);
  } else {
    reload();
  }
}

async function undoCompletion(completionId) {
  if (!completionId) return;
  const res = await api(`/api/tasks/completions/${completionId}`, { method: 'DELETE' });
  if (res) {
    showToast('Rückgängig gemacht', '');
    if (currentPage === 'all') loadAll(true);
    else loadToday(true);
  }
}


// ===== Stats =====
async function loadStats(silent) {
  const [putz, today] = await Promise.all([
    api('/api/stats/leaderboard/putzkoenig'),
    api('/api/stats/leaderboard/today'),
  ]);
  document.getElementById('lb-putzkoenig').innerHTML = renderLb(putz);
  document.getElementById('lb-today').innerHTML = renderLb(today);
}

function renderLb(entries) {
  if (!entries || entries.length === 0) {
    return '<div style="padding:8px 0;color:var(--text-dim);font-size:13px">Noch keine Einträge.</div>';
  }
  return entries.map((e, i) => `
    <div class="lb-entry">
      <div class="lb-rank ${i===0 ? 'first' : ''}">${i===0 ? '👑' : i+1}</div>
      <div class="lb-name ${e.is_self ? 'is-self' : ''}">${escHtml(e.username)}</div>
      <div class="lb-stats"><b>${e.calories} kcal</b>${e.completions} · ${e.minutes} Min</div>
    </div>
  `).join('');
}

// ===== Chat =====
let chatRecording = false;
let mediaRecorder = null;
let audioChunks = [];

function appendChat(role, text) {
  const log = document.getElementById('chat-log');
  const div = document.createElement('div');
  div.className = 'chat-msg msg-' + role;
  div.innerHTML = `<div class="msg-bubble">${escHtml(text)}</div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

function appendTyping() {
  const log = document.getElementById('chat-log');
  const div = document.createElement('div');
  div.className = 'chat-msg msg-bot';
  div.innerHTML = `<div class="msg-bubble"><span class="chat-typing"><span></span><span></span><span></span></span></div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

async function sendChatText() {
  const input = document.getElementById('chat-text');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  appendChat('user', text);
  const typing = appendTyping();
  const res = await api('/api/chat/text', { method: 'POST', body: { text } });
  typing.remove();
  if (res) appendChat('bot', res.answer);
}

async function toggleVoiceChat() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showToast('Mikro nur über HTTPS oder localhost verfügbar', 'error');
    return;
  }
  const btn = document.getElementById('chat-mic');
  if (chatRecording) { mediaRecorder.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      chatRecording = false;
      btn.classList.remove('recording');
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      const fd = new FormData();
      fd.append('file', blob, 'voice.webm');
      const typing = appendTyping();
      const res = await api('/api/chat/voice', { method: 'POST', body: fd });
      typing.remove();
      if (res) {
        if (res.transcript) appendChat('user', res.transcript);
        appendChat('bot', res.answer);
      }
    };
    mediaRecorder.start();
    chatRecording = true;
    btn.classList.add('recording');
  } catch (e) {
    showToast(e.name === 'NotAllowedError' ? 'Mikro-Berechtigung verweigert' : 'Mikro-Fehler', 'error');
  }
}

// ===== Confetti =====
function celebrate(originX, originY) {
  const colors = ['#2dd4bf', '#5eead4', '#fbbf24', '#f97316', '#a855f7', '#60a5fa', '#f43f5e'];
  const x = originX ?? window.innerWidth / 2;
  const y = originY ?? window.innerHeight / 3;
  for (let i = 0; i < 45; i++) {
    const p = document.createElement('div');
    p.className = 'confetti';
    const size = 6 + Math.random() * 10;
    p.style.width = size + 'px';
    p.style.height = size + 'px';
    p.style.background = colors[Math.floor(Math.random() * colors.length)];
    p.style.left = x + 'px';
    p.style.top = y + 'px';
    if (Math.random() > 0.5) p.style.borderRadius = '50%';
    const angle = Math.random() * Math.PI * 2;
    const velocity = 100 + Math.random() * 220;
    const dx = Math.cos(angle) * velocity;
    const dy = Math.sin(angle) * velocity - 100;
    p.style.setProperty('--dx', dx + 'px');
    p.style.setProperty('--dy', dy + 'px');
    p.style.setProperty('--rot', (Math.random() * 720 - 360) + 'deg');
    const dur = 1000 + Math.random() * 700;
    p.style.animationDuration = dur + 'ms';
    document.body.appendChild(p);
    setTimeout(() => p.remove(), dur + 100);
  }
}

// ===== Utility =====
function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}
function escAttr(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ===== URL Token (OIDC callback) =====
function consumeUrlToken() {
  const url = new URL(window.location.href);
  const t = url.searchParams.get('token');
  const err = url.searchParams.get('oidc_error');
  if (t) {
    token = t;
    localStorage.setItem('token', token);
    url.searchParams.delete('token');
    window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
    return true;
  }
  if (err) {
    url.searchParams.delete('oidc_error');
    window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
    showToast('OIDC-Login fehlgeschlagen: ' + err, 'error');
  }
  return false;
}

// ===== Init =====
async function init() {
  consumeUrlToken();
  try {
    const cfg = await (await fetch('/api/auth/config')).json();
    if (!cfg.registration_enabled) {
      document.querySelectorAll('[data-show-when="registration"]').forEach(el => el.classList.add('hidden'));
    }
    if (cfg.oidc_enabled) {
      document.getElementById('oidc-btn').classList.remove('hidden');
      document.getElementById('oidc-divider').classList.remove('hidden');
      if (cfg.oidc_button_label) document.getElementById('oidc-btn-label').textContent = cfg.oidc_button_label;
    }
  } catch (e) {}

  if (token) showApp();
  else document.getElementById('auth-screen').classList.add('active');
}
init();
