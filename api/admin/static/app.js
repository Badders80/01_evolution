/**
 * HLT Mission Control — Vanilla JS frontend.
 * Hash routing: #/horses, #/owners, #/trainers, #/create-hlt
 */

const app = document.getElementById("app");

const API = "/api";

function setLoading(show) {
  app.innerHTML = show ? `<div class="p-6 text-gray-600">Loading...</div>` : "";
}

function render() {
  const hash = window.location.hash.replace("#/", "").replace("#", "").replace("/", "") || "default";
  const viewFn = views[hash] || views.default;
  viewFn();

  // Update nav active state
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.toggle("active", link.dataset.route === hash);
  });
}

// ─── Horses ──────────────────────────────────────────────────────────────────

async function loadHorses() {
  const resp = await fetch(`${API}/horses`);
  const json = await resp.json();
  return json.success ? json.data : [];
}

async function saveHorse(payload) {
  const resp = await fetch(`${API}/horses`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

async function updateHorse(microchip, payload) {
  const resp = await fetch(`${API}/horses/${microchip}`, {
    method: "PATCH",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

async function deleteHorse(microchip) {
  if (!confirm("Delete this horse?")) return;
  const resp = await fetch(`${API}/horses/${microchip}`, {method: "DELETE"});
  const json = await resp.json();
  if (json.success) render();
}

async function lookupHorse(microchip) {
  const resp = await fetch(`${API}/horses/lookup`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({microchip}),
  });
  return await resp.json();
}

function horseTable(horses) {
  const rows = horses.map(h => `
    <tr class="border-b hover:bg-gray-50">
      <td class="px-4 py-2">${h.name || ""}</td>
      <td class="px-4 py-2 font-mono text-sm">${h.microchip}</td>
      <td class="px-4 py-2">${h.sex || ""}</td>
      <td class="px-4 py-2">${h.colour || ""}</td>
      <td class="px-4 py-2">${h.sire_name || ""}</td>
      <td class="px-4 py-2 text-right">
        <button onclick="editHorse('${h.microchip}')" class="text-blue-600 hover:underline text-sm mr-2">Edit</button>
        <button onclick="deleteHorse('${h.microchip}')" class="text-red-600 hover:underline text-sm">Delete</button>
      </td>
    </tr>
  `).join("");
  return `
    <table class="w-full text-left border mt-2">
      <thead class="bg-gray-100">
        <tr>
          <th class="px-4 py-2">Name</th>
          <th class="px-4 py-2">Microchip</th>
          <th class="px-4 py-2">Sex</th>
          <th class="px-4 py-2">Colour</th>
          <th class="px-4 py-2">Sire</th>
          <th class="px-4 py-2 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function horseForm(values = {}, editing = false) {
  const v = (key) => values[key] || "";
  return `
    <div class="bg-white shadow rounded-lg p-6 mt-4">
      <h3 class="text-lg font-bold mb-4">${editing ? "Edit Horse" : "Add Horse"}</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Microchip (15 digits)</label>
          <div class="flex gap-2 mt-1">
            <input id="h-microchip" type="text" maxlength="15" value="${v("microchip")}" ${editing ? "disabled" : ""} class="flex-1 border rounded-md px-3 py-2 text-sm" />
            <button onclick="doLookup()" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Lookup</button>
          </div>
          <p id="lookup-msg" class="text-sm text-gray-500 mt-1"></p>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Name</label>
          <input id="h-name" type="text" value="${v("name")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Sex</label>
          <select id="h-sex" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">
            <option value="">--</option>
            <option value="colt" ${v("sex")==="colt"?"selected":""}>Colt</option>
            <option value="filly" ${v("sex")==="filly"?"selected":""}>Filly</option>
            <option value="gelding" ${v("sex")==="gelding"?"selected":""}>Gelding</option>
            <option value="mare" ${v("sex")==="mare"?"selected":""}>Mare</option>
            <option value="stallion" ${v("sex")==="stallion"?"selected":""}>Stallion</option>
            <option value="horse" ${v("sex")==="horse"?"selected":""}>Horse</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Colour</label>
          <input id="h-colour" type="text" value="${v("colour")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Foaling Date</label>
          <input id="h-foaling_date" type="date" value="${v("foaling_date")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Sire Name</label>
          <input id="h-sire_name" type="text" value="${v("sire_name")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Dam Name</label>
          <input id="h-dam_name" type="text" value="${v("dam_name")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Breeder</label>
          <input id="h-breeder" type="text" value="${v("breeder")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Trainer ID</label>
          <input id="h-trainer_id" type="text" value="${v("trainer_id")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
      </div>
      <div class="mt-4 flex gap-2">
        <button onclick="submitHorse(${editing ? `'${v("microchip")}'` : "null"})" class="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium">Save</button>
        <button onclick="render()" class="bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm font-medium">Cancel</button>
      </div>
    </div>
  `;
}

window.doLookup = async function() {
  const chip = document.getElementById("h-microchip").value.trim();
  const msg = document.getElementById("lookup-msg");
  if (!/^\d{15}$/.test(chip)) {
    msg.textContent = "Enter exactly 15 digits.";
    msg.className = "text-sm text-red-500 mt-1";
    return;
  }
  msg.textContent = "Looking up...";
  msg.className = "text-sm text-gray-500 mt-1";
  const json = await lookupHorse(chip);
  if (!json.success) {
    msg.textContent = `Lookup failed: ${json.error}. You can enter details manually.`;
    msg.className = "text-sm text-orange-600 mt-1";
    return;
  }
  const d = json.data;
  if (d.name) document.getElementById("h-name").value = d.name;
  if (d.sex) document.getElementById("h-sex").value = d.sex;
  if (d.colour) document.getElementById("h-colour").value = d.colour;
  if (d.foaling_date) document.getElementById("h-foaling_date").value = d.foaling_date;
  if (d.sire_name) document.getElementById("h-sire_name").value = d.sire_name;
  if (d.dam_name) document.getElementById("h-dam_name").value = d.dam_name;
  if (d.breeder) document.getElementById("h-breeder").value = d.breeder;
  msg.textContent = `Found on loveracing.nz: ${d.name || ""}`;
  msg.className = "text-sm text-green-600 mt-1";
};

window.submitHorse = async function(microchip) {
  const payload = {
    microchip: document.getElementById("h-microchip").value.trim(),
    name: document.getElementById("h-name").value.trim(),
    sex: document.getElementById("h-sex").value || undefined,
    colour: document.getElementById("h-colour").value.trim() || undefined,
    foaling_date: document.getElementById("h-foaling_date").value || undefined,
    sire_name: document.getElementById("h-sire_name").value.trim() || undefined,
    dam_name: document.getElementById("h-dam_name").value.trim() || undefined,
    breeder: document.getElementById("h-breeder").value.trim() || undefined,
    trainer_id: document.getElementById("h-trainer_id").value.trim() || undefined,
  };
  if (microchip) {
    const resp = await updateHorse(microchip, payload);
    if (!resp.success) { alert(resp.error); return; }
  } else {
    const resp = await saveHorse(payload);
    if (!resp.success) { alert(resp.error); return; }
  }
  window.location.hash = "#/horses";
  render();
};

window.editHorse = async function(microchip) {
  const resp = await fetch(`${API}/horses/${microchip}`);
  const json = await resp.json();
  if (!json.success) return alert(json.error);
  const data = json.data;
  app.innerHTML = `
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">Horses</h2>
        <button onclick="window.location.hash='#/horses';render()" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Back</button>
      </div>
    </div>
    ${horseForm(data, true)}
  `;
};

window.deleteHorse = deleteHorse;

// ─── Owners ──────────────────────────────────────────────────────────────────

async function loadOwners() {
  const resp = await fetch(`${API}/owners`);
  const json = await resp.json();
  return json.success ? json.data : [];
}

async function saveOwner(payload) {
  const resp = await fetch(`${API}/owners`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

async function updateOwner(id, payload) {
  const resp = await fetch(`${API}/owners/${id}`, {
    method: "PATCH",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

async function deleteOwner(id) {
  if (!confirm("Delete this owner?")) return;
  const resp = await fetch(`${API}/owners/${id}`, {method: "DELETE"});
  const json = await resp.json();
  if (json.success) render();
}

function ownerTable(rows) {
  const trs = rows.map(r => `
    <tr class="border-b hover:bg-gray-50">
      <td class="px-4 py-2">${r.name}</td>
      <td class="px-4 py-2">${r.email || ""}</td>
      <td class="px-4 py-2">${r.entity_type || ""}</td>
      <td class="px-4 py-2 text-right">
        <button onclick="editOwner('${r.id}')" class="text-blue-600 hover:underline text-sm mr-2">Edit</button>
        <button onclick="deleteOwner('${r.id}')" class="text-red-600 hover:underline text-sm">Delete</button>
      </td>
    </tr>
  `).join("");
  return `
    <table class="w-full text-left border mt-2">
      <thead class="bg-gray-100">
        <tr><th class="px-4 py-2">Name</th><th class="px-4 py-2">Email</th><th class="px-4 py-2">Type</th><th class="px-4 py-2 text-right">Actions</th></tr>
      </thead>
      <tbody>${trs}</tbody>
    </table>
  `;
}

function ownerForm(values = {}, editing = false) {
  const v = (key) => values[key] || "";
  return `
    <div class="bg-white shadow rounded-lg p-6 mt-4">
      <h3 class="text-lg font-bold mb-4">${editing ? "Edit Owner" : "Add Owner"}</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Name *</label>
          <input id="o-name" type="text" value="${v("name")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Email *</label>
          <input id="o-email" type="email" value="${v("email")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Phone</label>
          <input id="o-phone" type="text" value="${v("phone")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Entity Type</label>
          <select id="o-entity_type" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">
            <option value="individual" ${v("entity_type")==="individual"?"selected":""}>Individual</option>
            <option value="company" ${v("entity_type")==="company"?"selected":""}>Company</option>
            <option value="syndicate" ${v("entity_type")==="syndicate"?"selected":""}>Syndicate</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Contact Name</label>
          <input id="o-contact_name" type="text" value="${v("contact_name")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Website</label>
          <input id="o-website" type="text" value="${v("website")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700">Address</label>
          <input id="o-address" type="text" value="${v("address")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
      </div>
      <div class="mt-4 flex gap-2">
        <button onclick="submitOwner(${editing ? `'${v("id")}'` : "null"})" class="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium">Save</button>
        <button onclick="render()" class="bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm font-medium">Cancel</button>
      </div>
    </div>
  `;
}

window.submitOwner = async function(id) {
  const payload = {
    name: document.getElementById("o-name").value.trim(),
    email: document.getElementById("o-email").value.trim(),
    phone: document.getElementById("o-phone").value.trim() || undefined,
    entity_type: document.getElementById("o-entity_type").value || undefined,
    contact_name: document.getElementById("o-contact_name").value.trim() || undefined,
    website: document.getElementById("o-website").value.trim() || undefined,
    address: document.getElementById("o-address").value.trim() || undefined,
  };
  if (id) {
    const resp = await updateOwner(id, payload);
    if (!resp.success) { alert(resp.error); return; }
  } else {
    const resp = await saveOwner(payload);
    if (!resp.success) { alert(resp.error); return; }
  }
  window.location.hash = "#/owners";
  render();
};

window.editOwner = async function(id) {
  const resp = await fetch(`${API}/owners/${id}`);
  const json = await resp.json();
  if (!json.success) return alert(json.error);
  const data = json.data;
  app.innerHTML = `
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">Owners</h2>
        <button onclick="window.location.hash='#/owners';render()" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Back</button>
      </div>
    </div>
    ${ownerForm(data, true)}
  `;
};

window.deleteOwner = deleteOwner;

// ─── Trainers ────────────────────────────────────────────────────────────────

async function loadTrainers() {
  const resp = await fetch(`${API}/trainers`);
  const json = await resp.json();
  return json.success ? json.data : [];
}

async function saveTrainer(payload) {
  const resp = await fetch(`${API}/trainers`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

async function updateTrainer(id, payload) {
  const resp = await fetch(`${API}/trainers/${id}`, {
    method: "PATCH",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

async function deleteTrainer(id) {
  if (!confirm("Delete this trainer?")) return;
  const resp = await fetch(`${API}/trainers/${id}`, {method: "DELETE"});
  const json = await resp.json();
  if (json.success) render();
}

function trainerTable(rows) {
  const trs = rows.map(r => `
    <tr class="border-b hover:bg-gray-50">
      <td class="px-4 py-2">${r.name}</td>
      <td class="px-4 py-2">${r.stable_name || ""}</td>
      <td class="px-4 py-2">${r.location || ""}</td>
      <td class="px-4 py-2">${r.email || ""}</td>
      <td class="px-4 py-2 text-right">
        <button onclick="editTrainer('${r.id}')" class="text-blue-600 hover:underline text-sm mr-2">Edit</button>
        <button onclick="deleteTrainer('${r.id}')" class="text-red-600 hover:underline text-sm">Delete</button>
      </td>
    </tr>
  `).join("");
  return `
    <table class="w-full text-left border mt-2">
      <thead class="bg-gray-100">
        <tr><th class="px-4 py-2">Name</th><th class="px-4 py-2">Stable</th><th class="px-4 py-2">Location</th><th class="px-4 py-2">Email</th><th class="px-4 py-2 text-right">Actions</th></tr>
      </thead>
      <tbody>${trs}</tbody>
    </table>
  `;
}

function trainerForm(values = {}, editing = false) {
  const v = (key) => values[key] || "";
  return `
    <div class="bg-white shadow rounded-lg p-6 mt-4">
      <h3 class="text-lg font-bold mb-4">${editing ? "Edit Trainer" : "Add Trainer"}</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Name *</label>
          <input id="t-name" type="text" value="${v("name")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Stable Name *</label>
          <input id="t-stable_name" type="text" value="${v("stable_name")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Location *</label>
          <input id="t-location" type="text" value="${v("location")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Email *</label>
          <input id="t-email" type="email" value="${v("email")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Phone</label>
          <input id="t-phone" type="text" value="${v("phone")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">NZTR License</label>
          <input id="t-nztr_license_number" type="text" value="${v("nztr_license_number")}" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700">Bio</label>
          <textarea id="t-bio" rows="3" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">${v("bio")}</textarea>
        </div>
      </div>
      <div class="mt-4 flex gap-2">
        <button onclick="submitTrainer(${editing ? `'${v("id")}'` : "null"})" class="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium">Save</button>
        <button onclick="render()" class="bg-gray-200 text-gray-800 px-4 py-2 rounded-md text-sm font-medium">Cancel</button>
      </div>
    </div>
  `;
}

window.submitTrainer = async function(id) {
  const payload = {
    name: document.getElementById("t-name").value.trim(),
    stable_name: document.getElementById("t-stable_name").value.trim(),
    location: document.getElementById("t-location").value.trim(),
    email: document.getElementById("t-email").value.trim(),
    phone: document.getElementById("t-phone").value.trim() || undefined,
    nztr_license_number: document.getElementById("t-nztr_license_number").value.trim() || undefined,
    bio: document.getElementById("t-bio").value.trim() || undefined,
  };
  if (id) {
    const resp = await updateTrainer(id, payload);
    if (!resp.success) { alert(resp.error); return; }
  } else {
    const resp = await saveTrainer(payload);
    if (!resp.success) { alert(resp.error); return; }
  }
  window.location.hash = "#/trainers";
  render();
};

window.editTrainer = async function(id) {
  const resp = await fetch(`${API}/trainers/${id}`);
  const json = await resp.json();
  if (!json.success) return alert(json.error);
  const data = json.data;
  app.innerHTML = `
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">Trainers</h2>
        <button onclick="window.location.hash='#/trainers';render()" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Back</button>
      </div>
    </div>
    ${trainerForm(data, true)}
  `;
};

window.deleteTrainer = deleteTrainer;

// ─── Leases / HLTs ───────────────────────────────────────────────────────────

async function loadLeases() {
  const resp = await fetch(`${API}/leases`);
  const json = await resp.json();
  return json.success ? json.data : [];
}

async function loadHlts() {
  const resp = await fetch(`${API}/hlts`);
  const json = await resp.json();
  return json.success ? json.data : [];
}

async function getHlt(id) {
  const resp = await fetch(`${API}/hlts/${id}`);
  return await resp.json();
}

async function createHltWorkflow(payload) {
  const resp = await fetch(`${API}/hlts/workflow`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  return await resp.json();
}

window.createHltWorkflow = createHltWorkflow;

window.previewHlt = function() {
  const percentLeased = parseFloat(document.getElementById("h-percent_leased").value) || 0;
  const durationMonths = parseInt(document.getElementById("h-duration_months").value) || 0;
  const tokenCount = parseInt(document.getElementById("h-token_count").value) || 1;
  const minUnitSize = parseFloat(document.getElementById("h-min_unit_size").value) || 0.25;
  const priceBasis = document.getElementById("h-price_basis").value;
  const pricePeriod = document.getElementById("h-price_period").value;
  const priceAmount = parseFloat(document.getElementById("h-price_amount").value) || 0;

  // Derive canonical price_per_1pct_per_month
  let pricePer1pctPerMonth = 0;
  if (priceBasis === "per_1pct") {
    if (pricePeriod === "month") pricePer1pctPerMonth = priceAmount;
    else if (pricePeriod === "year") pricePer1pctPerMonth = priceAmount / 12;
    else if (pricePeriod === "total") pricePer1pctPerMonth = priceAmount / durationMonths;
  } else if (priceBasis === "full_stake") {
    if (pricePeriod === "month") pricePer1pctPerMonth = priceAmount / percentLeased;
    else if (pricePeriod === "year") pricePer1pctPerMonth = (priceAmount / 12) / percentLeased;
    else if (pricePeriod === "total") pricePer1pctPerMonth = (priceAmount / durationMonths) / percentLeased;
  }

  const pricePer1pctPerYear = pricePer1pctPerMonth * 12;
  const monthlyStakePrice = pricePer1pctPerMonth * percentLeased;
  const annualStakePrice = pricePer1pctPerYear * percentLeased;
  const totalIssuanceValue = pricePer1pctPerMonth * durationMonths * percentLeased;
  const percentPerToken = percentLeased / tokenCount;
  const tokenPrice = totalIssuanceValue / tokenCount;

  document.getElementById("preview-area").classList.remove("hidden");
  document.getElementById("preview-fields").innerHTML = `
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">Price / 1% / Month</div><div class="font-semibold">$${pricePer1pctPerMonth.toFixed(2)}</div></div>
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">Total Value</div><div class="font-semibold">$${totalIssuanceValue.toFixed(2)} NZD</div></div>
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">Token Price</div><div class="font-semibold">$${tokenPrice.toFixed(2)}</div></div>
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">% Per Token</div><div class="font-semibold">${percentPerToken.toFixed(2)}%</div></div>
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">Monthly Stake</div><div class="font-semibold">$${monthlyStakePrice.toFixed(2)}</div></div>
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">Annual Stake</div><div class="font-semibold">$${annualStakePrice.toFixed(2)}</div></div>
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">Min Unit</div><div class="font-semibold">${minUnitSize}%</div></div>
    <div class="bg-white rounded p-2 border"><div class="text-gray-500 text-xs">Tokens</div><div class="font-semibold">${tokenCount}</div></div>
  `;
};

window.submitHlt = async function() {
  const payload = {
    horse_microchip: document.getElementById("h-horse").value,
    owner_id: document.getElementById("h-owner").value,
    trainer_id: document.getElementById("h-trainer").value,
    lease_id: document.getElementById("h-lease_id").value.trim(),
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
  };

  const resp = await createHltWorkflow(payload);
  if (!resp.success) {
    alert("Error: " + (resp.error || JSON.stringify(resp)));
    return;
  }
  window.location.hash = "#/hlts";
  render();
};

// ─── Views ───────────────────────────────────────────────────────────────────

const views = {
  horses: async () => {
    setLoading(true);
    const horses = await loadHorses();
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Horses</h2>
          <button onclick="window.horseAddMode=true;render()" class="bg-green-600 text-white px-3 py-2 rounded-md text-sm font-medium">Add Horse</button>
        </div>
        ${horseTable(horses)}
      </div>
      ${window.horseAddMode ? horseForm() : ""}
    `;
    window.horseAddMode = false;
  },
  owners: async () => {
    setLoading(true);
    const rows = await loadOwners();
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Owners</h2>
          <button onclick="window.ownerAddMode=true;render()" class="bg-green-600 text-white px-3 py-2 rounded-md text-sm font-medium">Add Owner</button>
        </div>
        ${ownerTable(rows)}
      </div>
      ${window.ownerAddMode ? ownerForm() : ""}
    `;
    window.ownerAddMode = false;
  },
  trainers: async () => {
    setLoading(true);
    const rows = await loadTrainers();
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Trainers</h2>
          <button onclick="window.trainerAddMode=true;render()" class="bg-green-600 text-white px-3 py-2 rounded-md text-sm font-medium">Add Trainer</button>
        </div>
        ${trainerTable(rows)}
      </div>
      ${window.trainerAddMode ? trainerForm() : ""}
    `;
    window.trainerAddMode = false;
  },
  "create-hlt": async () => {
    setLoading(true);
    const [horses, owners, trainers] = await Promise.all([loadHorses(), loadOwners(), loadTrainers()]);
    const horseOptions = horses.map(h => `<option value="${h.microchip}">${h.name} (${h.microchip})</option>`).join("");
    const ownerOptions = owners.map(o => `<option value="${o.id}">${o.name} (${o.id})</option>`).join("");
    const trainerOptions = trainers.map(t => `<option value="${t.id}">${t.name} — ${t.stable_name} (${t.id})</option>`).join("");
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6 max-w-4xl mx-auto">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-xl font-bold">Create HLT</h2>
          <button onclick="window.location.hash='#/hlts';render()" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Back</button>
        </div>
        <form id="hlt-form" onsubmit="event.preventDefault(); submitHlt();">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">Horse</label>
              <select id="h-horse" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">${horseOptions}</select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Owner</label>
              <select id="h-owner" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">${ownerOptions}</select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Trainer / Stable</label>
              <select id="h-trainer" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">${trainerOptions}</select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Lease ID</label>
              <input id="h-lease_id" type="text" placeholder="e.g. LSE-002" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Start Date</label>
              <input id="h-start_date" type="date" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">End Date</label>
              <input id="h-end_date" type="date" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Duration (months)</label>
              <input id="h-duration_months" type="number" min="1" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">% Leased</label>
              <input id="h-percent_leased" type="number" step="0.01" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Token Count</label>
              <input id="h-token_count" type="number" min="1" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Min Unit Size (%)</label>
              <input id="h-min_unit_size" type="number" step="0.01" placeholder="0.25" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Price Basis</label>
              <select id="h-price_basis" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">
                <option value="per_1pct">Per 1%</option>
                <option value="full_stake">Full Stake</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Price Period</label>
              <select id="h-price_period" class="mt-1 w-full border rounded-md px-3 py-2 text-sm">
                <option value="month">Per Month</option>
                <option value="year">Per Year</option>
                <option value="total">Total Duration</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Price Amount (NZD)</label>
              <input id="h-price_amount" type="number" step="0.01" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Investor Share %</label>
              <input id="h-investor_share" type="number" step="0.01" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Owner Share %</label>
              <input id="h-owner_share" type="number" step="0.01" class="mt-1 w-full border rounded-md px-3 py-2 text-sm" required />
            </div>
          </div>
          <div class="flex gap-2 mb-4">
            <button type="button" onclick="previewHlt()" class="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium">Preview Pricing</button>
            <button type="submit" class="bg-green-600 text-white px-4 py-2 rounded-md text-sm font-medium">Create HLT</button>
          </div>
          <div id="preview-area" class="hidden bg-gray-50 rounded-lg p-4 border">
            <h3 class="text-sm font-bold text-gray-700 mb-2">Derived Pricing</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm" id="preview-fields"></div>
          </div>
        </form>
      </div>
    `;
  },
  hlts: async () => {
    setLoading(true);
    const hlts = await loadHlts();
    const rows = hlts.map(h => `
      <tr class="border-b hover:bg-gray-50 cursor-pointer" onclick="window.location.hash='#/hlt/${h.id}';render()">
        <td class="px-4 py-3">
          <div class="font-semibold">${h.horse_name || h.horse_microchip}</div>
          <div class="text-xs text-gray-400 font-mono mt-0.5">ID: ${h.id} | Microchip: ${h.horse_microchip}</div>
        </td>
        <td class="px-4 py-3">${h.owner_name || h.owner_id}</td>
        <td class="px-4 py-3">${h.trainer_name || h.trainer_id}</td>
        <td class="px-4 py-3">${h.lease_id}</td>
        <td class="px-4 py-3"><span class="rounded-full px-2 py-0.5 text-xs font-semibold bg-gray-100 text-gray-700">${h.status}</span></td>
      </tr>
    `).join("");
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">HLTs</h2>
          <button onclick="window.location.hash='#/create-hlt';render()" class="bg-green-600 text-white px-3 py-2 rounded-md text-sm font-medium">Create HLT</button>
        </div>
        <table class="w-full text-left border mt-2">
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
    `;
  },
  default: async () => {
    const [stats, horses, owners, trainers, hlts] = await Promise.all([
      fetch(`${API}/stats`).then(r => r.json()).then(j => j.success ? j.data : {}),
      loadHorses(), loadOwners(), loadTrainers(), loadHlts()
    ]);
    const counts = {
      horses: stats.horses || horses.length,
      owners: stats.owners || owners.length,
      trainers: stats.trainers || trainers.length,
      hlts: stats.hlts || hlts.length,
    };
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-xl font-bold mb-6">HLT Mission Control</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div class="bg-emerald-50 rounded-lg p-4 border border-emerald-100">
            <div class="text-3xl font-bold text-emerald-700">${counts.horses}</div>
            <div class="text-sm text-emerald-600 font-medium">Horses</div>
          </div>
          <div class="bg-blue-50 rounded-lg p-4 border border-blue-100">
            <div class="text-3xl font-bold text-blue-700">${counts.owners}</div>
            <div class="text-sm text-blue-600 font-medium">Owners</div>
          </div>
          <div class="bg-amber-50 rounded-lg p-4 border border-amber-100">
            <div class="text-3xl font-bold text-amber-700">${counts.trainers}</div>
            <div class="text-sm text-amber-600 font-medium">Trainers / Stables</div>
          </div>
          <div class="bg-purple-50 rounded-lg p-4 border border-purple-100">
            <div class="text-3xl font-bold text-purple-700">${counts.hlts}</div>
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
};

// ─── HLT Detail View (dynamic route) ─────────────────────────────────────────

window.renderHltDetail = async function(id) {
  setLoading(true);
  const json = await getHlt(id);
  if (!json.success) {
    app.innerHTML = `<div class="p-6 text-red-600">HLT not found.</div>`;
    return;
  }
  const h = json.data;
  const horse = h.horse || {};
  const owner = h.owner || {};
  const trainer = h.trainer || {};
  const lease = h.lease || {};

  // Document badges
  const docBadge = (status) => `<span class="rounded-full px-2 py-0.5 text-xs font-semibold ${status === 'complete' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-700'}">${status}</span>`;

  app.innerHTML = `
    <div class="bg-white shadow rounded-lg p-6 max-w-5xl mx-auto">
      <!-- Header -->
      <div class="flex justify-between items-start mb-6">
        <div>
          <h1 class="text-2xl font-bold">${horse.name || 'Unnamed Horse'}</h1>
          <p class="text-sm text-gray-500 mt-1">HLT ${docBadge(h.status)} <span class="text-gray-400 mx-1">•</span> Lease ${h.lease_id}</p>
        </div>
        <button onclick="window.location.hash='#/hlts';render()" class="bg-gray-800 text-white px-3 py-2 rounded-md text-sm">Back</button>
      </div>

      <!-- Entity cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-gray-50 rounded-lg p-4 border">
          <h3 class="text-xs font-bold text-gray-500 uppercase mb-2">Horse</h3>
          <p class="font-semibold text-lg">${horse.name || '—'}</p>
          <p class="text-sm text-gray-500">${horse.sex || ''} ${horse.colour ? '• ' + horse.colour : ''}</p>
          <p class="text-sm text-gray-500">${horse.sire_name || ''} / ${horse.dam_name || ''}</p>
          <div class="mt-2 text-xs text-gray-400 font-mono">Microchip: ${h.horse_microchip}</div>
        </div>
        <div class="bg-gray-50 rounded-lg p-4 border">
          <h3 class="text-xs font-bold text-gray-500 uppercase mb-2">Owner</h3>
          <p class="font-semibold text-lg">${owner.name || '—'}</p>
          <p class="text-sm text-gray-500">${owner.email || ''}</p>
          <p class="text-sm text-gray-500">${owner.phone || ''}</p>
          <div class="mt-2 text-xs text-gray-400 font-mono">ID: ${h.owner_id}</div>
        </div>
        <div class="bg-gray-50 rounded-lg p-4 border">
          <h3 class="text-xs font-bold text-gray-500 uppercase mb-2">Trainer / Stable</h3>
          <p class="font-semibold text-lg">${trainer.name || '—'}</p>
          <p class="text-sm text-gray-500">${trainer.stable_name || ''}</p>
          <p class="text-sm text-gray-500">${trainer.location || ''}</p>
          <div class="mt-2 text-xs text-gray-400 font-mono">ID: ${h.trainer_id}</div>
        </div>
      </div>

      <!-- Lease Terms -->
      <div class="bg-gray-50 rounded-lg p-4 border mb-6">
        <h3 class="text-xs font-bold text-gray-500 uppercase mb-3">Lease Terms</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <tbody class="divide-y">
              <tr><td class="py-2 text-gray-500 w-48">Lease ID</td><td class="py-2 font-semibold">${lease.lease_id || h.lease_id || '—'}</td></tr>
              <tr><td class="py-2 text-gray-500">Duration</td><td class="py-2 font-semibold">${lease.duration_months || '—'} months</td></tr>
              <tr><td class="py-2 text-gray-500">Percent Leased</td><td class="py-2 font-semibold">${lease.percent_leased || '—'}%</td></tr>
              <tr><td class="py-2 text-gray-500">Token Count</td><td class="py-2 font-semibold">${lease.token_count || '—'}</td></tr>
              <tr><td class="py-2 text-gray-500">Min Unit Size</td><td class="py-2 font-semibold">${lease.min_unit_size || '—'}%</td></tr>
              <tr><td class="py-2 text-gray-500">Price per 1% per month</td><td class="py-2 font-semibold">$${lease.price_per_1pct_per_month || '—'}</td></tr>
              <tr><td class="py-2 text-gray-500">Total Issuance Value</td><td class="py-2 font-semibold">$${lease.total_issuance_value_nzd || '—'} NZD</td></tr>
              <tr><td class="py-2 text-gray-500">Token Price</td><td class="py-2 font-semibold">$${lease.token_price_nzd || '—'}</td></tr>
              <tr><td class="py-2 text-gray-500">Revenue Split</td><td class="py-2 font-semibold">Investor ${lease.investor_share_percent || '—'}% / Owner ${lease.owner_share_percent || '—'}% / Platform ${lease.platform_fee_percent || '0'}%</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 mb-6">
        <button onclick="generateTermSheet('${h.id}')" class="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium">Generate Term Sheet</button>
        <button onclick="alert('Document upload coming in Sprint 5')" class="bg-gray-600 text-white px-4 py-2 rounded-md text-sm font-medium">Upload Documents</button>
      </div>

      <!-- Document status -->
      <div class="grid grid-cols-3 gap-4 text-sm">
        <div class="border rounded-lg p-3">
          <div class="flex justify-between items-center">
            <span class="font-semibold">Term Sheet</span>
            ${docBadge(h.term_sheet_status)}
          </div>
        </div>
        <div class="border rounded-lg p-3">
          <div class="flex justify-between items-center">
            <span class="font-semibold">PDS</span>
            ${docBadge(h.pds_status)}
          </div>
        </div>
        <div class="border rounded-lg p-3">
          <div class="flex justify-between items-center">
            <span class="font-semibold">SA</span>
            ${docBadge(h.sa_status)}
          </div>
        </div>
      </div>
    </div>
  `;
};

// ─── Route with dynamic HLT id ─────────────────────────────────────────────

// ─── Term Sheet Generation ────────────────────────────────────────────────────

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
    // Refresh detail view to show updated status badge
    renderHltDetail(hltId);
  } catch (e) {
    alert("Term sheet generation failed: " + e.message);
  }
};

const oldRender = render;
window.render = function() {
  const hash = window.location.hash.replace("#/", "").replace("#", "");
  if (hash.startsWith("hlt/")) {
    const id = hash.replace("hlt/", "");
    renderHltDetail(id);
    return;
  }
  const viewFn = views[hash] || views.default;
  viewFn();
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.toggle("active", link.dataset.route === hash);
  });
};

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);
