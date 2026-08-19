#!/usr/bin/env python3
import json
import os
import platform
import socket
import subprocess
import time
from datetime import datetime, timezone

import psutil
from pypresence import Presence
from pypresence.exceptions import DiscordNotFound, InvalidID

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_cmd(cmd, timeout=3):
    try:
        return subprocess.check_output(
            cmd, text=True, stderr=subprocess.DEVNULL, timeout=timeout
        ).strip()
    except Exception:
        return ""


def get_os_name():
    try:
        data = {}
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.rstrip().split("=", 1)
                    data[k] = v.strip('"')
        return data.get("PRETTY_NAME", platform.platform())
    except Exception:
        return platform.platform()


def get_gpu():
    out = run_cmd([
        "nvidia-smi",
        "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ])
    if not out:
        return None
    parts = [x.strip() for x in out.splitlines()[0].split(",")]
    if len(parts) != 5:
        return None
    return {
        "name": parts[0],
        "temp": parts[1],
        "util": parts[2],
        "vram_used": parts[3],
        "vram_total": parts[4],
    }


def get_prime():
    return run_cmd(["prime-select", "query"]) or "unknown"


def get_session():
    return (
        os.environ.get("XDG_SESSION_TYPE", "unknown"),
        os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
    )


def get_uptime():
    seconds = int(time.time() - psutil.boot_time())
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def service_active(name):
    if not name:
        return False
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=2,
    )
    return result.returncode == 0


def get_health(cfg):
    services = cfg["presence"].get("health_services", [])
    active = []
    failed = []
    for item in services:
        name = item.get("name", "")
        label = item.get("label", name)
        if service_active(name):
            active.append(label)
        else:
            failed.append(label)

    # Only services explicitly configured affect health.
    if failed:
        return "warning", active, failed
    return "healthy", active, failed


def build_values(cfg):
    cpu = psutil.cpu_percent(interval=0.15)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    freq = psutil.cpu_freq()
    gpu = get_gpu()
    session, desktop = get_session()
    health, active_services, failed_services = get_health(cfg)

    return {
        "hostname": socket.gethostname(),
        "os": get_os_name(),
        "kernel": platform.release(),
        "cpu": f"{cpu:.0f}%",
        "cpu_freq": f"{freq.current / 1000:.1f} GHz" if freq else "N/A",
        "ram_used": f"{mem.used / 1024**3:.1f}",
        "ram_total": f"{mem.total / 1024**3:.1f}",
        "ram_percent": f"{mem.percent:.0f}%",
        "disk_percent": f"{disk.percent:.0f}%",
        "uptime": get_uptime(),
        "gpu": gpu["name"] if gpu else "NVIDIA unavailable",
        "gpu_short": "GTX 1650" if gpu and "GTX 1650" in gpu["name"] else (gpu["name"] if gpu else "NVIDIA"),
        "gpu_temp": f'{gpu["temp"]}°C' if gpu else "N/A",
        "gpu_util": f'{gpu["util"]}%' if gpu else "N/A",
        "vram_used": gpu["vram_used"] if gpu else "N/A",
        "vram_total": gpu["vram_total"] if gpu else "N/A",
        "prime": get_prime(),
        "session": session,
        "desktop": desktop,
        "health": health,
        "health_icon": {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}[health],
        "active_services": active_services,
        "failed_services": failed_services,
    }


def format_line(template, values):
    try:
        return template.format(**values)[:128]
    except KeyError as exc:
        return f"Config error: unknown placeholder {exc}"[:128]


def get_screen(cfg, values, index):
    screens = cfg["presence"].get("screens", [])
    if not screens:
        screens = [
            {
                "details": "{health_icon} {os} • {session}",
                "state": "CPU {cpu} • RAM {ram_percent} • Disk {disk_percent}",
            },
            {
                "details": "🎮 {gpu_short} • {gpu_temp} • GPU {gpu_util}",
                "state": "VRAM {vram_used}/{vram_total} MB • PRIME {prime}",
            },
            {
                "details": "⚙️ Kernel {kernel}",
                "state": "{desktop} • {prime} • Uptime {uptime}",
            },
        ]
    return screens[index % len(screens)]


def build_presence(cfg, values, index):
    screen = get_screen(cfg, values, index)
    activity = {
        "details": format_line(screen["details"], values),
        "state": format_line(screen["state"], values),
        "start": int(psutil.boot_time()),
    }

    assets = cfg["presence"].get("assets", {})
    if assets.get("large_image"):
        activity["large_image"] = assets["large_image"]
    if assets.get("large_text"):
        activity["large_text"] = format_line(assets["large_text"], values)
    if assets.get("small_image"):
        small = assets["small_image"]
        if small == "{health_image}":
            small = f"status_{values['health']}"
        activity["small_image"] = small
    if assets.get("small_text"):
        activity["small_text"] = format_line(assets["small_text"], values)

    buttons = cfg["presence"].get("buttons", [])
    if buttons:
        activity["buttons"] = buttons[:2]

    return activity


def main():
    cfg = load_config()
    client_id = str(cfg["discord"]["application_id"])

    if client_id == "PUT_YOUR_DISCORD_APPLICATION_ID_HERE":
        raise SystemExit("Set discord.application_id in config.json first.")

    while True:
        rpc = None
        try:
            rpc = Presence(client_id)
            rpc.connect()
            print("Connected to Discord IPC.", flush=True)

            index = 0
            while True:
                cfg = load_config()
                interval = max(10, int(cfg["discord"].get("update_interval", 10)))
                rotate = bool(cfg["presence"].get("rotate_screens", True))
                values = build_values(cfg)

                activity = build_presence(cfg, values, index)
                rpc.update(**activity)

                print(
                    datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                    activity["details"],
                    "|",
                    activity["state"],
                    flush=True,
                )

                index += 1 if rotate else 0
                time.sleep(interval)

        except (DiscordNotFound, FileNotFoundError, ConnectionError, BrokenPipeError):
            print("Discord desktop client is not available; retrying in 15s.", flush=True)
            time.sleep(15)
        except InvalidID:
            print("Invalid Discord Application ID.", flush=True)
            time.sleep(30)
        except Exception as exc:
            print(f"RPC error: {type(exc).__name__}: {exc}", flush=True)
            time.sleep(15)
        finally:
            try:
                if rpc:
                    rpc.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
