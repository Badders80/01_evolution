/**
 * HLT Mission Control — Vanilla JS frontend.
 * Hash routing: #/horses, #/owners, #/trainers, #/create-hlt
 */

const app = document.getElementById("app");

const views = {
  horses: () => `
    <div class="bg-white shadow rounded-lg p-6">
      <h2 class="text-xl font-bold mb-4">Horses</h2>
      <p class="text-gray-600">Horse management coming in Sprint 2.</p>
    </div>
  `,
  owners: () => `
    <div class="bg-white shadow rounded-lg p-6">
      <h2 class="text-xl font-bold mb-4">Owners</h2>
      <p class="text-gray-600">Owner management coming in Sprint 2.</p>
    </div>
  `,
  trainers: () => `
    <div class="bg-white shadow rounded-lg p-6">
      <h2 class="text-xl font-bold mb-4">Trainers</h2>
      <p class="text-gray-600">Trainer management coming in Sprint 2.</p>
    </div>
  `,
  "create-hlt": () => `
    <div class="bg-white shadow rounded-lg p-6">
      <h2 class="text-xl font-bold mb-4">Create HLT</h2>
      <p class="text-gray-600">HLT creation workflow coming in Sprint 3.</p>
    </div>
  `,
  default: () => `
    <div class="bg-white shadow rounded-lg p-6">
      <h2 class="text-xl font-bold mb-4">Dashboard</h2>
      <p class="text-gray-600">Welcome to HLT Mission Control. Use the nav above.</p>
    </div>
  `
};

function render() {
  const hash = window.location.hash.replace("#", "").replace("/", "") || "default";
  const viewFn = views[hash] || views.default;
  app.innerHTML = viewFn();

  // Update nav active state
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.toggle("active", link.dataset.route === hash);
  });
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", render);
