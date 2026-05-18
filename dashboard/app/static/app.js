let accessToken = null;
let pendingTwoFactorToken = null;

const loginView = document.querySelector("#login-view");
const dashboardView = document.querySelector("#dashboard-view");
const loginForm = document.querySelector("#login-form");
const loginMessage = document.querySelector("#login-message");
const dashboardMessage = document.querySelector("#dashboard-message");
const totpLoginRow = document.querySelector("#totp-login-row");

function csrfToken() {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_token="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

function showMessage(element, text) {
  element.textContent = text || "";
}

function showDashboard() {
  loginView.classList.add("hidden");
  dashboardView.classList.remove("hidden");
}

function showLogin() {
  dashboardView.classList.add("hidden");
  loginView.classList.remove("hidden");
}

async function apiFetch(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  if (["POST", "PUT", "PATCH", "DELETE"].includes((options.method || "GET").toUpperCase())) {
    headers.set("X-CSRF-Token", csrfToken());
  }

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && retry && path !== "/api/auth/refresh") {
    const refreshed = await refreshSession();
    if (refreshed) {
      return apiFetch(path, options, false);
    }
  }

  return response;
}

async function refreshSession() {
  if (!csrfToken()) {
    return false;
  }

  const response = await apiFetch("/api/auth/refresh", { method: "POST" }, false);
  if (!response.ok) {
    accessToken = null;
    return false;
  }

  const data = await response.json();
  accessToken = data.access_token;
  return true;
}

function formatDate(value) {
  return new Date(value).toLocaleString();
}

function severityBadge(severity) {
  const level = String(severity || "").toLowerCase();
  return `<span class="badge ${level}">${severity || "-"}</span>`;
}

async function loadDashboard() {
  const [summaryResponse, alertsResponse, logsResponse] = await Promise.all([
    apiFetch("/api/dashboard/summary"),
    apiFetch(`/api/dashboard/alerts?limit=${document.querySelector("#alert-limit").value}`),
    apiFetch(`/api/dashboard/logs?limit=${document.querySelector("#log-limit").value}`),
  ]);

  if (!summaryResponse.ok || !alertsResponse.ok || !logsResponse.ok) {
    showMessage(dashboardMessage, "No se pudieron cargar los datos.");
    return;
  }

  const summary = await summaryResponse.json();
  const alerts = await alertsResponse.json();
  const logs = await logsResponse.json();

  document.querySelector("#total-logs").textContent = summary.total_logs;
  document.querySelector("#total-alerts").textContent = summary.total_alerts;
  document.querySelector("#total-types").textContent = summary.alerts_by_type.length;

  document.querySelector("#alerts-body").innerHTML = alerts.alerts
    .map((alert) => `
      <tr>
        <td>${alert.alert_type}</td>
        <td>${severityBadge(alert.severity)}</td>
        <td>${alert.ip_address || "-"}</td>
        <td>${alert.endpoint || "-"}</td>
        <td>${formatDate(alert.created_at)}</td>
      </tr>
    `)
    .join("");

  document.querySelector("#logs-body").innerHTML = logs.logs
    .map((log) => `
      <tr>
        <td>${log.event_type}</td>
        <td>${log.status_code || "-"}</td>
        <td>${log.ip_address || "-"}</td>
        <td>${log.endpoint || "-"}</td>
        <td>${formatDate(log.created_at)}</td>
      </tr>
    `)
    .join("");

  showMessage(dashboardMessage, "");
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage(loginMessage, "");

  if (pendingTwoFactorToken) {
    const response = await fetch("/api/auth/2fa/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        two_factor_token: pendingTwoFactorToken,
        code: document.querySelector("#totp-login-code").value,
      }),
    });

    if (!response.ok) {
      showMessage(loginMessage, "Codigo 2FA invalido.");
      return;
    }

    const data = await response.json();
    accessToken = data.access_token;
    pendingTwoFactorToken = null;
    totpLoginRow.classList.add("hidden");
    showDashboard();
    loadDashboard();
    return;
  }

  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      email: document.querySelector("#email").value,
      password: document.querySelector("#password").value,
    }),
  });

  if (!response.ok) {
    showMessage(loginMessage, "Credenciales invalidas.");
    return;
  }

  const data = await response.json();
  if (data.requires_2fa) {
    pendingTwoFactorToken = data.two_factor_token;
    totpLoginRow.classList.remove("hidden");
    showMessage(loginMessage, "Ingresa tu codigo 2FA.");
    return;
  }

  accessToken = data.access_token;
  showDashboard();
  loadDashboard();
});

document.querySelector("#refresh-button").addEventListener("click", loadDashboard);
document.querySelector("#alert-limit").addEventListener("change", loadDashboard);
document.querySelector("#log-limit").addEventListener("change", loadDashboard);

document.querySelector("#logout-button").addEventListener("click", async () => {
  await apiFetch("/api/auth/logout", { method: "POST" }, false);
  accessToken = null;
  showLogin();
});

document.querySelector("#setup-2fa-button").addEventListener("click", async () => {
  const response = await apiFetch("/api/auth/2fa/setup", { method: "POST" });
  if (!response.ok) {
    showMessage(dashboardMessage, "No se pudo iniciar 2FA.");
    return;
  }

  const data = await response.json();
  document.querySelector("#totp-qr").src = data.qr_code_data_uri;
  document.querySelector("#totp-setup").classList.remove("hidden");
});

document.querySelector("#verify-2fa-button").addEventListener("click", async () => {
  const response = await apiFetch("/api/auth/2fa/verify", {
    method: "POST",
    body: JSON.stringify({
      code: document.querySelector("#totp-verify-code").value,
    }),
  });

  if (!response.ok) {
    showMessage(dashboardMessage, "Codigo 2FA invalido.");
    return;
  }

  showMessage(dashboardMessage, "2FA activado.");
  document.querySelector("#totp-setup").classList.add("hidden");
});

setInterval(() => {
  if (accessToken) {
    loadDashboard();
  }
}, 5000);

refreshSession().then((ok) => {
  if (ok) {
    showDashboard();
    loadDashboard();
  }
});
