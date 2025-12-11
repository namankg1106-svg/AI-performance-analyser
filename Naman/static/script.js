// script.js - fetches /api/stats every 1s, updates UI & charts

const formatBytes = (n) => {
  if (n === null || n === undefined) return "--";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
};

let cpuChart, memChart, gpuChart;
let cpuHistory = [], memHistory = [], gpuHistory = [], fpsDummy = 60;
const MAX_POINTS = 60;

// create line chart helper
function createLine(ctx, label, color, yMax = 100) {
  return new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [{ label, data: [], borderColor: color, backgroundColor: color, fill: true, tension: 0.3 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, max: yMax } },
      plugins: { legend: { display: false } },
      animation: { duration: 300 }
    }
  });
}

function updateChart(chart, value) {
  const labels = chart.data.labels;
  const data = chart.data.datasets[0].data;
  const now = new Date().toLocaleTimeString();

  labels.push(now);
  data.push(value);
  if (labels.length > MAX_POINTS) { labels.shift(); data.shift(); }
  chart.update("none");
}

function updateProcessesTable(procs) {
  const tbody = document.querySelector("#procTable tbody");
  tbody.innerHTML = "";
  procs.forEach(p => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${p.pid}</td><td>${p.name}</td><td>${p.cpu_percent}</td><td>${p.memory_mb}</td>`;
    tbody.appendChild(tr);
  });
}

function analyzeAndShow(payload) {
  const cpu = payload.cpu.percent;
  const ram = payload.memory.percent;
  const gpuLoad = payload.gpu ? payload.gpu.load_percent : null;
  const disk = payload.disk.percent;

  let insights = [];
  let perfLabel = "";
  let perfColor = "";

  // ---------- CPU ----------
  if (cpu < 40) { insights.push("🟢 CPU: Best performance"); perfLabel = "BEST"; perfColor = "#00ff95"; }
  else if (cpu < 60) { insights.push("🟩 CPU: Good"); perfLabel = "GOOD"; perfColor = "#4cffd6"; }
  else if (cpu < 80) { insights.push("🟡 CPU: Moderate load"); perfLabel = "MODERATE"; perfColor = "#ffd447"; }
  else if (cpu < 90) { insights.push("🟠 CPU: High load"); perfLabel = "BAD"; perfColor = "#ff884d"; }
  else { insights.push("🔴 CPU: CRITICAL load!"); perfLabel = "CRITICAL"; perfColor = "#ff3b3b"; }

  // ---------- RAM ----------
  if (ram > 90) insights.push("🔴 RAM is critically full!");
  else if (ram > 75) insights.push("🟠 RAM usage high.");
  else if (ram > 60) insights.push("🟡 RAM rising.");
  else insights.push("🟢 RAM normal.");

  // ---------- GPU ----------
  if (gpuLoad !== null) {
    if (gpuLoad > 85) insights.push("🔥 GPU MAXED OUT – rendering/compute peak.");
    else if (gpuLoad > 60) insights.push("⚡ GPU active.");
    else insights.push("🟢 GPU normal.");
  }

  // ---------- DISK ----------
  if (disk > 90) insights.push("🔴 Disk almost full!");
  else if (disk > 75) insights.push("🟠 Disk usage high.");
  else insights.push("🟢 Disk OK.");

  // ---------- NETWORK ----------
  if (payload.network.upload_bps > 2 * 1024 * 1024)
    insights.push("⬆️ High upload activity detected.");
  if (payload.network.download_bps > 5 * 1024 * 1024)
    insights.push("⬇️ Heavy download activity.");

  // ---------- SET HTML ----------
  document.getElementById("analysisBox").innerHTML =
    `<div style="font-size:1.2rem; font-weight:700; color:${perfColor}; margin-bottom:10px;">
       Performance Status: ${perfLabel}
     </div>` +
    insights.map(s => `<div>${s}</div>`).join("");

  // ---------- OPTIONAL: popup alert on critical load ----------
  if (cpu > 95 || ram > 95) {
    if (!window._alertShown) {
      alert("⚠️ SYSTEM WARNING: Your system is under extreme load!");
      window._alertShown = true;
      setTimeout(() => window._alertShown = false, 5000);
    }
  }
}


async function fetchAndUpdate() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) throw new Error("Network error");
    const payload = await res.json();

    // header meta
    const headerMeta = document.getElementById("headerMeta");
    headerMeta.textContent = `${payload.system.os} • Uptime ${Math.floor(payload.system.uptime_seconds/60)}m`;

    // system info
    const sysinfo = document.getElementById("sysinfoContent");
    sysinfo.innerHTML = `
      <div>Host: ${payload.system.hostname}</div>
      <div>Platform: ${payload.system.platform}</div>
      <div>Processor: ${payload.system.processor || "unknown"}</div>
      <div>Python: ${payload.system.python_version}</div>
    `;

    // CPU
    document.getElementById("cpuPercent").textContent = payload.cpu.percent;
    document.getElementById("cpuFreq").textContent = payload.cpu.frequency_ghz ?? "--";
    document.getElementById("cpuCores").textContent = `${payload.cpu.physical_cores}P/${payload.cpu.logical_cores}L`;
    cpuHistory.push(payload.cpu.percent);
    if (cpuHistory.length > MAX_POINTS) cpuHistory.shift();
    updateChart(cpuChart, payload.cpu.percent);

    // Memory
    document.getElementById("memPercent").textContent = payload.memory.percent;
    document.getElementById("memUsed").textContent = payload.memory.human.used;
    document.getElementById("memTotal").textContent = payload.memory.human.total;
    memHistory.push(payload.memory.percent);
    if (memHistory.length > MAX_POINTS) memHistory.shift();
    updateChart(memChart, payload.memory.percent);

    // GPU
    const gpuContent = document.getElementById("gpuContent");
    if (payload.gpu) {
      gpuContent.innerHTML = `
        <div>${payload.gpu.name} • ${payload.gpu.load_percent}% • ${payload.gpu.temperature_c ?? "--"}°C</div>
        <div>VRAM: ${payload.gpu.memory_used_mb}/${payload.gpu.memory_total_mb} MB</div>
      `;
      gpuHistory.push(payload.gpu.load_percent);
      if (gpuHistory.length > MAX_POINTS) gpuHistory.shift();
      updateChart(gpuChart, payload.gpu.load_percent);
    } else {
      gpuContent.innerHTML = "<div>No GPU detected</div>";
      updateChart(gpuChart, 0);
    }

    // Disk
    document.getElementById("diskUsed").textContent = payload.disk.human.used;
    document.getElementById("diskTotal").textContent = payload.disk.human.total;
    document.getElementById("diskPercent").textContent = payload.disk.percent;
    document.getElementById("diskRead").textContent = payload.disk.read_bps ? formatBytes(Math.round(payload.disk.read_bps)) : "--";
    document.getElementById("diskWrite").textContent = payload.disk.write_bps ? formatBytes(Math.round(payload.disk.write_bps)) : "--";

    // Network
    document.getElementById("netUp").textContent = payload.network.upload_bps ? formatBytes(Math.round(payload.network.upload_bps)) : "--";
    document.getElementById("netDown").textContent = payload.network.download_bps ? formatBytes(Math.round(payload.network.download_bps)) : "--";

    // Processes
    updateProcessesTable(payload.processes_top);

    // Analysis
    analyzeAndShow(payload);

  } catch (err) {
    console.error("fetch error", err);
  } finally {
    // schedule next
    setTimeout(fetchAndUpdate, 1000);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  const cpuCtx = document.getElementById("cpuChart").getContext("2d");
  const memCtx = document.getElementById("memChart").getContext("2d");
  const gpuCtx = document.getElementById("gpuChart").getContext("2d");
  cpuChart = createLine(cpuCtx, "CPU %", "#29b6f6", 100);
  memChart = createLine(memCtx, "Memory %", "#ffb74d", 100);
  gpuChart = createLine(gpuCtx, "GPU %", "#ff5252", 100);

  fetchAndUpdate();
});
