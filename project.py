"""
Full System Monitor Dashboard for Windows (Python)

Requirements:
  pip install psutil matplotlib pynvml GPUtil

Run:
  python system_monitor_dashboard.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import time
import datetime
import threading
from collections import deque
import platform
import os

# Matplotlib embedding
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

# Try import pynvml (NVIDIA). If missing, GPU features will be disabled.
try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
MAX_POINTS = 60
POLL_INTERVAL = 1_000  # ms

# ---------------------------------------------------------
# Data buffers
# ---------------------------------------------------------
time_buf = deque(maxlen=MAX_POINTS)

cpu_total_buf = deque(maxlen=MAX_POINTS)
cpu_percore_bufs = []
ram_buf = deque(maxlen=MAX_POINTS)
gpu_util_buf = deque(maxlen=MAX_POINTS)
disk_read_buf = deque(maxlen=MAX_POINTS)
disk_write_buf = deque(maxlen=MAX_POINTS)
net_up_buf = deque(maxlen=MAX_POINTS)
net_down_buf = deque(maxlen=MAX_POINTS)

NUM_CORES = psutil.cpu_count(logical=True)
for _ in range(NUM_CORES):
    cpu_percore_bufs.append(deque(maxlen=MAX_POINTS))

_prev_disk = psutil.disk_io_counters()
_prev_net = psutil.net_io_counters()

# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def format_bytes(bytes_num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_num) < 1024.0:
            return f"{bytes_num:3.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"

def get_uptime():
    secs = time.time() - psutil.boot_time()
    return str(datetime.timedelta(seconds=int(secs)))

def get_top_processes(n=5):
    procs = []
    for p in psutil.process_iter(['pid','name','cpu_percent','memory_percent']):
        try:
            procs.append(p.info)
        except:
            pass
    procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
    return procs[:n]

def get_gpu_info():
    if not NVML_AVAILABLE:
        return None
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = None
        power = None
        try:
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except:
            pass
        try:
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
        except:
            pass

        name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
        return {
            'name': name,
            'gpu_util': util.gpu,
            'mem_used': mem.used,
            'mem_total': mem.total,
            'temperature': temp,
            'power_watts': power
        }
    except:
        return None

# ---------------------------------------------------------
# Polling thread
# ---------------------------------------------------------
_polling = True
def poll_stats_loop():
    global _prev_disk, _prev_net, _polling

    while _polling:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        time_buf.append(ts)

        cpu_total_buf.append(psutil.cpu_percent(interval=None))
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        for i, val in enumerate(per_core):
            cpu_percore_bufs[i].append(val)

        vm = psutil.virtual_memory()
        ram_buf.append(vm.percent)

        # Disk IO
        disk = psutil.disk_io_counters()
        if _prev_disk:
            read_speed = (disk.read_bytes - _prev_disk.read_bytes) / (POLL_INTERVAL/1000)
            write_speed = (disk.write_bytes - _prev_disk.write_bytes) / (POLL_INTERVAL/1000)
        else:
            read_speed = write_speed = 0
        disk_read_buf.append(read_speed)
        disk_write_buf.append(write_speed)
        _prev_disk = disk

        # Network
        net = psutil.net_io_counters()
        if _prev_net:
            up_speed = (net.bytes_sent - _prev_net.bytes_sent) / (POLL_INTERVAL/1000)
            down_speed = (net.bytes_recv - _prev_net.bytes_recv) / (POLL_INTERVAL/1000)
        else:
            up_speed = down_speed = 0
        net_up_buf.append(up_speed)
        net_down_buf.append(down_speed)
        _prev_net = net

        # GPU
        if NVML_AVAILABLE:
            gpu = get_gpu_info()
            gpu_util_buf.append(gpu['gpu_util'] if gpu else 0)
        else:
            gpu_util_buf.append(0)

        time.sleep(POLL_INTERVAL/1000)

# ---------------------------------------------------------
# GUI
# ---------------------------------------------------------
root = tk.Tk()
root.title("Advanced System Monitor — Windows")
root.geometry("1180x760")
root.configure(bg="#111214")

title = tk.Label(root, text="🚀 Advanced System Monitor Dashboard", font=("Segoe UI", 18, "bold"),
                 fg="white", bg="#111214")
title.pack(pady=6)

top_frame = tk.Frame(root, bg="#111214")
top_frame.pack(fill="x", padx=8)

# Left Info Panel
info_frame = tk.Frame(top_frame, bg="#111214")
info_frame.pack(side="left", padx=10, anchor="n")

lbl_cpu = tk.Label(info_frame, text="CPU: -- %", font=("Segoe UI", 12), fg="cyan", bg="#111214")
lbl_cpu.pack(anchor="w")
lbl_cores = tk.Label(info_frame, text=f"Cores: {NUM_CORES}", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_cores.pack(anchor="w")
lbl_freq = tk.Label(info_frame, text="Freq: -- MHz", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_freq.pack(anchor="w")
lbl_ram = tk.Label(info_frame, text="RAM: -- %", font=("Segoe UI", 12), fg="orange", bg="#111214")
lbl_ram.pack(anchor="w", pady=(6,0))
lbl_disk = tk.Label(info_frame, text="Disk: -- %", font=("Segoe UI", 11), fg="lightgreen", bg="#111214")
lbl_disk.pack(anchor="w")
lbl_net = tk.Label(info_frame, text="Net: up -- / down --", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_net.pack(anchor="w")
lbl_bat = tk.Label(info_frame, text="Battery: N/A", font=("Segoe UI", 11), fg="lightgrey", bg="#111214")
lbl_bat.pack(anchor="w", pady=(6,0))
lbl_uptime = tk.Label(info_frame, text="Uptime: --", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_uptime.pack(anchor="w")
lbl_topprocs = tk.Label(info_frame, text="Top processes:\n", font=("Segoe UI", 10), fg="white",
                        bg="#111214", justify="left")
lbl_topprocs.pack(anchor="w", pady=(6,0))

# GPU Frame
gpu_frame = tk.Frame(top_frame, bg="#111214")
gpu_frame.pack(side="left", padx=40)

lbl_gpu_name = tk.Label(gpu_frame, text="GPU: (checking...)", font=("Segoe UI", 12), fg="magenta", bg="#111214")
lbl_gpu_name.pack(anchor="w")
lbl_gpu_util = tk.Label(gpu_frame, text="GPU Util: -- %", font=("Segoe UI", 11), fg="magenta", bg="#111214")
lbl_gpu_util.pack(anchor="w")
lbl_gpu_mem = tk.Label(gpu_frame, text="GPU Mem: --", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_gpu_mem.pack(anchor="w")
lbl_gpu_temp = tk.Label(gpu_frame, text="GPU Temp: --", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_gpu_temp.pack(anchor="w")
lbl_gpu_power = tk.Label(gpu_frame, text="Power: --", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_gpu_power.pack(anchor="w")

# Stop Button
def stop_and_exit():
    global _polling
    if messagebox.askyesno("Exit", "Stop monitoring and exit?"):
        _polling = False
        root.after(200, root.destroy)

btn_stop = tk.Button(root, text="❌ Stop & Exit", command=stop_and_exit,
                     bg="#292b2f", fg="white")
btn_stop.pack(pady=6)

# ---------------------------------------------------------
# Matplotlib Figure — NEW CLEAN 2×3 GRID
# ---------------------------------------------------------
fig = plt.Figure(figsize=(10,6), dpi=90)
fig.patch.set_facecolor('#111214')

# <<< FIX: add spacing between subplots to avoid graphs touching >>>
fig.subplots_adjust(hspace=0.40, wspace=0.30)

ax_cpu   = fig.add_subplot(231)
ax_ram   = fig.add_subplot(232)
ax_gpu   = fig.add_subplot(233)
ax_net   = fig.add_subplot(234)
ax_disk  = fig.add_subplot(235)
ax_drive = fig.add_subplot(236)

axes = [ax_cpu, ax_ram, ax_gpu, ax_net, ax_disk, ax_drive]
for ax in axes:
    ax.set_facecolor("#161618")
    for s in ax.spines.values():
        s.set_color("white")
    ax.tick_params(colors="white")

# ---------------------------------------------------------
# Plot lines
# ---------------------------------------------------------
cpu_lines = []
cpu_total_line, = ax_cpu.plot([], [], label="Total", linewidth=2)
cpu_lines.append(cpu_total_line)
for i in range(NUM_CORES):
    line, = ax_cpu.plot([], [], linewidth=1, label=f"Core {i}")
    cpu_lines.append(line)
ax_cpu.set_title("CPU Usage (%)", color="white")
ax_cpu.set_ylim(0, 100)
ax_cpu.legend(loc='upper right', fontsize='x-small', facecolor='#222222')

ram_line, = ax_ram.plot([], [], linewidth=2)
ax_ram.set_title("RAM Usage (%)", color="white")
ax_ram.set_ylim(0, 100)

gpu_line, = ax_gpu.plot([], [], linewidth=2)
ax_gpu.set_title("GPU Utilization (%)", color="white")
ax_gpu.set_ylim(0, 100)

net_up_line, = ax_net.plot([], [], label="Upload B/s")
net_down_line, = ax_net.plot([], [], label="Download B/s")
ax_net.set_title("Network (B/s)", color="white")
ax_net.legend(fontsize='x-small', facecolor='#222222')

disk_read_line, = ax_disk.plot([], [], label="Read B/s")
disk_write_line, = ax_disk.plot([], [], label="Write B/s")
ax_disk.set_title("Disk IO (B/s)", color="white")
ax_disk.legend(fontsize='x-small', facecolor='#222222')

canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill="both", expand=True, padx=6, pady=6)

# ---------------------------------------------------------
# Update function
# ---------------------------------------------------------
def update_plot(_):

    # CPU
    if cpu_total_buf:
        lbl_cpu.config(text=f"CPU: {cpu_total_buf[-1]:.1f} %")

    freq = psutil.cpu_freq()
    if freq:
        lbl_freq.config(text=f"Freq: {freq.current:.0f} MHz")

    # RAM
    if ram_buf:
        lbl_ram.config(text=f"RAM: {ram_buf[-1]:.1f} %")

    # Disk usage
    disk_usage = psutil.disk_usage(os.path.abspath(os.sep)).percent
    lbl_disk.config(text=f"Disk: {disk_usage:.1f} %")

    # Network
    up = net_up_buf[-1] if net_up_buf else 0
    down = net_down_buf[-1] if net_down_buf else 0
    lbl_net.config(text=f"Net: up {format_bytes(up)}/s  down {format_bytes(down)}/s")

    # Battery
    batt = psutil.sensors_battery()
    if batt:
        lbl_bat.config(
            text=f"Battery: {batt.percent}% — {'Plugged' if batt.power_plugged else 'On Battery'}"
        )
    else:
        lbl_bat.config(text="Battery: N/A")

    # Uptime
    lbl_uptime.config(text=f"Uptime: {get_uptime()}")

    # Top processes
    topp = get_top_processes(6)
    proc_text = "Top processes (CPU):\n"
    for p in topp:
        proc_text += f"{p['name']} | CPU: {p['cpu_percent']:.1f}% | MEM: {p['memory_percent']:.1f}%\n"
    lbl_topprocs.config(text=proc_text)

    # GPU
    if NVML_AVAILABLE:
        g = get_gpu_info()
        if g:
            lbl_gpu_name.config(text=f"GPU: {g['name']}")
            lbl_gpu_util.config(text=f"GPU Util: {g['gpu_util']}%")
            lbl_gpu_mem.config(text=f"GPU Mem: {format_bytes(g['mem_used'])} / {format_bytes(g['mem_total'])}")
            lbl_gpu_temp.config(text=f"GPU Temp: {g['temperature']} °C")
            lbl_gpu_power.config(text=f"Power: {g['power_watts']:.1f} W")
    else:
        lbl_gpu_name.config(text="GPU: NVML not available")

    # ---------------------------------------------------
    # Plot data
    # ---------------------------------------------------
    xs = list(range(-len(cpu_total_buf)+1, 1))

    # CPU
    cpu_lines[0].set_data(xs, list(cpu_total_buf))
    for i in range(NUM_CORES):
        cpu_lines[i+1].set_data(xs, list(cpu_percore_bufs[i]))
    ax_cpu.set_xlim(min(xs or [-MAX_POINTS]), 0)

    # RAM
    ram_line.set_data(xs, list(ram_buf))
    ax_ram.set_xlim(min(xs or [-MAX_POINTS]), 0)

    # GPU
    gpu_line.set_data(xs, list(gpu_util_buf))
    ax_gpu.set_xlim(min(xs or [-MAX_POINTS]), 0)

    # NET
    net_up_line.set_data(xs, list(net_up_buf))
    net_down_line.set_data(xs, list(net_down_buf))
    ax_net.set_xlim(min(xs or [-MAX_POINTS]), 0)
    ax_net.relim()
    ax_net.autoscale_view()

    # DISK IO
    disk_read_line.set_data(xs, list(disk_read_buf))
    disk_write_line.set_data(xs, list(disk_write_buf))
    ax_disk.set_xlim(min(xs or [-MAX_POINTS]), 0)
    ax_disk.relim()
    ax_disk.autoscale_view()

    # Disk partition usage (RIGHT BOTTOM PANEL)
    ax_drive.clear()
    ax_drive.set_facecolor("#161618")
    for s in ax_drive.spines.values():
        s.set_color("white")
    ax_drive.tick_params(colors="white")

    ax_drive.bar(["C:\\"], [disk_usage], color="royalblue")
    ax_drive.set_ylim(0, 100)
    ax_drive.set_title("Disk Partition Usage (%)", color="white")
    ax_drive.text(0, disk_usage + 2, f"{disk_usage:.1f}%", color="white")

    canvas.draw_idle()

# ---------------------------------------------------------
# Threads and Animation
# ---------------------------------------------------------
poll_thread = threading.Thread(target=poll_stats_loop, daemon=True)
poll_thread.start()

ani = animation.FuncAnimation(fig, update_plot, interval=POLL_INTERVAL)

def on_close():
    global _polling
    _polling = False
    if NVML_AVAILABLE:
        try:
            pynvml.nvmlShutdown()
        except:
            pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
