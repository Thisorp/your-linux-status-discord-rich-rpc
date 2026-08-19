# Linux Discord Rich Presence v2

A Linux desktop daemon that publishes a cleaner, rotating system dashboard to Discord Rich Presence.

## What changed in v2

Discord Rich Presence only gives you a small number of text fields. Instead of cramming CPU, RAM, GPU, VRAM, kernel and uptime into one long line, v2 rotates several compact views every 10 seconds:

1. **System**
   - Ubuntu / session
   - CPU
   - RAM
   - Disk

2. **GPU**
   - NVIDIA GPU
   - temperature
   - utilization
   - VRAM
   - PRIME mode

3. **Kernel**
   - kernel
   - desktop/session
   - CPU frequency
   - uptime

4. **Health**
   - health indicator
   - PRIME
   - RAM
   - GPU temperature

Discord renders `details` and `state` as the main two activity lines. Custom assets can provide the large and small images, and Discord supports up to two custom buttons. See the official Discord activity documentation for the field mapping and buttons. 

## Upgrade your existing installation

This release is safe to install over the previous project: `install.sh` does **not overwrite an existing config.json**.

From this project directory:

```bash
chmod +x install.sh upgrade.sh
./upgrade.sh
```

Then check:

```bash
systemctl --user status linux-discord-rpc --no-pager
journalctl --user -u linux-discord-rpc -f
```

## Configure

Edit:

```bash
nano ~/.local/share/linux-discord-rpc/config.json
```

The most important setting is:

```json
"application_id": "YOUR_DISCORD_APPLICATION_ID"
```

Do not paste your Discord token here. Rich Presence uses the local Discord client IPC connection; this project only needs your Application ID.

## Add images to Discord

Open the Discord Developer Portal:

https://discord.com/developers/applications

1. Select your application.
2. Open the **Rich Presence** section.
3. Find the application's **Art Assets** area.
4. Upload your images.
5. Give each uploaded image a short **asset key**.
6. Save the changes.
7. Put those exact asset keys in `config.json`.

Discord's current documentation says activity assets can use the unique identifier of an image uploaded to the application's Rich Presence page. 

### Recommended assets

Use these keys:

```text
ubuntu
status_healthy
status_warning
status_critical
nvidia
```

Recommended purpose:

| Asset key | Purpose |
|---|---|
| `ubuntu` | Large Ubuntu/Linux workstation image |
| `status_healthy` | Green healthy status icon |
| `status_warning` | Yellow warning status icon |
| `status_critical` | Red critical status icon |
| `nvidia` | GTX/NVIDIA small icon |

You can use your own artwork. Square PNG/WebP images work well for the large/small activity art.

### After uploading

Set:

```json
"assets": {
  "large_image": "ubuntu",
  "large_text": "Ubuntu 26.04 LTS",
  "small_image": "{health_image}",
  "small_text": "{health_icon} System {health}"
}
```

`{health_image}` is handled by the project and becomes:

```text
status_healthy
status_warning
status_critical
```

If you have not uploaded the assets yet, temporarily use:

```json
"large_image": "",
"small_image": ""
```

Then upload the assets and add the keys later.

## Recommended Discord Application setup

For a cleaner Discord card:

**Application Name**

```text
Linux Workstation
```


The application name is the title Discord displays for the activity. The Rich Presence activity documentation explains that the application/game name supplies the first activity line, while `details` and `state` control the following activity lines. 

Also set a good **application icon** in the application settings. This is useful as the fallback identity/icon when custom activity art is not available.

## Recommended config for your Ubuntu 26.04 laptop

Start with:

```json
{
  "discord": {
    "application_id": "YOUR_APPLICATION_ID",
    "update_interval": 10
  },
  "presence": {
    "rotate_screens": true,
    "assets": {
      "large_image": "ubuntu",
      "large_text": "Ubuntu 26.04 LTS",
      "small_image": "{health_image}",
      "small_text": "{health_icon} System {health}"
    },
    "screens": [
      {
        "details": "{health_icon} Ubuntu 26.04 LTS • {session}",
        "state": "CPU {cpu} • RAM {ram_percent} • Disk {disk_percent}"
      },
      {
        "details": "🎮 {gpu_short} • {gpu_temp} • GPU {gpu_util}",
        "state": "VRAM {vram_used}/{vram_total} MB • PRIME {prime}"
      },
      {
        "details": "⚙️ Kernel {kernel} • {desktop}",
        "state": "CPU {cpu} • {cpu_freq} • Uptime {uptime}"
      },
      {
        "details": "{health_icon} System {health} • {prime}",
        "state": "RAM {ram_used}/{ram_total} GB • {gpu_temp} GPU"
      }
    ],
    "health_services": [],
    "buttons": []
  }
}
```

## Add service health

You can optionally make configured systemd services affect the health indicator.

Example:

```json
"health_services": [
  {
    "name": "docker.service",
    "label": "Docker"
  },
  {
    "name": "tailscaled.service",
    "label": "Tailscale"
  },
  {
    "name": "nbfc_service.service",
    "label": "NBFC"
  }
]
```

If all configured services are active:

```text
🟢 System healthy
```

If one is inactive:

```text
🟡 System warning
```

Only services you explicitly put in `health_services` are checked.

## Buttons

Discord supports up to two custom Rich Presence buttons. They open URLs in the user's browser.

Example:

```json
"buttons": [
  {
    "label": "Grafana",
    "url": "https://example.com"
  },
  {
    "label": "GitHub",
    "url": "https://github.com"
  }
]
```

Do not put private LAN addresses here unless you intentionally want them exposed in your Discord activity.

## Useful placeholders

```text
{hostname}
{os}
{kernel}
{cpu}
{cpu_freq}
{ram_used}
{ram_total}
{ram_percent}
{disk_percent}
{uptime}
{gpu}
{gpu_short}
{gpu_temp}
{gpu_util}
{vram_used}
{vram_total}
{prime}
{session}
{desktop}
{health}
{health_icon}
```

## Service commands

Restart:

```bash
systemctl --user restart linux-discord-rpc
```

Status:

```bash
systemctl --user status linux-discord-rpc --no-pager
```

Live logs:

```bash
journalctl --user -u linux-discord-rpc -f
```

Disable:

```bash
systemctl --user disable --now linux-discord-rpc
```

Enable:

```bash
systemctl --user enable --now linux-discord-rpc
```

## Notes about Discord layout

Rich Presence is intentionally compact. Discord's activity model exposes the application name plus `details` and `state` as the main textual fields, so a dashboard with ten metrics cannot be displayed as ten separate rows. v2 therefore rotates concise screens instead of truncating one giant line.

Custom assets are the main way to make the card visually distinctive.

## Security

The daemon reads local system metrics and communicates with the locally running Discord desktop client. It does not open a listening network port.

Avoid putting private IP addresses, usernames, internal URLs, secrets, or credentials into activity text/buttons.
