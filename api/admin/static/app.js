import { 
  calculateHltTerms, 
  calculateDerivedFields, 
  formatCurrency, 
  formatPercent, 
  formatNumber,
  generateErc20Identifier,
  nextLeaseId,
  addMonthsIso,
  parseNumber 
} from './hlt-engine.js';

const app = document.getElementById("app");
const API = "/api";

// Wizard state
let wizardState = {
  step: 1,
  draft: {
    // Step 1: Entities
    horseId: '',
    ownerId: '',
    trainerId: '',
    governingBodyCode: '',
    // Step 2: Lease Terms
    leaseStartDate: '',
    leaseLengthMonths: '',
    percentageLeased: '',
    numTokens: '',
    // Step 3: Pricing
    monthlyRate: '',
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
  },
  lastEditedField: null,
  entities: { horses: [], owners: [], trainers: [], governingBodies: [], leases: [] },
};

function setLoading(show) {
  app.innerHTML = show ? '<div class="p-6 text-gray-600">Loading...</div>' : "";
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

async function loadHorses() {
  const r = await fetch(`${API}/horses`);
  const j = await r.json();
  return j.success ? j.data : [];
}
async function loadOwners() {
  const r = await fetch(`${API}/owners`);
  const j = await r.json();
  return j.success ? j.data : [];
}
async function loadTrainers() {
  const r = await fetch(`${API}/trainers`);
  const j = await r.json();
  return j.success ? j.data : [];
}
async function loadGoverningBodies() {
  const r = await fetch(`${API}/governing-bodies`);
  const j = await r.json();
  return j.success ? j.data.items : [];
}
async function loadHlts() {
  const r = await fetch(`${API}/hlts`);
  const j = await r.json();
  return j.success ? j.data : [];
}
async function getHlt(id) {
  const r = await fetch(`${API}/hlts/${id}`);
  return await r.json();
}
async function createHltWorkflow(payload) {
  const r = await fetch(`${API}/hlts/workflow`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return await r.json();
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

async function renderDashboard() {
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
      <h2 class="text-xl font-bold mb-6">HLT Mission Control</h2>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <div class="bg-emerald-50 rounded-lg p-4 border border-emerald-100">
          <div class="text-3xl font-bold text-emerald-700">${c.horses}</div>
          <div class="text-sm text-emerald-600 font-medium">Horses</div>
        </div>
        <div class="bg-blue-50 rounded-lg p-4 border border-blue-100">
          <div class="text-3xl font-bold text-blue-700">${c.owners}</div>
          <div class="text-sm text-blue-600 font-medium">Owners</div>
        </div>
        <div class="bg-amber-50 rounded-lg p-4 border border-amber-100">
          <div class="text-3xl font-bold text-amber-700">${c.trainers}</div>
          <div class="text-sm text-amber-600 font-medium">Trainers / Stables</div>
        </div>
        <div class="bg-rose-50 rounded-lg p-4 border border-rose-100">
          <div class="text-3xl font-bold text-rose-700">${c.governing_bodies}</div>
          <div class="text-sm text-rose-600 font-medium">Governing Bodies</div>
        </div>
        <div class="bg-purple-50 rounded-lg p-4 border border-purple-100">
          <div class="text-3xl font-bold text-purple-700">${c.hlts}</div>
          <div class="text-sm text-purple-600 font-medium">Active HLTs</div>
        </div>
      </div>
      <div class="flex gap-3">
        <a href="#/create-hlt" class="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-green-700">+ Create HLT</a>
        <a href="#/hlts" class="bg-gray-800 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-900">View HLTs</a>
      </div>
    </div>
  `;
}

// ─── Horses ───────────────────────────────────────────────────────────────────

async function renderHorses() {
  setLoading(true);
  const horses = await loadHorses();
  const rows = horses.map(h => `
    <tr class="border-b hover:bg-gray-50">
      <td class="px-4 py-3">
        <div class="font-semibold">${h.name || "—"}</div>
        <div class="tag">${h.microchip}</div>
      </td>
      <td class="px-4 py-3">${h.sex || "—"}</td>
      <td class="px-4 py-3">${h.colour || "—"}</td>
      <td class="px-4 py-3">${h.foaling_date || "—"}</td>
      <td class="px-4 py-3">${h.sire_name || "—"}</td>
      <td class="px-4 py-3">${h.dam_name || "—"}</td>
      <td class="px-4 py-3">${h.breeder || "—"}</td>
      <td class="px-4 py-3">${h.breeding_url ? `<a href="${h.breeding_url}" target="_blank" class="breeding-url">loveracing.nz</a>` : "—"}</td>
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
}

// ─── Owners ───────────────────────────────────────────────────────────────────

async function renderOwners() {
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
}

// ─── Trainers ─────────────────────────────────────────────────────────────────

async function renderTrainers() {
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
}

// ─── Create HLT ───────────────────────────────────────────────────────────────

async function renderCreateHlt() {
  setLoading(true);
  const [horses, owners, trainers, governing_bodies] = await Promise.all([loadHorses(), loadOwners(), loadTrainers(), loadGoverningBodies()]);
  const horseOpts = '<option value="" disabled selected>-- Select Horse --</option>' + horses.map(h => `<option value="${h.microchip}">${h.name}</option>`).join("");
  const ownerOpts = '<option value="" disabled selected>-- Select Owner --</option>' + owners.map(o => `<option value="${o.id}">${o.name}</option>`).join("");
  const trainerOpts = '<option value="" disabled selected>-- Select Trainer --</option>' + trainers.map(t => `<option value="${t.id}">${t.name} — ${t.stable_name}</option>`).join("");
  const govOpts = '<option value="" disabled selected>-- Select Governing Body --</option>' + governing_bodies.map(g => `<option value="${g.governing_body_code}">${g.governing_body_name}</option>`).join("");
  app.innerHTML = `
    <div class="card max-w-4xl mx-auto">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-bold">Create HLT</h2>
        <a href="#/hlts" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Back</a>
      </div>
      <form id="hlt-form" onsubmit="event.preventDefault(); submitHlt();">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div><label class="label">Horse</label><select id="h-horse" class="w-full border rounded-md px-3 py-2 text-sm">${horseOpts}</select></div>
          <div><label class="label">Owner</label><select id="h-owner" class="w-full border rounded-md px-3 py-2 text-sm">${ownerOpts}</select></div>
          <div><label class="label">Trainer / Stable</label><select id="h-trainer" class="w-full border rounded-md px-3 py-2 text-sm">${trainerOpts}</select></div>
          <div><label class="label">Governing Body</label><select id="h-governing_body" class="w-full border rounded-md px-3 py-2 text-sm">${govOpts}</select></div>
          <div><label class="label">Lease ID</label><input id="h-lease_id" type="text" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Start Date</label><input id="h-start_date" type="date" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">End Date</label><input id="h-end_date" type="date" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Duration (months)</label><input id="h-duration_months" type="number" min="1" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">% Leased</label><input id="h-percent_leased" type="number" step="0.01" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Token Count</label><input id="h-token_count" type="number" min="1" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Min Unit Size (%)</label><input id="h-min_unit_size" type="number" step="0.01" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Price Basis</label><select id="h-price_basis" class="w-full border rounded-md px-3 py-2 text-sm"><option value=""></option><option value="per_1pct">Per 1%</option><option value="full_stake">Full Stake</option></select></div>
          <div><label class="label">Price Period</label><select id="h-price_period" class="w-full border rounded-md px-3 py-2 text-sm"><option value=""></option><option value="month">Per Month</option><option value="year">Per Year</option><option value="total">Total Duration</option></select></div>
          <div><label class="label">Price Amount (NZD)</label><input id="h-price_amount" type="number" step="0.01" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Investor Share %</label><input id="h-investor_share" type="number" step="0.01" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Owner Share %</label><input id="h-owner_share" type="number" step="0.01" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
          <div><label class="label">Platform Fee %</label><input id="h-platform_fee" type="number" step="0.01" class="w-full border rounded-md px-3 py-2 text-sm" required /></div>
        </div>
        <div class="flex justify-between items-center">
          <button type="button" onclick="previewPricing()" class="bg-gray-600 text-white px-4 py-2 rounded-md text-sm font-medium">Preview Pricing</button>
          <button type="submit" class="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium">Create HLT</button>
        </div>
        <div id="preview-area" class="hidden bg-gray-50 rounded-lg p-4 border mt-4">
          <h3 class="text-sm font-bold text-gray-700 mb-2">Derived Pricing</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm" id="preview-fields"></div>
        </div>
      </form>
    </div>
  `;
}

window.previewPricing = function() {
  const basis = document.getElementById("h-price_basis").value;
  const period = document.getElementById("h-price_period").value;
  const amount = parseFloat(document.getElementById("h-price_amount").value) || 0;
  const percent = parseFloat(document.getElementById("h-percent_leased").value) || 0;
  const tokens = parseInt(document.getElementById("h-token_count").value) || 1;
  const duration = parseInt(document.getElementById("h-duration_months").value) || 1;
  const minUnit = parseFloat(document.getElementById("h-min_unit_size").value) || 0.25;

  let pricePer1pctPerMonth = 0;
  if (basis === "per_1pct" && period === "month") pricePer1pctPerMonth = amount;
  else if (basis === "per_1pct" && period === "year") pricePer1pctPerMonth = amount / 12;
  else if (basis === "per_1pct" && period === "total") pricePer1pctPerMonth = amount / duration;
  else if (basis === "full_stake" && period === "month") pricePer1pctPerMonth = amount / percent;
  else if (basis === "full_stake" && period === "year") pricePer1pctPerMonth = amount / (percent * 12);
  else if (basis === "full_stake" && period === "total") pricePer1pctPerMonth = amount / (percent * duration);

  const pctPerToken = percent / tokens;
  const tokenPrice = pricePer1pctPerMonth * pctPerToken * duration;
  const totalValue = pricePer1pctPerMonth * percent * duration;

  const fields = [
    ["Price per 1% / month", `$${pricePer1pctPerMonth.toFixed(2)}`],
    ["Percent per token", `${pctPerToken.toFixed(2)}%`],
    ["Token price", `$${tokenPrice.toFixed(2)}`],
    ["Total issuance value", `$${totalValue.toFixed(2)} NZD`],
    ["Min unit size", `${minUnit}%`],
  ];
  document.getElementById("preview-fields").innerHTML = fields.map(([k, v]) =>
    `<div><div class="text-gray-500 text-xs">${k}</div><div class="font-semibold">${v}</div></div>`
  ).join("");
  document.getElementById("preview-area").classList.remove("hidden");
};

window.submitHlt = async function() {
  const payload = {
    horse_microchip: document.getElementById("h-horse").value,
    owner_id: document.getElementById("h-owner").value,
    trainer_id: document.getElementById("h-trainer").value,
    governing_body_code: document.getElementById("h-governing_body").value,
    lease_id: document.getElementById("h-lease_id").value,
    start_date: document.getElementById("h-start_date").value,
    end_date: document.getElementById("h-end_date").value,
    duration_months: parseInt(document.getElementById("h-duration_months").value),
    percent_leased: parseFloat(document.getElementById("h-percent_leased").value),
    token_count: parseInt(document.getElementById("h-token_count").value),
    min_unit_size: parseFloat(document.getElementById("h-min_unit_size").value),
    price_basis: document.getElementById("h-price_basis").value,
    price_period: document.getElementById("h-price_period").value,
    price_amount: parseFloat(document.getElementById("h-price_amount").value),
    investor_share_percent: parseFloat(document.getElementById("h-investor_share").value),
    owner_share_percent: parseFloat(document.getElementById("h-owner_share").value),
    platform_fee_percent: parseFloat(document.getElementById("h-platform_fee").value),
  };
  const resp = await createHltWorkflow(payload);
  if (!resp.success) {
    alert("Error: " + (resp.error || JSON.stringify(resp)));
    return;
  }
  window.location.hash = "#/hlts";
  render();
};

// ─── HLTs ─────────────────────────────────────────────────────────────────────

async function renderHlts() {
  setLoading(true);
  const hlts = await loadHlts();
  const rows = hlts.map(h => `
    <tr class="border-b hover:bg-gray-50 cursor-pointer" onclick="window.location.hash='#/hlt/${h.id}';render()">
      <td class="px-4 py-3">
        <div class="font-semibold">${h.horse_name || h.horse_microchip}</div>
        <div class="tag">ID: ${h.id} | Microchip: ${h.horse_microchip}</div>
      </td>
      <td class="px-4 py-3">${h.owner_name || h.owner_id}</td>
      <td class="px-4 py-3">${h.trainer_name || h.trainer_id}</td>
      <td class="px-4 py-3">${h.lease_id}</td>
      <td class="px-4 py-3"><span class="badge ${h.status === 'published' ? 'badge-green' : 'badge-gray'}">${h.status}</span></td>
    </tr>
  `).join("");
  app.innerHTML = `
    <div class="card">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">HLTs (${hlts.length})</h2>
        <a href="#/create-hlt" class="bg-green-600 text-white px-3 py-2 rounded-md text-sm font-medium">Create HLT</a>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left border">
          <thead class="bg-gray-100">
            <tr>
              <th class="px-4 py-2">Horse</th>
              <th class="px-4 py-2">Owner</th>
              <th class="px-4 py-2">Trainer</th>
              <th class="px-4 py-2">Lease</th>
              <th class="px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>${rows || '<tr><td colspan="5" class="px-4 py-4 text-gray-500">No HLTs yet.</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  `;
}

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

      <!-- Lease Terms -->
      <div class="bg-gray-50 rounded-lg p-4 border mb-6">
        <h3 class="label mb-3">Lease Terms</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <tbody class="divide-y">
              <tr class="data-row"><td class="data-label">Lease ID</td><td class="data-value">${lease.lease_id || h.lease_id || '—'}</td></tr>
              <tr class="data-row"><td class="data-label">Duration</td><td class="data-value">${lease.duration_months || '—'} months</td></tr>
              <tr class="data-row"><td class="data-label">Percent Leased</td><td class="data-value">${lease.percent_leased || '—'}%</td></tr>
              <tr class="data-row"><td class="data-label">Token Count</td><td class="data-value">${lease.token_count || '—'}</td></tr>
              <tr class="data-row"><td class="data-label">Min Unit Size</td><td class="data-value">${lease.min_unit_size || '—'}%</td></tr>
              <tr class="data-row"><td class="data-label">Price per 1% per month</td><td class="data-value">$${lease.price_per_1pct_per_month || '—'}</td></tr>
              <tr class="data-row"><td class="data-label">Total Issuance Value</td><td class="data-value">$${lease.total_issuance_value_nzd || '—'} NZD</td></tr>
              <tr class="data-row"><td class="data-label">Token Price</td><td class="data-value">$${lease.token_price_nzd || '—'}</td></tr>
              <tr class="data-row"><td class="data-label">Revenue Split</td><td class="data-value">Investor ${lease.investor_share_percent || '—'}% / Owner ${lease.owner_share_percent || '—'}% / Platform ${lease.platform_fee_percent || '0'}%</td></tr>
            </tbody>
          </table>
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
  const viewFn = views[hash] || views[""];
  viewFn();
  document.querySelectorAll(".nav-item").forEach(link => {
    link.classList.toggle("active", link.dataset.route === hash);
  });
};

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);
