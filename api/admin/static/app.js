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

function closeDocModal() {
  const modal = document.querySelector('.modal-overlay');
  if (modal) modal.remove();
}

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
      governing_bodies: stats.governing_bodies ?? 0,
      hlts: stats.hlts ?? hlts.length,
    };
    app.innerHTML = `
      <div class="card">
        <h2 class="text-xl font-bold mb-6">Mission Control</h2>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <a href="#/horses" class="bg-white rounded-lg p-4 border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer block">
            <div class="text-3xl font-bold text-slate-900">${c.horses}</div>
            <div class="text-sm text-slate-600 font-medium">Horses</div>
          </a>
          <a href="#/owners" class="bg-white rounded-lg p-4 border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer block">
            <div class="text-3xl font-bold text-slate-900">${c.owners}</div>
            <div class="text-sm text-slate-600 font-medium">Owners</div>
          </a>
          <a href="#/trainers" class="bg-white rounded-lg p-4 border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer block">
            <div class="text-3xl font-bold text-slate-900">${c.trainers}</div>
            <div class="text-sm text-slate-600 font-medium">Trainers / Stables</div>
          </a>
          <a href="#/governing-bodies" class="bg-white rounded-lg p-4 border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer block">
            <div class="text-3xl font-bold text-slate-900">${c.governing_bodies}</div>
            <div class="text-sm text-slate-600 font-medium">Governing Bodies</div>
          </a>
          <a href="#/hlts" class="bg-white rounded-lg p-4 border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer block">
            <div class="text-3xl font-bold text-slate-900">${c.hlts}</div>
            <div class="text-sm text-slate-600 font-medium">Active HLTs</div>
          </a>
        </div>
        <div class="flex gap-3">
          <a href="#/create-hlt" class="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-green-700">+ Create HLT</a>
          <a href="#/hlts" class="bg-gray-800 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-900">View HLTs</a>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Dashboard render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Dashboard</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

// ─── Horses ───────────────────────────────────────────────────────────────────

async function renderHorses() {
  try {
    setLoading(true);
    const horses = await loadHorses();
    const rows = horses.map(h => `
      <tr class="border-b hover:bg-gray-50 cursor-pointer" onclick="window.navigateTo('#/horse/${encodeURIComponent(h.microchip)}')">
        <td class="px-4 py-3">
          <div class="font-semibold text-blue-600 hover:underline">${h.name || "—"}</div>
          <div class="tag">${h.microchip}</div>
        </td>
        <td class="px-4 py-3">${h.sex || "—"}</td>
        <td class="px-4 py-3">${h.colour || "—"}</td>
        <td class="px-4 py-3">${h.foaling_date || "—"}</td>
        <td class="px-4 py-3">${h.sire_name || "—"}</td>
        <td class="px-4 py-3">${h.dam_name || "—"}</td>
        <td class="px-4 py-3">${h.breeder || "—"}</td>
        <td class="px-4 py-3">${h.breeding_url ? `<a href="${h.breeding_url}" target="_blank" class="breeding-url" onclick="event.stopPropagation()">loveracing.nz</a>` : "—"}</td>
      </tr>
    `).join("");
    app.innerHTML = `
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Horses (${horses.length})</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border">
            <thead class="bg-gray-100">
              <tr>
                <th class="px-4 py-2">Name</th>
                <th class="px-4 py-2">Sex</th>
                <th class="px-4 py-2">Colour</th>
                <th class="px-4 py-2">Foaling Date</th>
                <th class="px-4 py-2">Sire</th>
                <th class="px-4 py-2">Dam</th>
                <th class="px-4 py-2">Breeder</th>
                <th class="px-4 py-2">Breeding URL</th>
              </tr>
            </thead>
            <tbody>${rows || '<tr><td colspan="8" class="px-4 py-4 text-gray-500">No horses.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Horses render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Horses</h2><p class="text-slate-600">${err.message}</p></div>`;
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
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Owners (${rows.length})</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border">
            <thead class="bg-gray-100">
              <tr>
                <th class="px-4 py-2">Name</th>
                <th class="px-4 py-2">Type</th>
                <th class="px-4 py-2">Contact</th>
                <th class="px-4 py-2">Email</th>
                <th class="px-4 py-2">Phone</th>
                <th class="px-4 py-2">Website</th>
              </tr>
            </thead>
            <tbody>${body || '<tr><td colspan="6" class="px-4 py-4 text-gray-500">No owners.</td></tr>'}</tbody>
          </table>
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
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Trainers / Stables (${rows.length})</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border">
            <thead class="bg-gray-100">
              <tr>
                <th class="px-4 py-2">Name</th>
                <th class="px-4 py-2">Stable</th>
                <th class="px-4 py-2">Location</th>
                <th class="px-4 py-2">Contact</th>
                <th class="px-4 py-2">Email</th>
                <th class="px-4 py-2">Phone</th>
                <th class="px-4 py-2">Website</th>
              </tr>
            </thead>
            <tbody>${body || '<tr><td colspan="7" class="px-4 py-4 text-gray-500">No trainers.</td></tr>'}</tbody>
          </table>
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
    showToast('HLT created successfully!', 'success');
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

  const horseOpts = '<option value="all">All Horses</option>' +
    horses.map(h => `<option value="${h.microchip}" ${horseFilter === h.microchip ? 'selected' : ''}>${h.name}</option>`).join("");

  const statuses = ['draft', 'review', 'complete', 'listing', 'listed', 'published'];
  const statusOpts = '<option value="all">All Statuses</option>' +
    statuses.map(s => `<option value="${s}" ${statusFilter === s ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`).join("");

  const rows = filteredHlts.map(hlt => renderHltRow(hlt)).join("");

  app.innerHTML = `
    <div class="surface-card">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-6 p-4 border-b border-slate-200">
        <div>
          <h3 class="text-xl font-semibold text-slate-900">HLT Registry</h3>
        </div>
        <div class="flex items-center gap-3">
          <button type="button" onclick="publishMarketplace()" class="btn-secondary">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>
            Publish Marketplace
          </button>
          <button type="button" onclick="openCreateHltWizard()" class="btn-primary">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
            Create HLT
          </button>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3 px-4 mb-4">
        <div class="relative">
          <select id="hlt-horse-filter" onchange="setHltHorseFilter(this.value)" class="form-input-sm appearance-none pr-8">
            ${horseOpts}
          </select>
        </div>
        <div class="relative">
          <select id="hlt-status-filter" onchange="setHltStatusFilter(this.value)" class="form-input-sm appearance-none pr-8">
            ${statusOpts}
          </select>
        </div>
        ${(horseFilter !== 'all' || statusFilter !== 'all') ? `
          <button type="button" onclick="clearHltFilters()" class="text-xs font-semibold text-blue-700 hover:underline">Clear filters</button>
        ` : ''}
      </div>

      <div class="overflow-x-auto px-4 pb-4">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="table-header">
              <th class="table-cell font-semibold">HLT Reference</th>
              <th class="table-cell font-semibold">Horse Name</th>
              <th class="table-cell font-semibold">Start Date</th>
              <th class="table-cell font-semibold">Percentage of Task Lease</th>
              <th class="table-cell font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            ${rows || '<tr><td colspan="5" class="px-5 py-8 text-center text-sm text-slate-500">No HLTs found for the selected filter.</td></tr>'}
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
    list = list.filter(l => l.status === hltsState.statusFilter);
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
  const { editingTermSheet, termSheetEdit } = hltsState;
  const isEditing = editingTermSheet === hlt.id;

  // Mock document data - in real app this would come from API
  const termSheetDoc = { document_id: `doc-ts-${hlt.id}`, file_path: `/api/hlts/${hlt.id}/term-sheet.docx` };
  const pdsDoc = { document_id: `doc-pds-${hlt.id}`, file_path: `/api/hlts/${hlt.id}/pds.docx` };
  const saDoc = { document_id: `doc-sa-${hlt.id}`, file_path: `/api/hlts/${hlt.id}/sa.docx` };

  const pdsStatus = 'for_review';
  const saStatus = 'for_review';

  const docBadge = (status) => {
    if (status === 'complete') return '<span class="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">complete</span>';
    if (status === 'flagged') return '<span class="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">flagged</span>';
    return '<span class="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700">for_review</span>';
  };

  const formatCurrency = (val) => {
    if (!val) return '—';
    return new Intl.NumberFormat('en-NZ', { style: 'currency', currency: 'NZD', minimumFractionDigits: 2 }).format(val);
  };

  const termSheetFields = [
    { key: 'token_name', label: 'Token Name', type: 'text', value: hlt.token_name || `HLT – ${horse?.name || 'Asset'} ${hlt.lease_id?.replace('LSE-', '')}` },
    { key: 'erc20_identifier', label: 'ERC20 Identifier', type: 'text', value: hlt.erc20_identifier || `TVHLT${horse?.name?.substring(0,3).toUpperCase()}${hlt.lease_id?.replace('LSE-', '')}` },
    { key: 'percentage_leased', label: 'Percentage Leased (%)', type: 'number', value: hlt.percent_leased || hlt.percentage_leased },
    { key: 'token_count', label: 'Number of Tokens', type: 'number', value: hlt.token_count },
    { key: 'percent_per_token', label: '% Per Token', type: 'number', step: '0.01', value: hlt.percent_per_token },
    { key: 'token_price_nzd', label: 'Token Price (NZD)', type: 'number', step: '0.01', value: hlt.token_price_nzd },
    { key: 'total_issuance_value_nzd', label: 'Total Issuance Value (NZD)', type: 'number', step: '0.01', value: hlt.total_issuance_value_nzd },
    { key: 'investor_share_percent', label: 'Investor Split (%)', type: 'number', value: hlt.investor_share_percent },
    { key: 'owner_share_percent', label: 'Owner Split (%)', type: 'number', value: hlt.owner_share_percent },
    { key: 'start_date', label: 'Start Date', type: 'date', value: hlt.start_date },
    { key: 'duration_months', label: 'Lease Length (months)', type: 'number', value: hlt.duration_months },
    { key: 'variations', label: 'Variations', type: 'text', value: hlt.notes || hlt.variations || 'n/a' },
  ];

  let editFormHtml = '';
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
              <input type="${f.type}" id="ts-${f.key}" value="${f.value || ''}" ${f.step ? `step="${f.step}"` : ''} class="form-input" />
            </label>
          `).join('')}
        </div>
        <div class="flex items-center gap-2 mt-3">
          <button type="button" onclick="saveTermSheetEdit('${hlt.id}')" class="btn-primary">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l5 5L21 7"/></svg> Save
          </button>
          <button type="button" onclick="cancelTermSheetEdit()" class="btn-secondary">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg> Cancel
          </button>
        </div>
      </div>
    `;
  }

  return `
    <tr class="expand-content">
      <td colspan="5" class="p-0">
        <div class="expand-inner">
          <!-- Term Sheet -->
          <div class="doc-card">
            <div class="doc-header">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              <span class="text-sm font-semibold text-slate-900">Term Sheet</span>
            </div>
            <div class="doc-actions">
              ${docBadge('complete')}
              <div class="flex items-center gap-3">
                <button type="button" onclick="event.stopPropagation(); viewTermSheet('${hlt.id}')" class="doc-btn doc-btn-primary">View</button>
                <button type="button" onclick="event.stopPropagation(); startTermSheetEdit('${hlt.id}')" class="doc-btn doc-btn-secondary">Edit</button>
                <button type="button" onclick="event.stopPropagation(); downloadDoc('${termSheetDoc.file_path}')" class="doc-btn doc-btn-muted">Download</button>
              </div>
            </div>
          </div>
          ${editFormHtml}

          <!-- PDS -->
          <div class="doc-card">
            <div class="doc-header">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              <span class="text-sm font-semibold text-slate-900">Product Disclosure Statement</span>
            </div>
            <div class="doc-actions">
              ${docBadge(pdsStatus)}
              <div class="flex items-center gap-3">
                <button type="button" onclick="event.stopPropagation(); viewDoc('${hlt.id}', 'pds')" class="doc-btn doc-btn-primary">View</button>
                <button type="button" onclick="event.stopPropagation(); editDoc('pds')" class="doc-btn doc-btn-secondary">Edit</button>
                <button type="button" onclick="event.stopPropagation(); downloadDoc('${pdsDoc.file_path}')" class="doc-btn doc-btn-muted">Download</button>
              </div>
            </div>
          </div>

          <!-- SA -->
          <div class="doc-card">
            <div class="doc-header">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              <span class="text-sm font-semibold text-slate-900">Syndicate Agreement</span>
            </div>
            <div class="doc-actions">
              ${docBadge(saStatus)}
              <div class="flex items-center gap-3">
                <button type="button" onclick="event.stopPropagation(); viewDoc('${hlt.id}', 'sa')" class="doc-btn doc-btn-primary">View</button>
                <button type="button" onclick="event.stopPropagation(); editDoc('sa')" class="doc-btn doc-btn-secondary">Edit</button>
                <button type="button" onclick="event.stopPropagation(); downloadDoc('${saDoc.file_path}')" class="doc-btn doc-btn-muted">Download</button>
              </div>
            </div>
          </div>
        </div>
      </td>
    </tr>
  `;
}

function toggleHltRow(id) {
  hltsState.expandedRow = hltsState.expandedRow === id ? null : id;
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

function viewDoc(hltId, type) {
  // Placeholder for PDS/SA view
  showToast(`${type.toUpperCase()} preview coming in Sprint 5`, 'info');
}

function editDoc(type) {
  showToast(`${type.toUpperCase()} editor coming in Sprint 5`, 'info');
}

function downloadDoc(path) {
  window.open(path, '_blank');
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
    app.innerHTML = '<div class="p-6 text-red-600">HLT not found.</div>';
    return;
  }
  const h = json.data;
  const horse = h.horse || {};
  const owner = h.owner || {};
  const trainer = h.trainer || {};
  const lease = h.lease || {};

  const docBadge = (status) => `<span class="badge ${status === 'complete' ? 'badge-green' : 'badge-gray'}">${status}</span>`;

  // Format currency for display
  const formatCurrency = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '$0.00';
    return new Intl.NumberFormat('en-NZ', {
      style: 'currency',
      currency: 'NZD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  // Format percentage for display
  const formatPercent = (value) => {
    if (value === null || value === undefined || isNaN(value)) return '0%';
    return `${value.toFixed(2)}%`;
  };

  // Create a more compact, user-friendly view
  app.innerHTML = `
    <div class="card max-w-5xl mx-auto">
      <!-- Header -->
      <div class="flex justify-between items-start mb-6">
        <div>
          <h1 class="text-2xl font-bold">${horse.name || 'Unnamed Horse'}</h1>
          <p class="text-sm text-gray-500 mt-1">HLT ${docBadge(h.status)} <span class="text-gray-400 mx-1">•</span> Lease ${h.lease_id}</p>
        </div>
        <a href="#/hlts" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Back</a>
      </div>

      <!-- Summary Card -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-blue-50 rounded-lg p-4 border">
          <h4 class="text-xs font-semibold text-blue-700 uppercase tracking-wide">Lease Value</h4>
          <p class="text-2xl font-bold text-blue-900 mt-2">${formatCurrency(lease.total_issuance_value_nzd)}</p>
          <p class="text-xs text-blue-600">Total Issuance Value</p>
        </div>
        <div class="bg-emerald-50 rounded-lg p-4 border">
          <h4 class="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Token Price</h4>
          <p class="text-2xl font-bold text-emerald-900 mt-2">${formatCurrency(lease.token_price_nzd)}</p>
          <p class="text-xs text-emerald-600">Per Token</p>
        </div>
        <div class="bg-amber-50 rounded-lg p-4 border">
          <h4 class="text-xs font-semibold text-amber-700 uppercase tracking-wide">Stake %</h4>
          <p class="text-2xl font-bold text-amber-900 mt-2">${formatPercent(lease.percent_leased)}</p>
          <p class="text-xs text-amber-600">Leased</p>
        </div>
        <div class="bg-purple-50 rounded-lg p-4 border">
          <h4 class="text-xs font-semibold text-purple-700 uppercase tracking-wide">Duration</h4>
          <p class="text-2xl font-bold text-purple-900 mt-2">${lease.duration_months || '—'} months</p>
          <p class="text-xs text-purple-600">Lease Term</p>
        </div>
      </div>

      <!-- Entity cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="entity-card">
          <h4>Horse</h4>
          <div class="name">${horse.name || '—'}</div>
          <div class="detail">${horse.sex || ''} ${horse.colour ? '• ' + horse.colour : ''}</div>
          <div class="detail">${horse.sire_name || ''} / ${horse.dam_name || ''}</div>
          <div class="tagline">Microchip: ${h.horse_microchip}</div>
          ${horse.breeding_url ? `<div class="mt-2"><a href="${horse.breeding_url}" target="_blank" class="breeding-url">View on loveracing.nz</a></div>` : ''}
        </div>
        <div class="entity-card">
          <h4>Owner</h4>
          <div class="name">${owner.name || '—'}</div>
          <div class="detail">${owner.email || ''}</div>
          <div class="detail">${owner.phone || ''}</div>
          <div class="tagline">ID: ${h.owner_id}</div>
        </div>
        <div class="entity-card">
          <h4>Trainer / Stable</h4>
          <div class="name">${trainer.name || '—'}</div>
          <div class="detail">${trainer.stable_name || ''}</div>
          <div class="detail">${trainer.location || ''}</div>
          <div class="tagline">ID: ${h.trainer_id}</div>
        </div>
        <div class="entity-card">
          <h4>Governing Body</h4>
          <div class="name">${h.governing_body_name || '—'}</div>
          <div class="detail">${h.governing_body_code || ''}</div>
          <div class="tagline">ID: ${h.governing_body_code || 'Not set'}</div>
        </div>
      </div>

      <!-- Lease Terms (Compact View) -->
      <div class="bg-gray-50 rounded-lg p-4 border mb-6">
        <h3 class="label mb-3">Lease Terms</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="space-y-2">
            <div class="flex justify-between">
              <span class="text-slate-500">Lease ID</span>
              <span class="font-semibold">${lease.lease_id || h.lease_id || '—'}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Start Date</span>
              <span class="font-semibold">${lease.start_date || '—'}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">End Date</span>
              <span class="font-semibold">${lease.end_date || '—'}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Token Count</span>
              <span class="font-semibold">${lease.token_count || '—'}</span>
            </div>
          </div>
          <div class="space-y-2">
            <div class="flex justify-between">
              <span class="text-slate-500">Price per 1% / month</span>
              <span class="font-semibold">${formatCurrency(lease.price_per_1pct_per_month)}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Min Unit Size</span>
              <span class="font-semibold">${lease.min_unit_size || '—'}%</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Revenue Split</span>
              <span class="font-semibold">Investor ${lease.investor_share_percent || '—'}% / Owner ${lease.owner_share_percent || '—'}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 mb-6">
        <button onclick="generateTermSheet('${h.id}')" class="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium">Generate Term Sheet</button>
        <button onclick="alert('Document upload coming in Sprint 5')" class="bg-gray-600 text-white px-4 py-2 rounded-md text-sm font-medium">Upload Documents</button>
      </div>

      <!-- Documents -->
      <div class="grid grid-cols-3 gap-4 text-sm">
        <div class="border rounded-lg p-3">
          <div class="flex justify-between items-center"><span class="font-semibold">Term Sheet</span>${docBadge(h.term_sheet_status)}</div>
        </div>
        <div class="border rounded-lg p-3">
          <div class="flex justify-between items-center"><span class="font-semibold">PDS</span>${docBadge(h.pds_status)}</div>
        </div>
        <div class="border rounded-lg p-3">
          <div class="flex justify-between items-center"><span class="font-semibold">SA</span>${docBadge(h.sa_status)}</div>
        </div>
      </div>
    </div>
  `;
};

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
    renderHltDetail(hltId);
  } catch (e) {
    alert("Term sheet generation failed: " + e.message);
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

const _oldRender = render;
window.render = function() {
  const hash = window.location.hash.replace("#/", "").replace("#", "");
  if (hash.startsWith("hlt/")) {
    renderHltDetail(hash.replace("hlt/", ""));
    return;
  }
  // Handle horse routes: #/horse/{microchip} or #/horse/{microchip}/media
  const horseMediaMatch = hash.match(/^horse\/([^/]+)\/media$/);
  if (horseMediaMatch) {
    const microchip = horseMediaMatch[1];
    renderHorseMedia(decodeURIComponent(microchip));
    return;
  }
  const horseDetailMatch = hash.match(/^horse\/([^/]+)$/);
  if (horseDetailMatch) {
    const microchip = horseDetailMatch[1];
    renderHorseDetail(decodeURIComponent(microchip));
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

// ─── Horse Detail Page (Full Profile + Media) ─────────────────────────────────

async function renderHorseDetail(microchip) {
  try {
    setLoading(true);
    const headers = await window.getAuthHeader();
    
    // Load horse details
    const horses = await loadHorses();
    const horse = horses.find(h => h.microchip === microchip);
    if (!horse) throw new Error('Horse not found');
    
    // Load media
    const mediaResp = await fetch(`${API}/horses/${encodeURIComponent(microchip)}/media`, { headers });
    const mediaResult = mediaResp.ok ? await mediaResp.json() : { data: { transcripts: [] } };
    const { transcripts = [] } = mediaResult.data || {};
    
    const transcriptCount = transcripts.length;
    
    app.innerHTML = `
      <div class="space-y-6">
        <!-- Header -->
        <div class="flex items-center gap-3">
          <a href="#/horses" class="text-slate-400 hover:text-slate-600">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          </a>
          <h2 class="text-2xl font-bold text-slate-900">${horse.name}</h2>
        </div>
        
        <!-- Profile Card -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h3 class="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">Basic Information</h3>
            <div class="space-y-3">
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Microchip</span>
                <span class="text-sm font-semibold text-slate-900">${horse.microchip}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Sex</span>
                <span class="text-sm font-semibold text-slate-900">${horse.sex || "—"}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Colour</span>
                <span class="text-sm font-semibold text-slate-900">${horse.colour || "—"}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Foaling Date</span>
                <span class="text-sm font-semibold text-slate-900">${horse.foaling_date || "—"}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Breeder</span>
                <span class="text-sm font-semibold text-slate-900">${horse.breeder || "—"}</span>
              </div>
            </div>
          </div>
          
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h3 class="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">Pedigree</h3>
            <div class="space-y-3">
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Sire</span>
                <span class="text-sm font-semibold text-slate-900">${horse.sire_name || "—"}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Dam</span>
                <span class="text-sm font-semibold text-slate-900">${horse.dam_name || "—"}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">Breeding URL</span>
                <span class="text-sm">
                  ${horse.breeding_url ? `<a href="${horse.breeding_url}" target="_blank" class="text-blue-600 hover:underline">loveracing.nz →</a>` : "—"}
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Media Section -->
        <div class="bg-white rounded-xl border border-slate-200 p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-slate-700 uppercase tracking-wide">Media & Transcripts</h3>
            <a href="#/horse/${encodeURIComponent(microchip)}/media" class="text-sm text-blue-600 hover:underline font-medium">View All →</a>
          </div>
          ${transcriptCount === 0 ? (
            '<div class="text-slate-500 text-sm">No transcripts yet. Transcripts will appear here when emails are ingested.</div>'
          ) : (
            `<div class="text-sm text-slate-600">${transcriptCount} transcript${transcriptCount > 1 ? 's' : ''} available</div>
            <div class="mt-3 space-y-2">
              ${transcripts.slice(0, 3).map(t => `
                <div class="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div>
                    <div class="text-sm font-medium text-slate-900">Transcript — ${t.date || 'Unknown'}</div>
                    <div class="text-xs text-slate-500">${t.speakers?.length || 0} speaker${(t.speakers?.length || 0) > 1 ? 's' : ''} • ${t.duration_seconds ? Math.round(t.duration_seconds) + 's' : '—'}</div>
                  </div>
                  <a href="#/horse/${encodeURIComponent(microchip)}/media" class="text-xs text-blue-600 hover:underline font-medium">View →</a>
                </div>
              `).join('')}
              ${transcriptCount > 3 ? `<div class="text-center pt-2"><a href="#/horse/${encodeURIComponent(microchip)}/media" class="text-sm text-blue-600 hover:underline font-medium">View all ${transcriptCount} transcripts →</a></div>` : ''}
            </div>`
          )}
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Horse detail render error:', err);
    app.innerHTML = `<div class="card"><h2 class="text-xl font-bold mb-4 text-rose-700">Error Loading Horse Details</h2><p class="text-slate-600">${err.message}</p></div>`;
  }
}

window.addEventListener("hashchange", () => window.render());

console.log('=== app.js module loaded ===');
