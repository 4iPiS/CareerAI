/* CareerAI Admin Panel — SPA. */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/* --- Безопасное экранирование --- */
const esc = (s) => String(s == null ? '' : s)
 .replace(/&/g, '&amp;')
 .replace(/</g, '&lt;')
 .replace(/>/g, '&gt;')
 .replace(/"/g, '&quot;')
 .replace(/'/g, '&#39;');

/* --- Chart.js экземпляры --- */
const chartInstances = {};

function destroyChart(id) {
 if (chartInstances[id]) {
 try { chartInstances[id].destroy(); } catch (_) {}
 delete chartInstances[id];
 }
}

/* --- Реестр активных setInterval --- */
const activeIntervals = new Set();

function registerInterval(id) {
 activeIntervals.add(id);
 return id;
}

function clearAllIntervals() {
 activeIntervals.forEach((id) => clearInterval(id));
 activeIntervals.clear();
}

/* --- Динамический менеджер вариантов --- */
const OptionsManager = {
 container: null,
 onChange: null,

 init(containerId, initialOptions, onChange) {
 this.container = document.getElementById(containerId);
 this.onChange = onChange || null;
 this.clear();
 if (initialOptions && initialOptions.length > 0) {
 initialOptions.forEach((opt) => this.add(opt));
 } else {
 this.add('');
 }
 },

 getOptions() {
 if (!this.container) return [];
 const rows = this.container.querySelectorAll('.opt-row');
 const opts = [];
 rows.forEach((row) => {
 const input = row.querySelector('.opt-val');
 if (!input) return;
 const val = input.value.trim();
 if (val) opts.push(val);
 });
 return opts;
 },

 add(value) {
 if (!this.container) return;
 const row = document.createElement('div');
 row.className = 'opt-row';
 row.innerHTML = `
 <span class="opt-num"></span>
 <input class="opt-val" type="text" value="${esc(value || '')}" placeholder="Вариант">
 <button type="button" class="opt-del" title="Удалить"></button>`;
 row.querySelector('.opt-del').addEventListener('click', () => {
 row.remove();
 this._renumber();
 if (this.onChange) this.onChange();
 });
 row.querySelector('.opt-val').addEventListener('input', () => {
 if (this.onChange) this.onChange();
 });
 this.container.appendChild(row);
 this._renumber();
 if (this.onChange) this.onChange();
 },

 clear() {
 if (this.container) this.container.innerHTML = '';
 },

 _renumber() {
 if (!this.container) return;
 const rows = this.container.querySelectorAll('.opt-row');
 rows.forEach((row, i) => {
 const num = row.querySelector('.opt-num');
 if (num) num.textContent = i + 1;
 const input = row.querySelector('.opt-val');
 if (input) input.placeholder = 'Вариант ' + (i + 1);
 });
 },
};

function yearsLabel(n) {
 n = Number(n) || 0;
 const mod10 = n % 10, mod100 = n % 100;
 if (mod10 === 1 && mod100 !== 11) return n + ' год';
 if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return n + ' года';
 return n + ' лет';
}

let currentUser = null;

/* --- API helper (cookie-сессия) --- */
async function api(path, options = {}) {
 const opts = { ...options };
 opts.credentials = 'include';
 opts.headers = { ...(opts.headers || {}) };

 if (opts.body && typeof opts.body !== 'string' && !(opts.body instanceof FormData)) {
 opts.headers['Content-Type'] = 'application/json';
 opts.body = JSON.stringify(opts.body);
 }

 const timeout = opts.timeout || 30000;
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), timeout);
 opts.signal = controller.signal;

 let resp;
 try {
 resp = await fetch('/api/admin' + path, opts);
 } catch (e) {
 clearTimeout(timeoutId);
 if (e.name === 'AbortError') throw new Error('Таймаут запроса');
 throw e;
 }
 clearTimeout(timeoutId);

 if (resp.status === 401) {
 showLogin();
 throw new Error('Unauthorized');
 }

 const text = await resp.text();
 let data = {};
 if (text) {
 try { data = JSON.parse(text); } catch (_) { data = { raw: text }; }
 }
 if (!resp.ok) {
 let msg = data.detail || data.error || data.raw || ('HTTP ' + resp.status);
 if (msg && typeof msg === 'object') msg = Object.values(msg).join(', ');
 throw new Error(msg);
 }
 return data;
}

/* --- auth --- */
async function bootstrap() {
 try {
 const me = await api('/auth/me');
 currentUser = me;
 showShell();
 navigate('dashboard');
 } catch (_) {
 showLogin();
 }
}

function showLogin() {
 clearAllIntervals();
 Object.keys(chartInstances).forEach(destroyChart);
 const ls = document.getElementById('loginScreen');
 const ash = document.getElementById('appShell');
 if (ls) ls.classList.remove('hidden');
 if (ash) ash.classList.add('hidden');
}

function showShell() {
 const ls = document.getElementById('loginScreen');
 const ash = document.getElementById('appShell');
 if (ls) ls.classList.add('hidden');
 if (ash) ash.classList.remove('hidden');
}

$('#loginBtn').addEventListener('click', async () => {
 const username = $('#loginUsername').value.trim();
 const password = $('#loginPassword').value;
 $('#loginError').textContent = '';
 try {
 const resp = await fetch('/api/admin/auth/login', {
 method: 'POST',
 credentials: 'include',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ username, password }),
 });
 const data = await resp.json().catch(() => ({}));
 if (!resp.ok) throw new Error(data.detail || data.error || 'Ошибка входа');
 currentUser = data;
 showShell();
 navigate('dashboard');
 } catch (e) {
 $('#loginError').textContent = e.message;
 }
});

$('#loginPassword').addEventListener('keydown', (e) => {
 if (e.key === 'Enter') $('#loginBtn').click();
});

$('#logoutBtn').addEventListener('click', async () => {
 await fetch('/api/admin/auth/logout', {
 method: 'POST',
 credentials: 'include',
 }).catch(() => {});
 currentUser = null;
 showLogin();
});

/* --- router --- */
const views = ['dashboard', 'directions', 'features', 'questions', 'custom', 'media', 'settings', 'recommender', 'users', 'responses'];

let editDirectionId = null;
let editFeatureId = null;
let editQuestionId = null;
let editCustomId = null;
let editUserId = null;

function resetEditState() {
 editDirectionId = null;
 editFeatureId = null;
 editQuestionId = null;
 editCustomId = null;
 editUserId = null;
}

const renderers = {};

function content() {
 return document.getElementById('content');
}

function navigate(view) {
 if (!views.includes(view)) view = 'dashboard';

 clearAllIntervals();
 Object.keys(chartInstances).forEach(destroyChart);
 resetEditState();

 $$('.sidebar nav a').forEach((a) => a.classList.toggle('active', a.dataset.view === view));

 try {
 const result = renderers[view]();
 if (result && result.catch) {
 result.catch((e) => {
 console.error(`navigate(${view}) error:`, e);
 const el = content();
 if (el) el.innerHTML = `<div class="error-text">Ошибка загрузки: ${esc(e.message)}</div>`;
 });
 }
 } catch (e) {
 console.error(`navigate(${view}) error:`, e);
 const el = content();
 if (el) el.innerHTML = `<div class="error-text">Ошибка загрузки: ${esc(e.message)}</div>`;
 }
}

$$('.sidebar nav a').forEach((a) => a.addEventListener('click', (e) => {
 e.preventDefault();
 navigate(a.dataset.view);
}));

function setTitle(title) {
 content().innerHTML = `<div class="topbar"><h1>${esc(title)}</h1></div>`;
}

async function handleError(e) {
 if (e && e.message === 'Unauthorized') return;
 const el = content();
 if (!el.innerHTML.includes('topbar')) setTitle('Ошибка');
 const errBox = document.createElement('div');
 errBox.className = 'error-text';
 errBox.textContent = e && e.message ? e.message : String(e);
 el.appendChild(errBox);
}

/* --- медиа-хранилище: модалка выбора файла --- */
async function openMediaPicker(kind, onPick) {
 let files = [];
 try {
 const data = await api('/media');
 files = (data.files || []).filter((f) => !kind || f.kind === kind);
 } catch (_) {
 files = [];
 }
 const overlay = document.createElement('div');
 overlay.className = 'modal-overlay';
 overlay.innerHTML = `
 <div class="modal">
 <h3>Выбор файла из хранилища${kind ? ` (${esc(kind)})` : ''}</h3>
 <div class="modal-list">
 ${files.length ? files.map((f) => `
 <div class="modal-item" data-path="${esc(f.path)}">
 ${f.kind === 'image'
 ? `<img src="${esc(f.url)}" alt="">`
 : f.kind === 'video'
 ? `<video src="${esc(f.url)}" muted></video>`
 : `<div style="height:90px;display:flex;align-items:center;justify-content:center;background:#e2e8f0;border-radius:6px;"></div>`}
 <div class="fname">${esc(f.name)}</div>
 </div>`).join('')
 : '<div class="modal-empty">В хранилище нет файлов. Загрузите их в разделе «Медиатека».</div>'}
 </div>
 <div style="margin-top:14px;text-align:right">
 <button class="btn ghost" id="pickerClose">Закрыть</button>
 </div>
 </div>`;
 document.body.appendChild(overlay);
 overlay.addEventListener('click', (e) => {
 if (e.target === overlay) overlay.remove();
 });
 overlay.querySelector('#pickerClose').addEventListener('click', () => overlay.remove());
 overlay.querySelectorAll('.modal-item').forEach((item) => {
 item.addEventListener('click', () => {
 onPick(item.dataset.path);
 overlay.remove();
 });
 });
}

function mediaInput(label, id, value, kind, placeholder) {
 return `
 <div>
 <label>${esc(label)}</label>
 <div style="display:flex; gap:6px;">
 <input id="${esc(id)}" value="${esc(value || '')}" placeholder="${esc(placeholder || (kind === 'video' ? 'video/xxx.mp4' : 'image/xxxx.jpg'))}">
 <button type="button" class="pick-btn" data-pick="${esc(kind)}" data-target="${esc(id)}" title="Выбрать из хранилища"></button>
 </div>
 </div>`;
}

/* --- datasetLabel --- */
function datasetLabel(dataset) {
 if (dataset == null) return '—';
 if (typeof dataset === 'string') {
 if (dataset === 'all') return 'синтетика + реал.';
 if (dataset === 'real_only') return 'только реал.';
 if (dataset === 'synthetic') return 'синтетика';
 return dataset;
 }
 if (typeof dataset === 'object') {
 const parts = [];
 if (dataset.synthetic || dataset.use_synthetic) parts.push('синтетика');
 if (dataset.real || dataset.use_real) parts.push('реал.');
 if (parts.length) return parts.join(' + ');
 return JSON.stringify(dataset);
 }
 return String(dataset);
}

/* =========================================================
 ДАШБОРД
 ========================================================= */
async function dashboard() {
 const [stats, train, ds, recMetrics] = await Promise.all([
  api('/stats').catch(() => ({ stats: {} })),
  api('/train/status').catch(() => ({ runs: [] })),
  api('/train/dataset').catch(() => ({ synthetic: {}, real: {} })),
  api('/recommender-metrics').catch(() => ({ metrics: {} })),
 ]);

 const s = stats.stats || {};
 const syn = ds.synthetic || {};
 const real = ds.real || {};
 const runs = train.runs || [];
 const rm = recMetrics.metrics || {};

 const html = `
 <div class="topbar"><h1>Дашборд</h1></div>
  <div class="cards">
  <div class="card"><div class="num">${s.total || 0}</div><div class="lbl">Всего сессий</div></div>
  <div class="card"><div class="num">${s.completed || 0}</div><div class="lbl">Завершено</div></div>
  <div class="card"><div class="num">${s.in_progress || 0}</div><div class="lbl">В процессе</div></div>
  <div class="card"><div class="num">${s.with_profile || 0}</div><div class="lbl">С профилем</div></div>
  <div class="card"><div class="num">${s.labeled || 0}</div><div class="lbl">С метками</div></div>
  </div>
  ${_renderRecommenderMetricsCards(rm)}
  <div class="panel">
 <h2>Обучающая выборка</h2>
 <div class="muted" style="margin-bottom:10px">
 <div style="margin-bottom:6px">
 Признаков: <b>${ds.active_features ?? '—'}</b> ·
 Направлений: <b>${ds.active_directions ?? '—'}</b>
 </div>
 <div style="font-size:0.78rem; color:var(--muted)">
 При добавлении новых направлений или признаков в каталог — при следующей генерации выборки они автоматически включаются в обучение.
 </div>
 </div>
 ${runs.length ? (() => {
 const lastRun = runs[0];
 const m = lastRun.metrics || {};
 const dsText = datasetLabel(lastRun.dataset);
 return `
 <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px;margin-bottom:10px">
 <div style="font-weight:600;color:#166534;margin-bottom:4px">Последнее обучение #${esc(lastRun.id)}</div>
 <div style="font-size:.85rem;color:#166534">
 Данные: <b>${esc(dsText)}</b> · Статус: <b>${esc(lastRun.status)}</b> ·
 F1: <b>${m.macro_f1 != null ? Math.round(m.macro_f1 * 100) + '%' : '—'}</b> ·
 AUC: <b>${m.macro_auc != null ? m.macro_auc.toFixed(3) : '—'}</b>
 </div>
 </div>`;
 })() : '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;margin-bottom:10px;color:#991b1b"> Обучение ещё не проводилось</div>'}
 <div class="form-grid" style="margin-bottom:10px">
 <div>
 <label>Синтетика (по каталогу)</label>
 <div>${syn.exists
 ? (syn.rows != null
 ? `<span class="badge success">готова (${syn.rows.toLocaleString('ru')} строк)</span>`
 : '<span class="badge success">готова</span>')
 : '<span class="badge failed">не сгенерирована</span>'}</div>
 </div>
 <div>
 <label>Реальные ответы (responses.csv)</label>
 <div>${real.exists
 ? (real.rows != null
 ? `<span class="badge success">${real.rows.toLocaleString('ru')} строк</span>`
 : '<span class="badge success">загружены</span>')
 : '<span class="badge failed">нет</span>'}</div>
 <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
 <button class="btn small" id="exportDbBtn" type="button">Экспортировать из БД</button>
 <input type="file" id="realCsvFile" accept=".csv" style="flex:1; min-width:0;">
 <button class="btn small" id="uploadRealBtn" type="button">Загрузить файл</button>
 </div>
 <div id="realExportProgress" class="muted" style="font-size:.78rem; margin-top:6px; display:none;">
 <div style="display:flex;align-items:center;gap:8px;">
 <div style="flex:1;height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
 <div id="realExportBar" style="width:0%;height:100%;background:#10b981;border-radius:4px;transition:width .3s;"></div>
 </div>
 <span id="realExportText"></span>
 </div>
 </div>
 <div id="realExportMsg" class="muted" style="font-size:.78rem; margin-top:6px"></div>
 <div id="realUploadProgress" class="muted" style="font-size:.78rem; margin-top:6px; display:none;">
 <div style="display:flex;align-items:center;gap:8px;">
 <div style="flex:1;height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
 <div id="realUploadBar" style="width:0%;height:100%;background:#3b82f6;border-radius:4px;transition:width .3s;"></div>
 </div>
 <span id="realUploadText"></span>
 </div>
 </div>
 <div id="realUploadMsg" class="muted" style="font-size:.78rem; margin-top:6px"></div>
 </div>
 </div>
 <button class="btn" id="genDsBtn" type="button">Сгенерировать синтетическую выборку</button>
 ${syn.exists ? `<a class="btn" style="margin-left:8px" href="/api/admin/train/dataset/download" download>Скачать CSV</a>` : ''}
 <div id="genDsProgress" style="display:none;margin-top:12px;">
 <div style="display:flex;align-items:center;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 16px;">
 <div style="width:20px;height:20px;border:3px solid #3b82f6;border-top-color:#fff;border-radius:50%;animation:spin 1s linear infinite;flex-shrink:0;"></div>
 <div style="flex:1;">
 <div style="font-weight:600;color:#1e40af;font-size:.9rem;" id="genDsTitle">Генерация выборки…</div>
 <div style="font-size:.78rem;color:#3b82f6;" id="genDsStatus">Создание профилей…</div>
 </div>
 </div>
 <div style="margin-top:8px;display:flex;align-items:center;gap:8px;">
 <div style="flex:1;height:10px;background:#e2e8f0;border-radius:5px;overflow:hidden;">
 <div id="genDsBar" style="width:0%;height:100%;background:linear-gradient(90deg,#3b82f6,#8b5cf6);border-radius:5px;transition:width .5s ease;"></div>
 </div>
 <span style="font-size:.8rem;color:#64748b;min-width:40px;" id="genDsPercent">0%</span>
 </div>
 </div>
 <div id="dsMsg" class="muted" style="margin-top:8px"></div>
 </div>
 <div class="panel">
 <h2>Обучение модели</h2>
 <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px">
 <button class="btn" id="trainBtn" type="button">Запустить обучение</button>
 <button class="btn danger" id="trainCancelBtn" type="button" style="display:none;background:#dc2626;">Остановить</button>
 </div>
 <div style="margin:6px 0 12px">
 <label style="font-size:.85rem;color:var(--muted)">Обучение:</label>
 <select id="trainTypeSelect" style="width:100%;margin-top:4px;padding:6px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)">
 <option value="synthetic">С нуля — только синтетика</option>
 <option value="all" selected>С нуля — синтетика + реальные</option>
 <option value="real_only">С нуля — только реальные</option>
 <option value="finetune">Fine-tuning — дообучение на реальных</option>
 </select>
 </div>
 <div id="finetuneSection" style="display:none;margin:6px 0 12px">
 <label style="font-size:.85rem;color:var(--muted)">Модель для дообучения:</label>
 <select id="trainModelSelect" style="width:100%;margin-top:4px;padding:6px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)">
 <option value="">— Выберите модель —</option>
 </select>
 </div>
 <div id="trainProgress" style="display:none; margin-bottom:16px;">
 <div style="display:flex;align-items:center;gap:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 16px;">
 <div style="width:20px;height:20px;border:3px solid #3b82f6;border-top-color:#fff;border-radius:50%;animation:spin 1s linear infinite;flex-shrink:0;"></div>
 <div style="flex:1;">
 <div style="font-weight:600;color:#1e40af;font-size:.9rem;" id="trainProgressTitle">Обучение...</div>
 <div style="font-size:.78rem;color:#3b82f6;" id="trainProgressStatus">Инициализация...</div>
 </div>
 <button class="btn small ghost" id="trainDismissBtn" type="button" style="flex-shrink:0;">x</button>
 </div>
 <div style="margin-top:8px;display:flex;align-items:center;gap:8px;">
 <div style="flex:1;height:10px;background:#e2e8f0;border-radius:5px;overflow:hidden;">
 <div id="trainProgressBar" style="width:0%;height:100%;background:linear-gradient(90deg,#3b82f6,#8b5cf6);border-radius:5px;transition:width .5s ease;"></div>
 </div>
 <span style="font-size:.8rem;color:#64748b;min-width:40px;" id="trainProgressPercent">0%</span>
 </div>
 </div>
 <div id="trainMsg" class="muted" style="margin-top:8px"></div>
 <div style="margin-top:16px" id="runsTable"></div>
 </div>`;
 content().innerHTML = html;

 renderRunsTable(runs);
 checkRunningTraining();
 loadModelSelect();

 /* --- кнопки --- */
 $('#genDsBtn').addEventListener('click', async () => {
 const msg = $('#dsMsg');
 const prog = $('#genDsProgress');
 const bar = $('#genDsBar');
 const pct = $('#genDsPercent');
 const status = $('#genDsStatus');
 msg.textContent = '';
 prog.style.display = 'block';
 bar.style.width = '0%';
 pct.textContent = '0%';
 status.textContent = 'Запуск генерации…';

 let done = false;
 let consecutiveErrors = 0;
 const MAX_CONSECUTIVE_ERRORS = 15;
 let lastStep = 0;
 let prevPercent = 0;

 const poll = async () => {
 if (done) return;
 try {
 const res = await fetch('/api/admin/train/dataset/progress');
 const data = await res.json();
 consecutiveErrors = 0;

 const step = data.step || 0;
 const total = data.total || 10;
 const rows = data.rows || 0;
 const percent = data.progress ?? Math.min(100, Math.round((step / total) * 100));

 // Не откатываем прогресс назад — запоминаем максимум
 if (percent > prevPercent) {
 prevPercent = percent;
 }
 bar.style.width = prevPercent + '%';
 pct.textContent = prevPercent + '%';

 // Не сбрасываем статус на "Подготовка" если уже был прогресс
 if (step >= total && step > 0) {
 status.textContent = 'Готово!';
 } else if (step > 0) {
 lastStep = step;
 status.textContent = `Шаг ${step}/${total} — ${rows.toLocaleString('ru')} строк`;
 } else if (step === 0 && lastStep === 0) {
 status.textContent = 'Подготовка…';
 }

 if (step >= total && step > 0) {
 done = true;
 msg.textContent = `Готово: ${rows.toLocaleString('ru')} строк`;
 bar.style.width = '100%';
 pct.textContent = '100%';
 status.textContent = 'Готово!';
 setTimeout(async () => {
 navigate('dashboard');
 }, 1500);
 } else {
 setTimeout(poll, 1000);
 }
 } catch (e) {
 consecutiveErrors++;
 if (!done && consecutiveErrors < MAX_CONSECUTIVE_ERRORS) {
 setTimeout(poll, 1000);
 } else if (!done) {
 done = true;
 status.textContent = 'Ошибка получения прогресса';
 msg.textContent = 'Не удалось получить прогресс генерации';
 }
 }
 };

 // Запускаем polling с задержкой 2 сек — файл прогресса должен создаться
 setTimeout(poll, 2000);

 try {
 await api('/train/dataset/generate', { method: 'POST', timeout: 300000 });
 } catch (e) {
 done = true;
 prog.style.display = 'none';
 msg.textContent = e.message;
 }
 });

 /* --- загрузка CSV через XHR (реальный прогресс) --- */
 $('#uploadRealBtn').addEventListener('click', () => {
 const file = $('#realCsvFile').files[0];
 const msg = $('#realUploadMsg');
 const prog = $('#realUploadProgress');
 const bar = $('#realUploadBar');
 const txt = $('#realUploadText');
 if (!file) { msg.textContent = 'Сначала выберите responses.csv'; return; }
 msg.textContent = '';
 prog.style.display = 'block';
 bar.style.width = '10%';
 txt.textContent = 'Отправка…';

 const fd = new FormData();
 fd.append('file', file);

 const xhr = new XMLHttpRequest();
 xhr.open('POST', '/api/admin/train/dataset/upload');
 xhr.withCredentials = true;

 xhr.upload.onprogress = (ev) => {
 if (ev.lengthComputable) {
 const percent = 10 + (ev.loaded / ev.total) * 80;
 bar.style.width = percent + '%';
 txt.textContent = 'Загрузка… ' + Math.round((ev.loaded / ev.total) * 100) + '%';
 }
 };
 xhr.onload = () => {
 let data = {};
 try { data = JSON.parse(xhr.responseText); } catch (_) {}
 if (xhr.status === 401) { showLogin(); return; }
 if (xhr.status >= 200 && xhr.status < 300) {
 bar.style.width = '100%';
 txt.textContent = 'Готово!';
 msg.textContent = `Загружено: ${data.rows} строк`;
 setTimeout(() => navigate('dashboard'), 1500);
 } else {
 prog.style.display = 'none';
 msg.textContent = data.detail || data.error || ('HTTP ' + xhr.status);
 }
 };
 xhr.onerror = () => {
 prog.style.display = 'none';
 msg.textContent = 'Ошибка сети при загрузке';
 };
 xhr.send(fd);
 });

 /* --- экспорт из БД в CSV на диск --- */
 $('#exportDbBtn').addEventListener('click', async () => {
 const msg = $('#realExportMsg');
 const prog = $('#realExportProgress');
 const bar = $('#realExportBar');
 const txt = $('#realExportText');
 msg.textContent = '';
 prog.style.display = 'block';
 bar.style.width = '10%';
 txt.textContent = 'Экспорт из БД…';

 try {
 const res = await api('/responses/export-to-disk', { method: 'POST' });
 bar.style.width = '100%';
 txt.textContent = 'Готово!';
 msg.textContent = `Экспортировано: ${res.rows} строк → ${res.path}`;
 // Обновлю статус на странице
 setTimeout(() => navigate('dashboard'), 2000);
 } catch (e) {
 prog.style.display = 'none';
 msg.textContent = e.message;
 }
 });

 /* --- показать/скрыть fine-tuning секцию --- */
 $('#trainTypeSelect').addEventListener('change', () => {
 const show = $('#trainTypeSelect').value === 'finetune';
 const sec = $('#finetuneSection');
 if (sec) sec.style.display = show ? 'block' : 'none';
 if (show) loadModelSelect();
 });

 $('#trainBtn').addEventListener('click', async () => {
 const msg = $('#trainMsg');
 msg.textContent = 'Запуск…';
 try {
 const type = $('#trainTypeSelect').value;
 const isFinetune = type === 'finetune';
 const body = {
 dataset: isFinetune ? 'real_only' : type,
 model_id: isFinetune ? $('#trainModelSelect').value ? Number($('#trainModelSelect').value) : null : null,
 };
 const res = await api('/train', { method: 'POST', body });
 msg.textContent = `Запуск #${res.run_id} создан (${res.dataset}).`;

 // Явно показать кнопку «Остановить» сразу
 const cb = $('#trainCancelBtn');
 if (cb) {
 cb.style.display = 'inline-block';
 cb.textContent = `Остановить (запуск #${res.run_id})`;
 cb.disabled = false;
 }

 startTrainPolling(res.run_id);
 } catch (e) {
 msg.textContent = e.message;
 }
 });

 $('#trainCancelBtn').addEventListener('click', async () => {
 const msg = $('#trainMsg');
 const btn = $('#trainCancelBtn');
 try {
 const data = await api('/train/status');
 const running = (data.runs || []).find(r => r.status === 'running');
 if (!running) {
 msg.textContent = 'Нет запущенного обучения.';
 btn.style.display = 'none';
 return;
 }
 msg.textContent = `Остановка запуска #${running.id}…`;
 btn.disabled = true;
 await api('/train/' + running.id + '/cancel', { method: 'POST' });
 msg.textContent = `Запуск #${running.id} остановлен.`;
 btn.style.display = 'none';
 btn.disabled = false;
 setTimeout(() => navigate('dashboard'), 1500);
 } catch (e) {
 msg.textContent = e.message;
 btn.disabled = false;
 }
 });

 /* --- автообновление таблицы/графиков --- */
 let lastRunsSnapshot = JSON.stringify(runs);
 registerInterval(setInterval(async () => {
 try {
 const data = await api('/train/status');
 const newRuns = data.runs || [];
 const newSnapshot = JSON.stringify(newRuns);
 if (newSnapshot === lastRunsSnapshot) return;
 lastRunsSnapshot = newSnapshot;
 renderRunsTable(newRuns);
 renderCharts(newRuns);
 } catch (e) {
 console.warn('Обновление дашборда:', e);
 }
 }, 10000));
}

/* --- поллинг обучения --- */
let trainPollInterval = null;
let trainStartTime = null;

function stopTrainPolling() {
 if (trainPollInterval) {
 clearInterval(trainPollInterval);
 trainPollInterval = null;
 }
 trainStartTime = null;
}

function startTrainPolling(runId) {
 stopTrainPolling();
 const prog = $('#trainProgress');
 const bar = $('#trainProgressBar');
 const pct = $('#trainProgressPercent');
 const status = $('#trainProgressStatus');
 const title = $('#trainProgressTitle');
 const dismissBtn = $('#trainDismissBtn');
 const cancelBtn = $('#trainCancelBtn');
 if (!prog) return;
 prog.style.display = 'block';
 title.textContent = `Обучение #${runId}`;
 pct.style.color = '';
 trainStartTime = Date.now();

 // Показать кнопку «Остановить» сразу
 if (cancelBtn) {
 cancelBtn.style.display = 'inline-block';
 cancelBtn.textContent = `Остановить (запуск #${runId})`;
 cancelBtn.disabled = false;
 }

 // НЕ регистрируем в activeIntervals — управляем отдельно
 trainPollInterval = setInterval(async () => {
 try {
 const data = await api('/train/status');
 const list = data.runs || [];
 const currentRun = list.find(r => String(r.id) === String(runId));
 if (!currentRun) {
 stopTrainPolling();
 if (cancelBtn) cancelBtn.style.display = 'none';
 navigate('dashboard');
 return;
 }
 const st = currentRun.status;

 if (st === 'running') {
 let percent = 0;
 let epochText = '?';

 if (currentRun.total_epochs && currentRun.current_epoch != null && currentRun.current_epoch > 0) {
 percent = Math.round((currentRun.current_epoch / currentRun.total_epochs) * 100);
 percent = Math.max(0, Math.min(99, percent));
 epochText = `${currentRun.current_epoch}/${currentRun.total_epochs}`;
 } else if (currentRun.total_epochs) {
 percent = 0;
 epochText = 'ожидание…';
 } else {
 percent = 0;
 epochText = '0/?';
 }

 bar.style.width = percent + '%';
 pct.textContent = percent + '%';
 status.textContent = `Обучение… ${epochText}`;

 } else if (st === 'completed') {
 stopTrainPolling();
 if (cancelBtn) cancelBtn.style.display = 'none';
 bar.style.width = '100%';
 pct.textContent = '100%';
 status.textContent = 'Готово!';
 title.textContent = `Обучение #${runId} завершено`;
 const msg = $('#trainMsg');
 if (msg) {
 const m = currentRun.metrics || {};
 msg.textContent = `F1: ${m.macro_f1 != null ? Math.round(m.macro_f1 * 100) + '%' : '—'} · AUC: ${m.macro_auc != null ? m.macro_auc.toFixed(3) : '—'}`;
 }
 // Обновляем таблицу запусков
 try {
 const data = await api('/train/status');
 renderRunsTable(data.runs || []);
 } catch (_) {}
 setTimeout(() => navigate('dashboard'), 2000);

 } else if (st === 'failed' || st === 'error') {
 stopTrainPolling();
 if (cancelBtn) cancelBtn.style.display = 'none';
 bar.style.width = '100%';
 pct.textContent = 'Ошибка';
 pct.style.color = '#dc2626';
 status.textContent = 'Ошибка: ' + (currentRun.error_message || 'неизвестно');
 title.textContent = `Обучение #${runId} провалено`;
 // Обновляем таблицу запусков
 try {
 const data = await api('/train/status');
 renderRunsTable(data.runs || []);
 } catch (_) {}
 setTimeout(() => navigate('dashboard'), 4000);

 } else if (st === 'pending') {
 status.textContent = 'Запуск обучения…';
 bar.style.width = '0%';
 pct.textContent = '0%';
 }
 } catch (e) {
 console.warn('Poll error:', e);
 }
 }, 2000);

 if (dismissBtn) {
 dismissBtn.onclick = () => {
 // Скрываем прогресс-бар, но поллинг продолжает работать,
 // чтобы поймать completed и обновить метрики
 prog.style.display = 'none';
 };
 }
}

async function checkRunningTraining() {
 try {
 const data = await api('/train/status');
 const runs = data.runs || [];
 const running = runs.find(r => r.status === 'running');
 const btn = $('#trainCancelBtn');
 if (!btn) return;

 if (running) {
 btn.style.display = 'inline-block';
 btn.textContent = `Остановить (запуск #${running.id})`;
 startTrainPolling(running.id);
 } else {
 btn.style.display = 'none';
 }
 } catch (_) {
 /* ignore */
 }
}

async function loadModelSelect() {
 const sel = $('#trainModelSelect');
 if (!sel) return;
 try {
 const data = await api('/train/models');
 const models = data.models || [];
 sel.innerHTML = '<option value="">— Нет (обучение с нуля) —</option>';
 models.forEach(m => {
 const f1 = m.metrics?.macro_f1 != null ? Math.round(m.metrics.macro_f1 * 100) + '%' : '—';
 const opt = document.createElement('option');
 opt.value = m.id;
 opt.textContent = `#${m.id} — F1: ${f1}`;
 sel.appendChild(opt);
 });
 } catch (e) {
 console.warn('loadModelSelect error:', e);
 }
}

/* --- единый рендер таблицы запусков --- */
function renderRunsTable(runs) {
 const el = document.getElementById('runsTable');
 if (!el) return;
 if (!runs.length) {
 el.innerHTML = '<p class="muted">Обучений ещё не было.</p>';
 return;
 }
 el.innerHTML = `
 <h3 style="margin:16px 0 10px">Метрики последних запусков</h3>
 <table>
 <tr><th>ID</th><th>Статус</th><th>Данные</th><th>Top-1</th><th>Top-3</th><th>Top-5</th><th>Precision</th><th>Recall</th><th>F1</th><th>AUC</th><th>Ошибка</th></tr>
 ${runs.map(renderRunRow).join('')}
 </table>
 ${renderPerClassMetrics(runs)}`;
}

function renderRunRow(r) {
 const m = r.metrics || {};
 const top1 = m.top1_accuracy != null ? Math.round(m.top1_accuracy * 100) : null;
 const top3 = m.top3_accuracy != null ? Math.round(m.top3_accuracy * 100) : null;
 const top5 = m.top5_accuracy != null ? Math.round(m.top5_accuracy * 100) : null;
 const prec = m.macro_precision != null ? Math.round(m.macro_precision * 100) : null;
 const rec = m.macro_recall != null ? Math.round(m.macro_recall * 100) : null;
 const f1 = m.macro_f1 != null ? Math.round(m.macro_f1 * 100) : null;
 const auc = m.macro_auc != null ? m.macro_auc : null;
 const datasetText = datasetLabel(r.dataset);

 const bar = (val, good, mid) => val == null ? '—' : `
 <div style="display:flex;align-items:center;gap:6px">
 <div style="flex:1;height:16px;background:#e2e8f0;border-radius:4px;overflow:hidden">
 <div style="width:${val}%;height:100%;background:${val >= good ? '#16a34a' : val >= mid ? '#f59e0b' : '#dc2626'};border-radius:4px"></div>
 </div>
 <span style="font-size:0.8rem;min-width:35px">${val}%</span>
 </div>`;

 return `
 <tr>
 <td>#${esc(r.id)}</td>
 <td><span class="badge ${esc(r.status)}">${esc(r.status)}</span></td>
 <td class="muted">${esc(datasetText)}</td>
 <td>${bar(top1, 80, 60)}</td>
 <td>${top3 != null ? top3 + '%' : '—'}</td>
 <td>${top5 != null ? top5 + '%' : '—'}</td>
 <td>${bar(prec, 70, 50)}</td>
 <td>${bar(rec, 70, 50)}</td>
 <td>${bar(f1, 70, 50)}</td>
 <td>${auc != null ? auc.toFixed(3) : '—'}</td>
 <td class="muted">${esc(r.error_message || '')}</td>
 </tr>`;
}

function renderPerClassMetrics(runs) {
 const runsWithMetrics = runs.filter(r => r.metrics && r.metrics.per_direction && r.metrics.per_direction.length > 0);
 if (runsWithMetrics.length === 0) return '';

 const latest = runsWithMetrics[0];
 const perDir = latest.metrics.per_direction;
 return `
 <div style="margin-top:20px;padding:16px;background:#f8fafc;border-radius:8px">
 <h4 style="margin:0 0 12px;font-size:.95rem">Метрики по направлениям (запуск #${latest.id})</h4>
 <table style="width:100%;font-size:.82rem;border-collapse:collapse">
 <thead>
 <tr style="border-bottom:2px solid #e2e8f0">
 <th style="text-align:left;padding:8px">Направление</th>
 <th style="text-align:center;padding:8px">Support</th>
 <th style="text-align:center;padding:8px">Precision</th>
 <th style="text-align:center;padding:8px">Recall</th>
 <th style="text-align:center;padding:8px">F1</th>
 </tr>
 </thead>
 <tbody>
 ${perDir.map(d => `
 <tr style="border-bottom:1px solid #e2e8f0">
 <td style="padding:6px 8px">${esc(d.label)}</td>
 <td style="text-align:center;padding:6px 8px">${esc(d.support)}</td>
 <td style="text-align:center;padding:6px 8px">${d.precision != null ? (d.precision * 100).toFixed(1) + '%' : '—'}</td>
 <td style="text-align:center;padding:6px 8px">${d.recall != null ? (d.recall * 100).toFixed(1) + '%' : '—'}</td>
 <td style="text-align:center;padding:6px 8px">${d.f1 != null ? (d.f1 * 100).toFixed(1) + '%' : '—'}</td>
 </tr>
 `).join('')}
 </tbody>
 </table>
 </div>`;
}

/* --- единый рендер графиков --- */
function renderCharts(runs) {
 const container = document.getElementById('chartsSection');
 if (!container) return;

 ['statusDoughnutChart'].forEach(destroyChart);

 const runsWithMetrics = runs.filter(r => r.metrics);
 if (runsWithMetrics.length === 0) {
 container.innerHTML = '';
 return;
 }

 const latest = runsWithMetrics[0];
 const m = latest.metrics || {};
 const perDirection = Array.isArray(m.per_direction) ? m.per_direction : [];
 const topDirections = Array.isArray(latest.top_directions_by_f1) ? latest.top_directions_by_f1 : [];

 let html = '';

 if (perDirection.length > 0) {
 html += `
 <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:16px">
 <h4 style="margin:0 0 12px;font-size:.95rem">Метрики по направлениям (запуск #${esc(latest.id)})</h4>
 <div style="overflow-x:auto">
 <table style="width:100%;font-size:.82rem">
 <tr><th>Направление</th><th>Support</th><th>Precision</th><th>Recall</th><th>F1</th></tr>
 ${perDirection.map(d => `
 <tr>
 <td>${esc(d.label)}</td>
 <td>${esc(d.support)}</td>
 <td>${d.precision != null ? (d.precision * 100).toFixed(1) + '%' : '—'}</td>
 <td>${d.recall != null ? (d.recall * 100).toFixed(1) + '%' : '—'}</td>
 <td>${d.f1 != null ? (d.f1 * 100).toFixed(1) + '%' : '—'}</td>
 </tr>
 `).join('')}
 </table>
 </div>
 </div>`;
 }

 if (topDirections.length > 0) {
 html += `
 <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-bottom:16px">
 <h4 style="margin:0 0 12px;font-size:.95rem">Топ направлений по F1 (запуск #${esc(latest.id)})</h4>
 <div style="display:flex;flex-direction:column;gap:6px">
 ${topDirections.slice(0, 10).map(d => {
 const f1v = Math.round((d.f1 || 0) * 100);
 return `
 <div style="display:flex;align-items:center;gap:8px">
 <div style="flex:1;font-size:.85rem">${esc(d.label)}</div>
 <div style="width:160px;height:14px;background:#e2e8f0;border-radius:4px;overflow:hidden">
 <div style="width:${f1v}%;height:100%;background:#16a34a;border-radius:4px"></div>
 </div>
 <div style="min-width:45px;text-align:right;font-size:.82rem">${f1v}%</div>
 </div>`;
 }).join('')}
 </div>
 </div>`;
 }

 const statusCounts = {};
 runs.forEach(r => { statusCounts[r.status] = (statusCounts[r.status] || 0) + 1; });

 html += `
 <div style="display:flex;gap:16px;flex-wrap:wrap">
 <div style="flex:1;min-width:260px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px">
 <h4 style="margin:0 0 12px;font-size:.95rem">Статусы запусков</h4>
 <canvas id="statusDoughnutChart" style="max-width:260px;margin:0 auto"></canvas>
 </div>
 </div>`;

 container.innerHTML = html;

 const statusColors = {
 completed: '#16a34a',
 running: '#3b82f6',
 failed: '#dc2626',
 pending: '#94a3b8',
 error: '#f59e0b',
 };
 const doughnutCanvas = document.getElementById('statusDoughnutChart');
 if (doughnutCanvas && typeof Chart !== 'undefined') {
 chartInstances['statusDoughnutChart'] = new Chart(doughnutCanvas, {
 type: 'doughnut',
 data: {
 labels: Object.keys(statusCounts).map(s => s.charAt(0).toUpperCase() + s.slice(1)),
 datasets: [{
 data: Object.values(statusCounts),
 backgroundColor: Object.keys(statusCounts).map(s => statusColors[s] || '#64748b'),
 borderWidth: 2,
 borderColor: '#fff',
 }],
 },
 options: {
 responsive: true,
 plugins: {
 legend: { position: 'bottom' },
 tooltip: { callbacks: { label: (ctx) => ctx.label + ': ' + ctx.raw } },
 },
 },
 });
 }
}

/* =========================================================
 НАПРАВЛЕНИЯ
 ========================================================= */
async function directions() {
 const data = await api('/directions').catch(handleError);
 const dirs = (data && data.directions) || [];
 content().innerHTML = `
 <div class="topbar"><h1>Направления</h1></div>
 <div class="panel">
 <h2>${editDirectionId ? 'Редактирование направления' : 'Новое направление'}</h2>
 <div class="form-grid">
 <div><label>Название</label><input id="dName"></div>
 <div><label>Код ФГОС</label><input id="dCode"></div>
 <div><label>Категория</label><input id="dCat"></div>
 <div><label>Срок обучения</label><input id="dYears" type="number" placeholder="4"></div>
 <div><label>ЕГЭ (через запятую)</label><input id="dEge"></div>
 <div><label>Сортировка</label><input id="dOrder" type="number" placeholder="0"></div>
 </div>
 <details style="margin-top:12px">
 <summary style="cursor:pointer; color:#64748b; font-size:.9rem;">Расширенные поля</summary>
 <div class="form-grid" style="margin-top:10px">
 <div><label>Описание</label><textarea id="dDesc" rows="3"></textarea></div>
 <div><label>Ключевые навыки (текст)</label><textarea id="dSkillsText" rows="3"></textarea></div>
 <div><label>Коды навыков (через запятую)</label><input id="dSkills"></div>
 <div>
 <label>Изображение</label>
 <div style="display:flex; gap:8px">
 <input id="dImage" readonly placeholder="image/xxxx.jpg">
 <button type="button" class="btn small" data-pick="image" data-target="dImage"></button>
 </div>
 <div class="muted" style="font-size:.75rem">Показывается рядом с названием в результатах. Можно не выбирать.</div>
 </div>
 <div><label>Средняя зарплата выпускников, ₽</label><input id="dSalary" type="number" placeholder="0"></div>
 <div><label>Трудоустройство, %</label><input id="dEmp" type="number" placeholder="0"></div>
 </div>
 </details>
 <div style="margin-top:8px"><input type="checkbox" id="dActive" checked style="width:16px;height:16px;margin:0;padding:0"> Активно (показывается в рекомендациях)</div>
 <div style="margin-top:10px;display:flex;gap:8px">
 <button class="btn" id="dSave">Сохранить</button>
 <button class="btn ghost" id="dCancel">Отмена</button>
 </div>
 </div>
 <div class="panel"><table>
 <tr><th>Название</th><th>Код</th><th>Категория</th><th>Срок</th><th>ЕГЭ</th><th>Активн.</th><th></th></tr>
 ${dirs.map((d) => `
 <tr>
 <td>${esc(d.name)}</td>
 <td>${esc(d.fgos_code)}</td>
 <td class="muted">${esc(d.category || '—')}</td>
 <td>${yearsLabel(d.study_years || 4)}</td>
 <td class="muted" style="font-size:0.78rem">${esc(d.ege_typical || '—')}</td>
 <td>${d.is_active ? 'да' : 'нет'}</td>
 <td><div class="row-actions">
 <button class="btn small" data-edit-dir="${esc(d.id)}">Ред.</button>
 <button class="btn small danger" data-del-dir="${esc(d.id)}">Удал.</button>
 </div></td>
 </tr>`).join('')}
 </table></div>`;
 fillDirectionForm(editDirectionId, dirs);

 $('#dSave').addEventListener('click', saveDirection);
 $('#dCancel').addEventListener('click', () => { editDirectionId = null; directions(); });

 $$('[data-pick]').forEach((b) => b.addEventListener('click', () => {
 openMediaPicker(b.dataset.pick, (p) => {
 const target = document.getElementById(b.dataset.target);
 if (target) target.value = p;
 });
 }));

 $$('[data-edit-dir]').forEach((b) => b.addEventListener('click', () => {
 editDirectionId = Number(b.dataset.editDir);
 directions();
 }));
 $$('[data-del-dir]').forEach((b) => b.addEventListener('click', async () => {
 if (!confirm('Удалить направление?')) return;
 try { await api('/directions/' + b.dataset.delDir, { method: 'DELETE' }); directions(); }
 catch (e) { alert(e.message); }
 }));
}

function fillDirectionForm(id, dirs) {
 const d = dirs.find((x) => x.id === id);
 if (!d) return;
 $('#dName').value = d.name || '';
 $('#dCode').value = d.fgos_code || '';
 $('#dCat').value = d.category || '';
 $('#dSalary').value = d.avg_salary || 0;
 $('#dEmp').value = d.employment_rate || 0;
 $('#dYears').value = d.study_years || 4;
 $('#dEge').value = d.ege_typical || '';
 $('#dOrder').value = d.sort_order || 0;
 $('#dDesc').value = d.description || '';
 $('#dSkillsText').value = d.key_skills_text || '';
 $('#dSkills').value = (d.skill_codes || []).join(', ');
 $('#dImage').value = d.image_path || '';
 $('#dActive').checked = !!d.is_active;
}

async function saveDirection() {
 const payload = {
 name: $('#dName').value.trim(),
 fgos_code: $('#dCode').value.trim(),
 category: $('#dCat').value.trim(),
 avg_salary: Number($('#dSalary').value) || 0,
 employment_rate: Number($('#dEmp').value) || 0,
 study_years: Number($('#dYears').value) || 4,
 ege_typical: $('#dEge').value.trim(),
 sort_order: Number($('#dOrder').value) || 0,
 description: $('#dDesc').value,
 key_skills_text: $('#dSkillsText').value,
 skill_codes: $('#dSkills').value.split(',').map((s) => s.trim()).filter(Boolean),
 image_path: $('#dImage').value.trim(),
 is_active: $('#dActive').checked,
 };
 try {
 if (editDirectionId) {
 await api('/directions/' + editDirectionId, { method: 'PUT', body: payload });
 } else {
 await api('/directions', { method: 'POST', body: payload });
 }
 editDirectionId = null;
 directions();
 } catch (e) { alert(e.message); }
}

/* =========================================================
 ПРИЗНАКИ
 ========================================================= */
async function features() {
 const data = await api('/features').catch(handleError);
 const items = (data && data.features) || [];
 content().innerHTML = `
 <div class="topbar"><h1>Признаки</h1></div>
 <div class="panel">
 <h2>${editFeatureId ? 'Редактирование' : 'Новый признак'}</h2>
 <div class="form-grid">
 <div><label>Код</label><input id="fCode"></div>
 <div><label>Название</label><input id="fLabel"></div>
 <div><label>Тип</label><select id="fType">
 <option value="rating_1_5">Оценка 1–5</option>
 <option value="salary">Зарплата</option>
 <option value="number">Число</option>
 <option value="text">Текст</option>
 </select></div>
 <div><label>По умолчанию</label><input id="fDefault" value="3.0"></div>
 <div><label>Порядок</label><input id="fOrder" type="number" value="0"></div>
 </div>
 <div style="display:flex; gap:24px; margin-top:8px;">
 <label style="display:flex; align-items:center; gap:6px;"><input type="checkbox" id="fCommon"> Общее качество</label>
 <label style="display:flex; align-items:center; gap:6px;"><input type="checkbox" id="fActive" checked> Активно</label>
 </div>
 <div style="margin-top:10px;display:flex;gap:8px">
 <button class="btn" id="fSave">Сохранить</button>
 <button class="btn ghost" id="fCancel">Отмена</button>
 </div>
 </div>
 <div class="panel"><table>
 <tr><th>Код</th><th>Название</th><th>Тип</th><th>По умолч.</th><th>Активн.</th><th></th></tr>
 ${items.map((f) => `
 <tr>
 <td>${esc(f.code)}</td><td>${esc(f.label)}</td>
 <td>${esc(f.data_type)}</td><td>${esc(f.default_value)}</td>
 <td>${f.is_active ? 'да' : 'нет'}</td>
 <td><div class="row-actions">
 <button class="btn small" data-edit-feat="${esc(f.id)}"></button>
 <button class="btn small danger" data-del-feat="${esc(f.id)}"></button>
 </div></td>
 </tr>`).join('')}
 </table></div>`;
 fillFeatureForm(editFeatureId, items);

 $('#fSave').addEventListener('click', saveFeature);
 $('#fCancel').addEventListener('click', () => { editFeatureId = null; features(); });
 $$('[data-edit-feat]').forEach((b) => b.addEventListener('click', () => {
 editFeatureId = Number(b.dataset.editFeat);
 features();
 }));
 $$('[data-del-feat]').forEach((b) => b.addEventListener('click', async () => {
 if (!confirm('Удалить признак?')) return;
 try { await api('/features/' + b.dataset.delFeat, { method: 'DELETE' }); features(); }
 catch (e) { alert(e.message); }
 }));
}

function fillFeatureForm(id, items) {
 const f = items.find((x) => x.id === id);
 if (!f) return;
 $('#fCode').value = f.code || '';
 $('#fLabel').value = f.label || '';
 $('#fType').value = f.data_type || 'rating_1_5';
 $('#fDefault').value = f.default_value ?? '';
 $('#fOrder').value = f.sort_order || 0;
 $('#fCommon').checked = !!f.is_common;
 $('#fActive').checked = !!f.is_active;
}

async function saveFeature() {
 const payload = {
 code: $('#fCode').value.trim(),
 label: $('#fLabel').value.trim(),
 data_type: $('#fType').value,
 default_value: $('#fDefault').value,
 sort_order: Number($('#fOrder').value) || 0,
 is_common: $('#fCommon').checked,
 is_active: $('#fActive').checked,
 };
 try {
 if (editFeatureId) {
 await api('/features/' + editFeatureId, { method: 'PUT', body: payload });
 } else {
 await api('/features', { method: 'POST', body: payload });
 }
 editFeatureId = null;
 features();
 } catch (e) { alert(e.message); }
}

/* =========================================================
 ВОПРОСЫ
 ========================================================= */
let questionGroup = 'all';

const QTYPE_LABELS = {
 rating_1_5: 'Оценка 1–5',
 salary: 'Зарплата',
 choice_single: 'Выбор одного',
 choice_multi: 'Выбор нескольких',
 text_input: 'Текст',
 number_input: 'Число',
};

function qActivationText(cond) {
 if (!cond) return 'всегда';
 if (cond.type === 'interest_ge') {
 return `если интерес к «${esc(cond.feature || '?')}» ≥ ${esc(cond.value)}`;
 }
 if (cond.type === 'any_interest_ge') {
 return `если интерес к одному из [${(cond.features || []).map(esc).join(', ')}] ≥ ${esc(cond.value)}`;
 }
 return esc(JSON.stringify(cond));
}

async function questions() {
 const groupsData = await api('/question-groups').catch(handleError);
 const qsData = await api('/questions' + (questionGroup && questionGroup !== 'all' ? '?group=' + encodeURIComponent(questionGroup) : '')).catch(handleError);
 const featuresData = await api('/features').catch(() => ({ features: [] }));
 const groups = (groupsData && groupsData.groups) || [];
 const items = (qsData && qsData.questions) || [];
 const featOpts = ((featuresData && featuresData.features) || [])
 .map((f) => `<option value="${esc(f.code)}">${esc(f.code)} — ${esc(f.label)}</option>`).join('');

 content().innerHTML = `
 <div class="topbar">
 <h1>Вопросы</h1>
 <div style="display:flex; gap:6px; flex-wrap:wrap;">
 <button class="btn small ${questionGroup === 'all' ? 'active' : 'ghost'}" data-qgroup="all">Все</button>
 ${groups.map((g) => `
 <button class="btn small ${questionGroup === g.code ? 'active' : 'ghost'}" data-qgroup="${esc(g.code)}">${esc(g.title)}</button>`).join('')}
 </div>
 </div>
 <div class="panel" style="background:rgba(255,255,255,0.03);">
 <b style="color:#e2e8f0">Как устроены вопросы</b>
 <ul class="muted" style="margin:8px 0 0; padding-left:18px; line-height:1.7;">
 <li><b>Группа</b> — этап опроса: Интересы → Углублённо → Личные качества → Зарплата → ЕГЭ.</li>
 <li><b>Порог (ветвление)</b> — минимальная оценка на предыдущем вопросе, при которой задаётся следующий (0 = цепочка прервана).</li>
 <li><b>Уровень</b> — сложность: 0 базовый, 1 средний, 2 продвинутый.</li>
 <li><b>Показывать если</b> — минимальный интерес к признаку, при котором эта цепочка показывается (0 = всегда).</li>
 <li>Самообучение модели использует только <b>признаки</b> и <b>направления</b>; тексты вопросов — для абитуриента.</li>
 </ul>
 </div>
 <div class="panel">
 <h2>${editQuestionId ? 'Редактирование' : 'Новый вопрос'}</h2>
 <div class="form-grid">
 <div><label>Группа</label><select id="qGroup"><option value="">— выберите —</option>${groups.map((g) => `<option value="${esc(g.code)}">${esc(g.title)}</option>`).join('')}</select></div>
 <div><label>Текст вопроса</label><textarea id="qText" style="min-height:60px"></textarea></div>
 ${mediaInput('Картинка к вопросу', 'qImageUrl', '', 'image', 'image/xxx.jpg')}
 <div><label>Признак</label><select id="qFeature"><option value="">—</option>${featOpts}</select></div>
 <div><label>Тип</label><select id="qType">
 <option value="rating_1_5">Оценка 1–5</option>
 <option value="salary">Зарплата</option>
 <option value="choice_single">Выбор одного</option>
 <option value="choice_multi">Выбор нескольких</option>
 <option value="text_input">Текст</option>
 <option value="number_input">Число</option>
 </select></div>
 <div><label>Порог (ветвление)</label><input id="qThreshold" type="number" step="1" placeholder="напр. 3"></div>
 <div><label>Уровень (0/1/2)</label><input id="qLevel" type="number" value="0"></div>
 <div><label>Порядок</label><input id="qOrder" type="number" value="0"></div>
 </div>
 <div id="qOptionsSection" class="form-grid" style="display:none">
 <div>
 <label>Варианты ответа</label>
 <div id="qOptionsContainer" style="display:flex;flex-direction:column;gap:4px;margin-bottom:6px;max-height:200px;overflow-y:auto;"></div>
 <button type="button" class="btn small" id="qAddOpt">+ Добавить вариант</button>
 </div>
 <div><label>Показывать если интерес к признаку ≥</label><input id="qActivation" type="number" step="0.1" placeholder="напр. 3"></div>
 </div>
 <div style="display:flex; gap:24px; margin-top:8px;">
 <label style="display:flex; align-items:center; gap:6px;"><input type="checkbox" id="qActive" checked> Активно</label>
 </div>
 <div style="margin-top:10px;display:flex;gap:8px">
 <button class="btn" id="qSave">Сохранить</button>
 <button class="btn ghost" id="qCancel">Отмена</button>
 </div>
 </div>
 <div class="panel"><table>
 <tr><th>Группа</th><th>Текст вопроса</th><th>Признак</th><th>Тип</th><th>Порог</th><th>Уровень</th><th>Показывается</th><th></th></tr>
 ${items.map((q) => `
 <tr>
 <td>${esc(q.group_code)}</td>
 <td style="min-width:200px">
 <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px">
 <input type="checkbox" class="q-active-toggle" data-id="${esc(q.id)}" ${q.is_active ? 'checked' : ''} style="width:16px;height:16px;cursor:pointer;flex-shrink:0" title="Активно">
 <span>${esc(q.text.slice(0, 80))}${q.text.length > 80 ? '…' : ''}</span>
 </div>
 <div style="font-size:0.75rem;color:var(--muted);margin-left:22px">Порог: ${esc(q.threshold ?? '—')} | Уровень: ${esc(q.level)} | ${qActivationText(q.activation_condition)}</div>
 </td>
 <td>${esc(q.feature_code || '—')}</td>
 <td>${esc(QTYPE_LABELS[q.question_type] || q.question_type)}</td>
 <td>${esc(q.threshold ?? '—')}</td>
 <td>${esc(q.level)}</td>
 <td class="muted" style="font-size:0.78rem">${qActivationText(q.activation_condition)}</td>
 <td><div class="row-actions">
 <button class="btn small" data-edit-q="${esc(q.id)}">Ред.</button>
 <button class="btn small danger" data-del-q="${esc(q.id)}">Удал.</button>
 </div></td>
 </tr>`).join('')}
 </table></div>`;

 fillQuestionForm(editQuestionId, items);

 let qOptionsCache = [];
 $('#qType').addEventListener('change', () => {
 const isChoice = ['choice_single', 'choice_multi'].includes($('#qType').value);
 if (!isChoice) qOptionsCache = OptionsManager.getOptions();
 $('#qOptionsSection').style.display = isChoice ? '' : 'none';
 if (isChoice) OptionsManager.init('qOptionsContainer', qOptionsCache, () => {});
 });

 $('#qAddOpt').addEventListener('click', () => OptionsManager.add(''));

 $$('[data-qgroup]').forEach((b) => b.addEventListener('click', () => {
 questionGroup = b.dataset.qgroup;
 editQuestionId = null;
 questions();
 }));
 $$('[data-pick]').forEach((b) => b.addEventListener('click', () => {
 openMediaPicker(b.dataset.pick, (p) => {
 const target = document.getElementById(b.dataset.target);
 if (target) target.value = p;
 });
 }));
 /* --- валидация группы --- */
 const origSave = saveQuestion;
 window.saveQuestion = async function() {
 if (!$('#qGroup').value) {
 alert('Выберите группу вопроса');
 return;
 }
 return origSave();
 };
 /* --- привязка кнопки сохранения к обёрнутой функции --- */
 $('#qSave').onclick = window.saveQuestion;
 $('#qCancel').addEventListener('click', () => { editQuestionId = null; questions(); });
 $$('[data-edit-q]').forEach((b) => b.addEventListener('click', () => {
 editQuestionId = Number(b.dataset.editQ);
 questions();
 }));
 $$('[data-del-q]').forEach((b) => b.addEventListener('click', async () => {
 if (!confirm('Удалить вопрос?')) return;
 try { await api('/questions/' + b.dataset.delQ, { method: 'DELETE' }); questions(); }
 catch (e) { alert(e.message); }
 }));
 $$('.q-active-toggle').forEach((cb) => cb.addEventListener('change', async () => {
 try {
 await api('/questions/' + cb.dataset.id + '/toggle-active', { method: 'PATCH', body: { is_active: cb.checked } });
 } catch (e) {
 alert(e.message);
 cb.checked = !cb.checked;
 }
 }));
}

function fillQuestionForm(id, items) {
 const q = items.find((x) => x.id === id);
 if (!q) return;
 $('#qText').value = q.text || '';
 $('#qGroup').value = q.group_code || '';
 $('#qFeature').value = q.feature_code || '';
 $('#qType').value = q.question_type || 'rating_1_5';
 $('#qThreshold').value = q.threshold == null ? '' : q.threshold;
 $('#qLevel').value = q.level || 0;
 $('#qOrder').value = q.sort_order || 0;
 $('#qActivation').value = q.activation_condition ? (q.activation_condition.value || '') : '';
 $('#qActive').checked = !!q.is_active;
 $('#qImageUrl').value = q.image_url || '';

 const isChoice = ['choice_single', 'choice_multi'].includes(q.question_type);
 $('#qOptionsSection').style.display = isChoice ? '' : 'none';
 if (isChoice) OptionsManager.init('qOptionsContainer', q.options || [], () => {});
}

async function saveQuestion() {
 const isChoice = ['choice_single', 'choice_multi'].includes($('#qType').value);
 const options = isChoice ? OptionsManager.getOptions() : null;
 const activationValue = $('#qActivation').value.trim() ? Number($('#qActivation').value) : null;
 const activation = activationValue != null
 ? { type: 'interest_ge', feature: $('#qFeature').value || '', value: activationValue }
 : null;
 const payload = {
 group_code: $('#qGroup').value,
 feature_code: $('#qFeature').value || null,
 text: $('#qText').value.trim(),
 image_url: $('#qImageUrl').value.trim() || null,
 question_type: $('#qType').value,
 options,
 threshold: $('#qThreshold').value === '' ? null : Number($('#qThreshold').value),
 level: Number($('#qLevel').value) || 0,
 activation_condition: activation,
 sort_order: Number($('#qOrder').value) || 0,
 is_active: $('#qActive').checked,
 };
 try {
 if (editQuestionId) {
 await api('/questions/' + editQuestionId, { method: 'PUT', body: payload });
 } else {
 await api('/questions', { method: 'POST', body: payload });
 }
 editQuestionId = null;
 questions();
 } catch (e) { alert(e.message); }
}

/* =========================================================
 АНКЕТА ВУЗА
 ========================================================= */
async function custom() {
 const data = await api('/custom-fields').catch(handleError);
 const items = (data && data.fields) || [];
 content().innerHTML = `
 <div class="topbar"><h1>Анкета вуза</h1></div>
 <p class="muted" style="margin-bottom:16px;">
 Анкета показывается абитуриенту по умолчанию сразу после кнопки «Начать опрос»
 (позицию можно сменить в «Настройках»). Ответы сохраняются по каждой сессии в разделе
 «Ответы» и в CSV-экспорте (колонка custom_data) — вуз может использовать их для связи
 с абитуриентом. В обучение модели эти поля не попадают.
 </p>
 <div class="panel">
 <h2>${editCustomId ? 'Редактирование' : 'Новое поле анкеты'}</h2>
 <div class="form-grid">
 <div><label>Код</label><input id="cCode"></div>
 <div><label>Подпись</label><input id="cLabel"></div>
 <div><label>Тип</label><select id="cType">
 <option value="text">Текст</option>
 <option value="email">Email</option>
 <option value="phone">Телефон</option>
 <option value="select">Выбор</option>
 <option value="checkbox">Чекбокс</option>
 <option value="date">Дата</option>
 <option value="number">Число</option>
 </select></div>
 <div><label>Порядок</label><input id="cOrder" type="number" value="0"></div>
 </div>
 <div id="cOptionsSection" class="form-grid" style="display:none">
 <div>
 <label>Варианты</label>
 <div id="cOptionsContainer" style="display:flex;flex-direction:column;gap:4px;margin-bottom:6px;max-height:200px;overflow-y:auto;"></div>
 <button type="button" class="btn small" id="cAddOpt">+ Добавить вариант</button>
 </div>
 </div>
 <div style="display:flex; gap:24px; margin-top:8px;">
 <label style="display:flex; align-items:center; gap:6px;"><input type="checkbox" id="cRequired"> Обязательное</label>
 <label style="display:flex; align-items:center; gap:6px;"><input type="checkbox" id="cActive" checked> Активно</label>
 </div>
 <div style="margin-top:10px;display:flex;gap:8px">
 <button class="btn" id="cSave">Сохранить</button>
 <button class="btn ghost" id="cCancel">Отмена</button>
 </div>
 </div>
 <div class="panel"><table>
 <tr><th>Код</th><th>Подпись</th><th>Тип</th><th>Обязат.</th><th>Активн.</th><th></th></tr>
 ${items.map((f) => `
 <tr>
 <td>${esc(f.code)}</td><td>${esc(f.label)}</td>
 <td>${esc(f.field_type)}</td><td>${f.required ? 'да' : 'нет'}</td>
 <td>${f.is_active ? 'да' : 'нет'}</td>
 <td><div class="row-actions">
 <button class="btn small" data-edit-c="${esc(f.id)}">Ред.</button>
 <button class="btn small danger" data-del-c="${esc(f.id)}">Удал.</button>
 </div></td>
 </tr>`).join('')}
 </table></div>`;
 fillCustomForm(editCustomId, items);

 let cOptionsCache = [];
 $('#cType').addEventListener('change', () => {
 const isChoice = ['select', 'checkbox'].includes($('#cType').value);
 if (!isChoice) cOptionsCache = OptionsManager.getOptions();
 $('#cOptionsSection').style.display = isChoice ? '' : 'none';
 if (isChoice) OptionsManager.init('cOptionsContainer', cOptionsCache, () => {});
 });

 $('#cAddOpt').addEventListener('click', () => OptionsManager.add(''));

 $('#cSave').addEventListener('click', saveCustom);
 $('#cCancel').addEventListener('click', () => { editCustomId = null; custom(); });
 $$('[data-edit-c]').forEach((b) => b.addEventListener('click', () => {
 editCustomId = Number(b.dataset.editC);
 custom();
 }));
 $$('[data-del-c]').forEach((b) => b.addEventListener('click', async () => {
 if (!confirm('Удалить поле?')) return;
 try { await api('/custom-fields/' + b.dataset.delC, { method: 'DELETE' }); custom(); }
 catch (e) { alert(e.message); }
 }));
}

function fillCustomForm(id, items) {
 const f = items.find((x) => x.id === id);
 if (!f) return;
 $('#cCode').value = f.code || '';
 $('#cLabel').value = f.label || '';
 $('#cType').value = f.field_type || 'text';
 $('#cOrder').value = f.sort_order || 0;
 $('#cRequired').checked = !!f.required;
 $('#cActive').checked = !!f.is_active;

 const isChoice = ['select', 'checkbox'].includes(f.field_type);
 $('#cOptionsSection').style.display = isChoice ? '' : 'none';
 if (isChoice) OptionsManager.init('cOptionsContainer', f.options || [], () => {});
}

async function saveCustom() {
 const isChoice = ['select', 'checkbox'].includes($('#cType').value);
 const options = isChoice ? OptionsManager.getOptions() : null;
 const payload = {
 code: $('#cCode').value.trim(),
 label: $('#cLabel').value.trim(),
 field_type: $('#cType').value,
 options,
 required: $('#cRequired').checked,
 sort_order: Number($('#cOrder').value) || 0,
 is_active: $('#cActive').checked,
 };
 try {
 if (editCustomId) {
 await api('/custom-fields/' + editCustomId, { method: 'PUT', body: payload });
 } else {
 await api('/custom-fields', { method: 'POST', body: payload });
 }
 editCustomId = null;
 custom();
 } catch (e) { alert('Ошибка: ' + e.message); }
}

/* =========================================================
 МЕДИАТЕКА
 ========================================================= */
function renderMediaList(files) {
 const list = document.getElementById('storageList');
 if (!list) return;
 if (!files.length) {
 list.innerHTML = '<p class="muted">Пока нет загруженных файлов.</p>';
 return;
 }
 list.innerHTML = files.map((f) => `
 <div style="border:1px solid var(--border); border-radius:10px; padding:10px; display:flex; gap:12px; align-items:center;">
 ${f.kind === 'image'
 ? `<img class="preview-img" style="max-width:90px; max-height:70px;" src="${esc(f.url)}" alt="">`
 : f.kind === 'video'
 ? `<video src="${esc(f.url)}" muted style="width:120px; height:70px; object-fit:cover; border-radius:6px;"></video>`
 : `<div style="font-size:1.6rem;"></div>`}
 <div style="flex:1; min-width:0;">
 <div style="word-break:break-all; font-size:0.85rem;">${esc(f.path)}</div>
 <div class="muted" style="font-size:0.75rem;">${Math.round((f.size || 0) / 1024)} КБ</div>
 </div>
 <button class="btn small danger" data-del-media="${esc(f.path)}">Удал.</button>
 </div>`).join('');
}

async function media() {
 const filesData = await api('/media').catch(() => ({ files: [] }));
 const files = (filesData && filesData.files) || [];
 content().innerHTML = `
 <div class="topbar"><h1>Медиатека</h1></div>
 <div class="panel">
 <h2>Загрузка файла</h2>
 <div class="form-grid">
 <div><label>Тип</label><select id="mKind">
 <option value="image">Изображение</option>
 <option value="video">Видео</option>
 <option value="audio">Аудио</option>
 </select></div>
 <div><label>Файл</label><input type="file" id="mFile"></div>
 </div>
 <button class="btn" id="mUpload">Загрузить</button>
 <div id="mResult" style="margin-top:12px"></div>
 </div>
 <div class="panel">
 <h2>Хранилище (${files.length})</h2>
 <div id="storageList" style="display:flex; flex-direction:column; gap:10px;"></div>
 </div>
 <div class="panel">
 <h2>Как использовать</h2>
 <p class="muted">Кнопка «выбрать из хранилища» есть в «Настройках» (логотип, фон, видео) и в редакторе направлений (картинка) — путь подставится сам.</p>
 </div>`;
 renderMediaList(files);

 $('#mUpload').addEventListener('click', () => {
 const file = $('#mFile').files[0];
 if (!file) return alert('Выберите файл');
 const kind = $('#mKind').value;
 const fd = new FormData();
 fd.append('file', file);

 const xhr = new XMLHttpRequest();
 xhr.open('POST', '/api/admin/media/upload/' + encodeURIComponent(kind));
 xhr.withCredentials = true;
 xhr.onload = () => {
 let data = {};
 try { data = JSON.parse(xhr.responseText); } catch (_) {}
 if (xhr.status === 401) { showLogin(); return; }
 if (xhr.status >= 200 && xhr.status < 300) {
 $('#mResult').innerHTML = `
 <div class="url-chip">${esc(data.path)}</div>
 ${kind === 'image' ? `<div style="margin-top:8px"><img class="preview-img" src="/media/${esc(data.path)}" alt="preview"></div>` : ''}`;
 media();
 } else {
 alert(data.error || data.detail || 'Ошибка загрузки');
 }
 };
 xhr.onerror = () => alert('Ошибка сети при загрузке');
 xhr.send(fd);
 });

 $$('[data-del-media]').forEach((b) => b.addEventListener('click', async () => {
 if (!confirm('Удалить файл из хранилища?')) return;
 try {
 await api('/media/' + b.dataset.delMedia, { method: 'DELETE' });
 media();
 } catch (e) { alert(e.message); }
 }));
}

/* =========================================================
 НАСТРОЙКИ
 ========================================================= */
async function settings() {
 const data = await api('/settings').catch(handleError);
 const s = (data && data.settings) || {};
 content().innerHTML = `
 <div class="topbar"><h1>Настройки</h1></div>
 <div class="panel">
 <h2>Логотип и название университета</h2>
 <div class="form-grid">
 <div>
 <label>Название университета (впишите вручную — показывается на стартовой странице)</label>
 <input id="sName" value="${esc(s.university_name || '')}" placeholder="Например, Государственный университет «Дубна»">
 </div>
 ${mediaInput('Логотип', 'sLogo', s.logo_path, 'image')}
 ${mediaInput('Фон (растягивается на весь экран)', 'sHero', s.hero_image_path, 'image')}
 </div>
 <h2 style="margin-top:16px">Основное</h2>
 <div class="form-grid">
 <div><label>Сайт</label><input id="sUrl" value="${esc(s.university_url || '')}"></div>
 <div><label>Страница абитуриента</label><input id="sAbitur" value="${esc(s.abitur_url || '')}"></div>
 <div><label>Слоган</label><input id="sTagline" value="${esc(s.tagline || '')}"></div>
 <div>
 <label>Основной цвет</label>
 <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
 <input id="sColor" type="color" value="${esc(s.primary_color || '#667eea')}" style="width:50px;height:36px;padding:2px;">
 <input id="sColorAlpha" type="range" min="0" max="100" value="${Math.round((s.primary_alpha || 1) * 100)}" style="flex:1;">
 <span id="sColorAlphaLabel" style="min-width:35px;font-size:.85rem;color:var(--muted)">${Math.round((s.primary_alpha || 1) * 100)}%</span>
 <div id="sColorPreview" style="width:50px;height:36px;border-radius:6px;border:1px solid var(--border);background:${esc(s.primary_color || '#667eea')}"></div>
 </div>
 </div>
 </div>
 <h2 style="margin-top:16px">Медиа — выберите файл кнопкой «Выбрать» из хранилища</h2>
 <div class="form-grid">
 ${mediaInput('Видео (презентация вуза)', 'sVideo', s.presenter_video_path, 'video')}
 </div>
 <div class="form-grid">
 <div><label>Текст согласия на обработку ПДн (152-ФЗ)</label><textarea id="sConsent">${esc(s.consent_text || '')}</textarea></div>
 <div><label>Позиция анкеты вуза</label><select id="sFormPos">
 <option value="start" ${(s.custom_form_position || 'start') === 'start' ? 'selected' : ''}>В начале опроса (после «Начать опрос»)</option>
 <option value="end" ${(s.custom_form_position || 'start') === 'end' ? 'selected' : ''}>В конце опроса (перед рекомендациями)</option>
 </select></div>
 </div>
 <p class="muted">
 Текст согласия показывается абитуриенту вместе с анкетой (обязательный чекбокс перед отправкой
 персональных данных). Пустое значение = стандартный текст по 152-ФЗ.
 </p>
 <button class="btn" id="sSave" style="margin-top:10px;">Сохранить</button>
 </div>`;

 $$('[data-pick]').forEach((b) => b.addEventListener('click', () => {
 openMediaPicker(b.dataset.pick, (p) => {
 const target = document.getElementById(b.dataset.target);
 if (target) target.value = p;
 });
 }));

 /* --- прозрачность цвета --- */
 const colorInput = document.getElementById('sColor');
 const alphaInput = document.getElementById('sColorAlpha');
 const alphaLabel = document.getElementById('sColorAlphaLabel');
 const colorPreview = document.getElementById('sColorPreview');
 if (alphaInput && alphaLabel) {
 alphaInput.addEventListener('input', () => {
 alphaLabel.textContent = alphaInput.value + '%';
 updateColorPreview();
 });
 }
 if (colorInput) {
 colorInput.addEventListener('input', updateColorPreview);
 }
 function updateColorPreview() {
 if (!colorPreview || !colorInput || !alphaInput) return;
 let hex = colorInput.value;
 const alpha = parseInt(alphaInput.value) / 100;
 const r = hex.slice(1, 3);
 const g = hex.slice(3, 5);
 const b = hex.slice(5, 7);
 if (alpha >= 0.99) {
 colorPreview.style.background = hex;
 } else {
 colorPreview.style.background = `rgba(${parseInt(r,16)},${parseInt(g,16)},${parseInt(b,16)},${alpha})`;
 }
 }
 /* Инициализация превью с учётом сохранённого alpha */
 function initColorPreview(savedColor, savedAlpha) {
 if (!colorPreview || !colorInput || !alphaInput) return;
 let hex = savedColor || '#667eea';
 let alpha = savedAlpha ?? 1;
 // Если цвет 8-значный (#RRGGBBAA) — извлекаем alpha и обрезаем
 if (hex.length === 9) {
 const aHex = hex.slice(7, 9);
 alpha = parseInt(aHex, 16) / 255;
 hex = hex.slice(0, 7);
 }
 colorInput.value = hex;
 alphaInput.value = Math.round(alpha * 100);
 if (alphaLabel) alphaLabel.textContent = Math.round(alpha * 100) + '%';
 updateColorPreview();
 }
 initColorPreview(s.primary_color, s.primary_alpha);

 $('#sSave').addEventListener('click', async () => {
 const alpha = parseInt(alphaInput?.value || 100) / 100;
 const hex = colorInput?.value || '#667eea';
 const r = hex.slice(1, 3);
 const g = hex.slice(3, 5);
 const b = hex.slice(5, 7);
 const a = Math.round(alpha * 255).toString(16).padStart(2, '0');
 const primary_color = alpha >= 0.99 ? hex : `#${r}${g}${b}${a}`;
 const payload = {
 university_name: $('#sName').value.trim(),
 university_url: $('#sUrl').value.trim(),
 abitur_url: $('#sAbitur').value.trim(),
 tagline: $('#sTagline').value.trim(),
 primary_color: primary_color,
 primary_alpha: alpha,
 logo_path: $('#sLogo').value.trim(),
 hero_image_path: $('#sHero').value.trim(),
 presenter_video_path: $('#sVideo').value.trim(),
 consent_text: $('#sConsent').value,
 custom_form_position: $('#sFormPos').value,
 };
 try {
 await api('/settings', { method: 'PUT', body: payload });
 alert('Сохранено');
 } catch (e) { alert(e.message); }
 });
}

/* =========================================================
 ПОЛЬЗОВАТЕЛИ
 ========================================================= */
async function users() {
 const data = await api('/users').catch(handleError);
 const items = (data && data.users) || [];
 const editUser = items.find((u) => u.id === editUserId) || null;

 let editHtml = '';
 if (editUser) {
 editHtml = `
 <div class="panel">
 <h2>Редактирование: ${esc(editUser.username)}</h2>
 <div class="form-grid">
 <div><label>Статус</label><select id="ueActive">
 <option value="1" ${editUser.is_active ? 'selected' : ''}>Активен</option>
 <option value="0" ${!editUser.is_active ? 'selected' : ''}>Отключён</option>
 </select></div>
 </div>
 <h3 style="margin:10px 0 8px; font-size:0.95rem;">Смена пароля</h3>
 <div class="form-grid">
 <div><label>Текущий пароль *</label><input id="ueCurrent" type="password" autocomplete="current-password"></div>
 <div><label>Новый пароль</label><input id="ueNew" type="password" autocomplete="new-password"></div>
 <div><label>Повторите новый пароль</label><input id="ueConfirm" type="password" autocomplete="new-password"></div>
 </div>
 <p class="muted">* Текущий пароль обязателен, если задаётся новый.</p>
 <div style="margin-top:10px;display:flex;gap:8px">
 <button class="btn" id="ueSave">Сохранить</button>
 <button class="btn ghost" id="ueCancel">Отмена</button>
 </div>
 </div>`;
 }

 content().innerHTML = `
 <div class="topbar"><h1>Пользователи</h1></div>
 <div class="panel">
 <h2>Новый пользователь</h2>
 <div class="form-grid">
 <div><label>Логин</label><input id="uName"></div>
 <div><label>Пароль</label><input id="uPass" type="password" autocomplete="new-password"></div>
 </div>
 <button class="btn" id="uCreate">Создать</button>
 </div>
 ${editHtml}
 <div class="panel"><table>
 <tr><th>ID</th><th>Логин</th><th>Активн.</th><th></th></tr>
 ${items.map((u) => `
 <tr>
 <td>${esc(u.id)}</td><td>${esc(u.username)}</td>
 <td>${u.is_active ? 'да' : 'нет'}</td>
 <td><div class="row-actions">
 <button class="btn small" data-edit-u="${esc(u.id)}">Ред.</button>
 <button class="btn small danger" data-del-u="${esc(u.id)}">Удал.</button>
 </div></td>
 </tr>`).join('')}
 </table></div>`;

 $('#uCreate').addEventListener('click', async () => {
 const username = $('#uName').value.trim();
 const password = $('#uPass').value;
 if (!username) { alert('Введите логин'); return; }
 if (!password || password.length < 8) { alert('Пароль должен быть не менее 8 символов'); return; }
 try {
 await api('/users', { method: 'POST', body: { username, password } });
 users();
 } catch (e) { alert(e.message); }
 });

 if (editUser) {
 $('#ueSave').addEventListener('click', async () => {
 const newPass = $('#ueNew').value;
 const confirmPass = $('#ueConfirm').value;
 if (newPass !== confirmPass) {
 alert('Новые пароли не совпадают');
 return;
 }
 const payload = { is_active: $('#ueActive').value === '1' };
 if (newPass) {
 payload.password = newPass;
 payload.current_password = $('#ueCurrent').value;
 }
 try {
 await api('/users/' + editUser.id, { method: 'PUT', body: payload });
 editUserId = null;
 users();
 } catch (e) { alert(e.message); }
 });
 $('#ueCancel').addEventListener('click', () => {
 editUserId = null;
 users();
 });
 }

 $$('[data-edit-u]').forEach((b) => b.addEventListener('click', () => {
 editUserId = Number(b.dataset.editU);
 users();
 }));

 // Модалка подтверждения пароля
 function promptPassword() {
 return new Promise((resolve) => {
 const overlay = document.createElement('div');
 overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:9999;';
 const box = document.createElement('div');
 box.style.cssText = 'background:#fff;padding:24px;border-radius:12px;min-width:320px;box-shadow:0 4px 24px rgba(0,0,0,0.2);';
 box.innerHTML = `
 <h3 style="margin:0 0 16px;font-size:1rem">Подтверждение удаления</h3>
 <p style="margin:0 0 12px;font-size:.85rem;color:#64748b">Введите ваш пароль для подтверждения:</p>
 <input id="delPassword" type="password" placeholder="Пароль" style="width:100%;padding:10px;border:1px solid #e2e8f0;border-radius:6px;font-size:.9rem;box-sizing:border-box;">
 <div style="display:flex;gap:8px;margin-top:16px;justify-content:flex-end">
 <button id="delCancel" style="padding:8px 16px;border:1px solid #e2e8f0;border-radius:6px;background:#f8fafc;cursor:pointer;font-size:.85rem">Отмена</button>
 <button id="delConfirm" style="padding:8px 16px;border:none;border-radius:6px;background:#dc2626;color:#fff;cursor:pointer;font-size:.85rem">Удалить</button>
 </div>`;
 overlay.appendChild(box);
 document.body.appendChild(overlay);

 const pwdInput = document.getElementById('delPassword');
 pwdInput.focus();

 const close = (val) => { overlay.remove(); resolve(val); };
 document.getElementById('delCancel').onclick = () => close(null);
 document.getElementById('delConfirm').onclick = () => close(pwdInput.value);
 overlay.addEventListener('click', (e) => { if (e.target === overlay) close(null); });
 pwdInput.addEventListener('keydown', (e) => {
 if (e.key === 'Enter') close(pwdInput.value);
 if (e.key === 'Escape') close(null);
 });
 });
 }

 $$('[data-del-u]').forEach((b) => b.addEventListener('click', async () => {
 const password = await promptPassword();
 if (!password) return;
 try {
 await api('/users/' + b.dataset.delU, {
 method: 'DELETE',
 body: { password },
 });
 users();
 } catch (e) { alert(e.message); }
 }));
}

/* =========================================================
 ОТВЕТЫ
 ========================================================= */
async function responses() {
 const data = await api('/sessions?limit=50').catch(handleError);
 const items = (data && data.sessions) || [];
 content().innerHTML = `
 <div class="topbar">
 <h1>Ответы</h1>
 <a class="btn" href="/api/admin/responses.csv" download>Экспорт CSV</a>
 </div>
 <div class="panel"><table>
 <tr><th>ID</th><th>Статус</th><th>Вопросов</th><th>Источник</th><th>Метки</th><th>Оценка</th><th>Рекомендации</th></tr>
 ${items.map((s) => `
 <tr>
 <td>${esc(s.id)}</td>
 <td>${esc(s.status)}</td>
 <td>${esc(s.questions_asked)}</td>
 <td>${esc(s.source)}</td>
 <td class="muted">${esc((s.chosen_fields || []).join(', ') || '—')}</td>
 <td>${esc(s.feedback_score ?? '—')}</td>
 <td class="muted">${esc((s.recommendations || []).slice(0, 3).map((r) => r.field).join(', '))}</td>
 </tr>`).join('')}
 </table></div>`;
}

/* =========================================================
 РЕКОМЕНДАЦИИ — выбор между локальной моделью и API
 ========================================================= */
async function recommender() {
 const data = await api('/recommender-settings').catch(handleError);
 const s = (data && data.settings) || {};

 content().innerHTML = `
 <div class="topbar"><h1>Рекомендации</h1></div>
 <div class="panel">
 <h2>Источник рекомендаций</h2>
 <div style="display:flex;gap:8px;margin-bottom:20px;">
 <button class="btn ${s.engine !== 'api' ? '' : 'btn-secondary'}" id="rBtnLocal" style="flex:1;">Локальная модель (Keras)</button>
 <button class="btn ${s.engine === 'api' ? '' : 'btn-secondary'}" id="rBtnApi" style="flex:1;">Внешний API</button>
 </div>

 <div id="apiSettings" style="display:none">
 <h2>Настройки API</h2>
 <div class="form-grid" style="grid-template-columns: 1fr;">
 <div><label>Провайдер</label>
 <select id="rProvider">
 <option value="openai" ${s.api_provider === 'openai' ? 'selected' : ''}>OpenAI</option>
 <option value="sbercloud" ${s.api_provider === 'sbercloud' ? 'selected' : ''}>СберCloud (GigaChat)</option>
 <option value="deepseek" ${s.api_provider === 'deepseek' ? 'selected' : ''}>DeepSeek</option>
 <option value="anthropic" ${s.api_provider === 'anthropic' ? 'selected' : ''}>Anthropic (Claude)</option>
 <option value="ollama" ${s.api_provider === 'ollama' ? 'selected' : ''}>Ollama (локальная)</option>
 <option value="lmstudio" ${s.api_provider === 'lmstudio' ? 'selected' : ''}>LM Studio (локальная)</option>
 <option value="vllm" ${s.api_provider === 'vllm' ? 'selected' : ''}>vLLM (локальная)</option>
 <option value="custom" ${s.api_provider === 'custom' ? 'selected' : ''}>Другой (кастомный URL)</option>
 </select>
 </div>
 <div><label>API ключ</label>
 <input id="rApiKey" type="text" value="${esc(s.api_key || '')}" placeholder="sk-... или ваш ключ" autocomplete="off">
 </div>
 <div><label>Модель LLM</label>
 <input id="rModel" type="text" value="${esc(s.api_model || '')}" placeholder="gpt-4o-mini (по умолчанию)">
 </div>
 <div><label>Базовый URL</label>
 <input id="rBaseUrl" value="${esc(s.api_base_url || '')}" placeholder="https://api.example.com/v1">
 </div>
 <div><label>Системный промпт</label>
 <textarea id="rSystemPrompt" rows="8" style="font-family:monospace;font-size:12px;resize:vertical;">${esc(s.system_prompt || '')}</textarea>
 </div>
 </div>

 <div style="margin-top:20px;">
 <button class="btn" id="rPreviewPrompt" style="margin-bottom:12px;">Предпросмотр полного промпта</button>
 <textarea id="rPromptPreview" rows="15" readonly style="width:100%;font-family:monospace;font-size:11px;resize:vertical;background:#f5f5f5;border:1px solid #ddd;border-radius:4px;padding:8px;"></textarea>
 </div>

 <button class="btn" id="rSave" style="margin-top:16px;">Сохранить</button>
 </div>`;

 /* Переключение между локальной моделью и API */
 const btnLocal = $('#rBtnLocal');
 const btnApi = $('#rBtnApi');
 const apiSettings = $('#apiSettings');
 const providerSelect = $('#rProvider');
 const baseUrlInput = $('#rBaseUrl');
 const modelInput = $('#rModel');
 const systemPromptInput = $('#rSystemPrompt');
 const promptPreview = $('#rPromptPreview');

 /* Явный state engine */
 let currentEngine = (s.engine === 'api') ? 'api' : 'local';

 /* Дефолтные значения для каждого провайдера */
 const PROVIDER_CONFIGS = {
 openai: { url: 'https://api.openai.com/v1', model: 'gpt-4o-mini', key: 'sk-' },
 sbercloud: { url: 'https://gigachat.devices.sbercloud.ru/api/v1', model: 'GigaChat', key: '' },
 deepseek: { url: 'https://api.deepseek.com/v1', model: 'deepseek-chat', key: 'sk-' },
 anthropic: { url: 'https://api.anthropic.com/v1', model: 'claude-3-5-sonnet-20241022', key: 'sk-ant-' },
 ollama: { url: 'http://host.docker.internal:11434/v1', model: 'llama3', key: '' },
 lmstudio: { url: 'http://host.docker.internal:1234/v1', model: 'qwen2.5-7b-instruct', key: '' },
 vllm: { url: 'http://host.docker.internal:8000/v1', model: 'Llama-3.1-8B-Instruct', key: '' },
 custom: { url: '', model: '', key: '' },
 };

 /* Применить UI к текущему engine */
 function applyEngineUI() {
 if (currentEngine === 'api') {
 apiSettings.style.display = '';
 btnApi.className = 'btn';
 btnLocal.className = 'btn btn-secondary';
 } else {
 apiSettings.style.display = 'none';
 btnLocal.className = 'btn';
 btnApi.className = 'btn btn-secondary';
 }
 }
 applyEngineUI();

 /* Подставить дефолтные значения при смене провайдера */
 providerSelect.addEventListener('change', () => {
 const cfg = PROVIDER_CONFIGS[providerSelect.value];
 baseUrlInput.value = cfg.url;
 modelInput.value = cfg.model;
 // Ключ не подставляем — оставляем текущий или пустой
 });

 btnApi.addEventListener('click', () => {
 currentEngine = 'api';
 applyEngineUI();
 });

 btnLocal.addEventListener('click', () => {
 currentEngine = 'local';
 applyEngineUI();
 });

 /* Предпросмотр промпта */
 $('#rPreviewPrompt').addEventListener('click', async () => {
 try {
 const res = await api('/recommender-preview-prompt', {
 method: 'POST',
 body: { profile: {} },
 });
 promptPreview.value = res.full_prompt || '(пусто)';
 } catch (e) {
 alert('Ошибка: ' + e.message);
 }
 });

 /* Сохранение */
 $('#rSave').addEventListener('click', async () => {
 const payload = {
 engine: currentEngine,
 api_provider: providerSelect.value,
 api_key: $('#rApiKey').value.trim(),
 api_base_url: $('#rBaseUrl').value.trim() || (PROVIDER_CONFIGS[providerSelect.value]?.url || ''),
 api_model: modelInput.value.trim() || '',
 system_prompt: systemPromptInput.value.trim(),
 };
 try {
 await api('/recommender-settings', { method: 'PUT', body: payload });
 alert('Сохранено');
 } catch (e) {
 alert(e.message);
 }
 });
}

/* =========================================================
  Метрики рекомендера
  ========================================================= */
 function _renderRecommenderCards(m) {
  const a1 = m.accuracy_at_1 != null ? Math.round(m.accuracy_at_1 * 100) : null;
  const a3 = m.accuracy_at_3 != null ? Math.round(m.accuracy_at_3 * 100) : null;
  const a5 = m.accuracy_at_5 != null ? Math.round(m.accuracy_at_5 * 100) : null;
  const hr = m.hit_rate_any != null ? Math.round(m.hit_rate_any * 100) : null;
  const avg = m.avg_best_rank != null ? m.avg_best_rank : null;
  const total = m.sessions_with_hit || 0;
  const totalSessions = m.total_sessions || 0;

  const card = (val, label, color) => `
  <div class="card" style="border-left:3px solid ${color}">
   <div class="num" style="color:${color}">${val != null ? val + '%' : '—'}</div>
   <div class="lbl">${label}</div>
  </div>`;

  return `
  <div class="cards" style="margin-bottom:16px">
  ${card(a1, 'Accuracy@1 (лучшее совпало)', '#6366f1')}
  ${card(a3, 'Accuracy@3', '#8b5cf6')}
  ${card(a5, 'Accuracy@5', '#a78bfa')}
  ${card(hr, 'Hit Rate (любое совпадение)', '#06b6d4')}
  ${card(avg != null ? avg.toFixed(1) : '—', 'Средний ранг лучшего', '#f59e0b')}
  </div>
  ${total > 0 ? `
  <div style="font-size:.78rem;color:var(--muted);margin-bottom:12px">
   Рассчитано по <b>${total}</b> сессиям с фидбеком из <b>${totalSessions}</b> завершённых
  </div>` : ''}`;
 }

 function _renderRecommenderMetricsCards(m) {
  const total = m.sessions_with_hit || 0;
  if (total === 0) return '';
  return _renderRecommenderCards(m);
 }

 /* =========================================================
  Регистрация renderers + init
  ========================================================= */
renderers.dashboard = dashboard;
renderers.directions = directions;
renderers.features = features;
renderers.questions = questions;
renderers.custom = custom;
renderers.media = media;
renderers.settings = settings;
renderers.recommender = recommender;
renderers.users = users;
renderers.responses = responses;

document.addEventListener('DOMContentLoaded', () => {
 bootstrap();
});