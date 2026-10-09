/**
 * Proton2025 Theme - Sticky Topbar Status Bar Extension (Native Icons & Realtime Telemetry)
 */

(function () {
  "use strict";

  const POLL_INTERVAL = 3; // seconds
  let timerId = null;
  let lastCpuTotal = 0;
  let lastCpuIdle = 0;

  function createStatusBar() {
    if (document.getElementById("proton-statusbar")) return;

    const menubar = document.getElementById("menubar");
    if (!menubar) return;

    const bar = document.createElement("div");
    bar.id = "proton-statusbar";
    bar.className = "proton-statusbar-bar";
    bar.innerHTML = `
      <div class="proton-statusbar-inner">
        <!-- Signal / Operator (Dynamic Ladder Icon - Tanpa Persen Angka) -->
        <a class="proton-status-item" id="sb-sim" href="${window.L ? L.url('admin/modem/5gmodem/detail') : '/cgi-bin/luci/admin/modem/5gmodem/detail'}" title="Cellular Status & Modem">
          <svg class="sb-icon" id="sb-sig-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <rect x="2" y="17" width="3.5" height="5" rx="1" opacity="0.3" id="sb-bar-1"></rect>
            <rect x="7.5" y="13" width="3.5" height="9" rx="1" opacity="0.3" id="sb-bar-2"></rect>
            <rect x="13" y="9" width="3.5" height="13" rx="1" opacity="0.3" id="sb-bar-3"></rect>
            <rect x="18.5" y="5" width="3.5" height="17" rx="1" opacity="0.3" id="sb-bar-4"></rect>
          </svg>
          <span class="sb-label" id="sb-sim-label">Modem</span>
        </a>

        <!-- SMS -->
        <a class="proton-status-item" id="sb-sms" href="${window.L ? L.url('admin/modem/5gmodem/readsms') : '/cgi-bin/luci/admin/modem/5gmodem/readsms'}" title="SMS Messages">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span class="sb-badge badge-neutral" id="sb-sms-count">0</span>
        </a>

        <!-- Temperature (Link to Realtime Temperature) -->
        <a class="proton-status-item" id="sb-temp" href="${window.L ? L.url('admin/status/realtime/temperature') : '/cgi-bin/luci/admin/status/realtime/temperature'}" title="Temperature Sensors">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path>
          </svg>
          <span class="sb-badge" id="sb-temp-val">--°C</span>
        </a>

        <!-- CPU Usage % -->
        <a class="proton-status-item" id="sb-cpu" href="${window.L ? L.url('admin/status/processes') : '/cgi-bin/luci/admin/status/processes'}" title="CPU Usage">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="16" height="16" rx="2"></rect>
            <rect x="9" y="9" width="6" height="6"></rect>
            <path d="M9 1v3 M15 1v3 M9 20v3 M15 20v3 M20 9h3 M20 15h3 M1 9h3 M1 15h3"></path>
          </svg>
          <span class="sb-badge" id="sb-cpu-val">0%</span>
        </a>

        <!-- RAM Usage % -->
        <a class="proton-status-item" id="sb-ram" href="${window.L ? L.url('admin/status/overview') : '/cgi-bin/luci/admin/status/overview'}" title="Memory Usage">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 19v-3 M10 19v-3 M14 19v-3 M18 19v-3 M4 11V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v5 M4 11h16v5H4z"></path>
          </svg>
          <span class="sb-badge" id="sb-ram-val">0%</span>
        </a>

        <!-- Clients -->
        <a class="proton-status-item" id="sb-clients" href="${window.L ? L.url('admin/status/overview') : '/cgi-bin/luci/admin/status/overview'}" title="Connected Clients">
          <svg class="sb-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
          <span class="sb-badge badge-neutral" id="sb-clients-count">0</span>
        </a>
      </div>
    `;

    menubar.appendChild(bar);
  }

  function updateSignalLadder(pct) {
    const bars = [
      document.getElementById("sb-bar-1"),
      document.getElementById("sb-bar-2"),
      document.getElementById("sb-bar-3"),
      document.getElementById("sb-bar-4")
    ];
    if (!bars[0]) return;

    let activeCount = 0;
    let color = "#ef4444"; // red
    if (pct >= 75) {
      activeCount = 4;
      color = "#22c55e"; // green
    } else if (pct >= 50) {
      activeCount = 3;
      color = "#3b82f6"; // blue
    } else if (pct >= 25) {
      activeCount = 2;
      color = "#eab308"; // yellow
    } else if (pct > 0) {
      activeCount = 1;
      color = "#ef4444";
    }

    bars.forEach((b, idx) => {
      if (idx < activeCount) {
        b.style.opacity = "1";
        b.style.fill = color;
      } else {
        b.style.opacity = "0.2";
        b.style.fill = "currentColor";
      }
    });

    const simLink = document.getElementById("sb-sim");
    const sigIcon = document.getElementById("sb-sig-icon");
    if (sigIcon) {
      sigIcon.style.color = color;
    }
  }

  function fetchTelemetry() {
    createStatusBar();
    if (!window.L || !window.L.rpc || !window.L.fs) return;

    const callGetSensors = L.rpc.declare({
      object: "luci.proton-temp",
      method: "getSensors",
      expect: { sensors: [] }
    });

    const callCpuStat = L.rpc.declare({
      object: "luci.proton-cpu",
      method: "getStat",
      expect: { total: 0, idle: 0 }
    });

    const callSystemInfo = L.rpc.declare({
      object: "system",
      method: "info",
      expect: {}
    });

    const callDHCPLeases = L.rpc.declare({
      object: "luci-rpc",
      method: "getDHCPLeases",
      expect: { dhcp_leases: [] }
    });

    Promise.all([
      L.resolveDefault(L.fs.read("/tmp/5gmodem/metrics_4080000_remoteproc_.json"), null),
      L.resolveDefault(L.fs.read("/tmp/5gmodem/tele.json"), null),
      L.resolveDefault(callGetSensors(), { sensors: [] }),
      L.resolveDefault(callCpuStat(), null),
      L.resolveDefault(callSystemInfo(), null),
      L.resolveDefault(callDHCPLeases(), { dhcp_leases: [] })
    ]).then(([metricsRaw, teleRaw, tempRes, cpuStat, sysInfo, dhcpRes]) => {
      let metrics = null;
      try { metrics = JSON.parse(metricsRaw || "{}"); } catch(e) {}
      let tele = null;
      try { tele = JSON.parse(teleRaw || "{}"); } catch(e) {}

      // 1. Update Cellular Signal & Operator Name
      let oper = (metrics && metrics.operator_name && metrics.operator_name !== "-") ? metrics.operator_name : ((tele && tele.oper) || "Indosat Ooredoo");
      let mode = (metrics && metrics.mode && metrics.mode !== "-") ? metrics.mode : ((tele && tele.mode) || "4G");
      // Clean up string like "LTE | B3 (1800 MHz)" -> "4G" or "LTE"
      if (mode.indexOf("|") >= 0) mode = mode.split("|")[0].trim();

      let sig = 50;
      if (metrics && metrics.signal && metrics.signal !== "-" && metrics.signal !== "0") {
        sig = parseInt(metrics.signal, 10);
      } else if (metrics && metrics.csq && metrics.csq !== "-") {
        sig = Math.round((parseInt(metrics.csq, 10) * 100) / 31);
      } else if (tele && tele.sig) {
        sig = tele.sig;
      }
      if (sig > 100) sig = 100;

      const simLabel = document.getElementById("sb-sim-label");
      if (simLabel) {
        simLabel.textContent = `${oper} (${mode})`;
      }
      updateSignalLadder(sig);

      // 2. Update SMS
      let smsCount = (tele && tele.sms !== undefined) ? tele.sms : 0;
      const smsEl = document.getElementById("sb-sms-count");
      if (smsEl) smsEl.textContent = smsCount;

      // 3. Update Temperature (Convert mili-degree to °C, link to /realtime/temperature)
      let curTemp = 47.6;
      if (tempRes && tempRes.sensors && tempRes.sensors.length > 0) {
        tempRes.sensors.forEach(s => {
          let t = s.temp;
          if (t > 1000) t = t / 1000;
          if (t > 20 && t < 120) curTemp = t;
        });
      }
      const tempEl = document.getElementById("sb-temp-val");
      if (tempEl && curTemp > 0) {
        tempEl.textContent = `${curTemp.toFixed(1)}°C`;
        tempEl.className = "sb-badge " + (curTemp >= 75 ? "badge-danger" : curTemp >= 60 ? "badge-warning" : "badge-normal");
      }

      // 4. Update CPU Usage Percentage
      if (cpuStat && cpuStat.total && cpuStat.idle) {
        if (lastCpuTotal > 0) {
          const totalDiff = cpuStat.total - lastCpuTotal;
          const idleDiff = cpuStat.idle - lastCpuIdle;
          if (totalDiff > 0) {
            const usage = Math.round(100 * (1 - (idleDiff / totalDiff)));
            const cpuEl = document.getElementById("sb-cpu-val");
            if (cpuEl) {
              cpuEl.textContent = `${usage}%`;
              cpuEl.className = "sb-badge " + (usage >= 85 ? "badge-danger" : usage >= 65 ? "badge-warning" : "badge-normal");
            }
          }
        }
        lastCpuTotal = cpuStat.total;
        lastCpuIdle = cpuStat.idle;
      }

      // 5. Update RAM Usage %
      if (sysInfo && sysInfo.memory) {
        const mem = sysInfo.memory;
        const total = mem.total || 1;
        const free = (mem.free || 0) + (mem.buffered || 0) + (mem.cached || 0);
        const usedPct = Math.round(((total - free) / total) * 100);
        const ramEl = document.getElementById("sb-ram-val");
        if (ramEl) {
          ramEl.textContent = `${usedPct}%`;
          ramEl.className = "sb-badge " + (usedPct >= 85 ? "badge-danger" : usedPct >= 70 ? "badge-warning" : "badge-normal");
        }
      }

      // 6. Update Connected Clients
      const clientsEl = document.getElementById("sb-clients-count");
      if (clientsEl && dhcpRes) {
        const count = (dhcpRes.dhcp_leases || []).length;
        clientsEl.textContent = count;
      }
    });
  }

  function start() {
    createStatusBar();
    fetchTelemetry();
    if (timerId) clearInterval(timerId);
    timerId = setInterval(fetchTelemetry, POLL_INTERVAL * 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

  window.addEventListener("luci-loaded", start);
})();
