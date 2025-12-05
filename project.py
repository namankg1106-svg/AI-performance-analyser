import psutil
import time
import datetime

def monitor_resources(interval=1):
    print("=== Resource Usage Monitor Started ===")
    while True:
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=0.5)

        # RAM usage
        ram = psutil.virtual_memory()
        ram_usage = ram.percent
        ram_used = round(ram.used / (1024 ** 3), 2)
        ram_total = round(ram.total / (1024 ** 3), 2)

        # Battery / Power usage
        battery = psutil.sensors_battery()
        if battery:
            power_percent = battery.percent
            power_plugged = battery.power_plugged
        else:
            power_percent = None
            power_plugged = None

        # Display results
        print("\nTime:", datetime.datetime.now().strftime("%H:%M:%S"))
        print(f"CPU Usage: {cpu_usage}%")
        print(f"RAM Usage: {ram_usage}% ({ram_used} GB / {ram_total} GB)")
        
        if battery:
            print(f"Battery: {power_percent}%")
            print("Charging: Yes" if power_plugged else "Charging: No")
        else:
            print("Battery info not available.")

        time.sleep(interval)


# Optional: Test batch inference performance
def batch_inference_test(batch_size=1000000):
    print("\nRunning batch performance test...")
    start = time.time()

    # Dummy heavy operation
    result = sum(range(batch_size))

    end = time.time()
    print(f"Batch Size: {batch_size}")
    print(f"Time Taken: {round(end - start, 4)} seconds")


# Run the monitor
if __name__ == "__main__":
    # Uncomment this to test batch performance
    # batch_inference_test(5000000)

    monitor_resources(interval=2)  # update every 2 seconds





import tkinter as tk
from tkinter import ttk
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

# ----------------------- Data Lists -------------------------
cpu_data = []
ram_data = []
time_data = []

# ----------------------- Update Function --------------------
def update_stats(i):
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    cpu_data.append(cpu)
    ram_data.append(ram)
    time_data.append(len(cpu_data))

    if len(cpu_data) > 50:  # limit graph length
        cpu_data.pop(0)
        ram_data.pop(0)
        time_data.pop(0)

    # Update plots
    cpu_line.set_data(time_data, cpu_data)
    ram_line.set_data(time_data, ram_data)

    ax1.relim()
    ax1.autoscale_view()
    ax2.relim()
    ax2.autoscale_view()

    # Update labels
    cpu_label.config(text=f"CPU Usage: {cpu}%")
    ram_label.config(text=f"RAM Usage: {ram}%")

    batt = psutil.sensors_battery()
    if batt:
        battery_label.config(text=f"Battery: {batt.percent}% — {'Charging' if batt.power_plugged else 'Not Charging'}")
    else:
        battery_label.config(text="Battery Info Not Available")

# ----------------------- UI Setup ---------------------------
root = tk.Tk()
root.title("💻 Real-Time System Resource Monitor")
root.geometry("950x600")
root.configure(bg="#1e1e1e")

title = tk.Label(root, text="📊 System Resource Monitor", font=("Segoe UI", 20, "bold"), bg="#1e1e1e", fg="white")
title.pack(pady=10)

# ----- Labels -----
frame = tk.Frame(root, bg="#1e1e1e")
frame.pack()

cpu_label = tk.Label(frame, text="CPU Usage: 0%", font=("Segoe UI", 14), bg="#1e1e1e", fg="cyan")
cpu_label.grid(row=0, column=0, padx=20, pady=10)

ram_label = tk.Label(frame, text="RAM Usage: 0%", font=("Segoe UI", 14), bg="#1e1e1e", fg="orange")
ram_label.grid(row=0, column=1, padx=20, pady=10)

battery_label = tk.Label(frame, text="Battery: Loading...", font=("Segoe UI", 14), bg="#1e1e1e", fg="lightgreen")
battery_label.grid(row=0, column=2, padx=20, pady=10)

# ------------------- Matplotlib Graph -----------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
fig.patch.set_facecolor("#1e1e1e")

# Line placeholders
cpu_line, = ax1.plot([], [], linewidth=2)
ram_line, = ax2.plot([], [], linewidth=2)

# Graph styles
ax1.set_title("CPU Usage %", color="cyan")
ax2.set_title("RAM Usage %", color="orange")

for ax in (ax1, ax2):
    ax.set_facecolor("#2d2d2d")
    ax.tick_params(colors="white")
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.spines['right'].set_color('white')

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

ani = animation.FuncAnimation(fig, update_stats, interval=1000)

root.mainloop()





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
except Exception as e:
    NVML_AVAILABLE = False

# ----------------- Configuration -----------------
MAX_POINTS = 60  # how many historical points to keep (60 => last 60 seconds)
POLL_INTERVAL = 1_000  # ms (1000ms = 1s)

# ----------------- Data buffers -----------------
time_buf = deque(maxlen=MAX_POINTS)

cpu_total_buf = deque(maxlen=MAX_POINTS)
cpu_percore_bufs = []  # list of deques
ram_buf = deque(maxlen=MAX_POINTS)
gpu_util_buf = deque(maxlen=MAX_POINTS)
disk_read_buf = deque(maxlen=MAX_POINTS)
disk_write_buf = deque(maxlen=MAX_POINTS)
net_up_buf = deque(maxlen=MAX_POINTS)
net_down_buf = deque(maxlen=MAX_POINTS)

# Initialize per-core buffers based on number of cores:
NUM_CORES = psutil.cpu_count(logical=True)
for _ in range(NUM_CORES):
    cpu_percore_bufs.append(deque(maxlen=MAX_POINTS))

# For disk & net speed calculation (store previous counters)
_prev_disk = psutil.disk_io_counters()
_prev_net = psutil.net_io_counters()

_start_time = time.time()

# ----------------- Helper functions -----------------
def format_bytes(bytes_num):
    """Return human readable bytes"""
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
        except Exception:
            pass
    # sort by cpu_percent desc
    procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
    return procs[:n]

def get_gpu_info():
    if not NVML_AVAILABLE:
        return None
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # primary GPU
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = None
        power = None
        try:
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except Exception:
            temp = None
        try:
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # milliwatts -> watts
        except Exception:
            power = None

        name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
        return {
            'name': name,
            'gpu_util': util.gpu,          # percent
            'mem_used': mem.used,         # bytes
            'mem_total': mem.total,       # bytes
            'temperature': temp,
            'power_watts': power
        }
    except Exception:
        return None

# ----------------- Polling thread (collect stats) -----------------
_polling = True
def poll_stats_loop():
    global _prev_disk, _prev_net, _polling
    while _polling:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        time_buf.append(ts)

        # CPU
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_total_buf.append(cpu_total)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        for i, val in enumerate(per_core):
            cpu_percore_bufs[i].append(val)

        # RAM
        vm = psutil.virtual_memory()
        ram_buf.append(vm.percent)

        # Disk IO speeds
        disk = psutil.disk_io_counters()
        if _prev_disk:
            read_speed = (disk.read_bytes - _prev_disk.read_bytes) / max(POLL_INTERVAL/1000.0, 0.0001)
            write_speed = (disk.write_bytes - _prev_disk.write_bytes) / max(POLL_INTERVAL/1000.0, 0.0001)
        else:
            read_speed = 0
            write_speed = 0
        disk_read_buf.append(read_speed)
        disk_write_buf.append(write_speed)
        _prev_disk = disk

        # Net speeds
        net = psutil.net_io_counters()
        if _prev_net:
            up_speed = (net.bytes_sent - _prev_net.bytes_sent) / max(POLL_INTERVAL/1000.0, 0.0001)
            down_speed = (net.bytes_recv - _prev_net.bytes_recv) / max(POLL_INTERVAL/1000.0, 0.0001)
        else:
            up_speed = 0
            down_speed = 0
        net_up_buf.append(up_speed)
        net_down_buf.append(down_speed)
        _prev_net = net

        # GPU
        if NVML_AVAILABLE:
            info = get_gpu_info()
            gpu_util_buf.append(info['gpu_util'] if info else 0)
        else:
            gpu_util_buf.append(0)

        time.sleep(POLL_INTERVAL/1000.0)

# ----------------- GUI Setup -----------------
root = tk.Tk()
root.title("Advanced System Monitor — NVIDIA (Windows)")
root.geometry("1100x700")
root.configure(bg="#111214")

# Title
title = tk.Label(root, text="🚀 Advanced System Monitor", font=("Segoe UI", 18, "bold"), fg="white", bg="#111214")
title.pack(pady=6)

top_frame = tk.Frame(root, bg="#111214")
top_frame.pack(fill="x", padx=8)

# Left info panel
info_frame = tk.Frame(top_frame, bg="#111214")
info_frame.pack(side="left", padx=10, pady=6, anchor="n")

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

lbl_topprocs = tk.Label(info_frame, text="Top processes:\n", font=("Segoe UI", 10), fg="white", bg="#111214", justify="left")
lbl_topprocs.pack(anchor="w", pady=(6,0))

# Right: GPU Info
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
lbl_gpu_power = tk.Label(gpu_frame, text="GPU Power: --", font=("Segoe UI", 11), fg="white", bg="#111214")
lbl_gpu_power.pack(anchor="w")

# Add a stop button
def stop_and_exit():
    global _polling
    if messagebox.askyesno("Exit", "Stop monitoring and exit?"):
        _polling = False
        root.after(200, root.destroy)

btn_stop = tk.Button(root, text="❌ Stop & Exit", command=stop_and_exit, bg="#292b2f", fg="white")
btn_stop.pack(pady=6)

# ----------------- Matplotlib figure -----------------
fig = plt.Figure(figsize=(10,6), dpi=90)
fig.patch.set_facecolor('#111214')

ax_cpu = fig.add_subplot(321)
ax_ram = fig.add_subplot(322)
ax_gpu = fig.add_subplot(323)
ax_disk = fig.add_subplot(324)
ax_net = fig.add_subplot(325)
ax_blank = fig.add_subplot(326)  # used for top processes text

# Styling
for ax in [ax_cpu, ax_ram, ax_gpu, ax_disk, ax_net, ax_blank]:
    ax.set_facecolor("#161618")
    for spine in ax.spines.values():
        spine.set_color("white")
    ax.tick_params(colors="white")
ax_blank.axis('off')

cpu_lines = []
# plot per-core lines
x_init = list(range(-MAX_POINTS+1, 1))
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

disk_read_line, = ax_disk.plot([], [], label="Read B/s")
disk_write_line, = ax_disk.plot([], [], label="Write B/s")
ax_disk.set_title("Disk IO (B/s)", color="white")
ax_disk.legend(fontsize='x-small', facecolor='#222222')

net_up_line, = ax_net.plot([], [], label="Upload B/s")
net_down_line, = ax_net.plot([], [], label="Download B/s")
ax_net.set_title("Network (B/s)", color="white")
ax_net.legend(fontsize='x-small', facecolor='#222222')

canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill="both", expand=True, padx=6, pady=6)

# ----------------- Animation update function -----------------
def update_plot(frame):
    # Update labels with very latest values if available
    try:
        # CPU label & freq
        cpu_pct = cpu_total_buf[-1] if cpu_total_buf else 0
        lbl_cpu.config(text=f"CPU: {cpu_pct:.1f} %")
        try:
            freq = psutil.cpu_freq()
            if freq:
                lbl_freq.config(text=f"Freq: {freq.current:.0f} MHz")
        except Exception:
            pass

        # RAM
        ram_pct = ram_buf[-1] if ram_buf else 0
        lbl_ram.config(text=f"RAM: {ram_pct:.1f} %")

        # Disk usage
        disk_usage = psutil.disk_usage(os.path.abspath(os.sep)).percent
        lbl_disk.config(text=f"Disk: {disk_usage:.1f} %")

        # Net (last values)
        up = net_up_buf[-1] if net_up_buf else 0
        down = net_down_buf[-1] if net_down_buf else 0
        lbl_net.config(text=f"Net: up {format_bytes(up)}/s  down {format_bytes(down)}/s")

        # Battery
        batt = psutil.sensors_battery()
        if batt:
            lbl_bat.config(text=f"Battery: {batt.percent:.0f}% — {'Plugged' if batt.power_plugged else 'On Battery'}")
        else:
            lbl_bat.config(text="Battery: N/A")

        # Uptime & top processes
        lbl_uptime.config(text=f"Uptime: {get_uptime()}")
        topp = get_top_processes(6)
        proc_text = "Top processes (by CPU):\n"
        for p in topp:
            proc_text += f"{p.get('name','?')} (pid:{p.get('pid')}) — CPU: {p.get('cpu_percent',0):.1f}%  MEM: {p.get('memory_percent',0):.1f}%\n"
        lbl_topprocs.config(text=proc_text)

        # GPU info
        if NVML_AVAILABLE:
            g = get_gpu_info()
            if g:
                lbl_gpu_name.config(text=f"GPU: {g['name']}")
                lbl_gpu_util.config(text=f"GPU Util: {g['gpu_util']}%")
                lbl_gpu_mem.config(text=f"GPU Mem: {format_bytes(g['mem_used'])} / {format_bytes(g['mem_total'])}")
                lbl_gpu_temp.config(text=f"GPU Temp: {g['temperature']} °C" if g['temperature'] is not None else "GPU Temp: N/A")
                lbl_gpu_power.config(text=f"Power: {g['power_watts']:.1f} W" if g['power_watts'] else "Power: N/A")
        else:
            lbl_gpu_name.config(text="GPU: NVIDIA (NVML not available)")
            lbl_gpu_util.config(text="GPU Util: N/A")
            lbl_gpu_mem.config(text="GPU Mem: N/A")
            lbl_gpu_temp.config(text="GPU Temp: N/A")
            lbl_gpu_power.config(text="GPU Power: N/A")

        # ---------- Plot data ----------
        xs = list(range(-len(cpu_total_buf)+1, 1))
        # CPU total + per-core
        cpu_total_vals = list(cpu_total_buf)
        cpu_lines[0].set_data(xs, cpu_total_vals)
        for i in range(NUM_CORES):
            vals = list(cpu_percore_bufs[i])
            cpu_lines[1 + i].set_data(xs, vals)

        ax_cpu.set_xlim(min(xs or [-MAX_POINTS+1]), 0)

        # RAM
        ram_vals = list(ram_buf)
        ram_line.set_data(xs, ram_vals)
        ax_ram.set_xlim(min(xs or [-MAX_POINTS+1]), 0)

        # GPU
        gpu_vals = list(gpu_util_buf)
        gpu_line.set_data(xs, gpu_vals)
        ax_gpu.set_xlim(min(xs or [-MAX_POINTS+1]), 0)

        # Disk IO
        read_vals = list(disk_read_buf)
        write_vals = list(disk_write_buf)
        disk_read_line.set_data(xs, read_vals)
        disk_write_line.set_data(xs, write_vals)
        ax_disk.set_xlim(min(xs or [-MAX_POINTS+1]), 0)

        # Net IO
        up_vals = list(net_up_buf)
        down_vals = list(net_down_buf)
        net_up_line.set_data(xs, up_vals)
        net_down_line.set_data(xs, down_vals)
        ax_net.set_xlim(min(xs or [-MAX_POINTS+1]), 0)

        # Autoscale y where relevant
        try:
            ax_disk.relim(); ax_disk.autoscale_view()
            ax_net.relim(); ax_net.autoscale_view()
        except Exception:
            pass

        canvas.draw_idle()
    except Exception as e:
        print("Update error:", e)

# Start polling thread
poll_thread = threading.Thread(target=poll_stats_loop, daemon=True)
poll_thread.start()

ani = animation.FuncAnimation(fig, update_plot, interval=POLL_INTERVAL)

# Graceful shutdown on window close
def on_close():
    global _polling
    _polling = False
    try:
        if NVML_AVAILABLE:
            pynvml.nvmlShutdown()
    except Exception:
        pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()


