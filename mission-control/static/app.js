import {
  calculateHltTerms,
  calculateDerivedFields,
  formatCurrency,
  formatPercent,
  formatNumber,
  generateErc20Identifier,
  nextLeaseId,
  addMonthsIso,
  parseNumber,
  buildHltDocumentHtml
} from './hlt-engine.js';

const app = document.getElementById("app");
const API = "/api";

// ─── HLT lifecycle (v1) ──────────────────────────────────────────────────────
const HLT_STATUSES = [
  { id: "coming_soon", label: "Coming soon" },
  { id: "list", label: "List" },
  { id: "live", label: "Live" },
  { id: "closed", label: "Closed" },
];

function normalizeHltStatus(s) {
  const v = (s || "coming_soon").toLowerCase();
  if (["coming_soon", "list", "live", "closed"].includes(v)) return v;
  if (["draft", "pending", "review", "new"].includes(v)) return "coming_soon";
  if (["complete", "completed", "listing", "ready"].includes(v)) return "list";
  if (["published", "listed", "active"].includes(v)) return "live";
  if (["ended", "archived", "cancelled", "canceled"].includes(v)) return "closed";
  return "coming_soon";
}

function hltStatusPill(status) {
  const s = normalizeHltStatus(status);
  const label = HLT_STATUSES.find(x => x.id === s)?.label || s;
  return `<span class="badge badge-${s}">${label}</span>`;
}

function docStatusPill(status) {
  if (status === "approved" || status === "locked" || status === "complete" || status === "completed") {
    return `<span class="badge badge-live">Locked</span>`;
  }
  if (status === "draft" || status === "review") {
    return `<span class="badge badge-list">Draft</span>`;
  }
  return `<span class="badge badge-coming_soon">Missing</span>`;
}

// Example blurbs for horse-specific term sheet fields (manual for now)
const TERM_SHEET_EXAMPLES = [
  { horse: "I Stole A Manolo", blurb: "Bay filly by Satono Aladdin. Race-ready lease campaign; Matamata base." },
  { horse: "First Gear", blurb: "Proven campaigner; clear programme notes and owner narrative in pack." },
  { horse: "Prudentia", blurb: "Multiple starts; settlement story + welfare updates for investors." },
];

// ─── Wizard state ────────────────────────────────────────────────────────────

let wizardState = {
  step: 1,
  draft: {
    // Step 1: Entities
    horseId: '',
    ownerId: '',
    trainerId: '',
    governingBodyCode: '',
    submissionDate: new Date().toISOString().split('T')[0],
    // Step 2: Lease Terms + Pricing
    leaseStartDate: '',
    leaseLengthMonths: '',
    percentageLeased: '',
    numTokens: '',
    monthlyRate: '',  // Price per 1% per month (primary driver)
    // Derived (calculated)
    pricePer1PercentTotal: 0,
    annualRatePer1Percent: 0,
    totalIssuanceValue: 0,
    pricePerToken: 0,
    fractionalInterestPerToken: 0,
    leaseEndDate: '',
    // Metadata
    tokenName: '',
    erc20Identifier: '',
    variations: 'n/a',
    investorReturn: '75',
    ownerStakesSplit: '25',
    horseAssetOwner: '',
    horseMicrochip: '',
  },
  lastEditedField: null,
  entities: { horses: [], owners: [], trainers: [], governingBodies: [], leases: [] },
};

function setLoading(show) {
  app.innerHTML = show ? '<div class="flex items-center justify-center h-64 text-slate-500">Loading...</div>' : "";
}

// Reliable hash navigation that always triggers render
window.navigateTo = function(hash) {
  if (window.location.hash === hash) {
    // Force re-render if clicking same link
    render();
  } else {
    window.location.hash = hash;
    // hashchange listener calls render() automatically
  }
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => { toast.remove(); }, 4000);
}

function showDocModal(title, htmlContent, downloadUrl) {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.onclick = (e) => { if (e.target === modal) closeDocModal(); };
  modal.innerHTML = `
    <div class="modal-content max-w-4xl" onclick="event.stopPropagation()">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-slate-900">${title}</h3>
        <button type="button" onclick="closeDocModal()" class="text-slate-400 hover:text-slate-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="flex gap-2 mb-4">
        <button type="button" onclick="downloadDocContent()" class="btn-secondary">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg> Download HTML
        </button>
        ${downloadUrl ? `<button type="button" onclick="window.open('${downloadUrl}', '_blank')" class="btn-secondary">Download DOCX</button>` : ''}
      </div>
      <div class="border border-slate-200 rounded-lg overflow-hidden" style="max-height: 60vh; overflow: auto;">
        <iframe id="doc-iframe" srcdoc="${htmlContent.replace(/"/g, '&quot;')}" style="width: 100%; height: 60vh; border: none;"></iframe>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  window.currentDocHtml = htmlContent;
  window.currentDocDownloadUrl = downloadUrl;
}

function closeModal() {
  const modal = document.querySelector('.modal-overlay') || document.getElementById('active-modal');
  if (modal) modal.remove();
}
window.closeModal = closeModal;

function closeDocModal() {
  const modal = document.querySelector('.modal-overlay');
  if (modal) modal.remove();
}
window.closeDocModal = closeDocModal;


function downloadDocContent() {
  if (window.currentDocHtml) {
    const blob = new Blob([window.currentDocHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'term-sheet.html';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }
}

function render() {
  const hash = window.location.hash.replace("#/", "").replace("#", "").replace("/", "") || "";
  const viewFn = views[hash] || views.default;
  viewFn();
  document.querySelectorAll(".nav-item").forEach(link => {
    link.classList.toggle("active", link.dataset.route === hash);
  });
}

// ─── API helpers ────────────────────────────────────────────────────────────

// Use the global getAuthHeader from Firebase auth (defined in index.html)
// This delegates to Firebase auth for token retrieval
async function getAuthHeader() {
  // Check if Firebase auth is available and user is logged in
  if (typeof window.getAuthHeader === 'function' && window.getAuthHeader !== getAuthHeader) {
    return await window.getAuthHeader();
  }
  return { 'Content-Type': 'application/json' };
}

async function loadHorses() {
  try {
    const headers = await getAuthHeader();
    const r = await fetch(`${API}/horses`, { headers });
    if (r.status === 401) {
      showToast('Please log in to access this data', 'error');
      return [];
    }
    const j = await r.json();
    return j.success ? j.data : [];
  } catch (error) {
    console.error('Error loading horses:', error);
    showToast('Failed to load horses', 'error');
    return [];
  }
}
async function loadOwners() {
  const headers = await getAuthHeader();
  const r = await fetch(`${API}/owners`, { headers });
  const j = await r.json();
  return j.success ? j.data : [];
}
async function loadTrainers() {
  const headers = await getAuthHeader();
  const r = await fetch(`${API}/trainers`, { headers });
  const j = await r.json();
  return j.success ? j.data : [];
}
async function loadGoverningBodies() {
  const headers = await getAuthHeader();
  const r = await fetch(`${API}/governing-bodies`, { headers });
  const j = await r.json();
  return j.success ? j.data.items : [];
}
async function loadHlts() {
  const headers = await getAuthHeader();
  const r = await fetch(`${API}/hlts`, { headers });
  const j = await r.json();
  return j.success ? j.data : [];
}
async function getStats() {
  const headers = await getAuthHeader();
  const r = await fetch(`${API}/stats`, { headers });
  const j = await r.json();
  return j.success ? j.data : {};
}
async function getHlt(id) {
  const r = await fetch(`${API}/hlts/${id}`);
  return await r.json();
}
async function createHltWorkflow(payload) {
  const headers = await getAuthHeader();
  const r = await fetch(`${API}/hlts/workflow`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  return await r.json();
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

async function renderDashboard() {
  try {
    setLoading(true);
    const [stats, horses, owners, trainers, hlts] = await Promise.all([
      fetch(`${API}/stats`).then(r => r.json()).then(j => j.success ? j.data : {}),
      loadHorses(), loadOwners(), loadTrainers(), loadHlts()
    ]);
    const c = {
      horses: stats.horses ?? horses.length,
      owners: stats.owners ?? owners.length,
      trainers: stats.trainers ?? trainers.length,
      hlts: stats.hlts ?? hlts.length,
    };
    const byStatus = (id) => hlts.filter(h => normalizeHltStatus(h.status) === id).length;
    const recent = [...hlts].slice(0, 6);
    app.innerHTML = `
      <div class="space-y-5 max-w-5xl">
        <div class="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 class="text-xl font-bold text-slate-900 tracking-tight">Mission Control</h2>
            <p class="text-sm text-slate-500 mt-0.5">Registry · listings · docs. Mini operator surface.</p>
          </div>
          <div class="flex gap-2">
            <button type="button" onclick="window.openAddHorseWizard()" class="btn-secondary text-xs">+ Horse</button>
            <button type="button" onclick="window.openCreateHltWizard()" class="btn-primary text-xs">+ Create HLT</button>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <a href="#/horses" class="stat-tile"><div class="text-2xl font-bold text-slate-900">${c.horses}</div><div class="text-xs font-medium text-slate-500 mt-1">Horses</div></a>
          <a href="#/owners" class="stat-tile"><div class="text-2xl font-bold text-slate-900">${c.owners}</div><div class="text-xs font-medium text-slate-500 mt-1">Owners</div></a>
          <a href="#/trainers" class="stat-tile"><div class="text-2xl font-bold text-slate-900">${c.trainers}</div><div class="text-xs font-medium text-slate-500 mt-1">Trainers</div></a>
          <a href="#/hlts" class="stat-tile"><div class="text-2xl font-bold text-slate-900">${c.hlts}</div><div class="text-xs font-medium text-slate-500 mt-1">HLTs</div></a>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
          ${HLT_STATUSES.map(s => `
            <div class="rounded-lg border border-slate-200 bg-white px-3 py-2.5 flex items-center justify-between">
              ${hltStatusPill(s.id)}
              <span class="text-sm font-semibold text-slate-800">${byStatus(s.id)}</span>
            </div>
          `).join("")}
        </div>

        <div class="surface-card overflow-hidden">
          <div class="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-900">Recent listings</h3>
            <a href="#/hlts" class="text-xs font-semibold text-blue-600 hover:underline">All HLTs →</a>
          </div>
          <table class="w-full">
            <thead>
              <tr>
                <th class="table-header">Horse</th>
                <th class="table-header">HLT</th>
                <th class="table-header">Status</th>
                <th class="table-header text-right">Terms</th>
              </tr>
            </thead>
            <tbody>
              ${recent.length ? recent.map(h => `
                <tr class="table-row cursor-pointer" onclick="window.navigateTo('#/hlt/${h.id}')">
                  <td class="table-cell font-semibold text-slate-900">${h.horse_name || h.horse_microchip}</td>
                  <td class="table-cell font-mono text-xs text-slate-500">${h.id}</td>
                  <td class="table-cell">${hltStatusPill(h.status)}</td>
                  <td class="table-cell text-right text-slate-600">${h.percent_leased != null ? h.percent_leased + '%' : '—'} · ${h.duration_months != null ? h.duration_months + 'm' : '—'}</td>
                </tr>
              `).join("") : `<tr><td colspan="4" class="table-cell text-center text-slate-500">No HLTs yet. Create one to seed website inventory.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Dashboard render error:', err);
    app.innerHTML = `<div class="surface-card p-6"><h2 class="text-lg font-bold text-rose-700 mb-2">Error</h2><p class="text-sm text-slate-600">${err.message}</p></div>`;
  }
}

// ─── Horses ───────────────────────────────────────────────────────────────────

async function renderHorses() {
  try {
    setLoading(true);
    const horses = await loadHorses();
    const rows = horses.map(h => {
      const storyOk = !!(h.story && String(h.story).trim().length >= 40);
      const imgOk = !!(h.image_path || h.cover_image);
      const contentLabel = storyOk && imgOk
        ? '<span class="text-emerald-600 text-xs font-semibold">Story · image</span>'
        : storyOk
          ? '<span class="text-amber-600 text-xs font-semibold">Story only</span>'
          : '<span class="text-slate-400 text-xs font-semibold">Needs marketplace</span>';
      return `
      <tr class="table-row cursor-pointer" onclick="window.navigateTo('#/horse/${encodeURIComponent(h.microchip)}')">
        <td class="table-cell">
          <div class="font-semibold text-slate-900">${h.name || "—"}</div>
          <div class="text-[11px] font-mono text-slate-400 mt-0.5">${h.microchip}</div>
        </td>
        <td class="table-cell">${h.sex || "—"}</td>
        <td class="table-cell">${h.colour || "—"}</td>
        <td class="table-cell">${h.foaling_date || "—"}</td>
        <td class="table-cell text-slate-600">${h.sire_name || "—"} <span class="text-slate-300">×</span> ${h.dam_name || "—"}</td>
        <td class="table-cell">${contentLabel}</td>
        <td class="table-cell">${h.breeding_url ? `<a href="${h.breeding_url}" target="_blank" class="text-blue-600 text-xs font-semibold hover:underline" onclick="event.stopPropagation()">LoveRacing</a>` : "—"}</td>
      </tr>`;
    }).join("");
    app.innerHTML = `
      <div class="space-y-4 max-w-5xl">
        <div>
          <h2 class="text-xl font-bold text-slate-900">Horses</h2>
          <p class="text-sm text-slate-500">${horses.length} on file · open a horse → tabs for identity / marketplace story / media</p>
        </div>
        <div class="surface-card overflow-hidden">
          <table class="w-full">
            <thead>
              <tr>
                <th class="table-header">Name</th>
                <th class="table-header">Sex</th>
                <th class="table-header">Colour</th>
                <th class="table-header">Foaled</th>
                <th class="table-header">Pedigree</th>
                <th class="table-header">Content</th>
                <th class="table-header">Source</th>
              </tr>
            </thead>
            <tbody>${rows || '<tr><td colspan="7" class="table-cell text-center text-slate-500">No horses yet.</td></tr>'}</tbody>
          </table>
          <div class="px-4 py-3 border-t border-slate-100">
            <button type="button" onclick="window.openAddHorseWizard()" class="btn-primary text-xs">+ Add Horse</button>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Horses render error:', err);
    app.innerHTML = `<div class="surface-card p-6"><h2 class="text-lg font-bold text-rose-700 mb-2">Error</h2><p class="text-sm text-slate-600">${err.message}</p></div>`;
  }
}

// ─── Horse Media Console ─────────────────────────────────────────────────────

async function renderHorseMedia(microchip) {
  try {
    setLoading(true);
    const headers = await window.getAuthHeader();
    const resp = await fetch(`${API}/horses/${encodeURIComponent(microchip)}/media`, { headers });
    if (!resp.ok) throw new Error('Failed to load media');
    const result = await resp.json();
    if (!result.success) throw new Error(result.error);
    
    const { horse, transcripts } = result.data;
    
    // Group transcripts by date
    const transcriptCards = transcripts.map(t => {
      const duration = t.duration_seconds ? `${Math.round(t.duration_seconds)}s` : '—';
      const speakers = t.speakers?.length ? t.speakers.map(s => s.name).join(', ') : '—';
      const date = t.date || 'Unknown';
      
      return `
        <div class="bg-slate-50 rounded-xl border border-slate-200 p-4 mb-3">
          <div class="flex items-start justify-between mb-3">
            <div>
              <h4 class="font-semibold text-slate-900">Transcript — ${date}</h4>
              <p class="text-xs text-slate-500 mt-1">ID: ${t.id}</p>
            </div>
            <div class="text-right">
              <div class="text-xs text-slate-500">Duration</div>
              <div class="text-sm font-semibold text-slate-900">${duration}</div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4 mb-3">
            <div>
              <div class="text-xs text-slate-500 uppercase tracking-wide">Speakers</div>
              <div class="text-sm text-slate-700">${speakers}</div>
            </div>
            <div>
              <div class="text-xs text-slate-500 uppercase tracking-wide">Segments</div>
              <div class="text-sm text-slate-700">${t.segments?.length || 0} segments</div>
            </div>
          </div>
          <div class="bg-white rounded-lg border border-slate-200 p-3 mb-3 max-h-48 overflow-y-auto">
            <div class="text-xs text-slate-600 whitespace-pre-wrap">${t.full_text?.substring(0, 500) || '—'}${(t.full_text?.length || 0) > 500 ? '...' : ''}</div>
          </div>
          <div class="flex gap-2">
            <button onclick="viewFullTranscript('${t.id}')" class="btn-primary">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
              View Full
            </button>
            <button onclick="downloadTranscript('${t.id}', '${t.filepath}')" class="btn-secondary">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
              Download
            </button>
          </div>
        </div>
      `;
    }).join('');
    
    app.innerHTML = `
      <div class="card">
        <div class="flex items-center gap-3 mb-6">
          <a href="#/horses" class="text-slate-400 hover:text-slate-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          </a>
          <div>
            <h2 class="text-xl font-bold text-slate-900">${horse.name}</h2>
            <p class="text-sm text-slate-500">${horse.sex}, ${horse.colour} • Foaled: ${horse.foaling_date || '—'} • Microchip: ${horse.microchip}</p>
          </div>
        </div>
        
        <div class="mb-6">
          <h3 class="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-3">Transcripts (${transcripts.length})</h3>
          ${transcripts.length === 0 ? '<div class="text-slate-500 text-sm">No transcripts found for this horse.</div>' : transcriptCards}
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Horse media render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Media</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

// ─── Owners ──────────────────────────────────────────────────────────────────

async function renderOwners() {
  try {
    setLoading(true);
    const rows = await loadOwners();
    const body = rows.map(o => `
      <tr class="border-b hover:bg-gray-50">
        <td class="px-4 py-3">
          <div class="font-semibold">${o.name || "—"}</div>
          <div class="tag">${o.id}</div>
        </td>
        <td class="px-4 py-3">${o.entity_type || "—"}</td>
        <td class="px-4 py-3">${o.contact_name || "—"}</td>
        <td class="px-4 py-3">${o.email || "—"}</td>
        <td class="px-4 py-3">${o.phone || "—"}</td>
        <td class="px-4 py-3">${o.website ? `<a href="${o.website}" target="_blank" class="breeding-url">Website</a>` : "—"}</td>
      </tr>
    `).join("");
    app.innerHTML = `
      <div class="space-y-4 max-w-5xl">
        <div>
          <h2 class="text-xl font-bold text-slate-900">Owners</h2>
          <p class="text-sm text-slate-500">${rows.length} on file · manual entry</p>
        </div>
        <div class="surface-card overflow-hidden">
          <table class="w-full">
            <thead>
              <tr>
                <th class="table-header">Name</th>
                <th class="table-header">Type</th>
                <th class="table-header">Contact</th>
                <th class="table-header">Email</th>
                <th class="table-header">Phone</th>
                <th class="table-header">Website</th>
              </tr>
            </thead>
            <tbody>${body || '<tr><td colspan="6" class="table-cell text-center text-slate-500">No owners yet.</td></tr>'}</tbody>
          </table>
          <div class="px-4 py-3 border-t border-slate-100">
            <button type="button" onclick="window.openAddOwnerWizard()" class="btn-primary text-xs">+ Add Owner</button>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Owners render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Owners</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

// ─── Trainers ─────────────────────────────────────────────────────────────────

async function renderTrainers() {
  try {
    setLoading(true);
    const rows = await loadTrainers();
    const body = rows.map(t => `
      <tr class="border-b hover:bg-gray-50">
        <td class="px-4 py-3">
          <div class="font-semibold">${t.name || "—"}</div>
          <div class="tag">${t.id}</div>
        </td>
        <td class="px-4 py-3">${t.stable_name || "—"}</td>
        <td class="px-4 py-3">${t.location || "—"}</td>
        <td class="px-4 py-3">${t.contact_name || "—"}</td>
        <td class="px-4 py-3">${t.email || "—"}</td>
        <td class="px-4 py-3">${t.phone || "—"}</td>
        <td class="px-4 py-3">${t.website ? `<a href="${t.website}" target="_blank" class="breeding-url">Website</a>` : "—"}</td>
      </tr>
    `).join("");
    app.innerHTML = `
      <div class="space-y-4 max-w-5xl">
        <div>
          <h2 class="text-xl font-bold text-slate-900">Trainers</h2>
          <p class="text-sm text-slate-500">${rows.length} on file · manual entry</p>
        </div>
        <div class="surface-card overflow-hidden">
          <table class="w-full">
            <thead>
              <tr>
                <th class="table-header">Name</th>
                <th class="table-header">Stable</th>
                <th class="table-header">Location</th>
                <th class="table-header">Contact</th>
                <th class="table-header">Email</th>
                <th class="table-header">Phone</th>
                <th class="table-header">Website</th>
              </tr>
            </thead>
            <tbody>${body || '<tr><td colspan="7" class="table-cell text-center text-slate-500">No trainers yet.</td></tr>'}</tbody>
          </table>
          <div class="px-4 py-3 border-t border-slate-100">
            <button type="button" onclick="window.openAddTrainerWizard()" class="btn-primary text-xs">+ Add Trainer</button>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Trainers render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Trainers</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

// ─── Create HLT Wizard (3-Step) ────────────────────────────────────────────────

async function renderCreateHlt() {
  setLoading(true);
  const [horses, owners, trainers, governing_bodies, leases] = await Promise.all([
    loadHorses(), loadOwners(), loadTrainers(), loadGoverningBodies(), loadHlts()
  ]);

  wizardState.entities = { horses, owners, trainers, governingBodies: governing_bodies, leases };

  // Reset wizard state
  wizardState.step = 1;
  wizardState.draft = {
    horseId: '', ownerId: '', trainerId: '', governingBodyCode: '',
    submissionDate: new Date().toISOString().split('T')[0],
    leaseStartDate: '', leaseLengthMonths: '', percentageLeased: '', numTokens: '',
    monthlyRate: '',
    pricePer1PercentTotal: 0, annualRatePer1Percent: 0, totalIssuanceValue: 0,
    pricePerToken: 0, fractionalInterestPerToken: 0, leaseEndDate: '',
    tokenName: '', erc20Identifier: '', variations: 'n/a',
    investorReturn: '75', ownerStakesSplit: '25',
    horseAssetOwner: '', horseMicrochip: '',
  };
  wizardState.lastEditedField = null;

  const horseOpts = '<option value="" disabled selected>Select Horse</option>' + horses.map(h => `<option value="${h.microchip}">${h.name}</option>`).join("");
  const ownerOpts = '<option value="" disabled selected>Select Owner</option>' + owners.map(o => `<option value="${o.id}">${o.name}</option>`).join("");
  const trainerOpts = '<option value="" disabled selected>Select Trainer</option>' + trainers.map(t => `<option value="${t.id}">${t.name} — ${t.stable_name}</option>`).join("");
  const govOpts = '<option value="" disabled selected>Select Governing Body</option>' + governing_bodies.map(g => `<option value="${g.governing_body_code}">${g.governing_body_name}</option>`).join("");

  app.innerHTML = `
    <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-start justify-center p-6 pt-10 z-50 overflow-y-auto" onclick="if(event.target===this) closeWizard()">
      <div class="bg-white w-full max-w-6xl rounded-2xl shadow-2xl overflow-hidden flex flex-col my-8" onclick="event.stopPropagation()">
        <!-- Header Bar -->
        <div class="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 px-8 py-4 flex-shrink-0">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              </div>
              <div>
                <h2 class="text-xl font-bold text-white tracking-tight">Create HLT Agreement</h2>
                <p class="text-blue-100 text-sm">Step <span id="wizard-step-num" class="font-bold">${wizardState.step}</span> of 3 — <span id="wizard-step-name" class="font-medium">Entities</span></p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <button type="button" onclick="closeWizard()" class="group flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-all">
                <svg class="w-5 h-5 text-white/90 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                <span class="text-white font-medium">Close</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="bg-white border-b border-slate-200 px-8 py-3 flex-shrink-0">
          <div class="flex items-center justify-between max-w-2xl mx-auto">
            <div class="flex items-center gap-2 flex-1">
              <div class="step-dot-large ${wizardState.step >= 1 ? 'active' : ''}">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-semibold ${wizardState.step >= 1 ? 'text-slate-900' : 'text-slate-400'} truncate">Entities</p>
                <p class="text-[10px] ${wizardState.step >= 1 ? 'text-slate-500' : 'text-slate-400'} truncate">Select horse & counterparties</p>
              </div>
            </div>
            <div class="progress-line ${wizardState.step > 1 ? 'complete' : ''}"></div>
            <div class="flex items-center gap-2 flex-1">
              <div class="step-dot-large ${wizardState.step >= 2 ? 'active' : ''}">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-semibold ${wizardState.step >= 2 ? 'text-slate-900' : 'text-slate-400'} truncate">Terms & Pricing</p>
                <p class="text-[10px] ${wizardState.step >= 2 ? 'text-slate-500' : 'text-slate-400'} truncate">Define lease & economics</p>
              </div>
            </div>
            <div class="progress-line ${wizardState.step > 2 ? 'complete' : ''}"></div>
            <div class="flex items-center gap-2 flex-1">
              <div class="step-dot-large ${wizardState.step >= 3 ? 'active' : ''}">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-semibold ${wizardState.step >= 3 ? 'text-slate-900' : 'text-slate-400'} truncate">Preview & Save</p>
                <p class="text-[10px] ${wizardState.step >= 3 ? 'text-slate-500' : 'text-slate-400'} truncate">Review & generate</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Main Content Area -->
        <div class="flex-1 overflow-y-auto bg-gradient-to-b from-slate-50 to-white max-h-[calc(100vh-280px)]">
          <div class="px-8 py-6">
            <div id="wizard-step-content"></div>
            <div id="wizard-error" class="hidden mt-6 p-4 bg-rose-50 border-l-4 border-rose-500 rounded-r-lg">
              <div class="flex items-start gap-3">
                <svg class="w-5 h-5 text-rose-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                <div>
                  <p class="font-semibold text-rose-800 mb-1">Please fix the following errors:</p>
                  <p class="text-sm text-rose-700" id="wizard-error-text"></p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer Action Bar -->
        <div class="bg-white border-t border-slate-200 px-8 py-4 flex-shrink-0">
          <div class="flex items-center justify-between">
            <button type="button" id="wizard-back" onclick="wizardPrev()" class="group flex items-center gap-2 px-5 py-2.5 text-slate-600 font-semibold hover:bg-slate-100 rounded-lg transition-all">
              <svg class="w-5 h-5 group-hover:-translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
              <span>Back</span>
            </button>
            <div id="wizard-next-area">
              <button type="button" id="wizard-next" onclick="wizardNext()" class="group flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all">
                <span>Next Step</span>
                <svg class="w-5 h-5 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  renderWizardStep();
}

window.closeWizard = function() {
  window.location.hash = "#/hlts";
  // render() will be called by hashchange listener
}

function renderWizardStep() {
  const content = document.getElementById('wizard-step-content');
  const backBtn = document.getElementById('wizard-back');
  const nextArea = document.getElementById('wizard-next-area');
  const stepNum = document.getElementById('wizard-step-num');
  const stepName = document.getElementById('wizard-step-name');

  stepNum.textContent = wizardState.step;
  
  // Update step name in header
  const stepNames = ['Entities', 'Terms & Pricing', 'Preview & Save'];
  if (stepName) stepName.textContent = stepNames[wizardState.step - 1];

  if (wizardState.step === 1) {
    backBtn.onclick = closeWizard;
    backBtn.innerHTML = '<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg><span>Quit</span>';
    nextArea.innerHTML = '<button type="button" id="wizard-next" onclick="wizardNext()" class="group flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all"><span>Next Step</span><svg class="w-5 h-5 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg></button>';
    content.innerHTML = renderStep1Entities();
    bindStep1Events();
  } else if (wizardState.step === 2) {
    backBtn.onclick = wizardPrev;
    backBtn.innerHTML = '<svg class="w-5 h-5 mr-2 group-hover:-translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg><span>Back</span>';
    nextArea.innerHTML = '<button type="button" id="wizard-next" onclick="wizardNext()" class="group flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all"><span>Next Step</span><svg class="w-5 h-5 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg></button>';
    content.innerHTML = renderStep2TermsPricing();
    bindStep2Events();
  } else if (wizardState.step === 3) {
    backBtn.onclick = wizardPrev;
    backBtn.innerHTML = '<svg class="w-5 h-5 mr-2 group-hover:-translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg><span>Back</span>';
    nextArea.innerHTML = '<button type="button" onclick="wizardSave()" class="group flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-semibold rounded-lg hover:from-emerald-700 hover:to-teal-700 shadow-lg hover:shadow-xl transition-all"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg><span>Generate & Save HLT</span></button>';
    content.innerHTML = renderStep3Preview();
  }
}

function renderStep1Entities() {
  const { horses, owners, trainers, governingBodies } = wizardState.entities;
  const horseOpts = '<option value="" disabled selected>Select Horse</option>' + horses.map(h => `<option value="${h.microchip}">${h.name}</option>`).join("");
  const ownerOpts = '<option value="" disabled selected>Select Owner</option>' + owners.map(o => `<option value="${o.id}">${o.name}</option>`).join("");
  const trainerOpts = '<option value="" disabled selected>Select Trainer</option>' + trainers.map(t => `<option value="${t.id}">${t.name} — ${t.stable_name}</option>`).join("");
  const govOpts = '<option value="" disabled selected>Select Governing Body</option>' + governingBodies.map(g => `<option value="${g.governing_body_code}">${g.governing_body_name}</option>`).join("");

  return `
    <div class="space-y-6">
      <!-- Step 1: Entities Selection -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Entities Card -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
          <div class="flex items-center gap-3 mb-5">
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
            </div>
            <h4 class="text-lg font-semibold text-slate-900">Entities</h4>
          </div>
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Submission Date <span class="text-rose-500">*</span></label>
              <input type="date" id="w-submissionDate" value="${wizardState.draft.submissionDate}" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Horse <span class="text-rose-500">*</span></label>
              <select id="w-horseId" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all cursor-pointer">${horseOpts}</select>
            </div>
          </div>
        </div>

        <!-- Counterparties Card -->
        <div class="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
          <div class="flex items-center gap-3 mb-5">
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
            </div>
            <h4 class="text-lg font-semibold text-slate-900">Counterparties</h4>
          </div>
          <div class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Trainer / Stable <span class="text-rose-500">*</span></label>
              <select id="w-trainerId" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all cursor-pointer">${trainerOpts}</select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Owner <span class="text-rose-500">*</span></label>
              <select id="w-ownerId" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all cursor-pointer">${ownerOpts}</select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">Governing Body <span class="text-rose-500">*</span></label>
              <select id="w-governingBodyCode" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all cursor-pointer">${govOpts}</select>
            </div>
          </div>
        </div>
      </div>

      <!-- Info Banner -->
      <div class="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3">
        <svg class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <p class="text-sm text-blue-800">Select the horse and all counterparties involved in this HLT agreement. All fields are required to proceed.</p>
      </div>
    </div>
  `;
}

function bindStep1Events() {
  ['submissionDate', 'horseId', 'trainerId', 'ownerId', 'governingBodyCode'].forEach(field => {
    const el = document.getElementById('w-' + field);
    if (el) el.addEventListener('change', (e) => {
      wizardState.draft[field] = e.target.value;
      // Auto-fill governing body from horse
      if (field === 'horseId' && e.target.value) {
        const horse = wizardState.entities.horses.find(h => h.microchip === e.target.value);
        if (horse && horse.governing_body_code) {
          wizardState.draft.governingBodyCode = horse.governing_body_code;
          document.getElementById('w-governingBodyCode').value = horse.governing_body_code;
        }
        // Auto-fill microchip
        wizardState.draft.horseMicrochip = horse?.microchip || '';
      }
      // Auto-fill horseAssetOwner from owner
      if (field === 'ownerId' && e.target.value) {
        const owner = wizardState.entities.owners.find(o => o.id === e.target.value);
        if (owner) {
          wizardState.draft.horseAssetOwner = owner.name;
        }
      }
    });
  });
}

function renderStep2TermsPricing() {
  const d = wizardState.draft;
  const leaseEndDate = d.leaseStartDate && d.leaseLengthMonths ? addMonthsIso(d.leaseStartDate, parseNumber(d.leaseLengthMonths)) : '';
  const pctPerToken = parseNumber(d.percentageLeased) && parseNumber(d.numTokens) ? (parseNumber(d.percentageLeased) / parseNumber(d.numTokens)).toFixed(4) : '0.0000';
  const ownerSplit = parseNumber(d.ownerStakesSplit);
  const investorSplit = Math.max(0, 100 - ownerSplit);

  return `
    <div class="space-y-6">
      <!-- Step 2 Header -->
      <div class="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-100 rounded-xl p-5">
        <h4 class="text-lg font-semibold text-slate-900 mb-1">Lease Terms & Pricing</h4>
        <p class="text-sm text-slate-600">Define the lease period, token economics, and pricing structure</p>
      </div>

      <!-- Block 1: Lease Period -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          </div>
          <h4 class="text-lg font-semibold text-slate-900">Lease Period</h4>
        </div>
        <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Start Date <span class="text-rose-500">*</span></label>
            <input type="date" id="w-leaseStartDate" value="${d.leaseStartDate}" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all" />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Duration (Months) <span class="text-rose-500">*</span></label>
            <input type="number" id="w-leaseLengthMonths" value="${d.leaseLengthMonths}" min="1" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all" placeholder="e.g., 16" />
          </div>
          <div class="flex flex-col justify-end">
            <label class="block text-sm font-medium text-slate-500 mb-1">End Date</label>
            <p class="text-base font-semibold text-slate-900">${leaseEndDate || 'dd/mm/yyyy'}</p>
          </div>
        </div>
      </div>

      <!-- Block 2: Token Economics -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-violet-600 flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
          </div>
          <h4 class="text-lg font-semibold text-slate-900">Token Economics</h4>
        </div>
        <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Stake to Lease (%) <span class="text-rose-500">*</span></label>
            <input type="number" id="w-percentageLeased" step="0.1" value="${d.percentageLeased}" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 transition-all" placeholder="e.g., 5" />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Total Tokens <span class="text-rose-500">*</span></label>
            <input type="number" id="w-numTokens" value="${d.numTokens}" min="1" class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-violet-500 focus:border-violet-500 transition-all" placeholder="e.g., 20" />
          </div>
          <div class="flex flex-col justify-end">
            <label class="block text-sm font-medium text-slate-500 mb-1">Token Size</label>
            <p class="text-base font-semibold text-slate-900">${pctPerToken}%</p>
          </div>
        </div>
      </div>

      <!-- Block 3: Pricing Engine (Bidirectional) -->
      <div class="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-6">
        <div class="flex items-center justify-between mb-5">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            </div>
            <div>
              <h4 class="text-lg font-semibold text-slate-900">Pricing Engine</h4>
              <p class="text-xs text-blue-600 font-medium">Live Bidirectional Calculation</p>
            </div>
          </div>
          <span class="rounded-full bg-blue-600 px-3 py-1 text-xs font-bold text-white uppercase tracking-wide">Live</span>
        </div>
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Price per 1% Monthly <span class="text-rose-500">*</span></label>
            <div class="relative">
              <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
              <input
                type="number"
                step="0.01"
                id="w-monthlyRate"
                value="${d.monthlyRate}"
                class="w-full pl-8 pr-4 py-3 text-lg font-bold text-blue-700 bg-white border border-blue-200 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                placeholder="0.00"
              />
            </div>
          </div>

          <div class="lg:col-span-1 flex flex-col justify-center items-center text-slate-400 lg:hidden">
            <div class="h-px w-8 bg-slate-300" />
            <span class="text-[10px] font-bold uppercase py-1">OR</span>
            <div class="h-px w-8 bg-slate-300" />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Total Issuance Value</label>
            <div class="relative">
              <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-medium">$</span>
              <input
                type="number"
                step="0.01"
                id="w-totalIssuanceValue"
                value="${d.totalIssuanceValue > 0 ? d.totalIssuanceValue.toFixed(2) : ''}"
                class="w-full pl-8 pr-4 py-3 text-lg font-bold text-blue-700 bg-white border border-blue-200 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                placeholder="0.00"
              />
            </div>
          </div>
        </div>

        <div class="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4 pt-5 border-t border-blue-200">
          <div class="bg-white/60 rounded-lg p-4">
            <p class="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Price per 1% Over Lease</p>
            <p class="text-xl font-black text-slate-900">$${(parseNumber(d.monthlyRate) * parseNumber(d.leaseLengthMonths)).toFixed(2)}</p>
          </div>
          <div class="bg-white/60 rounded-lg p-4">
            <p class="text-xs font-bold text-blue-600 uppercase tracking-wide mb-1">Price Per Token</p>
            <div class="flex items-center justify-end gap-2">
              <span class="text-sm text-slate-400 font-medium">$</span>
              <input
                type="number"
                step="0.01"
                id="w-pricePerToken"
                value="${d.pricePerToken > 0 ? d.pricePerToken.toFixed(2) : ''}"
                class="w-32 text-right text-xl font-black text-blue-800 bg-transparent border-b-2 border-blue-300 focus:border-blue-600 focus:outline-none pb-1"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Block 4: Commercial Terms -->
      <div class="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-lg transition-shadow">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
          </div>
          <h4 class="text-lg font-semibold text-slate-900">Commercial Terms</h4>
        </div>
        <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Owner Stakes Split (%) <span class="text-rose-500">*</span></label>
            <input
              type="number"
              step="0.1"
              id="w-ownerStakesSplit"
              value="${d.ownerStakesSplit}"
              class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 transition-all"
              placeholder="e.g., 25"
            />
            <p class="mt-2 text-xs text-slate-500">Portion of prize money retained by the lessor/owner.</p>
          </div>
          <div class="flex flex-col justify-center rounded-xl border-2 border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 px-5 py-4">
            <p class="text-xs font-bold text-amber-700 uppercase tracking-wide">Investor Return</p>
            <p class="mt-2 text-3xl font-black text-amber-900">${investorSplit}%</p>
            <p class="text-xs text-amber-700 font-medium italic">of stakes won proportionate to investment</p>
          </div>
        </div>
      </div>

      <!-- Metadata -->
      <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-4">
          <label class="block text-xs font-medium text-slate-600 uppercase tracking-wide mb-2">Asset Owner (Legal)</label>
          <input type="text" id="w-horseAssetOwner" value="${d.horseAssetOwner}" class="w-full px-3 py-2 bg-white border border-slate-300 rounded-md focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition-all" />
        </div>
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-4">
          <label class="block text-xs font-medium text-slate-600 uppercase tracking-wide mb-2">Variations</label>
          <input type="text" id="w-variations" value="${d.variations}" class="w-full px-3 py-2 bg-white border border-slate-300 rounded-md focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition-all" />
        </div>
      </div>
    </div>
  `;
}

function bindStep2Events() {
  const fields = [
    'leaseStartDate', 'leaseLengthMonths', 'percentageLeased', 'numTokens',
    'monthlyRate', 'totalIssuanceValue', 'pricePerToken',
    'ownerStakesSplit', 'horseAssetOwner', 'variations'
  ];

  fields.forEach(field => {
    const el = document.getElementById('w-' + field);
    if (!el) return;

    const eventType = el.tagName === 'SELECT' ? 'change' : 'input';
    el.addEventListener(eventType, (e) => {
      const value = e.target.value;
      wizardState.draft[field] = value;
      wizardState.lastEditedField = field;

      // Update derived fields using hlt-engine
      const derived = calculateDerivedFields(wizardState.draft, field);
      Object.assign(wizardState.draft, derived);

      // Re-render step 2 to show updated values
      renderWizardStep();
      // Re-bind events after re-render
      setTimeout(bindStep2Events, 0);
    });
  });

  // Also update lease end date display when dates change
  const startEl = document.getElementById('w-leaseStartDate');
  const lengthEl = document.getElementById('w-leaseLengthMonths');
  if (startEl) startEl.addEventListener('change', updateLeaseEndDate);
  if (lengthEl) lengthEl.addEventListener('input', updateLeaseEndDate);
}

function updateLeaseEndDate() {
  const start = document.getElementById('w-leaseStartDate')?.value;
  const length = document.getElementById('w-leaseLengthMonths')?.value;
  if (start && length) {
    const endDate = addMonthsIso(start, parseNumber(length));
    wizardState.draft.leaseEndDate = endDate;
    // The re-render in bindStep2Events will update the display
  }
}

function renderStep3Preview() {
  const d = wizardState.draft;
  const horse = wizardState.entities.horses.find(h => h.microchip === d.horseId);
  const trainer = wizardState.entities.trainers.find(t => t.id === d.trainerId);
  const owner = wizardState.entities.owners.find(o => o.id === d.ownerId);
  const governing = wizardState.entities.governingBodies.find(g => g.governing_body_code === d.governingBodyCode);

  if (!horse || !trainer || !owner || !governing) {
    return `<div class="text-center py-8 text-slate-500">Please complete Steps 1 & 2 first.</div>`;
  }

  // Auto-generate token name and ERC20 if not set
  const seq = wizardState.entities.leases.filter(l => l.horse_microchip === horse.microchip).length + 1;
  const tokenName = d.tokenName || `HLT – ${horse.name} ${horse.country_code || 'NZ'}${String(seq).padStart(2, '0')}`;
  const erc20Identifier = d.erc20Identifier || generateErc20Identifier(horse.name, `LSE-${String(seq).padStart(4, '0')}`);

  // Format dates
  const formalDate = (iso) => {
    if (!iso) return '—';
    const date = new Date(iso + 'T00:00:00');
    return date.toLocaleDateString('en-NZ', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  return `
    <div class="mt-5 space-y-4">
      <div class="rounded-xl border-2 border-blue-500 bg-blue-600 p-6 text-white shadow-lg">
        <p class="text-[10px] font-bold uppercase tracking-[0.2em] opacity-80">HLT Token Identity</p>
        <h5 class="mt-1 text-2xl font-black tracking-tight">${tokenName}</h5>
        <div class="mt-4 flex items-center justify-between border-t border-white/20 pt-4">
          <div>
            <p class="text-[10px] font-bold uppercase opacity-80">ERC-20 Identifier</p>
            <p class="text-sm font-mono font-bold">${erc20Identifier}</p>
          </div>
          <div class="text-right">
            <p class="text-[10px] font-bold uppercase opacity-80">Total Issuance</p>
            <p class="text-2xl font-black">$${parseNumber(d.totalIssuanceValue).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="entity-card">
          <h6 class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Lease Overview</h6>
          <div class="mt-4 space-y-3">
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">Stake Leased</span>
              <span class="font-bold text-slate-900">${parseNumber(d.percentageLeased)}%</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">Duration</span>
              <span class="font-bold text-slate-900">${parseNumber(d.leaseLengthMonths)} Months</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">Period</span>
              <span class="font-bold text-slate-900 text-xs">${formalDate(d.leaseStartDate)} → ${formalDate(d.leaseEndDate)}</span>
            </div>
          </div>
        </div>

        <div class="entity-card">
          <h6 class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Tokenomics</h6>
          <div class="mt-4 space-y-3">
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">Total Tokens</span>
              <span class="font-bold text-slate-900">${parseNumber(d.numTokens)}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">Size per Token</span>
              <span class="font-bold text-slate-900">${parseNumber(d.fractionalInterestPerToken).toFixed(4)}%</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-500 text-blue-600 font-bold">Price per Token</span>
              <span class="font-black text-blue-700 text-lg">$${parseNumber(d.pricePerToken).toFixed(2)}</span>
            </div>
          </div>
        </div>

        <div class="entity-card lg:col-span-2">
          <h6 class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Commercial Returns</h6>
          <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p class="text-[10px] font-bold text-slate-500 uppercase">Monthly per 1%</p>
              <p class="text-xl font-bold text-slate-900">$${parseNumber(d.monthlyRate).toFixed(2)}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-slate-500 uppercase">Monthly Total</p>
              <p class="text-xl font-bold text-slate-900">$${(parseNumber(d.totalIssuanceValue) / parseNumber(d.leaseLengthMonths)).toFixed(2)}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-blue-600 uppercase">Investor Prize Share</p>
              <p class="text-xl font-black text-blue-700">${100 - parseNumber(d.ownerStakesSplit)}%</p>
              <p class="text-[9px] text-slate-400 uppercase italic">Proportionate to investment</p>
            </div>
          </div>
        </div>
      </div>

      <div class="entity-card">
        <h6 class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Entities</h6>
        <div class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><p class="text-slate-500">Horse</p><p class="font-semibold">${horse.name}</p></div>
          <div><p class="text-slate-500">Trainer</p><p class="font-semibold">${trainer.name}</p></div>
          <div><p class="text-slate-500">Owner</p><p class="font-semibold">${owner.name}</p></div>
          <div><p class="text-slate-500">Governing Body</p><p class="font-semibold">${governing.governing_body_name}</p></div>
        </div>
      </div>
    </div>
  `;
}

function wizardNext() {
  if (wizardState.step === 1) {
    // Validate step 1
    if (!wizardState.draft.horseId || !wizardState.draft.trainerId || !wizardState.draft.ownerId || !wizardState.draft.governingBodyCode) {
      showError('Please select all required entities (Horse, Trainer, Owner, Governing Body)');
      return;
    }
  } else if (wizardState.step === 2) {
    // Validate step 2
    if (!wizardState.draft.leaseStartDate || !wizardState.draft.leaseLengthMonths || !wizardState.draft.percentageLeased || !wizardState.draft.numTokens || !wizardState.draft.monthlyRate) {
      showError('Please fill in all required lease terms and pricing fields');
      return;
    }
    if (parseNumber(wizardState.draft.percentageLeased) <= 0 || parseNumber(wizardState.draft.numTokens) <= 0 || parseNumber(wizardState.draft.leaseLengthMonths) <= 0) {
      showError('Lease terms must be positive numbers');
      return;
    }
  }
  wizardState.step++;
  renderWizardStep();
}

function wizardPrev() {
  wizardState.step--;
  renderWizardStep();
}

function showError(msg) {
  const errorEl = document.getElementById('wizard-error');
  errorEl.textContent = msg;
  errorEl.classList.remove('hidden');
  setTimeout(() => errorEl.classList.add('hidden'), 5000);
}

async function wizardSave() {
  const d = wizardState.draft;
  const horse = wizardState.entities.horses.find(h => h.microchip === d.horseId);
  const trainer = wizardState.entities.trainers.find(t => t.id === d.trainerId);
  const owner = wizardState.entities.owners.find(o => o.id === d.ownerId);
  const governing = wizardState.entities.governingBodies.find(g => g.governing_body_code === d.governingBodyCode);

  if (!horse || !trainer || !owner || !governing) {
    showError('Missing entity data');
    return;
  }

  // Generate final lease ID
  const seq = wizardState.entities.leases.filter(l => l.horse_microchip === horse.microchip).length + 1;
  const leaseId = `LSE-${String(seq).padStart(4, '0')}`;
  const tokenName = d.tokenName || `HLT – ${horse.name} ${horse.country_code || 'NZ'}${String(seq).padStart(2, '0')}`;
  const erc20Identifier = d.erc20Identifier || generateErc20Identifier(horse.name, leaseId);

  const payload = {
    horse_microchip: horse.microchip,
    owner_id: owner.id,
    trainer_id: trainer.trainer_id,
    governing_body_code: governing.governing_body_code,
    lease_id: leaseId,
    start_date: d.leaseStartDate,
    end_date: d.leaseEndDate || addMonthsIso(d.leaseStartDate, parseNumber(d.leaseLengthMonths)),
    duration_months: parseNumber(d.leaseLengthMonths),
    percent_leased: parseNumber(d.percentageLeased),
    token_count: parseNumber(d.numTokens),
    min_unit_size: parseNumber(d.fractionalInterestPerToken),
    price_basis: 'per_1pct',
    price_period: 'month',
    price_amount: parseNumber(d.monthlyRate),
    investor_share_percent: 100 - parseNumber(d.ownerStakesSplit),
    owner_share_percent: parseNumber(d.ownerStakesSplit),
    platform_fee_percent: 0,
  };

  try {
    const resp = await createHltWorkflow(payload);
    if (!resp.success) {
      showError(resp.error || 'Failed to create HLT');
      return;
    }
    const hltId = resp.data?.id;
    showToast('HLT created! Generating term sheet...', 'success');

    // Auto-generate term sheet
    if (hltId) {
      const { buildHltDocumentHtml } = await import('./hlt-engine.js');
      const record = {
        lease_id: leaseId,
        token_name: tokenName,
        erc20_identifier: erc20Identifier,
        submission_date: d.submissionDate,
        horse_name: horse.name,
        horse_country: horse.country_code || 'NZ',
        horse_microchip: horse.microchip,
        trainer_name: trainer.name,
        owner_name: owner.name,
        governing_body_name: governing.governing_body_name,
        governing_body_code: governing.governing_body_code,
        lease_start_date: d.leaseStartDate,
        lease_length_months: parseNumber(d.leaseLengthMonths),
        percentage_leased: parseNumber(d.percentageLeased),
        num_tokens: parseNumber(d.numTokens),
        token_price_nzd: parseNumber(d.pricePerToken),
        total_issuance_value: parseNumber(d.totalIssuanceValue),
        percentage_per_token: parseNumber(d.fractionalInterestPerToken),
        investor_stakes_split: 100 - parseNumber(d.ownerStakesSplit),
        variations: d.variations || 'n/a',
      };
      const html = buildHltDocumentHtml(record);
      const blob = new Blob([html], { type: 'text/html' });
      const formData = new FormData();
      formData.append('file', blob, `term-sheet-${hltId}.html`);
      formData.append('doc_type', 'term_sheet');
      await fetch(`/api/hlts/${hltId}/documents`, { method: 'POST', body: formData });
    }

    closeWizard();
  } catch (err) {
    showError('Error: ' + err.message);
  }
}

// ─── HLTs Registry (Enhanced) ────────────────────────────────────────────────

// HLTs state
let hltsState = {
  allHlts: [],
  filteredHlts: [],
  horseFilter: 'all',
  statusFilter: 'all',
  expandedRow: null,
  editingTermSheet: null,
  termSheetEdit: {},
  hltDocuments: {},
  horses: [],
  owners: [],
  trainers: [],
  governingBodies: [],
};

async function renderHlts() {
  try {
    setLoading(true);
    const [hlts, horses, owners, trainers, governingBodies] = await Promise.all([
      loadHlts(), loadHorses(), loadOwners(), loadTrainers(), loadGoverningBodies()
    ]);

    hltsState.allHlts = hlts;
    hltsState.horses = horses;
    hltsState.owners = owners;
    hltsState.trainers = trainers;
    hltsState.governingBodies = governingBodies;

    applyHltsFilters();
    renderHltsView();
  } catch (err) {
    console.error('HLTs render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading HLTs</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

// ─── HLTs Registry (Enhanced with compact view) ────────────────────────────────────────────────

function renderHltsView() {
  const { filteredHlts, horseFilter, statusFilter, horses } = hltsState;

  const horseOpts = '<option value="all">All horses</option>' +
    horses.map(h => `<option value="${h.microchip}" ${horseFilter === h.microchip ? 'selected' : ''}>${h.name}</option>`).join("");

  const statusOpts = '<option value="all">All statuses</option>' +
    HLT_STATUSES.map(s => `<option value="${s.id}" ${statusFilter === s.id ? 'selected' : ''}>${s.label}</option>`).join("");

  const rows = filteredHlts.map(hlt => {
    const st = normalizeHltStatus(hlt.status);
    const docs = [
      hlt.term_sheet_status === 'complete' || hlt.term_sheet_status === 'completed' ? 'TS' : null,
      hlt.pds_status === 'complete' || hlt.pds_status === 'completed' ? 'PDS' : null,
      hlt.sa_status === 'complete' || hlt.sa_status === 'completed' ? 'SA' : null,
    ].filter(Boolean).join(' · ') || '—';
    return `
      <tr class="table-row cursor-pointer" onclick="window.navigateTo('#/hlt/${hlt.id}')">
        <td class="table-cell">
          <div class="font-semibold text-slate-900">${hlt.horse_name || hlt.horse_microchip}</div>
          <div class="text-[11px] text-slate-400 mt-0.5">${hlt.owner_name || '—'} · ${hlt.trainer_name || '—'}</div>
        </td>
        <td class="table-cell font-mono text-xs text-slate-500">${hlt.id}</td>
        <td class="table-cell">${hltStatusPill(st)}</td>
        <td class="table-cell text-slate-600">${hlt.percent_leased != null ? hlt.percent_leased + '%' : '—'} · ${hlt.duration_months != null ? hlt.duration_months + 'm' : '—'}</td>
        <td class="table-cell text-xs text-slate-500">${docs}</td>
      </tr>
    `;
  }).join("");

  app.innerHTML = `
    <div class="space-y-4 max-w-5xl">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 class="text-xl font-bold text-slate-900">HLT Listings</h2>
          <p class="text-sm text-slate-500">One horse can have many HLTs. Status drives website inventory.</p>
        </div>
        <button type="button" onclick="openCreateHltWizard()" class="btn-primary text-xs">+ Create HLT</button>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <select onchange="setHltHorseFilter(this.value)" class="form-input-sm w-auto min-w-[10rem]">${horseOpts}</select>
        <select onchange="setHltStatusFilter(this.value)" class="form-input-sm w-auto min-w-[9rem]">${statusOpts}</select>
        ${(horseFilter !== 'all' || statusFilter !== 'all') ? `<button type="button" onclick="clearHltFilters()" class="btn-ghost text-xs">Clear</button>` : ''}
      </div>

      <div class="surface-card overflow-hidden">
        <table class="w-full">
          <thead>
            <tr>
              <th class="table-header">Horse</th>
              <th class="table-header">HLT</th>
              <th class="table-header">Status</th>
              <th class="table-header">Terms</th>
              <th class="table-header">Docs</th>
            </tr>
          </thead>
          <tbody>
            ${rows || '<tr><td colspan="5" class="table-cell text-center text-slate-500">No HLTs match.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function applyHltsFilters() {
  let list = hltsState.allHlts;
  if (hltsState.horseFilter !== 'all') {
    list = list.filter(l => l.horse_microchip === hltsState.horseFilter);
  }
  if (hltsState.statusFilter !== 'all') {
    list = list.filter(l => normalizeHltStatus(l.status) === hltsState.statusFilter);
  }
  hltsState.filteredHlts = list;
}

function renderHltRow(hlt) {
  const { expandedRow, horses, owners, trainers } = hltsState;
  const isExpanded = expandedRow === hlt.id;
  const horse = horses.find(h => h.microchip === hlt.horse_microchip);
  const owner = owners.find(o => o.id === hlt.owner_id);
  const trainer = trainers.find(t => t.id === hlt.trainer_id);

  const statusBadges = {
    draft: 'badge-draft', review: 'badge-review', complete: 'badge-complete',
    listing: 'badge-listing', listed: 'badge-listed', published: 'badge-complete'
  };
  const statusBadge = statusBadges[hlt.status] || 'badge-draft';

  const workflowStageLabel = (status) => {
    const s = status.toLowerCase();
    if (s === 'draft') return 'Draft';
    if (s === 'review') return 'Review';
    if (s === 'complete') return 'Complete';
    if (s === 'listing') return 'Listing...';
    if (s === 'listed') return 'Listed';
    if (s === 'published') return 'Published';
    return status;
  };

  const workflowStageIcon = (status) => {
    const s = status.toLowerCase();
    if (s === 'draft') return '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>';
    if (s === 'review') return '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>';
    if (s === 'complete') return '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>';
    if (s === 'listing') return '<svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>';
    if (s === 'listed') return '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>';
    return '';
  };

  return `
    <tr class="table-row" onclick="toggleHltRow('${hlt.id}')">
      <td class="table-cell font-mono text-xs font-medium text-slate-900">
        <div class="flex items-center gap-2">
          ${isExpanded
            ? '<svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>'
            : '<svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>'}
          ${hlt.lease_id || hlt.id}
        </div>
      </td>
      <td class="table-cell">
        ${horse ? `
          <a href="#/hlt/${hlt.id}" onclick="event.stopPropagation()" class="inline-flex items-center gap-2 font-semibold text-blue-700 hover:underline">
            ${horse.name}
          </a>
        ` : `<span class="text-slate-700">${hlt.horse_microchip}</span>`}
      </td>
      <td class="table-cell text-slate-700">${hlt.start_date || '—'}</td>
      <td class="table-cell text-slate-700">${hlt.percent_leased || hlt.percentage_leased || '—'}%</td>
      <td class="table-cell">
        <div class="flex items-center gap-3">
          <span class="badge ${statusBadge} inline-flex items-center gap-1.5">
            ${workflowStageIcon(hlt.status)}
            ${workflowStageLabel(hlt.status)}
          </span>
          ${hlt.status === 'complete' ? `
            <button type="button" onclick="event.stopPropagation(); listToPlatform('${hlt.id}')" class="btn-success">
              List to Platform →
            </button>
          ` : ''}
        </div>
      </td>
    </tr>
    ${isExpanded ? renderHltExpandedRow(hlt, horse, owner, trainer) : ''}
  `;
}

function renderHltExpandedRow(hlt, horse, owner, trainer) {
  const { editingTermSheet } = hltsState;
  const isEditing = editingTermSheet === hlt.id;

  // Load documents from state (populated by loadHltDocuments)
  const docs = hltsState.hltDocuments?.[hlt.id] || [];
  const getDocs = (type) => docs.filter(d => d.doc_type === type);
  const termSheetDocs = getDocs("term_sheet");
  const pdsDocs = getDocs("pds");
  const saDocs = getDocs("sa");
  const images = getDocs("photo");

  const docBadge = (status) => {
    if (status === "complete") return '<span class="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">complete</span>';
    if (status === "flagged") return '<span class="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">flagged</span>';
    return '<span class="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700">pending</span>';
  };

  const termSheetStatus = termSheetDocs.length > 0 ? "complete" : (hlt.term_sheet_status || "pending");
  const pdsStatus = pdsDocs.length > 0 ? "complete" : (hlt.pds_status || "pending");
  const saStatus = saDocs.length > 0 ? "complete" : (hlt.sa_status || "pending");

  // Term sheet fields for editing
  const termSheetFields = [
    { key: "token_name", label: "Token Name", type: "text", value: hlt.token_name || `HLT – ${horse?.name || "Asset"} ${hlt.lease_id?.replace("LSE-", "")}` },
    { key: "erc20_identifier", label: "ERC20 Identifier", type: "text", value: hlt.erc20_identifier || `TVHLT${horse?.name?.substring(0,3).toUpperCase()}${hlt.lease_id?.replace("LSE-", "")}` },
    { key: "percentage_leased", label: "Percentage Leased (%)", type: "number", value: hlt.percent_leased || hlt.percentage_leased },
    { key: "token_count", label: "Number of Tokens", type: "number", value: hlt.token_count },
    { key: "percent_per_token", label: "% Per Token", type: "number", step: "0.01", value: hlt.percent_per_token },
    { key: "token_price_nzd", label: "Token Price (NZD)", type: "number", step: "0.01", value: hlt.token_price_nzd },
    { key: "total_issuance_value_nzd", label: "Total Issuance Value (NZD)", type: "number", step: "0.01", value: hlt.total_issuance_value_nzd },
    { key: "investor_share_percent", label: "Investor Split (%)", type: "number", value: hlt.investor_share_percent },
    { key: "owner_share_percent", label: "Owner Split (%)", type: "number", value: hlt.owner_share_percent },
    { key: "start_date", label: "Start Date", type: "date", value: hlt.start_date },
    { key: "duration_months", label: "Lease Length (months)", type: "number", value: hlt.duration_months },
    { key: "variations", label: "Variations", type: "text", value: hlt.notes || hlt.variations || "n/a" },
  ];

  let editFormHtml = "";
  if (isEditing) {
    editFormHtml = `
      <div class="edit-form">
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-sm font-semibold text-slate-900">Edit Term Sheet</h4>
          <button type="button" onclick="cancelTermSheetEdit()" class="text-slate-400 hover:text-slate-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="edit-grid">
          ${termSheetFields.map(f => `
            <label class="edit-field">
              <span class="form-label-sm">${f.label}</span>
              <input type="${f.type}" id="ts-${f.key}" value="${f.value || ""}" ${f.step ? `step="${f.step}"` : ""} class="form-input" />
            </label>
          `).join("")}
        </div>
        <div class="flex items-center gap-2 mt-3">
          <button type="button" onclick="saveTermSheetEdit('${hlt.id}')" class="btn-primary">Save</button>
          <button type="button" onclick="cancelTermSheetEdit()" class="btn-secondary">Cancel</button>
        </div>
      </div>
    `;
  }

  // Render a document row with upload/delete
  const renderDocRow = (type, label, status, existingDocs) => {
    const hasDoc = existingDocs.length > 0;
    const doc = existingDocs[0];
    const isImage = type === "photo";
    const acceptAttr = type === "photo" ? "image/*" : ".pdf,.docx,.doc";

    return `
      <div class="doc-card">
        <div class="doc-header">
          <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <span class="text-sm font-semibold text-slate-900">${label}</span>
        </div>
        <div class="doc-actions">
          ${docBadge(status)}
          <div class="flex items-center gap-2">
            ${hasDoc ? `
              ${isImage ? `<img src="${doc.file_path}" class="w-8 h-8 rounded object-cover border border-slate-200" alt="thumb" />` : ""}
              <button type="button" onclick="event.stopPropagation(); viewDocument('${doc.file_path}', '${doc.file_name}')" class="doc-btn doc-btn-primary">View</button>
              <button type="button" onclick="event.stopPropagation(); deleteDocument('${doc.id}', '${hlt.id}')" class="doc-btn doc-btn-ghost" title="Delete">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            ` : `
              <label class="doc-btn doc-btn-primary cursor-pointer">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
                Upload
                <input type="file" accept="${acceptAttr}" onchange="uploadDocument(this, '${hlt.id}', '${type}')" class="hidden" />
              </label>
            `}
          </div>
        </div>
      </div>
    `;
  };

  // Image gallery
  const imageGallery = images.length > 0 ? `
    <div class="doc-card">
      <div class="doc-header">
        <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
        <span class="text-sm font-semibold text-slate-900">Images (${images.length})</span>
      </div>
      <div class="flex flex-wrap gap-3 p-3">
        ${images.map(img => `
          <div class="relative group">
            <img src="${img.file_path}" class="w-20 h-20 rounded-lg object-cover border border-slate-200 cursor-pointer hover:border-blue-400 transition-colors" onclick="event.stopPropagation(); viewDocument('${img.file_path}', '${img.file_name}')" alt="${img.file_name}" />
            <button type="button" onclick="event.stopPropagation(); deleteDocument('${img.id}', '${hlt.id}')" class="absolute -top-2 -right-2 w-5 h-5 bg-rose-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" title="Delete">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
        `).join("")}
        <label class="w-20 h-20 rounded-lg border-2 border-dashed border-slate-300 flex items-center justify-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
          <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          <input type="file" accept="image/*" onchange="uploadDocument(this, '${hlt.id}', 'photo')" class="hidden" />
        </label>
      </div>
    </div>
  ` : "";

  return `
    <tr class="expand-content">
      <td colspan="5" class="p-0">
        <div class="expand-inner">
          ${renderDocRow("term_sheet", "Term Sheet", termSheetStatus, termSheetDocs)}
          ${editFormHtml}
          ${renderDocRow("pds", "Product Disclosure Statement", pdsStatus, pdsDocs)}
          ${renderDocRow("sa", "Syndicate Agreement", saStatus, saDocs)}
          ${imageGallery}
          ${images.length === 0 ? renderDocRow("photo", "Images", "pending", []) : ""}
        </div>
      </td>
    </tr>
  `;
}

function toggleHltRow(id) {
  hltsState.expandedRow = hltsState.expandedRow === id ? null : id;
  if (hltsState.expandedRow === id) {
    loadHltDocuments(id);
  }
  renderHltsView();
}

function setHltHorseFilter(value) {
  hltsState.horseFilter = value;
  hltsState.expandedRow = null;
  applyHltsFilters();
  renderHltsView();
}

function setHltStatusFilter(value) {
  hltsState.statusFilter = value;
  hltsState.expandedRow = null;
  applyHltsFilters();
  renderHltsView();
}

function clearHltFilters() {
  hltsState.horseFilter = 'all';
  hltsState.statusFilter = 'all';
  document.getElementById('hlt-horse-filter').value = 'all';
  document.getElementById('hlt-status-filter').value = 'all';
  applyHltsFilters();
  renderHltsView();
}

function startTermSheetEdit(hltId) {
  hltsState.editingTermSheet = hltId;
  renderHltsView();
}

function cancelTermSheetEdit() {
  hltsState.editingTermSheet = null;
  hltsState.termSheetEdit = {};
  renderHltsView();
}

async function saveTermSheetEdit(hltId) {
  const hlt = hltsState.allHlts.find(h => h.id === hltId);
  if (!hlt) return;

  const updated = {
    ...hlt,
    token_name: document.getElementById('ts-token_name')?.value || hlt.token_name,
    erc20_identifier: document.getElementById('ts-erc20_identifier')?.value || hlt.erc20_identifier,
    percent_leased: parseFloat(document.getElementById('ts-percentage_leased')?.value) || hlt.percent_leased,
    token_count: parseInt(document.getElementById('ts-token_count')?.value) || hlt.token_count,
    percent_per_token: parseFloat(document.getElementById('ts-percent_per_token')?.value) || hlt.percent_per_token,
    token_price_nzd: parseFloat(document.getElementById('ts-token_price_nzd')?.value) || hlt.token_price_nzd,
    total_issuance_value_nzd: parseFloat(document.getElementById('ts-total_issuance_value_nzd')?.value) || hlt.total_issuance_value_nzd,
    investor_share_percent: parseInt(document.getElementById('ts-investor_share_percent')?.value) || hlt.investor_share_percent,
    owner_share_percent: parseInt(document.getElementById('ts-owner_share_percent')?.value) || hlt.owner_share_percent,
    start_date: document.getElementById('ts-start_date')?.value || hlt.start_date,
    duration_months: parseInt(document.getElementById('ts-duration_months')?.value) || hlt.duration_months,
    notes: document.getElementById('ts-variations')?.value || hlt.notes,
  };

  try {
    const res = await fetch('/__save_hlt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leaseId: hltId, content: updated })
    });
    const result = await res.json();
    if (!result.success) throw new Error(result.error);
    showToast('Term sheet saved!', 'success');
    hltsState.editingTermSheet = null;
    window.location.reload();
  } catch (err) {
    showToast('Failed to save: ' + err.message, 'error');
  }
}

function viewTermSheet(hltId) {
  const hlt = hltsState.allHlts.find(h => h.id === hltId);
  const horse = hltsState.horses.find(h => h.microchip === hlt?.horse_microchip);
  const trainer = hltsState.trainers.find(t => t.id === hlt?.trainer_id);
  const owner = hltsState.owners.find(o => o.id === hlt?.owner_id);
  const governing = hltsState.governingBodies.find(g => g.governing_body_code === hlt?.governing_body_code);

  if (!hlt || !horse || !trainer || !owner || !governing) return;

  const record = {
    lease_id: hlt.lease_id,
    token_name: hlt.token_name,
    erc20_identifier: hlt.erc20_identifier,
    submission_date: hlt.created_at,
    horse_id: hlt.horse_id,
    horse_name: horse.name,
    horse_country: horse.country_code || 'NZ',
    horse_microchip: horse.microchip_number,
    trainer_name: trainer.name,
    owner_name: owner.name,
    governing_body_name: governing.governing_body_name,
    governing_body_code: governing.governing_body_code,
    lease_start_date: hlt.start_date,
    lease_length_months: hlt.duration_months,
    percentage_leased: hlt.percent_leased,
    num_tokens: hlt.token_count,
    token_price_nzd: hlt.token_price_nzd,
    total_issuance_value: hlt.total_issuance_value_nzd,
    percentage_per_token: hlt.percent_per_token,
    investor_stakes_split: hlt.investor_share_percent,
    variations: hlt.notes || 'n/a'
  };

  // Import and use the HTML template
  import('./hlt-engine.js').then(({ buildHltDocumentHtml }) => {
    const html = buildHltDocumentHtml(record);
    showDocModal(`${horse.name} - Term Sheet Preview`, html, termSheetDoc.file_path);
  });
}

// ─── Document Operations ──────────────────────────────────────────────────────

window.loadHltDocuments = async function(hltId) {
  try {
    const resp = await fetch(`/api/hlts/${hltId}/documents`);
    const result = await resp.json();
    if (result.success) {
      if (!hltsState.hltDocuments) hltsState.hltDocuments = {};
      hltsState.hltDocuments[hltId] = result.data;
      renderHltsView();
    }
  } catch (err) {
    console.error("Failed to load documents:", err);
  }
}

window.uploadDocument = async function(input, hltId, docType) {
  const file = input.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);

  try {
    const resp = await fetch(`/api/hlts/${hltId}/documents`, {
      method: "POST",
      body: formData,
    });
    const result = await resp.json();
    if (result.success) {
      showToast(`${docType.replace("_", " ")} uploaded!`, "success");
      loadHltDocuments(hltId);
    } else {
      showToast(result.error || "Upload failed", "error");
    }
  } catch (err) {
    showToast("Upload error: " + err.message, "error");
  }
}

window.deleteDocument = async function(docId, hltId) {
  if (!confirm("Delete this document?")) return;

  try {
    const resp = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
    const result = await resp.json();
    if (result.success) {
      showToast("Document deleted", "success");
      loadHltDocuments(hltId);
    } else {
      showToast(result.error || "Delete failed", "error");
    }
  } catch (err) {
    showToast("Delete error: " + err.message, "error");
  }
}

window.viewDocument = function(filePath, fileName) {
  const ext = fileName.split(".").pop().toLowerCase();
  const imageExts = ["png", "jpg", "jpeg", "gif", "webp", "svg"];

  if (imageExts.includes(ext)) {
    // Show image in modal
    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    modal.innerHTML = `
      <div class="modal-content max-w-4xl" onclick="event.stopPropagation()">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-slate-900">${fileName}</h3>
          <button type="button" onclick="this.closest('.modal-overlay').remove()" class="text-slate-400 hover:text-slate-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <img src="${filePath}" alt="${fileName}" class="max-w-full max-h-[70vh] rounded-lg" />
      </div>
    `;
    document.body.appendChild(modal);
  } else {
    // Open document in new tab
    window.open(filePath, "_blank");
  }
}

function viewDoc(hltId, type) {
  showToast(`${type.toUpperCase()} — upload a file to view it`, "info");
}

function editDoc(type) {
  showToast(`Upload a ${type.toUpperCase()} file to manage it`, "info");
}

function downloadDoc(path) {
  window.open(path, "_blank");
}

async function listToPlatform(hltId) {
  const hlt = hltsState.allHlts.find(h => h.id === hltId);
  if (!hlt) return;

  if (!confirm('List this HLT to Evolution Platform? It will appear on the marketplace as "Coming Soon".')) return;

  const originalStatus = hlt.status;

  try {
    // Step 1: Set intermediate status
    await fetch('/__save_hlt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leaseId: hltId, content: { ...hlt, status: 'listing' } })
    });

    // Step 2: Publish to platform
    const res = await fetch('/__publish_to_platform', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leaseId: hltId })
    });

    const result = await res.json();

    if (result.success) {
      // Step 3a: Success - finalize status
      await fetch('/__save_hlt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leaseId: hltId, content: { ...hlt, status: 'listed' } })
      });
      showToast(`HLT listed on platform! ${result.platformResult?.upserted ? `(${result.platformResult.upserted} listings synced)` : ''}`, 'success');
    } else {
      // Step 3b: Platform error - rollback
      await fetch('/__save_hlt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leaseId: hltId, content: { ...hlt, status: originalStatus } })
      });
      throw new Error(result.error || 'Platform sync failed');
    }
  } catch (err) {
    // Step 3c: Network/other error - rollback
    await fetch('/__save_hlt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leaseId: hltId, content: { ...hlt, status: originalStatus } })
    });
    showToast('List failed: ' + err.message, 'error');
  } finally {
    window.location.reload();
  }
}

async function publishMarketplace() {
  const activeLeases = hltsState.allHlts.filter(l => l.status === 'active' || l.status === 'listed' || l.status === 'published');
  if (activeLeases.length === 0) {
    showToast('No "Active" or "Listed" leases found to publish.', 'error');
    return;
  }

  const horseByMicrochip = new Map(hltsState.horses.map(h => [h.microchip, h]));
  const payload = {
    generatedAt: new Date().toISOString(),
    listings: activeLeases.map(lease => {
      const horse = horseByMicrochip.get(lease.horse_microchip);
      return {
        slug: horse?.name?.toLowerCase().replace(/\s+/g, '-') || 'unknown',
        horse: {
          horseId: horse?.id || horse?.microchip,
          name: horse?.name,
          microchipNumber: horse?.microchip_number,
          sex: horse?.sex,
          foalingDate: horse?.foaling_date,
          colour: horse?.colour,
          sire: horse?.sire_name,
          dam: horse?.dam_name
        },
        offering: {
          leaseId: lease.lease_id,
          tokenCount: parseInt(lease.token_count),
          tokenPriceNzd: parseFloat(lease.token_price_nzd),
          totalIssuanceValueNzd: parseFloat(lease.total_issuance_value_nzd),
          investorSharePercent: parseInt(lease.investor_share_percent),
          owner_share_percent: parseInt(lease.owner_share_percent),
          startDate: lease.start_date,
          endDate: lease.end_date,
          durationMonths: lease.duration_months,
          percentPerToken: lease.percent_per_token,
          leaseStatus: 'active'
        }
      };
    })
  };

  try {
    const res = await fetch('/__publish_marketplace', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) showToast(`Successfully published ${activeLeases.length} listings to Marketplace draft!`, 'success');
    else throw new Error(result.error);
  } catch (err) {
    showToast('Publish failed: ' + err.message, 'error');
  }
}

function openCreateHltWizard() {
  window.location.hash = '#/create-hlt';
  render();
}

// Expose openCreateHltWizard to global scope for HTML onclick handlers
window.openCreateHltWizard = openCreateHltWizard;

// ─── HLT Detail ───────────────────────────────────────────────────────────────

window.renderHltDetail = async function(id) {
  setLoading(true);
  const json = await getHlt(id);
  if (!json.success) {
    app.innerHTML = '<div class="p-6 text-red-600 text-sm">HLT not found.</div>';
    return;
  }
  const h = json.data;
  const horse = h.horse || {};
  const owner = h.owner || {};
  const trainer = h.trainer || {};
  const lease = h.lease || {};
  const status = normalizeHltStatus(h.status);

  const money = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '—';
    return new Intl.NumberFormat('en-NZ', { style: 'currency', currency: 'NZD', maximumFractionDigits: 0 }).format(value);
  };

  const statusOpts = HLT_STATUSES.map(s =>
    `<option value="${s.id}" ${status === s.id ? 'selected' : ''}>${s.label}</option>`
  ).join("");

  app.innerHTML = `
    <div class="space-y-4 max-w-3xl">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button type="button" onclick="window.navigateTo('#/hlts')" class="btn-ghost text-xs px-0 mb-1">← HLTs</button>
          <h1 class="text-xl font-bold text-slate-900 tracking-tight">${horse.name || 'Unnamed horse'}</h1>
          <p class="text-sm text-slate-500 mt-0.5 font-mono">${h.id} · lease ${h.lease_id || '—'}</p>
        </div>
        <div class="flex items-center gap-2">
          ${hltStatusPill(status)}
          <select id="hlt-status-select" class="form-input-sm w-auto" onchange="window.setHltLifecycleStatus('${h.id}', this.value)">
            ${statusOpts}
          </select>
        </div>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div class="surface-card p-3">
          <div class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Issuance</div>
          <div class="text-lg font-bold text-slate-900 mt-1">${money(lease.total_issuance_value_nzd)}</div>
        </div>
        <div class="surface-card p-3">
          <div class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Token</div>
          <div class="text-lg font-bold text-slate-900 mt-1">${money(lease.token_price_nzd)}</div>
        </div>
        <div class="surface-card p-3">
          <div class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Stake</div>
          <div class="text-lg font-bold text-slate-900 mt-1">${lease.percent_leased != null ? lease.percent_leased + '%' : '—'}</div>
        </div>
        <div class="surface-card p-3">
          <div class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Term</div>
          <div class="text-lg font-bold text-slate-900 mt-1">${lease.duration_months != null ? lease.duration_months + 'm' : '—'}</div>
        </div>
      </div>

      <div class="surface-card p-4 space-y-3">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-400">Parties</h3>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div>
            <div class="text-[11px] text-slate-400 font-semibold">Horse</div>
            <div class="font-semibold text-slate-900">${horse.name || '—'}</div>
            <div class="text-xs text-slate-500">${horse.sex || ''} ${horse.colour ? '· ' + horse.colour : ''}</div>
            <div class="text-xs text-slate-400 font-mono mt-0.5">${h.horse_microchip || ''}</div>
          </div>
          <div>
            <div class="text-[11px] text-slate-400 font-semibold">Owner</div>
            <div class="font-semibold text-slate-900">${owner.name || h.owner_id || '—'}</div>
          </div>
          <div>
            <div class="text-[11px] text-slate-400 font-semibold">Trainer</div>
            <div class="font-semibold text-slate-900">${trainer.name || h.trainer_id || '—'}</div>
            <div class="text-xs text-slate-500">${trainer.stable_name || ''}</div>
          </div>
        </div>
      </div>

      <div class="surface-card p-4 space-y-2">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-400">Commercial</h3>
        <div class="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
          <div class="flex justify-between gap-2"><span class="text-slate-500">Start</span><span class="font-medium">${lease.start_date || '—'}</span></div>
          <div class="flex justify-between gap-2"><span class="text-slate-500">End</span><span class="font-medium">${lease.end_date || '—'}</span></div>
          <div class="flex justify-between gap-2"><span class="text-slate-500">Tokens</span><span class="font-medium">${lease.token_count ?? '—'}</span></div>
          <div class="flex justify-between gap-2"><span class="text-slate-500">$/1%·mo</span><span class="font-medium">${money(lease.price_per_1pct_per_month)}</span></div>
          <div class="flex justify-between gap-2 col-span-2"><span class="text-slate-500">Split</span><span class="font-medium">Investor ${lease.investor_share_percent ?? '—'}% / Owner ${lease.owner_share_percent ?? '—'}%</span></div>
        </div>
      </div>

      <div class="surface-card p-4 space-y-3" id="hlt-detail-docs">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-400">Documents</h3>
          <span class="text-[11px] text-slate-400">Term sheet · PDS+SA pack generate · upload/lock</span>
        </div>
        <div class="text-sm text-slate-500">Loading…</div>
      </div>
    </div>
  `;

  loadHltDetailDocuments(h.id);
};

window.setHltLifecycleStatus = async function(hltId, status) {
  try {
    const headers = await window.getAuthHeader();
    const resp = await fetch(`${API}/hlts/${hltId}/status`, {
      method: "PATCH",
      headers,
      body: JSON.stringify({ status }),
    });
    const res = await resp.json();
    if (!res.success) throw new Error(res.error || "Status update failed");
    showToast(`Status → ${normalizeHltStatus(status)} · MC only (publish via Sync)`, "success");
    window.renderHltDetail(hltId);
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ─── HLT Detail Document Management ──────────────────────────────────────────

window.loadHltDetailDocuments = async function(hltId) {
  const container = document.getElementById("hlt-detail-docs");
  if (!container) return;

  try {
    const resp = await fetch(`/api/hlts/${hltId}/documents`);
    const result = await resp.json();
    const docs = result.success ? result.data : [];

    const getDocs = (type) => docs.filter(d => d.doc_type === type);
    const termSheetDocs = getDocs("term_sheet");
    const pdsDocs = getDocs("pds");
    const saDocs = getDocs("sa");

    const examples = TERM_SHEET_EXAMPLES.map(e =>
      `<div class="text-[11px] text-slate-500"><span class="font-semibold text-slate-600">${e.horse}:</span> ${e.blurb}</div>`
    ).join("");

    const renderDocRow = (type, label, existingDocs, opts = {}) => {
      const hasDoc = existingDocs.length > 0;
      const doc = existingDocs[0];
      const status = hasDoc ? (doc.status || 'draft') : 'uncreated';
      const acceptAttr = ".pdf,.docx,.doc";

      let actionsHtml = '';
      if (type === 'term_sheet' && !hasDoc) {
        actionsHtml = `
          <button type="button" onclick="window.generateTermSheet('${hltId}')" class="btn-primary text-xs">Generate term sheet</button>
          <label class="btn-secondary text-xs cursor-pointer">Upload
            <input type="file" accept="${acceptAttr}" onchange="uploadDocument(this, '${hltId}', '${type}').then(() => setTimeout(() => loadHltDetailDocuments('${hltId}'), 400))" class="hidden" />
          </label>
        `;
      } else if ((type === 'pds' || type === 'sa') && !hasDoc) {
        actionsHtml = `
          <button type="button" onclick="window.generateInvestorPack('${hltId}')" class="btn-primary text-xs">Generate draft pack</button>
          <label class="btn-secondary text-xs cursor-pointer">Upload
            <input type="file" accept="${acceptAttr}" onchange="uploadDocument(this, '${hltId}', '${type}').then(() => setTimeout(() => loadHltDetailDocuments('${hltId}'), 400))" class="hidden" />
          </label>
        `;
      } else if (!hasDoc) {
        actionsHtml = `
          <label class="btn-primary text-xs cursor-pointer">Upload
            <input type="file" accept="${acceptAttr}" onchange="uploadDocument(this, '${hltId}', '${type}').then(() => setTimeout(() => loadHltDetailDocuments('${hltId}'), 400))" class="hidden" />
          </label>
        `;
      } else if ((type === 'pds' || type === 'sa') && status === 'draft') {
        actionsHtml = `
          <a href="${doc.file_path}" target="_blank" class="btn-secondary text-xs">Preview</a>
          <button type="button" onclick="window.generateInvestorPack('${hltId}')" class="btn-secondary text-xs">Regenerate</button>
          <button type="button" onclick="window.toggleDocStatus('${doc.id}', 'approved', '${hltId}')" class="btn-primary text-xs">Lock</button>
          <button type="button" onclick="deleteDocument('${doc.id}', '${hltId}').then(() => loadHltDetailDocuments('${hltId}'))" class="btn-ghost text-xs text-rose-600">Delete</button>
        `;
      } else if (status === 'approved' || status === 'locked') {
        actionsHtml = `
          <a href="${doc.file_path}" target="_blank" class="btn-secondary text-xs">View</a>
          <button type="button" onclick="window.toggleDocStatus('${doc.id}', 'draft', '${hltId}')" class="btn-ghost text-xs">Unlock</button>
        `;
      } else {
        actionsHtml = `
          <a href="${doc.file_path}" target="_blank" class="btn-secondary text-xs">Preview</a>
          <button type="button" onclick="window.toggleDocStatus('${doc.id}', 'approved', '${hltId}')" class="btn-primary text-xs">Lock</button>
          <button type="button" onclick="deleteDocument('${doc.id}', '${hltId}').then(() => loadHltDetailDocuments('${hltId}'))" class="btn-ghost text-xs text-rose-600">Delete</button>
        `;
      }

      return `
        <div class="flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg border border-slate-200 bg-slate-50/50">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold text-slate-900">${label}</span>
              ${docStatusPill(status)}
            </div>
            <div class="text-xs text-slate-500 truncate">${hasDoc ? (doc.file_name || 'On file') : (opts.hint || 'Not on file')}</div>
          </div>
          <div class="flex flex-wrap items-center gap-1.5">${actionsHtml}</div>
        </div>
      `;
    };

    container.innerHTML = `
      <div class="flex items-center justify-between gap-2 mb-1">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-400">Documents</h3>
        <span class="text-[11px] text-slate-400">Term sheet · PDS+SA pack generate · upload/lock</span>
      </div>
      <div class="space-y-2">
        ${renderDocRow("term_sheet", "Term sheet", termSheetDocs, { hint: "Generate from HLT terms · horse narrative manual for now" })}
        ${renderDocRow("pds", "PDS", pdsDocs, { hint: "Generate combined PDS+SA draft pack from HLT commercials (or upload counsel PDF)" })}
        ${renderDocRow("sa", "Syndicate agreement", saDocs, { hint: "Same draft pack as PDS until counsel splits finals" })}
      </div>
      <div class="mt-3 rounded-lg border border-dashed border-slate-200 bg-white p-3 space-y-1.5">
        <div class="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Past horse examples (term narrative)</div>
        ${examples}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="text-sm text-rose-600">Failed to load documents: ${err.message}</div>`;
  }
}

// ─── Term Sheet ───────────────────────────────────────────────────────────────

window.generateTermSheet = async function(hltId) {
  try {
    const res = await fetch(`/api/hlts/${hltId}/term-sheet.docx`);
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `term-sheet-${hltId}.docx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showToast("Term sheet downloaded · horse-specific narrative still manual", "success");
    loadHltDetailDocuments(hltId);
  } catch (err) {
    showToast("Term sheet failed: " + err.message, "error");
  }
};

/** Generate combined PDS+SA DRAFT DOCX from HLT commercial data (wizard UI retired). */
window.generateInvestorPack = async function(hltId) {
  try {
    showToast("Generating PDS+SA draft pack…", "info");
    const headers = await window.getAuthHeader();
    const res = await fetch(`/api/hlts/${hltId}/investor-pack.docx`, {
      method: "POST",
      headers,
    });
    if (!res.ok) {
      let msg = await res.text();
      try {
        const j = JSON.parse(msg);
        msg = j.error || msg;
      } catch (_) {}
      throw new Error(msg || res.statusText);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Investor-Pack-${hltId}-DRAFT.docx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showToast("Draft pack downloaded · registered as PDS + SA drafts — lock after counsel review", "success");
    loadHltDetailDocuments(hltId);
  } catch (err) {
    showToast("Pack generation failed: " + err.message, "error");
  }
};

window.openWizardForHlt = function(hltId) {
  window.navigateTo(`#/hlt/${hltId}`);
  showToast("Wizard retired — use Generate draft pack on this HLT.", "info");
};

window.toggleDocStatus = async function(docId, newStatus, hltId) {
  try {
    const headers = await window.getAuthHeader();
    const resp = await fetch(`/api/documents/${docId}/status`, {
      method: "PATCH",
      headers,
      body: JSON.stringify({ status: newStatus })
    });
    const res = await resp.json();
    if (res.success) {
      showToast(`Document status set to '${newStatus}'`, "success");
      window.loadHltDetailDocuments(hltId);
    } else {
      showToast("Error updating status: " + (res.error || "Unknown"), "error");
    }
  } catch (err) {
    showToast("Status update error: " + err.message, "error");
  }
};

// ─── Governing Bodies ───────────────────────────────────────────────────────

async function renderGoverningBodies() {
  try {
    setLoading(true);
    const items = await loadGoverningBodies();
    const rows = items.map(g => `
      <tr class="border-b hover:bg-gray-50">
        <td class="px-4 py-3">${g.governing_body_name}</td>
        <td class="px-4 py-3"><span class="tag">${g.governing_body_code}</span></td>
        <td class="px-4 py-3">${g.website ? `<a href="${g.website}" target="_blank" class="text-blue-600 hover:underline">${g.website}</a>` : '—'}</td>
        <td class="px-4 py-3">${g.status}</td>
      </tr>
    `).join("");
    app.innerHTML = `
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Governing Bodies</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="bg-gray-50 text-gray-600 font-medium">
              <tr>
                <th class="px-4 py-2">Name</th>
                <th class="px-4 py-2">Code</th>
                <th class="px-4 py-2">Website</th>
                <th class="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody>${rows || '<tr><td colspan="4" class="px-4 py-4 text-gray-500">No governing bodies.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Governing Bodies render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Governing Bodies</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

// ─── Views map ────────────────────────────────────────────────────────────────

const views = {
  "": renderDashboard,
  horses: renderHorses,
  owners: renderOwners,
  trainers: renderTrainers,
  "governing-bodies": renderGoverningBodies,
  hlts: renderHlts,
  "create-hlt": renderCreateHlt,
};

// ─── Router ───────────────────────────────────────────────────────────────────

window.triggerSync = async function(opts = {}) {
  const dryRun = opts.dryRun !== false && !opts.confirm;
  const confirmWrite = !!opts.confirm;
  try {
    const headers = await window.getAuthHeader();
    headers["Content-Type"] = "application/json";
    const resp = await fetch("/api/sync/website", {
      method: "POST",
      headers,
      body: JSON.stringify({ dry_run: dryRun, confirm: confirmWrite }),
    });
    const data = await resp.json();
    const payload = data.data || data;
    if (!data.success && payload.success === false) {
      showToast("Sync failed: " + (payload.error || data.error || "Unknown"), "error");
      return payload;
    }
    if (payload.dry_run || payload.blocked) {
      const h = payload.horses || {};
      const l = payload.hlts || {};
      const msg = [
        `Preview: horses ${h.would_write ?? "?"} (remove ${ (h.removed || []).join(", ") || "none" })`,
        `hlts ${l.would_write ?? "?"} (remove ${ (l.removed || []).join(", ") || "none" })`,
        payload.warning || "",
      ].filter(Boolean).join(" · ");
      showToast(msg, "info");
      const box = document.getElementById("sync-preview");
      if (box) {
        box.innerHTML = `<pre class="text-xs whitespace-pre-wrap text-slate-700">${JSON.stringify(payload, null, 2)}</pre>`;
      }
      return payload;
    }
    showToast(
      `Wrote website JSON · horses ${payload.horses_synced} · hlts ${payload.hlts_synced} (backups saved). Sheet: ${(payload.gsheet && payload.gsheet.status) || "n/a"}`,
      "success"
    );
    const box = document.getElementById("sync-preview");
    if (box) {
      box.innerHTML = `<pre class="text-xs whitespace-pre-wrap text-slate-700">${JSON.stringify(payload, null, 2)}</pre>`;
    }
    return payload;
  } catch (err) {
    showToast("Sync error: " + err.message, "error");
  }
};

window.confirmAndSync = async function() {
  const preview = await window.triggerSync({ dryRun: true });
  if (!preview) return;
  const removed = [
    ...((preview.horses && preview.horses.removed) || []),
    ...((preview.hlts && preview.hlts.removed) || []),
  ];
  const warn = removed.length
    ? `\n\nWILL REMOVE from website JSON: ${removed.join(", ")}`
    : "\n\nNo removals detected.";
  const ok = window.confirm(
    "Publish Mission Control inventory to 02_website/src/data/horses.json + hlts.json?\n" +
    "Backups are written first. shares_sold preserved by slug where possible." +
    warn +
    "\n\nGoogle Sheet is NOT updated yet (stub)."
  );
  if (ok) await window.triggerSync({ dryRun: false, confirm: true });
};

async function renderLeads() {
  app.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-bold text-slate-900">🎯 Leads & Waitlist</h2>
          <p class="text-sm text-slate-500">Investor interest signups captured via public website & Google Sheet sync.</p>
        </div>
        <button onclick="window.triggerSync()" class="btn-secondary text-xs">🔄 Refresh & Pull Leads</button>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <table class="w-full">
          <thead>
            <tr>
              <th class="table-header">Investor Email</th>
              <th class="table-header">Timestamp</th>
              <th class="table-header">Horse Interest</th>
              <th class="table-header">Status</th>
              <th class="table-header text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr class="table-row">
              <td class="table-cell font-semibold text-slate-900">investor@example.com</td>
              <td class="table-cell text-slate-500 font-mono text-xs">2026-08-07 10:15:00</td>
              <td class="table-cell"><span class="badge badge-review">Nellie (Almanzor x Night Danza)</span></td>
              <td class="table-cell"><span class="badge badge-complete">New Waitlist</span></td>
              <td class="table-cell text-right">
                <a href="mailto:investor@example.com" class="btn-primary text-xs">Email Lead</a>
              </td>
            </tr>
            <tr class="table-row">
              <td class="table-cell font-semibold text-slate-900">syndicate.buyer@bloodstock.co.nz</td>
              <td class="table-cell text-slate-500 font-mono text-xs">2026-08-06 18:40:12</td>
              <td class="table-cell"><span class="badge badge-review">I Stole A Manolo</span></td>
              <td class="table-cell"><span class="badge badge-complete">Contacted</span></td>
              <td class="table-cell text-right">
                <a href="mailto:syndicate.buyer@bloodstock.co.nz" class="btn-primary text-xs">Email Lead</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `;
}

async function renderDocVault() {
  // Retired: documents live on each HLT Detail page
  window.location.hash = "#/hlts";
  showToast("Doc vault retired — open an HLT for term sheet / PDS+SA pack.", "info");
}

async function renderSync() {
  app.innerHTML = `
    <div class="space-y-4 max-w-2xl">
      <div>
        <h2 class="text-xl font-bold text-slate-900">Sync / Publish</h2>
        <p class="text-sm text-slate-500 mt-0.5">MC SQLite → website JSON only when you confirm. No silent writes.</p>
      </div>
      <div class="surface-card p-4 space-y-3">
        <div class="text-sm text-slate-700 space-y-1">
          <div class="font-mono text-xs text-slate-500">02_website/src/data/horses.json</div>
          <div class="font-mono text-xs text-slate-500">02_website/src/data/hlts.json</div>
        </div>
        <ul class="text-xs text-slate-600 list-disc pl-4 space-y-1">
          <li>Horse / HLT / status edits stay in Mission Control until you publish here.</li>
          <li>Preview shows adds/removes before write. Backups: <span class="font-mono">*.json.bak-…</span></li>
          <li><span class="font-semibold">shares_sold</span> preserved from existing file by slug (checkout owns sales).</li>
          <li>Google Sheet push: not implemented (website still Sheet-first in prod).</li>
          <li>Locked legal PDFs → public/documents: not wired yet (manual copy for now).</li>
        </ul>
        <div class="flex flex-wrap gap-2 pt-1">
          <button type="button" onclick="window.triggerSync({ dryRun: true })" class="btn-secondary text-xs">Preview diff</button>
          <button type="button" onclick="window.confirmAndSync()" class="btn-primary text-xs">Publish to website JSON…</button>
        </div>
        <div id="sync-preview" class="mt-2 max-h-80 overflow-auto rounded-lg bg-slate-50 border border-slate-200 p-3 text-xs text-slate-500">
          Run Preview to see what would change.
        </div>
      </div>
    </div>
  `;
  // Auto-load preview
  window.triggerSync({ dryRun: true });
}

const _oldRender = render;
window.render = function() {
  const hash = window.location.hash.replace("#/", "").replace("#", "");
  // Retired surfaces → HLTs
  if (hash === "wizard" || hash === "investor-wizard" || hash === "leads" || hash === "doc-vault") {
    window.location.hash = "#/hlts";
    return;
  }
  if (hash === "sync") {
    renderSync();
    return;
  }
  if (hash.startsWith("hlt/")) {
    renderHltDetail(hash.replace("hlt/", ""));
    return;
  }
  const horseMediaMatch = hash.match(/^horse\/([^/]+)\/media$/);
  if (horseMediaMatch) {
    renderHorseMedia(decodeURIComponent(horseMediaMatch[1]));
    return;
  }
  const horseDetailMatch = hash.match(/^horse\/([^/]+)$/);
  if (horseDetailMatch) {
    renderHorseDetail(decodeURIComponent(horseDetailMatch[1]));
    return;
  }
  _oldRender();
};

// ─── Transcript helpers ───────────────────────────────────────────────────────

window.viewFullTranscript = function(id) {
  // For now, just show an alert - can be enhanced to open a modal with full transcript
  alert('Full transcript viewer coming soon. Transcript ID: ' + id);
};

window.downloadTranscript = function(id, filepath) {
  // Create a download link for the transcript file
  const link = document.createElement('a');
  link.href = filepath;
  link.download = `transcript_${id}.json`;
  link.click();
};

// ─── Horse Detail Page (tabbed content workspace) ─────────────────────────────

window._horseDetailTab = window._horseDetailTab || "identity";

function _horseContentChecklist(h) {
  const storyOk = !!(h.story && String(h.story).trim().length >= 40);
  const imageOk = !!(h.image_path || h.cover_image);
  const nextOk = !!(h.next_up && String(h.next_up).trim() && h.next_up !== "TBD");
  const idOk = !!(h.name && h.microchip && h.sire_name && h.dam_name);
  return [
    { id: "identity", label: "Identity & pedigree", ok: idOk },
    { id: "marketplace", label: "Marketplace story", ok: storyOk },
    { id: "marketplace-img", label: "Marketplace image", ok: imageOk },
    { id: "marketplace-next", label: "Next up", ok: nextOk },
  ];
}

async function renderHorseDetail(microchip) {
  try {
    setLoading(true);
    const headers = await window.getAuthHeader();

    // Prefer single-horse GET (includes story fields)
    let horse = null;
    try {
      const one = await fetch(`${API}/horses/${encodeURIComponent(microchip)}`, { headers });
      const j = await one.json();
      if (j.success) horse = j.data;
    } catch (_) {}
    if (!horse) {
      const horses = await loadHorses();
      horse = horses.find(h => h.microchip === microchip);
    }
    if (!horse) throw new Error("Horse not found");

    const mediaResp = await fetch(`${API}/horses/${encodeURIComponent(microchip)}/media`, { headers });
    const mediaResult = mediaResp.ok ? await mediaResp.json() : { data: { transcripts: [] } };
    const { transcripts = [] } = mediaResult.data || {};
    const transcriptCount = transcripts.length;

    const tab = window._horseDetailTab || "identity";
    const checks = _horseContentChecklist(horse);
    const done = checks.filter(c => c.ok).length;

    const tabBtn = (id, label) => {
      const active = tab === id;
      return `<button type="button" data-horse-tab="${id}"
        class="px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
          active
            ? "bg-blue-600 text-white shadow-sm"
            : "text-slate-600 hover:bg-slate-100"
        }">${label}</button>`;
    };

    const checklistHtml = checks.map(c => `
      <div class="flex items-center gap-2 text-xs">
        <span class="${c.ok ? "text-emerald-600" : "text-amber-500"}">${c.ok ? "●" : "○"}</span>
        <span class="${c.ok ? "text-slate-600" : "text-slate-500"}">${c.label}</span>
      </div>
    `).join("");

    let panel = "";
    if (tab === "identity") {
      panel = `
        <div class="space-y-4">
          <p class="text-sm text-slate-500">Core identity from NZTR / LoveRacing pull. Edit if needed, then Save.</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Name</span>
              <input id="hd-name" class="form-input mt-1 w-full" value="${(horse.name || "").replace(/"/g, "&quot;")}" /></label>
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Slug (web)</span>
              <input id="hd-name_slug" class="form-input mt-1 w-full font-mono text-sm" value="${(horse.name_slug || "").replace(/"/g, "&quot;")}" placeholder="e.g. nellie" /></label>
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Sex</span>
              <select id="hd-sex" class="form-input mt-1 w-full">
                ${["filly","colt","gelding","mare","stallion","horse"].map(s =>
                  `<option value="${s}" ${horse.sex === s ? "selected" : ""}>${s}</option>`).join("")}
              </select></label>
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Colour</span>
              <input id="hd-colour" class="form-input mt-1 w-full" value="${(horse.colour || "").replace(/"/g, "&quot;")}" /></label>
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Foaling date</span>
              <input id="hd-foaling_date" type="date" class="form-input mt-1 w-full" value="${(horse.foaling_date || "").slice(0,10)}" /></label>
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Breeder</span>
              <input id="hd-breeder" class="form-input mt-1 w-full" value="${(horse.breeder || "").replace(/"/g, "&quot;")}" /></label>
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Sire</span>
              <input id="hd-sire_name" class="form-input mt-1 w-full" value="${(horse.sire_name || "").replace(/"/g, "&quot;")}" /></label>
            <label class="block text-sm"><span class="text-slate-500 text-xs font-semibold uppercase">Dam</span>
              <input id="hd-dam_name" class="form-input mt-1 w-full" value="${(horse.dam_name || "").replace(/"/g, "&quot;")}" /></label>
            <label class="block text-sm sm:col-span-2"><span class="text-slate-500 text-xs font-semibold uppercase">Microchip</span>
              <input class="form-input mt-1 w-full font-mono bg-slate-50" value="${horse.microchip}" disabled /></label>
          </div>
          <button type="button" class="btn-primary text-sm" onclick="window.saveHorseTab('${microchip}', 'identity')">Save identity</button>
        </div>`;
    } else if (tab === "marketplace") {
      const storyVal = (horse.story || "").replace(/</g, "&lt;");
      const nextVal = (horse.next_up || "").replace(/"/g, "&quot;");
      const imgVal = (horse.image_path || horse.cover_image || "").replace(/"/g, "&quot;");
      const p1cat = (horse.pillar1_cat || "").replace(/"/g, "&quot;");
      const p1val = (horse.pillar1_val || "").replace(/"/g, "&quot;");
      const p2cat = (horse.pillar2_cat || "").replace(/"/g, "&quot;");
      const p2val = (horse.pillar2_val || "").replace(/"/g, "&quot;");
      const p3cat = (horse.pillar3_cat || "").replace(/"/g, "&quot;");
      const p3val = (horse.pillar3_val || "").replace(/"/g, "&quot;");
      const pedBlurb = (horse.pedigree_blurb || "").replace(/"/g, "&quot;");
      const trnComm = (horse.trainer_commentary || "").replace(/"/g, "&quot;");
      const pillarOpts = [
        "", "Distance Profile", "Pedigree Hook", "Campaign Target",
        "Sire Performance", "Conformation", "Trainer Insight", "Prep Readiness"
      ];
      const renderPillarOpt = (sel) => pillarOpts.map(o => `<option value="${o}" ${o === sel ? 'selected' : ''}>${o || '-- Select category --'}</option>`).join("");

      panel = `
        <div class="space-y-4">
          <p class="text-sm text-slate-500">
            What the website marketplace shows. Fill this for each horse — not auto-generated from breeder.
          </p>
          <label class="block text-sm">
            <span class="text-slate-500 text-xs font-semibold uppercase">Marketplace story / blurb</span>
            <textarea id="hd-story" rows="4" class="form-input mt-1 w-full font-sans text-sm leading-relaxed"
              placeholder="2–4 sentences: who the horse is, programme, why an investor should care…">${storyVal}</textarea>
            <span class="text-[11px] text-slate-400 mt-1 block">Aim for 40+ characters. Shown on marketplace cards / detail.</span>
          </label>
          <div class="border-t border-b border-slate-100 py-3 space-y-3">
            <span class="text-slate-600 text-xs font-bold uppercase tracking-wide">Hero Pillars (1–3 Badges)</span>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div class="p-2 rounded bg-slate-50 border border-slate-200">
                <span class="font-semibold text-slate-500 block mb-1">Pillar 1</span>
                <select id="hd-pillar1_cat" class="form-select w-full text-xs mb-1">${renderPillarOpt(p1cat)}</select>
                <input id="hd-pillar1_val" class="form-input w-full text-xs" value="${p1val}" placeholder="e.g. 1200m - 1600m" />
              </div>
              <div class="p-2 rounded bg-slate-50 border border-slate-200">
                <span class="font-semibold text-slate-500 block mb-1">Pillar 2</span>
                <select id="hd-pillar2_cat" class="form-select w-full text-xs mb-1">${renderPillarOpt(p2cat)}</select>
                <input id="hd-pillar2_val" class="form-input w-full text-xs" value="${p2val}" placeholder="e.g. Proisir x Fastnet Rock" />
              </div>
              <div class="p-2 rounded bg-slate-50 border border-slate-200 sm:col-span-2">
                <span class="font-semibold text-slate-500 block mb-1">Pillar 3 (Optional)</span>
                <select id="hd-pillar3_cat" class="form-select w-full text-xs mb-1">${renderPillarOpt(p3cat)}</select>
                <input id="hd-pillar3_val" class="form-input w-full text-xs" value="${p3val}" placeholder="e.g. Ready for Spring Trials" />
              </div>
            </div>
          </div>
          <label class="block text-sm">
            <span class="text-slate-500 text-xs font-semibold uppercase">Pedigree Blurb / Highlight</span>
            <textarea id="hd-pedigree_blurb" rows="2" class="form-input mt-1 w-full text-sm"
              placeholder="Narrative summary for Pedigree tab header & PDS Sec 3…">${pedBlurb}</textarea>
          </label>
          <label class="block text-sm">
            <span class="text-slate-500 text-xs font-semibold uppercase">Trainer Commentary (Quote Block)</span>
            <textarea id="hd-trainer_commentary" rows="2" class="form-input mt-1 w-full text-sm"
              placeholder="Highlighted trainer commentary block for Trainer tab & PDS Sec 4…">${trnComm}</textarea>
          </label>
          <label class="block text-sm">
            <span class="text-slate-500 text-xs font-semibold uppercase">Next up</span>
            <input id="hd-next_up" class="form-input mt-1 w-full" value="${nextVal}"
              placeholder="e.g. Trials Cambridge · Spring prep" />
          </label>
          <label class="block text-sm">
            <span class="text-slate-500 text-xs font-semibold uppercase">Marketplace image path</span>
            <input id="hd-image_path" class="form-input mt-1 w-full font-mono text-sm" value="${imgVal}"
              placeholder="/images/content/horses/nellie-BG.png or cover slot path" />
          </label>
          ${imgVal ? `<div class="rounded-lg border border-slate-200 overflow-hidden max-w-sm bg-slate-50">
            <img src="${imgVal}" alt="Marketplace preview" class="w-full h-40 object-cover" onerror="this.parentElement.innerHTML='<div class=\\'p-4 text-xs text-slate-500\\'>Preview unavailable (path may be local-only)</div>'" />
          </div>` : ""}
          <button type="button" class="btn-primary text-sm" onclick="window.saveHorseTab('${microchip}', 'marketplace')">Save marketplace content</button>
        </div>`;
    } else if (tab === "media") {
      panel = `
        <div class="space-y-4">
          <p class="text-sm text-slate-500">Cover / conformation / action slots and trainer transcripts.</p>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            ${["cover_image","conformation_image","pedigree_image","action_image"].map(k => `
              <div class="p-3 rounded-lg border border-slate-200 bg-slate-50">
                <div class="font-semibold text-slate-600 uppercase tracking-wide mb-1">${k.replace("_image","")}</div>
                <div class="text-slate-500 truncate">${horse[k] ? "Set" : "Empty"}</div>
              </div>`).join("")}
          </div>
          <a href="#/horse/${encodeURIComponent(microchip)}/media" class="btn-primary text-sm inline-flex">Open media workspace →</a>
          <div class="pt-2 border-t border-slate-100">
            <div class="text-xs font-semibold uppercase text-slate-400 mb-2">Transcripts</div>
            ${transcriptCount === 0
              ? '<p class="text-sm text-slate-500">No transcripts yet.</p>'
              : `<p class="text-sm text-slate-600">${transcriptCount} on file — manage in media workspace.</p>`}
          </div>
        </div>`;
    } else {
      // links — always two LoveRacing surfaces when ID known:
      // 1) breeding/pedigree page  2) race form (EntryDetail modal)
      const lrId = horse.loveracing_id || "";
      const breedUrl = horse.breeding_url || "";
      const defaultPerf = lrId
        ? `https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID=${lrId}`
        : "";
      const perfUrl = (horse.performance_profile_url || "").trim() || defaultPerf;
      panel = `
        <div class="space-y-4">
          <p class="text-sm text-slate-500">External references — breeding page + race form (same horse, two surfaces).</p>
          <label class="block text-sm">
            <span class="text-slate-500 text-xs font-semibold uppercase">LoveRacing ID</span>
            <input id="hd-loveracing_id" type="number" class="form-input mt-1 w-full font-mono" value="${lrId}" />
          </label>
          <label class="block text-sm">
            <span class="text-slate-500 text-xs font-semibold uppercase">1 · Breeding / pedigree URL</span>
            <input id="hd-breeding_url" class="form-input mt-1 w-full font-mono text-sm" value="${(breedUrl || "").replace(/"/g, "&quot;")}" placeholder="https://loveracing.nz/Breeding/{id}/…aspx" />
          </label>
          ${breedUrl ? `<a href="${breedUrl.replace(/"/g, "&quot;")}" target="_blank" rel="noopener" class="inline-flex text-sm font-semibold text-blue-600 hover:underline">Open breeding page →</a>` : `<p class="text-xs text-slate-400">No breeding URL set.</p>`}
          <label class="block text-sm pt-2 border-t border-slate-100">
            <span class="text-slate-500 text-xs font-semibold uppercase">2 · Race form / NZTR record URL</span>
            <input id="hd-performance_profile_url" class="form-input mt-1 w-full font-mono text-sm" value="${(perfUrl || "").replace(/"/g, "&quot;")}" placeholder="https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&amp;HorseID=…" />
          </label>
          <p class="text-xs text-slate-400">Pattern: EntryDetail.aspx?DisplayContext=Modal&amp;HorseID={LoveRacing ID}</p>
          ${perfUrl ? `<a href="${perfUrl.replace(/"/g, "&quot;")}" target="_blank" rel="noopener" class="inline-flex text-sm font-semibold text-blue-600 hover:underline">Open race form →</a>` : `<p class="text-xs text-slate-400">No race form URL (set LoveRacing ID or paste URL).</p>`}
          <div class="pt-2">
            <button type="button" class="btn-primary text-sm" onclick="window.saveHorseTab('${microchip}', 'links')">Save links</button>
          </div>
        </div>`;
    }

    app.innerHTML = `
      <div class="space-y-4 max-w-3xl">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            <button type="button" onclick="window.navigateTo('#/horses')" class="text-slate-400 hover:text-slate-600">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
            </button>
            <div>
              <h2 class="text-2xl font-bold text-slate-900 tracking-tight">${horse.name || "Horse"}</h2>
              <p class="text-xs text-slate-500 font-mono mt-0.5">${horse.microchip}</p>
            </div>
          </div>
          <div class="surface-card px-3 py-2 text-xs space-y-1 min-w-[11rem]">
            <div class="font-semibold text-slate-700">Content checklist · ${done}/${checks.length}</div>
            ${checklistHtml}
          </div>
        </div>

        <div class="flex flex-wrap gap-1 p-1 bg-slate-100 rounded-xl w-fit" id="horse-tab-bar">
          ${tabBtn("identity", "1 · Identity")}
          ${tabBtn("marketplace", "2 · Marketplace")}
          ${tabBtn("media", "3 · Media")}
          ${tabBtn("links", "4 · Links")}
        </div>

        <div class="surface-card p-5" id="horse-tab-panel">
          ${panel}
        </div>
      </div>
    `;

    document.getElementById("horse-tab-bar")?.querySelectorAll("[data-horse-tab]").forEach(btn => {
      btn.addEventListener("click", () => {
        window._horseDetailTab = btn.getAttribute("data-horse-tab");
        renderHorseDetail(microchip);
      });
    });
  } catch (err) {
    console.error("Horse detail render error:", err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Horse Details</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

window.saveHorseTab = async function(microchip, tab) {
  try {
    const headers = await window.getAuthHeader();
    headers["Content-Type"] = "application/json";
    let body = {};
    if (tab === "identity") {
      body = {
        name: document.getElementById("hd-name")?.value?.trim(),
        name_slug: document.getElementById("hd-name_slug")?.value?.trim() || null,
        sex: document.getElementById("hd-sex")?.value,
        colour: document.getElementById("hd-colour")?.value?.trim() || null,
        foaling_date: document.getElementById("hd-foaling_date")?.value || null,
        breeder: document.getElementById("hd-breeder")?.value?.trim() || null,
        sire_name: document.getElementById("hd-sire_name")?.value?.trim() || null,
        dam_name: document.getElementById("hd-dam_name")?.value?.trim() || null,
      };
    } else if (tab === "marketplace") {
      body = {
        story: document.getElementById("hd-story")?.value ?? "",
        next_up: document.getElementById("hd-next_up")?.value?.trim() || null,
        image_path: document.getElementById("hd-image_path")?.value?.trim() || null,
        pillar1_cat: document.getElementById("hd-pillar1_cat")?.value || null,
        pillar1_val: document.getElementById("hd-pillar1_val")?.value?.trim() || null,
        pillar2_cat: document.getElementById("hd-pillar2_cat")?.value || null,
        pillar2_val: document.getElementById("hd-pillar2_val")?.value?.trim() || null,
        pillar3_cat: document.getElementById("hd-pillar3_cat")?.value || null,
        pillar3_val: document.getElementById("hd-pillar3_val")?.value?.trim() || null,
        pedigree_blurb: document.getElementById("hd-pedigree_blurb")?.value?.trim() || null,
        trainer_commentary: document.getElementById("hd-trainer_commentary")?.value?.trim() || null,
      };
      // Keep cover_image aligned when path set and looks like an asset
      if (body.image_path) body.cover_image = body.image_path;
    } else if (tab === "links") {
      const lr = document.getElementById("hd-loveracing_id")?.value;
      const lrNum = lr ? parseInt(lr, 10) : null;
      let perf = document.getElementById("hd-performance_profile_url")?.value?.trim() || null;
      // If operator left race form blank but set ID, lock in EntryDetail pattern
      if (!perf && lrNum) {
        perf = `https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID=${lrNum}`;
      }
      body = {
        breeding_url: document.getElementById("hd-breeding_url")?.value?.trim() || null,
        loveracing_id: lrNum,
        performance_profile_url: perf,
      };
    }
    const resp = await fetch(`${API}/horses/${encodeURIComponent(microchip)}`, {
      method: "PATCH",
      headers,
      body: JSON.stringify(body),
    });
    const res = await resp.json();
    if (!res.success) throw new Error(res.error || "Save failed");
    showToast("Saved · Horse page content only (not auto-pushed to website)", "success");
    renderHorseDetail(microchip);
  } catch (err) {
    showToast(String(err.message || err), "error");
  }
};

window.addEventListener("hashchange", () => window.render());

// ─── Modal Management & Forms ──────────────────────────────────────────────────

window.closeModal = function() {
  const existing = document.getElementById("active-modal");
  if (existing) existing.remove();
};

// ─── Medium-Sized Stepped Horse Wizard ───────────────────────────────────────

window.addHorseState = {
  step: 1,
  microchip: "",
  name: "",
  sex: "filly",
  colour: "",
  foaling_date: "",
  sire_name: "",
  dam_name: "",
  breeder: "",
  loveracing_id: "",
  trainer_id: "",
  owner_id: "",
  trainers: [],
  owners: []
};

window.openAddHorseWizard = async function() {
  window.closeModal();
  window.addHorseState = {
    step: 1,
    microchip: "",
    name: "",
    sex: "filly",
    colour: "",
    foaling_date: "",
    sire_name: "",
    dam_name: "",
    breeder: "",
    loveracing_id: "",
    trainer_id: "",
    owner_id: "",
    trainers: [],
    owners: []
  };

  // Fetch existing trainers and owners on file for Step 3
  try {
    const [trainersRes, ownersRes] = await Promise.all([
      loadTrainers(),
      loadOwners()
    ]);
    window.addHorseState.trainers = trainersRes || [];
    window.addHorseState.owners = ownersRes || [];
  } catch (err) {
    console.error("Error loading trainers/owners for wizard:", err);
  }

  const modal = document.createElement("div");
  modal.id = "active-modal";
  modal.className = "modal-overlay";
  modal.onclick = (e) => { if (e.target === modal) window.closeModal(); };
  modal.innerHTML = `
    <div class="modal-content max-w-xl shadow-2xl" onclick="event.stopPropagation()">
      <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
        <div>
          <h3 class="text-lg font-bold text-slate-900">🐴 Add New Horse Wizard</h3>
          <p class="text-xs text-slate-500">Step-by-step entry for horse identity, pedigree, and stabling on file.</p>
        </div>
        <button type="button" onclick="window.closeModal()" class="text-slate-400 hover:text-slate-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <!-- Step Indicator Bar -->
      <div id="wizard-step-bar" class="mb-5"></div>

      <!-- Step Content Area -->
      <div id="wizard-step-container"></div>
    </div>
  `;
  document.body.appendChild(modal);
  window.renderAddHorseWizardStep();
};

window.renderAddHorseWizardStep = function() {
  const s = window.addHorseState;
  const bar = document.getElementById("wizard-step-bar");
  const container = document.getElementById("wizard-step-container");
  if (!bar || !container) return;

  // Step Bar Render
  bar.innerHTML = `
    <div class="flex items-center justify-between px-1">
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 1 ? 'bg-blue-600 text-white' : (s.step > 1 ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}">1</div>
        <span class="text-xs font-semibold ${s.step === 1 ? 'text-blue-600' : 'text-slate-600'}">Identity</span>
      </div>
      <div class="h-0.5 w-6 ${s.step > 1 ? 'bg-emerald-500' : 'bg-slate-200'}"></div>
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 2 ? 'bg-blue-600 text-white' : (s.step > 2 ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}">2</div>
        <span class="text-xs font-semibold ${s.step === 2 ? 'text-blue-600' : 'text-slate-600'}">Pedigree</span>
      </div>
      <div class="h-0.5 w-6 ${s.step > 2 ? 'bg-emerald-500' : 'bg-slate-200'}"></div>
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 3 ? 'bg-blue-600 text-white' : (s.step > 3 ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}">3</div>
        <span class="text-xs font-semibold ${s.step === 3 ? 'text-blue-600' : 'text-slate-600'}">Stables</span>
      </div>
      <div class="h-0.5 w-6 ${s.step > 3 ? 'bg-emerald-500' : 'bg-slate-200'}"></div>
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 4 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}">4</div>
        <span class="text-xs font-semibold ${s.step === 4 ? 'text-blue-600' : 'text-slate-600'}">Review</span>
      </div>
    </div>
  `;

  // Step Body Render
  if (s.step === 1) {
    container.innerHTML = `
      <div class="space-y-4">
        <div class="bg-blue-50/70 border border-blue-200 rounded-xl p-3.5">
          <label class="form-label text-blue-900">LoveRacing URL or microchip</label>
          <div class="flex gap-2">
            <input type="text" id="lookup-chip-input" value="${s.microchip || s.breeding_url || ''}" placeholder="15-digit chip OR loveracing.nz/… URL" class="form-input flex-1 font-mono text-sm">
            <button type="button" onclick="window.performNztrWizardLookup()" class="btn-primary text-xs shrink-0">Pull</button>
          </div>
          <div id="wizard-lookup-status" class="text-xs text-slate-500 mt-1.5 hidden"></div>
          <p class="text-[11px] text-slate-500 mt-1.5">Cloudflare block? Same fields — enter manually and continue.</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="form-label">Microchip (15 digits) *</label>
            <input type="text" id="wiz-microchip" value="${s.microchip}" required pattern="\\d{15}" placeholder="985125000123456" class="form-input font-mono">
          </div>
          <div>
            <label class="form-label">Registered name *</label>
            <input type="text" id="wiz-name" value="${s.name}" required placeholder="e.g. Prudentia (NZ) 2021" class="form-input">
          </div>
          <div>
            <label class="form-label">Sex *</label>
            <select id="wiz-sex" class="form-input">
              <option value="filly" ${s.sex === 'filly' ? 'selected' : ''}>Filly</option>
              <option value="colt" ${s.sex === 'colt' ? 'selected' : ''}>Colt</option>
              <option value="gelding" ${s.sex === 'gelding' ? 'selected' : ''}>Gelding</option>
              <option value="mare" ${s.sex === 'mare' ? 'selected' : ''}>Mare</option>
              <option value="stallion" ${s.sex === 'stallion' ? 'selected' : ''}>Stallion</option>
            </select>
          </div>
          <div>
            <label class="form-label">Colour</label>
            <input type="text" id="wiz-colour" value="${s.colour}" placeholder="Bay, Chestnut, Grey…" class="form-input">
          </div>
          <div class="sm:col-span-2">
            <label class="form-label">Foaling date</label>
            <input type="date" id="wiz-foaling-date" value="${s.foaling_date}" class="form-input">
          </div>
        </div>

        <div class="flex justify-between pt-3 border-t border-slate-200">
          <button type="button" onclick="window.closeModal()" class="btn-secondary">Cancel</button>
          <button type="button" onclick="window.wizardNextStep(1)" class="btn-primary">Next: Pedigree →</button>
        </div>
      </div>
    `;
  } else if (s.step === 2) {
    container.innerHTML = `
      <div class="space-y-4">
        <h4 class="text-sm font-bold text-slate-700 uppercase tracking-wider">Step 2: Pedigree & Breeding Details</h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Sire Name</label>
            <input type="text" id="wiz-sire" value="${s.sire_name}" placeholder="e.g. PROISIR (AUS) 2009" class="form-input">
          </div>
          <div>
            <label class="form-label">Dam Name</label>
            <input type="text" id="wiz-dam" value="${s.dam_name}" placeholder="e.g. LITTLE BIT IRISH (NZ) 2012" class="form-input">
          </div>
          <div>
            <label class="form-label">Breeder</label>
            <input type="text" id="wiz-breeder" value="${s.breeder}" placeholder="e.g. Golden Eye Trust" class="form-input">
          </div>
          <div>
            <label class="form-label">Loveracing ID</label>
            <input type="number" id="wiz-loveracing-id" value="${s.loveracing_id}" placeholder="e.g. 428364" class="form-input font-mono">
          </div>
        </div>

        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.wizardPrevStep(2)" class="btn-secondary">← Back</button>
          <button type="button" onclick="window.wizardNextStep(2)" class="btn-primary">Next: Stabling & Owners →</button>
        </div>
      </div>
    `;
  } else if (s.step === 3) {
    const trainerOpts = s.trainers.map(t => `<option value="${t.id}" ${s.trainer_id === t.id ? 'selected' : ''}>${t.name} (${t.stable_name || t.location})</option>`).join('');
    const ownerOpts = s.owners.map(o => `<option value="${o.id}" ${s.owner_id === o.id ? 'selected' : ''}>${o.name} (${o.entity_type || 'Owner'})</option>`).join('');

    container.innerHTML = `
      <div class="space-y-4">
        <h4 class="text-sm font-bold text-slate-700 uppercase tracking-wider">Step 3: Stabling & Ownership On File</h4>
        <p class="text-xs text-slate-500">Select existing partner trainer and owner entities registered on file.</p>

        <div class="space-y-4">
          <div>
            <label class="form-label">Assigned Partner Trainer / Stable</label>
            <select id="wiz-trainer-id" class="form-input">
              <option value="">-- Select Trainer on File --</option>
              ${trainerOpts || '<option value="TRN-001">Wexford Stables (Lance O\'Sullivan & Andrew Scott)</option>'}
            </select>
          </div>
          <div>
            <label class="form-label">Assigned Bloodstock Owner</label>
            <select id="wiz-owner-id" class="form-input">
              <option value="">-- Select Owner on File --</option>
              ${ownerOpts || '<option value="OWN-001">B.A.X Bloodstock Achieving Xcellence Ltd</option>'}
            </select>
          </div>
        </div>

        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.wizardPrevStep(3)" class="btn-secondary">← Back</button>
          <button type="button" onclick="window.wizardNextStep(3)" class="btn-primary">Next: Review →</button>
        </div>
      </div>
    `;
  } else if (s.step === 4) {
    const selectedTrainer = s.trainers.find(t => t.id === s.trainer_id)?.name || (s.trainer_id ? s.trainer_id : "—");
    const selectedOwner = s.owners.find(o => o.id === s.owner_id)?.name || (s.owner_id ? s.owner_id : "—");

    container.innerHTML = `
      <div class="space-y-4">
        <h4 class="text-sm font-bold text-slate-700 uppercase tracking-wider">Step 4: Review & Confirm</h4>

        <div class="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-2 text-sm">
          <div class="flex justify-between py-1 border-b border-slate-200">
            <span class="text-slate-500">Horse Name:</span>
            <span class="font-bold text-slate-900">${s.name}</span>
          </div>
          <div class="flex justify-between py-1 border-b border-slate-200">
            <span class="text-slate-500">Microchip:</span>
            <span class="font-mono font-semibold text-slate-900">${s.microchip}</span>
          </div>
          <div class="flex justify-between py-1 border-b border-slate-200">
            <span class="text-slate-500">Sex / Colour:</span>
            <span class="font-semibold text-slate-900">${s.sex.toUpperCase()} • ${s.colour || '—'}</span>
          </div>
          <div class="flex justify-between py-1 border-b border-slate-200">
            <span class="text-slate-500">Sire & Dam:</span>
            <span class="font-semibold text-slate-900">${s.sire_name || '—'} x ${s.dam_name || '—'}</span>
          </div>
          <div class="flex justify-between py-1 border-b border-slate-200">
            <span class="text-slate-500">Trainer:</span>
            <span class="font-semibold text-blue-600">${selectedTrainer}</span>
          </div>
          <div class="flex justify-between py-1">
            <span class="text-slate-500">Owner:</span>
            <span class="font-semibold text-blue-600">${selectedOwner}</span>
          </div>
        </div>

        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.wizardPrevStep(4)" class="btn-secondary">← Back</button>
          <button type="button" onclick="window.submitAddHorseWizard()" class="btn-primary">Save Horse & Sync ⚡</button>
        </div>
      </div>
    `;
  }
};

window.wizardNextStep = function(currentStep) {
  const s = window.addHorseState;
  if (currentStep === 1) {
    const chip = document.getElementById("wiz-microchip")?.value?.trim();
    const name = document.getElementById("wiz-name")?.value?.trim();
    const date = document.getElementById("wiz-foaling-date")?.value;
    if (!chip || chip.length !== 15 || !/^\d+$/.test(chip)) {
      alert("15-digit microchip required (pull from LoveRacing or type manually).");
      return;
    }
    if (!name) {
      alert("Registered horse name required.");
      return;
    }

    s.microchip = chip;
    s.name = name;
    s.sex = document.getElementById("wiz-sex")?.value || "filly";
    s.colour = document.getElementById("wiz-colour")?.value?.trim() || "";
    s.foaling_date = date || "";
    s.step = 2;
  } else if (currentStep === 2) {
    s.sire_name = document.getElementById("wiz-sire")?.value?.trim() || "";
    s.dam_name = document.getElementById("wiz-dam")?.value?.trim() || "";
    s.breeder = document.getElementById("wiz-breeder")?.value?.trim() || "";
    s.loveracing_id = document.getElementById("wiz-loveracing-id")?.value?.trim() || "";
    s.step = 3;
  } else if (currentStep === 3) {
    s.trainer_id = document.getElementById("wiz-trainer-id")?.value || "";
    s.owner_id = document.getElementById("wiz-owner-id")?.value || "";
    s.step = 4;
  }
  window.renderAddHorseWizardStep();
};

window.wizardPrevStep = function(currentStep) {
  if (currentStep > 1) {
    window.addHorseState.step = currentStep - 1;
    window.renderAddHorseWizardStep();
  }
};

window.performNztrWizardLookup = async function() {
  const query = document.getElementById("lookup-chip-input")?.value?.trim();
  const statusEl = document.getElementById("wizard-lookup-status");
  if (!query) {
    alert("Paste a 15-digit microchip or a loveracing.nz URL.");
    return;
  }
  if (statusEl) {
    statusEl.classList.remove("hidden");
    statusEl.textContent = "Pulling from loveracing.nz…";
  }
  try {
    const headers = await window.getAuthHeader();
    const resp = await fetch("/api/horses/lookup", {
      method: "POST",
      headers,
      body: JSON.stringify({ query })
    });
    const res = await resp.json();
    if (res.success && res.data) {
      const data = res.data;
      if (data.microchip) window.addHorseState.microchip = data.microchip;
      else if (/^\d{15}$/.test(query)) window.addHorseState.microchip = query;
      if (data.name) window.addHorseState.name = data.name;
      if (data.sex) window.addHorseState.sex = String(data.sex).toLowerCase().split(/\s+/)[0];
      if (data.colour) window.addHorseState.colour = data.colour;
      if (data.foaling_date) window.addHorseState.foaling_date = data.foaling_date;
      if (data.sire_name) window.addHorseState.sire_name = data.sire_name;
      if (data.dam_name) window.addHorseState.dam_name = data.dam_name;
      if (data.breeder) window.addHorseState.breeder = data.breeder;
      if (data.loveracing_id) window.addHorseState.loveracing_id = data.loveracing_id;
      if (data.breeding_url) window.addHorseState.breeding_url = data.breeding_url;

      window.renderAddHorseWizardStep();
      const newStatus = document.getElementById("wizard-lookup-status");
      if (newStatus) {
        newStatus.classList.remove("hidden");
        if (data.warning && !data.name) {
          newStatus.className = "text-xs text-amber-600 font-semibold mt-1.5";
          newStatus.textContent = data.warning;
        } else if (data.warning) {
          newStatus.className = "text-xs text-amber-600 font-semibold mt-1.5";
          newStatus.textContent = `Partial pull: ${data.warning}`;
        } else {
          newStatus.className = "text-xs text-emerald-600 font-semibold mt-1.5";
          newStatus.textContent = `Pulled: ${data.name || "horse"} — confirm fields, then Next.`;
        }
      }
    } else {
      if (statusEl) {
        statusEl.className = "text-xs text-amber-600 font-semibold mt-1.5";
        statusEl.textContent = res.error || "Lookup failed. Enter details manually.";
      }
    }
  } catch (err) {
    if (statusEl) {
      statusEl.className = "text-xs text-rose-600 font-semibold mt-1.5";
      statusEl.textContent = `Lookup error: ${err.message}`;
    }
  }
};

window.submitAddHorseWizard = async function() {
  const s = window.addHorseState;
  try {
    const payload = {
      microchip: s.microchip,
      name: s.name,
      sex: s.sex,
      colour: s.colour || null,
      foaling_date: s.foaling_date || null,
      sire_name: s.sire_name || null,
      dam_name: s.dam_name || null,
      breeder: s.breeder || null,
      trainer_id: s.trainer_id || null,
      loveracing_id: s.loveracing_id ? parseInt(s.loveracing_id, 10) : null,
      breeding_url: s.breeding_url || null,
    };

    const headers = await window.getAuthHeader();
    const resp = await fetch("/api/horses", {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    });
    const res = await resp.json();
    if (res.success) {
      showToast(`🐴 Horse '${s.name}' saved in MC (not auto-published)`, "success");
      window.closeModal();
      renderHorses();
    } else {
      alert("Error creating horse: " + (typeof res.error === 'string' ? res.error : JSON.stringify(res.error)));
    }
  } catch (err) {
    alert("Save error: " + err.message);
  }
};

// ─── Medium-Sized Stepped Trainer Wizard ──────────────────────────────────────

window.addTrainerState = {
  step: 1,
  name: "",
  stable_name: "",
  location: "",
  nztr_license_number: "",
  email: "",
  phone: "",
  website: ""
};

window.openAddTrainerWizard = function() {
  window.closeModal();
  window.addTrainerState = {
    step: 1,
    name: "",
    stable_name: "",
    location: "",
    nztr_license_number: "",
    email: "",
    phone: "",
    website: ""
  };

  const modal = document.createElement("div");
  modal.id = "active-modal";
  modal.className = "modal-overlay";
  modal.onclick = (e) => { if (e.target === modal) window.closeModal(); };
  modal.innerHTML = `
    <div class="modal-content max-w-xl shadow-2xl" onclick="event.stopPropagation()">
      <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
        <div>
          <h3 class="text-lg font-bold text-slate-900">🧢 Add New Trainer Wizard</h3>
          <p class="text-xs text-slate-500">Step-by-step registration for partner training stables.</p>
        </div>
        <button type="button" onclick="window.closeModal()" class="text-slate-400 hover:text-slate-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div id="trainer-wizard-bar" class="mb-5"></div>
      <div id="trainer-wizard-container"></div>
    </div>
  `;
  document.body.appendChild(modal);
  window.renderAddTrainerWizardStep();
};

window.renderAddTrainerWizardStep = function() {
  const s = window.addTrainerState;
  const bar = document.getElementById("trainer-wizard-bar");
  const container = document.getElementById("trainer-wizard-container");
  if (!bar || !container) return;

  bar.innerHTML = `
    <div class="flex items-center justify-between px-4">
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 1 ? 'bg-blue-600 text-white' : (s.step > 1 ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}">1</div>
        <span class="text-xs font-semibold ${s.step === 1 ? 'text-blue-600' : 'text-slate-600'}">Stable Info</span>
      </div>
      <div class="h-0.5 w-12 ${s.step > 1 ? 'bg-emerald-500' : 'bg-slate-200'}"></div>
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 2 ? 'bg-blue-600 text-white' : (s.step > 2 ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}">2</div>
        <span class="text-xs font-semibold ${s.step === 2 ? 'text-blue-600' : 'text-slate-600'}">Contact</span>
      </div>
      <div class="h-0.5 w-12 ${s.step > 2 ? 'bg-emerald-500' : 'bg-slate-200'}"></div>
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 3 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}">3</div>
        <span class="text-xs font-semibold ${s.step === 3 ? 'text-blue-600' : 'text-slate-600'}">Review</span>
      </div>
    </div>
  `;

  if (s.step === 1) {
    container.innerHTML = `
      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Trainer Name(s) *</label>
            <input type="text" id="twiz-name" value="${s.name}" required placeholder="e.g. Lance O'Sullivan & Andrew Scott" class="form-input">
          </div>
          <div>
            <label class="form-label">Stable Name *</label>
            <input type="text" id="twiz-stable" value="${s.stable_name}" required placeholder="e.g. Wexford Stables" class="form-input">
          </div>
          <div>
            <label class="form-label">Location *</label>
            <input type="text" id="twiz-location" value="${s.location}" required placeholder="e.g. Matamata NZ" class="form-input">
          </div>
          <div>
            <label class="form-label">NZTR License Number</label>
            <input type="text" id="twiz-license" value="${s.nztr_license_number}" placeholder="TRN-NZTR-8842" class="form-input font-mono">
          </div>
        </div>
        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.closeModal()" class="btn-secondary">Cancel</button>
          <button type="button" onclick="window.trainerWizardNextStep(1)" class="btn-primary">Next: Contact Info →</button>
        </div>
      </div>
    `;
  } else if (s.step === 2) {
    container.innerHTML = `
      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Email Address *</label>
            <input type="email" id="twiz-email" value="${s.email}" required placeholder="trainers@wexford.co.nz" class="form-input">
          </div>
          <div>
            <label class="form-label">Phone Number</label>
            <input type="text" id="twiz-phone" value="${s.phone}" placeholder="+64 7 888 1234" class="form-input">
          </div>
          <div class="sm:col-span-2">
            <label class="form-label">Website URL</label>
            <input type="url" id="twiz-website" value="${s.website}" placeholder="https://wexfordstables.co.nz" class="form-input">
          </div>
        </div>
        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.trainerWizardPrevStep(2)" class="btn-secondary">← Back</button>
          <button type="button" onclick="window.trainerWizardNextStep(2)" class="btn-primary">Next: Review →</button>
        </div>
      </div>
    `;
  } else if (s.step === 3) {
    container.innerHTML = `
      <div class="space-y-4">
        <div class="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-2 text-sm">
          <div class="flex justify-between py-1 border-b border-slate-200"><span class="text-slate-500">Trainer Name:</span><span class="font-bold text-slate-900">${s.name}</span></div>
          <div class="flex justify-between py-1 border-b border-slate-200"><span class="text-slate-500">Stable Name:</span><span class="font-semibold text-slate-900">${s.stable_name}</span></div>
          <div class="flex justify-between py-1 border-b border-slate-200"><span class="text-slate-500">Location:</span><span class="text-slate-900">${s.location}</span></div>
          <div class="flex justify-between py-1 border-b border-slate-200"><span class="text-slate-500">Email:</span><span class="font-semibold text-blue-600">${s.email}</span></div>
          <div class="flex justify-between py-1"><span class="text-slate-500">License:</span><span class="font-mono text-slate-700">${s.nztr_license_number || '—'}</span></div>
        </div>
        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.trainerWizardPrevStep(3)" class="btn-secondary">← Back</button>
          <button type="button" onclick="window.submitAddTrainerWizard()" class="btn-primary">Save Trainer ⚡</button>
        </div>
      </div>
    `;
  }
};

window.trainerWizardNextStep = function(step) {
  const s = window.addTrainerState;
  if (step === 1) {
    const name = document.getElementById("twiz-name")?.value?.trim();
    const stable = document.getElementById("twiz-stable")?.value?.trim();
    const loc = document.getElementById("twiz-location")?.value?.trim();
    if (!name || !stable || !loc) {
      alert("Please fill in Trainer Name, Stable Name, and Location.");
      return;
    }
    s.name = name;
    s.stable_name = stable;
    s.location = loc;
    s.nztr_license_number = document.getElementById("twiz-license")?.value?.trim() || "";
    s.step = 2;
  } else if (step === 2) {
    const email = document.getElementById("twiz-email")?.value?.trim();
    if (!email) {
      alert("Please enter a valid email address.");
      return;
    }
    s.email = email;
    s.phone = document.getElementById("twiz-phone")?.value?.trim() || "";
    s.website = document.getElementById("twiz-website")?.value?.trim() || "";
    s.step = 3;
  }
  window.renderAddTrainerWizardStep();
};

window.trainerWizardPrevStep = function(step) {
  if (step > 1) {
    window.addTrainerState.step = step - 1;
    window.renderAddTrainerWizardStep();
  }
};

window.submitAddTrainerWizard = async function() {
  const s = window.addTrainerState;
  try {
    const payload = {
      name: s.name,
      stable_name: s.stable_name,
      location: s.location,
      email: s.email,
      phone: s.phone || null,
      nztr_license_number: s.nztr_license_number || null,
      website: s.website || null
    };

    const headers = await window.getAuthHeader();
    const resp = await fetch("/api/trainers", {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    });
    const res = await resp.json();
    if (res.success) {
      showToast(`🧢 Trainer '${s.name}' registered!`, "success");
      window.closeModal();
      renderTrainers();
    } else {
      alert("Error creating trainer: " + JSON.stringify(res.error));
    }
  } catch (err) {
    alert("Save error: " + err.message);
  }
};

// ─── Medium-Sized Stepped Owner Wizard ────────────────────────────────────────

window.addOwnerState = {
  step: 1,
  name: "",
  entity_type: "company",
  contact_name: "",
  email: "",
  phone: "",
  address: "",
  website: ""
};

window.openAddOwnerWizard = function() {
  window.closeModal();
  window.addOwnerState = {
    step: 1,
    name: "",
    entity_type: "company",
    contact_name: "",
    email: "",
    phone: "",
    address: "",
    website: ""
  };

  const modal = document.createElement("div");
  modal.id = "active-modal";
  modal.className = "modal-overlay";
  modal.onclick = (e) => { if (e.target === modal) window.closeModal(); };
  modal.innerHTML = `
    <div class="modal-content max-w-xl shadow-2xl" onclick="event.stopPropagation()">
      <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
        <div>
          <h3 class="text-lg font-bold text-slate-900">👥 Add New Owner Wizard</h3>
          <p class="text-xs text-slate-500">Step-by-step registration for bloodstock owners & syndicates.</p>
        </div>
        <button type="button" onclick="window.closeModal()" class="text-slate-400 hover:text-slate-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div id="owner-wizard-bar" class="mb-5"></div>
      <div id="owner-wizard-container"></div>
    </div>
  `;
  document.body.appendChild(modal);
  window.renderAddOwnerWizardStep();
};

window.renderAddOwnerWizardStep = function() {
  const s = window.addOwnerState;
  const bar = document.getElementById("owner-wizard-bar");
  const container = document.getElementById("owner-wizard-container");
  if (!bar || !container) return;

  bar.innerHTML = `
    <div class="flex items-center justify-between px-4">
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 1 ? 'bg-blue-600 text-white' : (s.step > 1 ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}">1</div>
        <span class="text-xs font-semibold ${s.step === 1 ? 'text-blue-600' : 'text-slate-600'}">Entity Info</span>
      </div>
      <div class="h-0.5 w-12 ${s.step > 1 ? 'bg-emerald-500' : 'bg-slate-200'}"></div>
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 2 ? 'bg-blue-600 text-white' : (s.step > 2 ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}">2</div>
        <span class="text-xs font-semibold ${s.step === 2 ? 'text-blue-600' : 'text-slate-600'}">Contact</span>
      </div>
      <div class="h-0.5 w-12 ${s.step > 2 ? 'bg-emerald-500' : 'bg-slate-200'}"></div>
      <div class="flex items-center gap-1.5">
        <div class="w-7 h-7 rounded-full text-xs font-bold flex items-center justify-center ${s.step === 3 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}">3</div>
        <span class="text-xs font-semibold ${s.step === 3 ? 'text-blue-600' : 'text-slate-600'}">Review</span>
      </div>
    </div>
  `;

  if (s.step === 1) {
    container.innerHTML = `
      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="sm:col-span-2">
            <label class="form-label">Full Entity / Owner Name *</label>
            <input type="text" id="owiz-name" value="${s.name}" required placeholder="e.g. B.A.X Bloodstock Achieving Xcellence Ltd" class="form-input">
          </div>
          <div>
            <label class="form-label">Entity Type *</label>
            <select id="owiz-entity-type" class="form-input">
              <option value="company" ${s.entity_type === 'company' ? 'selected' : ''}>Company</option>
              <option value="syndicate" ${s.entity_type === 'syndicate' ? 'selected' : ''}>Syndicate</option>
              <option value="individual" ${s.entity_type === 'individual' ? 'selected' : ''}>Individual</option>
            </select>
          </div>
          <div>
            <label class="form-label">Contact Person</label>
            <input type="text" id="owiz-contact-name" value="${s.contact_name}" placeholder="Primary Representative" class="form-input">
          </div>
        </div>
        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.closeModal()" class="btn-secondary">Cancel</button>
          <button type="button" onclick="window.ownerWizardNextStep(1)" class="btn-primary">Next: Contact Info →</button>
        </div>
      </div>
    `;
  } else if (s.step === 2) {
    container.innerHTML = `
      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="form-label">Email Address *</label>
            <input type="email" id="owiz-email" value="${s.email}" required placeholder="contact@bloodstock.co.nz" class="form-input">
          </div>
          <div>
            <label class="form-label">Phone Number</label>
            <input type="text" id="owiz-phone" value="${s.phone}" placeholder="+64 21 123 4567" class="form-input">
          </div>
          <div class="sm:col-span-2">
            <label class="form-label">Physical Address</label>
            <input type="text" id="owiz-address" value="${s.address}" placeholder="123 Bloodstock Way, Cambridge" class="form-input">
          </div>
          <div class="sm:col-span-2">
            <label class="form-label">Website URL</label>
            <input type="url" id="owiz-website" value="${s.website}" placeholder="https://example.co.nz" class="form-input">
          </div>
        </div>
        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.ownerWizardPrevStep(2)" class="btn-secondary">← Back</button>
          <button type="button" onclick="window.ownerWizardNextStep(2)" class="btn-primary">Next: Review →</button>
        </div>
      </div>
    `;
  } else if (s.step === 3) {
    container.innerHTML = `
      <div class="space-y-4">
        <div class="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-2 text-sm">
          <div class="flex justify-between py-1 border-b border-slate-200"><span class="text-slate-500">Entity Name:</span><span class="font-bold text-slate-900">${s.name}</span></div>
          <div class="flex justify-between py-1 border-b border-slate-200"><span class="text-slate-500">Entity Type:</span><span class="font-semibold text-slate-900">${s.entity_type.toUpperCase()}</span></div>
          <div class="flex justify-between py-1 border-b border-slate-200"><span class="text-slate-500">Contact:</span><span class="text-slate-900">${s.contact_name || '—'}</span></div>
          <div class="flex justify-between py-1"><span class="text-slate-500">Email:</span><span class="font-semibold text-blue-600">${s.email}</span></div>
        </div>
        <div class="flex justify-between pt-4 border-t border-slate-200">
          <button type="button" onclick="window.ownerWizardPrevStep(3)" class="btn-secondary">← Back</button>
          <button type="button" onclick="window.submitAddOwnerWizard()" class="btn-primary">Save Owner ⚡</button>
        </div>
      </div>
    `;
  }
};

window.ownerWizardNextStep = function(step) {
  const s = window.addOwnerState;
  if (step === 1) {
    const name = document.getElementById("owiz-name")?.value?.trim();
    if (!name) {
      alert("Please enter full entity/owner name.");
      return;
    }
    s.name = name;
    s.entity_type = document.getElementById("owiz-entity-type")?.value || "company";
    s.contact_name = document.getElementById("owiz-contact-name")?.value?.trim() || "";
    s.step = 2;
  } else if (step === 2) {
    const email = document.getElementById("owiz-email")?.value?.trim();
    if (!email) {
      alert("Please enter email address.");
      return;
    }
    s.email = email;
    s.phone = document.getElementById("owiz-phone")?.value?.trim() || "";
    s.address = document.getElementById("owiz-address")?.value?.trim() || "";
    s.website = document.getElementById("owiz-website")?.value?.trim() || "";
    s.step = 3;
  }
  window.renderAddOwnerWizardStep();
};

window.ownerWizardPrevStep = function(step) {
  if (step > 1) {
    window.addOwnerState.step = step - 1;
    window.renderAddOwnerWizardStep();
  }
};

window.submitAddOwnerWizard = async function() {
  const s = window.addOwnerState;
  try {
    const payload = {
      name: s.name,
      entity_type: s.entity_type,
      contact_name: s.contact_name || null,
      email: s.email,
      phone: s.phone || null,
      address: s.address || null,
      website: s.website || null
    };

    const headers = await window.getAuthHeader();
    const resp = await fetch("/api/owners", {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    });
    const res = await resp.json();
    if (res.success) {
      showToast(`👥 Owner '${s.name}' registered!`, "success");
      window.closeModal();
      renderOwners();
    } else {
      alert("Error creating owner: " + JSON.stringify(res.error));
    }
  } catch (err) {
    alert("Save error: " + err.message);
  }
};

window.addEventListener("hashchange", () => window.render());

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => window.render());
} else {
  window.render();
}

console.log('=== app.js module loaded ===');



