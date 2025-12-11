import time
import threading
import platform
import subprocess
import json
from collections import defaultdict

from flask import Flask, render_template, jsonify
import psutil
import GPUtil  # safe if not available GPUtil will still import if installed

app = Flask(__name__)

lock = threading.Lock()

# store previous counters to calculate rates
_prev = {
    "net": None,     # psutil.net_io_counters()
    "disk": None,    # psutil.disk_io_counters()
    "ts": None       # timestamp
}


def safe_gpu_info():
    """Try GPUtil first. If no GPUs found, try nvidia-smi as a fallback, else return None."""
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            return {
                "name": gpu.name,
                "load_percent": round(gpu.load * 100, 1),
                "memory_used_mb": round(gpu.memoryUsed, 1),
                "memory_total_mb": round(gpu.memoryTotal, 1),
                "temperature_c": gpu.temperature if hasattr(gpu, "temperature") else None
            }
    except Exception:
        pass

    # fallback to nvidia-smi (if NVIDIA)
    try:
        p = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=1)
        if p.returncode == 0 and p.stdout.strip():
            # CSV: name, util%, mem.used, mem.total, temp
            parts = [x.strip() for x in p.stdout.split(",")]
            if len(parts) >= 5:
                return {
                    "name": parts[0],
                    "load_percent": float(parts[1]),
                    "memory_used_mb": float(parts[2]),
                    "memory_total_mb": float(parts[3]),
                    "temperature_c": float(parts[4]),
                }
    except Exception:
        pass

    return None


def get_top_processes(n=5):
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            mem_mb = info["memory_info"].rss / (1024 * 1024) if info.get("memory_info") else 0
            procs.append({
                "pid": info.get("pid"),
                "name": info.get("name") or "",
                "cpu_percent": round(info.get("cpu_percent") or 0, 1),
                "memory_mb": round(mem_mb, 1)
            })
        except Exception:
            continue

    # sort and return top by cpu
    procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
    return procs[:n]


def bytes_to_human(n):
    # simple helper
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < step:
            return f"{n:.1f} {unit}"
        n /= step
    return f"{n:.1f} PB"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def stats():
    with lock:
        now = time.time()
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        per_core = psutil.cpu_percent(interval=0.0, percpu=True)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_current = round(cpu_freq.current / 1000.0, 2) if cpu_freq else None  # MHz -> GHz

        # Memory
        vm = psutil.virtual_memory()
        mem_total = vm.total
        mem_used = vm.used
        mem_free = vm.available
        mem_percent = vm.percent

        # Disk (usage)
        disk = psutil.disk_usage('/')
        disk_total = disk.total
        disk_used = disk.used
        disk_free = disk.free
        disk_percent = disk.percent

        # Disk IO and Network IO rates (bytes/sec) - compute from previous counters
        net_counters = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()

        prev = _prev.get("net")
        prev_disk = _prev.get("disk")
        prev_ts = _prev.get("ts")
        delta_t = now - prev_ts if prev_ts else None

        upload_bps = None
        download_bps = None
        read_bps = None
        write_bps = None

        if prev and prev_ts and delta_t and delta_t > 0:
            upload_bps = (net_counters.bytes_sent - prev.bytes_sent) / delta_t
            download_bps = (net_counters.bytes_recv - prev.bytes_recv) / delta_t

        if prev_disk and prev_ts and delta_t and delta_t > 0:
            read_bps = (disk_io.read_bytes - prev_disk.read_bytes) / delta_t
            write_bps = (disk_io.write_bytes - prev_disk.write_bytes) / delta_t

        # update previous
        _prev["net"] = net_counters
        _prev["disk"] = disk_io
        _prev["ts"] = now

        # Network interfaces summary
        net_if = {}
        try:
            pernic = psutil.net_io_counters(pernic=True)
            for k, v in pernic.items():
                net_if[k] = {
                    "bytes_sent": v.bytes_sent,
                    "bytes_recv": v.bytes_recv,
                    "packets_sent": v.packets_sent,
                    "packets_recv": v.packets_recv
                }
        except Exception:
            net_if = {}

        # GPU best-effort
        gpu = safe_gpu_info()

        # Processes
        top_procs = get_top_processes(5)

        # Battery (if available)
        try:
            batt = psutil.sensors_battery()
            battery = None
            if batt:
                battery = {
                    "percent": round(batt.percent, 1),
                    "plugged": bool(batt.power_plugged)
                }
            else:
                battery = None
        except Exception:
            battery = None

        # System info
        sysinfo = {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "boot_time": psutil.boot_time(),
            "uptime_seconds": int(time.time() - psutil.boot_time())
        }

        # Compose JSON response
        payload = {
            "timestamp": now,
            "cpu": {
                "percent": round(cpu_percent, 1),
                "per_core": [round(x, 1) for x in per_core],
                "frequency_ghz": cpu_freq_current,
                "logical_cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False)
            },
            "memory": {
                "total_bytes": mem_total,
                "used_bytes": mem_used,
                "available_bytes": mem_free,
                "percent": mem_percent,
                "human": {
                    "total": bytes_to_human(mem_total),
                    "used": bytes_to_human(mem_used),
                    "available": bytes_to_human(mem_free)
                }
            },
            "disk": {
                "total_bytes": disk_total,
                "used_bytes": disk_used,
                "free_bytes": disk_free,
                "percent": disk_percent,
                "read_bps": read_bps,
                "write_bps": write_bps,
                "human": {
                    "total": bytes_to_human(disk_total),
                    "used": bytes_to_human(disk_used),
                    "free": bytes_to_human(disk_free)
                }
            },
            "network": {
                "interfaces": net_if,
                "upload_bps": upload_bps,
                "download_bps": download_bps,
            },
            "gpu": gpu,
            "processes_top": top_procs,
            "battery": battery,
            "system": sysinfo
        }

        return jsonify(payload)

if __name__ == "__main__":
    # initialize previous counters baseline
    _prev["net"] = psutil.net_io_counters()
    _prev["disk"] = psutil.disk_io_counters()
    _prev["ts"] = time.time()
    app.run(debug=True, host="0.0.0.0", port=5000)
