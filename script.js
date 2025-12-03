// Random real-time performance generator (replace with real backend API if needed)
function getRandomUsage() {
    return Math.floor(Math.random() * 60) + 20;  // 20–80%
}

function update() {
    let cpu = getRandomUsage();
    let ram = getRandomUsage();
    let gpu = getRandomUsage();

    // Update bars
    document.getElementById("cpuBar").style.width = cpu + "%";
    document.getElementById("ramBar").style.width = ram + "%";
    document.getElementById("gpuBar").style.width = gpu + "%";

    // Update text
    document.getElementById("cpuText").innerText = cpu + "%";
    document.getElementById("ramText").innerText = ram + "%";
    document.getElementById("gpuText").innerText = gpu + "%";

    // Update chart
    addPoint(cpu, ram, gpu);
}

setInterval(update, 1000);

// ---------------- Chart.js Graph ----------------
const canvas = document.getElementById("chart");
const ctx = canvas.getContext("2d");

let cpuData = [];
let ramData = [];
let gpuData = [];

function addPoint(cpu, ram, gpu) {
    if (cpuData.length > 30) {
        cpuData.shift();
        ramData.shift();
        gpuData.shift();
    }

    cpuData.push(cpu);
    ramData.push(ram);
    gpuData.push(gpu);

    drawChart();
}

function drawChart() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    drawLine(cpuData, "#ff4757");
    drawLine(ramData, "#1e90ff");
    drawLine(gpuData, "#2ed573");
}

function drawLine(data, color) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;

    data.forEach((point, i) => {
        let x = (i / 30) * canvas.width;
        let y = canvas.height - (point / 100) * canvas.height;

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    ctx.stroke();
}
