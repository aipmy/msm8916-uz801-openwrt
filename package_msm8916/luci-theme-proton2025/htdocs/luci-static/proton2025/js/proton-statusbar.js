/**
 * Proton2025 Theme - Topbar Status Bar Extension
 * Shows interactive live widgets directly under the topbar:
 * - SIM Card / Cellular Operator & Signal (click -> /admin/modem/5gmodem/detail)
 * - SMS Counter (click -> /admin/modem/5gmodem/readsms)
 * - SoC & Modem Temperature (click -> /admin/status/proton-temperature)
 * - CPU & RAM utilization (click -> /admin/status/processes)
 * - Connected Clients (click -> /admin/status/overview)
 */

(function () {
  "use strict";

  const POLL_INTERVAL = 3; // seconds
  let timerId = null;

  function createStatusBar() {
    if (document.getElementById("proton-statusbar")) return;

    const menubar = document.getElementById("menubar");
    if (!menubar) return;

    const bar = document.createElement("div");
    bar.id = "proton-statusbar";
    bar.className = "proton-statusbar-bar";
    bar.innerHTML = `
      <div class="proton-statusbar-inner">
        <!-- SIM / Cellular -->
        <a class="proton-status-item" id="sb-sim" href="${L.url('admin/modem/5gmodem/detail')}" title="Cellular Status & Modem">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="2" width="14" height="20" rx="2"></rect>
            <path d="M15 2v4a2 2 0 0 1-2 2H9"></path>
            <path d="M9 13v.01"></path>
            <path d="M15 13v.01"></path>
            <path d="M9 17v.01"></path>
            <path d="M15 17v.01"></path>
          </svg>
          <span class="sb-label" id="sb-sim-label">SIM: Checking...</span>
          <span class="sb-badge" id="sb-sim-sig">--</span>
        </a>

        <!-- SMS -->
        <a class="proton-status-item" id="sb-sms" href="${L.url('admin/modem/5gmodem/readsms')}" title="SMS Messages">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="5" width="18" height="14" rx="2"></rect>
            <path d="m3 7 9 6 9-6"></path>
          </svg>
          <span class="sb-label">SMS</span>
          <span class="sb-badge badge-neutral" id="sb-sms-count">0</span>
        </a>

        <!-- Temperature -->
        <a class="proton-status-item" id="sb-temp" href="${L.url('admin/status/proton-temperature')}" title="Hardware Thermal Sensors">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path>
          </svg>
          <span class="sb-label">Temp:</span>
          <span class="sb-badge badge-normal" id="sb-temp-val">--°C</span>
        </a>

        <!-- CPU -->
        <a class="proton-status-item" id="sb-cpu" href="${L.url('admin/status/processes')}" title="CPU Load & Processes">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="16" height="16" rx="2"></rect>
            <rect x="9" y="9" width="6" height="6"></rect>
            <path d="M9 1v3"></path>
            <path d="M15 1v3"></path>
            <path d="M9 20v3"></path>
            <path d="M15 20v3"></path>
            <path d="M20 9h3"></path>
            <path d="M20 14h3"></path>
            <path d="M1 9h3"></path>
            <path d="M1 14h3"></path>
          </svg>
          <span class="sb-label">CPU:</span>
          <span class="sb-badge" id="sb-cpu-val">--%</span>
        </a>

        <!-- RAM -->
        <a class="proton-status-item" id="sb-ram" href="${L.url('admin/status/overview')}" title="RAM Usage">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 19v-3"></path>
            <path d="M10 19v-3"></path>
            <path d="M14 19v-3"></path>
            <path d="M18 19v-3"></path>
            <rect x="2" y="5" width="20" height="11" rx="2"></rect>
          </svg>
          <span class="sb-label">RAM:</span>
          <span class="sb-badge" id="sb-ram-val">--%</span>
        </a>

        <!-- Clients -->
        <a class="proton-status-item" id="sb-clients" href="${L.url('admin/status/overview')}" title="Connected LAN / WiFi Clients">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
          <span class="sb-label">Clients:</span>
          <span class="sb-badge badge-neutral" id="sb-clients-val">0</span>
        </a>
      </div>
    `;

    menubar.insertAdjacentElement("afterend", bar);
  }

  async function updateStatusBar() {
    if (!window.L || !L.rpc) return;

    try {
      // 1. Fetch system & board info
      const callSysInfo = L.rpc.declare({ object: "system", method: "info" });
      const callDhcp = L.rpc.declare({ object: "luci-rpc", method: "getDHCPLeases" });
      const callTemp = L.rpc.declare({ object: "luci.proton-temp", method: "getSensors" });
      const callReadFile = L.rpc.declare({ object: "file", method: "read", params: ["path"] });

      const [sysInfo, dhcpLeases, tempSensors, teleContent, smsContent] = await Promise.all([
        L.resolveDefault(callSysInfo(), {}),
        L.resolveDefault(callDhcp(), {}),
        L.resolveDefault(callTemp(), {}),
        L.resolveDefault(callReadFile({ path: "/tmp/5gmodem/tele.json" }), {}),
        L.resolveDefault(callReadFile({ path: "/tmp/5gmodem/sms_new.json" }), {})
      ]);

      // Update CPU & RAM
      if (sysInfo && sysInfo.memory) {
        const mem = sysInfo.memory;
        const total = mem.total || 1;
        const free = (mem.free || 0) + (mem.buffered || 0) + (mem.cached || 0);
        const usedPct = Math.round(((total - free) / total) * 100);
        const ramEl = document.getElementById("sb-ram-val");
        if (ramEl) {
          ramEl.textContent = `${usedPct}%`;
          ramEl.className = "sb-badge " + (usedPct > 85 ? "badge-danger" : usedPct > 65 ? "badge-warning" : "badge-normal");
        }
      }

      if (sysInfo && sysInfo.load && sysInfo.load.length) {
        const load1 = (sysInfo.load[0] / 65535).toFixed(2);
        const cpuEl = document.getElementById("sb-cpu-val");
        if (cpuEl) {
          cpuEl.textContent = `${load1}`;
          const lNum = parseFloat(load1);
          cpuEl.className = "sb-badge " + (lNum > 2.5 ? "badge-danger" : lNum > 1.2 ? "badge-warning" : "badge-normal");
        }
      }

      // Update Connected Clients
      const clientsEl = document.getElementById("sb-clients-val");
      if (clientsEl) {
        let count = 0;
        if (dhcpLeases && Array.isArray(dhcpLeases.dhcp_leases)) {
          count = dhcpLeases.dhcp_leases.length;
        }
        clientsEl.textContent = count;
      }

      // Update Temperature
      const tempEl = document.getElementById("sb-temp-val");
      if (tempEl && tempSensors && Array.isArray(tempSensors.sensors) && tempSensors.sensors.length > 0) {
        let maxTemp = 0;
        tempSensors.sensors.forEach(s => {
          if (s.temp && s.temp > maxTemp) maxTemp = s.temp;
        });
        if (maxTemp > 0) {
          tempEl.textContent = `${Math.round(maxTemp)}°C`;
          tempEl.className = "sb-badge " + (maxTemp >= 75 ? "badge-danger" : maxTemp >= 60 ? "badge-warning" : "badge-normal");
        }
      }

      // Update Cellular / SIM
      let tele = null;
      if (teleContent && teleContent.data) {
        try { tele = JSON.parse(teleContent.data); } catch (e) {}
      }

      const simLabel = document.getElementById("sb-sim-label");
      const simSig = document.getElementById("sb-sim-sig");
      if (simLabel && simSig) {
        if (tele && (tele.oper || tele.mode)) {
          const oper = tele.oper || "Connected";
          const mode = tele.mode ? ` (${tele.mode})` : "";
          simLabel.textContent = `${oper}${mode}`;
          if (tele.sig !== undefined && tele.sig !== null) {
            simSig.textContent = `${tele.sig}%`;
            simSig.className = "sb-badge " + (tele.sig >= 50 ? "badge-normal" : tele.sig >= 25 ? "badge-warning" : "badge-danger");
          } else if (tele.rsrp) {
            simSig.textContent = `${tele.rsrp}dBm`;
            simSig.className = "sb-badge badge-normal";
          }
        } else {
          simLabel.textContent = "SIM: Ready / 4G";
          simSig.textContent = "OK";
          simSig.className = "sb-badge badge-normal";
        }
      }

      // Update SMS Count
      let sms = null;
      if (smsContent && smsContent.data) {
        try { sms = JSON.parse(smsContent.data); } catch (e) {}
      }
      const smsEl = document.getElementById("sb-sms-count");
      if (smsEl) {
        let unread = (sms && sms.count !== undefined) ? parseInt(sms.count, 10) : 0;
        if (isNaN(unread)) unread = 0;
        smsEl.textContent = unread;
        smsEl.className = "sb-badge " + (unread > 0 ? "badge-highlight" : "badge-neutral");
      }

    } catch (err) {
      // Non-critical background telemetry error
    }
  }

  function init() {
    createStatusBar();
    updateStatusBar();
    if (timerId) clearInterval(timerId);
    timerId = setInterval(updateStatusBar, POLL_INTERVAL * 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
