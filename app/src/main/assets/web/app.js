const API = '';  // Même origine (localhost:8080)
let currentMode = 'CONTINUOUS';

// --- Polling état toutes les 3 s ---
async function fetchStatus() {
  try {
    const r = await fetch(`${API}/api/status`);
    const d = await r.json();

    // Badges
    setActive('badge-recording', d.recording?.active);
    setActive('badge-sentry',    d.sentry?.active);
    document.getElementById('badge-storage').textContent =
      `💾 ${d.storage?.freeGB ?? '--'} GB libre`;

    // Mode actif
    currentMode = d.recording?.mode ?? currentMode;
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.mode === currentMode);
    });

    // Stockage
    const usage = d.storage?.usage ?? {};
    document.getElementById('storage-info').innerHTML =
      Object.entries(usage).map(([k, v]) => `<b>${k}</b>: ${v}`).join('&nbsp;|&nbsp;') +
      `<br>Libre : <b>${d.storage?.freeGB ?? '--'} GB</b>`;

  } catch (e) { /* serveur pas encore prêt */ }
}

// --- Modes d'enregistrement ---
document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    await fetch(`${API}/api/recording`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: btn.dataset.mode })
    });
    fetchStatus();
  });
});

// --- Sensibilité sentinelle ---
const sensitivityInput = document.getElementById('sensitivity');
const sensitivityVal   = document.getElementById('sensitivity-val');
sensitivityInput.addEventListener('input', () => {
  sensitivityVal.textContent = sensitivityInput.value;
});

// --- Boutons sentinelle ---
document.getElementById('btn-sentry-on').addEventListener('click', () => setSentry(true));
document.getElementById('btn-sentry-off').addEventListener('click', () => setSentry(false));

async function setSentry(enabled) {
  await fetch(`${API}/api/sentry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled, sensitivity: parseFloat(sensitivityInput.value) })
  });
  fetchStatus();
}

// --- Nettoyage stockage ---
document.getElementById('btn-cleanup').addEventListener('click', async () => {
  document.getElementById('btn-cleanup').textContent = 'Nettoyage en cours...';
  await fetch(`${API}/api/storage/cleanup`, { method: 'POST' });
  document.getElementById('btn-cleanup').textContent = 'Nettoyer maintenant';
  fetchStatus();
});

// --- Liste clips ---
async function fetchClips() {
  try {
    const r = await fetch(`${API}/api/clips`);
    const d = await r.json();
    const list = document.getElementById('clip-list');
    list.innerHTML = (d.clips ?? []).map(c => `
      <li>
        <span>${c.name}</span>
        <span class="clip-size">${c.sizeKB} KB</span>
        <a href="/clips/${encodeURIComponent(c.name)}" target="_blank">⬇ Télécharger</a>
      </li>
    `).join('') || '<li style="color:#666">Aucun clip</li>';
  } catch (_) {}
}

function setActive(id, on) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle('on', !!on);
  el.classList.toggle('off', !on);
}

// Init
fetchStatus();
fetchClips();
setInterval(fetchStatus, 3_000);
setInterval(fetchClips, 30_000);
