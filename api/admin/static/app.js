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
  "create-hlt": () => {
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-xl font-bold mb-4">Create HLT</h2>
        <p class="text-gray-600">HLT creation workflow coming in Sprint 3.</p>
      </div>
    `;
  },
  default: () => {
    app.innerHTML = `
      <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-xl font-bold mb-4">Dashboard</h2>
        <p class="text-gray-600">Welcome to HLT Mission Control. Use the nav above.</p>
      </div>
    `;
  }
};

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);
