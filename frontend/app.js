// ── Config ────────────────────────────────────────────────────────────────────
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : '/api';  // Vercel rewrite proxies /api/* to Railway

// ── Theme ─────────────────────────────────────────────────────────────────────
(function () {
  const saved = localStorage.getItem('theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(saved);
})();

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
  localStorage.setItem('theme', theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

// ── Session ───────────────────────────────────────────────────────────────────
let sessionId = localStorage.getItem('pdfMergerSession') || crypto.randomUUID();
localStorage.setItem('pdfMergerSession', sessionId);

// ── State ─────────────────────────────────────────────────────────────────────
let fileOrder = [];        // array of file IDs in current order
let fileRegistry = {};     // id → { id, filename, type, thumbnail_url }

// ── DOM refs ──────────────────────────────────────────────────────────────────
const dropZone     = document.getElementById('drop-zone');
const fileInput    = document.getElementById('file-input');
const cardsCont    = document.getElementById('cards');
const fileList     = document.getElementById('file-list');
const actions      = document.getElementById('actions');
const fileCountEl  = document.getElementById('file-count');
const mergeBtn     = document.getElementById('merge-btn');
const mergeLabel   = document.getElementById('merge-label');
const mergeSpinner = document.getElementById('merge-spinner');
const warningBanner = document.getElementById('warning-banner');
const warningSizeEl = document.getElementById('warning-size');

// ── Drop zone events ──────────────────────────────────────────────────────────
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  uploadFiles(Array.from(e.dataTransfer.files));
});
dropZone.addEventListener('click', e => {
  if (e.target !== fileInput) fileInput.click();
});
fileInput.addEventListener('change', () => {
  uploadFiles(Array.from(fileInput.files));
  fileInput.value = '';
});

// ── Upload ────────────────────────────────────────────────────────────────────
async function uploadFiles(files) {
  if (!files.length) return;

  const formData = new FormData();
  files.forEach(f => formData.append('files', f));

  // Add placeholder cards while uploading
  const placeholderIds = files.map(f => {
    const pid = 'pending-' + crypto.randomUUID();
    addPlaceholderCard(pid, f.name);
    return pid;
  });

  let uploaded;
  try {
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      headers: { 'X-Session-ID': sessionId },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    uploaded = await res.json();
  } catch (err) {
    alert(`Upload error: ${err.message}`);
    // Remove placeholders
    placeholderIds.forEach(pid => {
      fileOrder = fileOrder.filter(id => id !== pid);
      delete fileRegistry[pid];
    });
    renderCards();
    return;
  }

  // Remove placeholders
  placeholderIds.forEach(pid => {
    fileOrder = fileOrder.filter(id => id !== pid);
    delete fileRegistry[pid];
  });

  // Register new files
  uploaded.forEach(f => {
    fileRegistry[f.id] = f;
    fileOrder.push(f.id);
  });

  renderCards();
}

function addPlaceholderCard(pid, filename) {
  fileRegistry[pid] = { id: pid, filename, type: '...', thumbnail_url: null, pending: true };
  fileOrder.push(pid);
  renderCards();
}

// ── Render ────────────────────────────────────────────────────────────────────
function renderCards() {
  cardsCont.innerHTML = '';

  fileOrder.forEach((id, idx) => {
    const f = fileRegistry[id];
    if (!f) return;

    const card = document.createElement('div');
    card.className = 'card';
    card.dataset.id = id;

    if (f.pending) {
      card.innerHTML = `
        <div class="card-thumb-placeholder">📄</div>
        <div class="card-loading"><span class="spinner" style="border-color:rgba(0,0,0,.15);border-top-color:#0071e3"></span></div>
        <div class="card-info">
          <div class="card-name">${escHtml(f.filename)}</div>
          <span class="card-type">...</span>
        </div>`;
    } else {
      const thumbSrc = f.thumbnail_url ? `${API_BASE}${f.thumbnail_url}` : null;
      card.innerHTML = `
        <div class="card-order">${idx + 1}</div>
        ${thumbSrc
          ? `<img class="card-thumb" src="${thumbSrc}" alt="${escHtml(f.filename)}" loading="lazy" />`
          : `<div class="card-thumb-placeholder">${typeIcon(f.type)}</div>`}
        <div class="card-info">
          <div class="card-name" title="${escHtml(f.filename)}">${escHtml(f.filename)}</div>
          <span class="card-type">${escHtml(f.type)}</span>
        </div>
        <button class="card-remove" title="Remove" onclick="removeFile('${id}')">✕</button>`;

      attachDragEvents(card, id);
    }

    cardsCont.appendChild(card);
  });

  const count = fileOrder.filter(id => !fileRegistry[id]?.pending).length;
  fileCountEl.textContent = `${count} file${count !== 1 ? 's' : ''}`;

  const hasFiles = fileOrder.length > 0;
  fileList.classList.toggle('hidden', !hasFiles);
  actions.classList.toggle('hidden', !hasFiles);
  warningBanner.classList.add('hidden');
}

function typeIcon(type) {
  const t = (type || '').toLowerCase();
  if (['jpg','jpeg','png','gif','webp'].includes(t)) return '🖼️';
  if (t === 'pdf') return '📄';
  if (t === 'doc' || t === 'docx') return '📝';
  return '📎';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ── Remove ────────────────────────────────────────────────────────────────────
function removeFile(id) {
  fileOrder = fileOrder.filter(fid => fid !== id);
  delete fileRegistry[id];
  renderCards();
}

function clearAll() {
  fileOrder = [];
  fileRegistry = {};
  renderCards();
}

// ── Drag-and-drop reorder ─────────────────────────────────────────────────────
let dragSrcId = null;

function attachDragEvents(card, id) {
  card.draggable = true;

  card.addEventListener('dragstart', e => {
    dragSrcId = id;
    card.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });

  card.addEventListener('dragend', () => {
    dragSrcId = null;
    card.classList.remove('dragging');
    document.querySelectorAll('.card.drag-over').forEach(c => c.classList.remove('drag-over'));
  });

  card.addEventListener('dragover', e => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragSrcId && dragSrcId !== id) {
      document.querySelectorAll('.card.drag-over').forEach(c => c.classList.remove('drag-over'));
      card.classList.add('drag-over');
    }
  });

  card.addEventListener('dragleave', () => card.classList.remove('drag-over'));

  card.addEventListener('drop', e => {
    e.preventDefault();
    card.classList.remove('drag-over');
    if (!dragSrcId || dragSrcId === id) return;

    const srcIdx = fileOrder.indexOf(dragSrcId);
    const dstIdx = fileOrder.indexOf(id);
    if (srcIdx === -1 || dstIdx === -1) return;

    fileOrder.splice(srcIdx, 1);
    fileOrder.splice(dstIdx, 0, dragSrcId);
    renderCards();
  });
}

// ── Merge ─────────────────────────────────────────────────────────────────────
async function mergeFiles() {
  const validOrder = fileOrder.filter(id => !fileRegistry[id]?.pending);
  if (validOrder.length === 0) {
    alert('No files to merge.');
    return;
  }

  mergeBtn.disabled = true;
  mergeLabel.textContent = 'Merging…';
  mergeSpinner.classList.remove('hidden');
  warningBanner.classList.add('hidden');

  try {
    const res = await fetch(`${API_BASE}/merge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, order: validOrder }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Merge failed' }));
      throw new Error(err.detail || 'Merge failed');
    }

    const data = await res.json();

    if (!data.compressed_to_target) {
      warningSizeEl.textContent = `${data.size_mb} MB`;
      warningBanner.classList.remove('hidden');
    }

    // Trigger download
    window.location.href = `${API_BASE}/download/${sessionId}/${data.job_id}`;

  } catch (err) {
    alert(`Merge error: ${err.message}`);
  } finally {
    mergeBtn.disabled = false;
    mergeLabel.textContent = 'Merge & Download PDF';
    mergeSpinner.classList.add('hidden');
  }
}
