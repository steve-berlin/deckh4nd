# DECKH4ND

Minimal YouTube-to-audio web service in pure Python. Paste a link, pick a format, and the server downloads the audio with `yt-dlp`. Finished files are listed at `/downloads` and can be downloaded from there.

No pip packages. No frameworks. Three files: `server.py`, `public/index.html`, and the optional `tailscale.sh`.

## Requirements

- Python 3.8 or newer (target: Debian 13, Python 3.13, LAN host)
- `yt-dlp` and `ffmpeg` on `PATH`:

```sh
sudo apt install yt-dlp ffmpeg     # Debian/Ubuntu; elsewhere use your package manager or pipx
```

## Run

```sh
python3 server.py                          # http://localhost:8000
PORT=9000 python3 server.py                # another port
HOST=0.0.0.0 python3 server.py             # reachable from the whole LAN
DOWNLOAD_DIR=/srv/music python3 server.py  # save and serve from another folder
```

Stop with `Ctrl+C`.

### Defaults

| Variable       | Default                 |
|----------------|-------------------------|
| `HOST`         | `127.0.0.1` (this computer only) |
| `PORT`         | `8000`                  |
| `DOWNLOAD_DIR` | `public/downloads` next to `server.py` (created if missing) |

### Reach from other devices

The default `HOST=127.0.0.1` refuses every other machine. To open the site from a phone or laptop on the same Wi-Fi:

```sh
HOST=0.0.0.0 python3 server.py   # listen on all network interfaces
hostname -I                      # find this machine's LAN IP, e.g. 192.168.1.161
```

Then browse to `http://<LAN IP>:8000` on the other device. If it still won't load, check these in order:

1. **VPN:** many VPNs block incoming LAN traffic. NordVPN: `nordvpn set lan-discovery on`.
2. **Firewall:** with ufw, run `sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp` (adjust the subnet to match your LAN).
3. **Router client isolation** ("AP isolation" or guest networks) stops Wi-Fi devices from reaching each other. Turn it off, or use the main network.

Only do this on a network you trust. See [Security](#security).

### Access from anywhere (Tailscale)

`tailscale.sh` lets devices in your [Tailscale](https://tailscale.com) network ("tailnet") open the service from any network. Nobody outside the tailnet can reach it, and `server.py` keeps its safe `127.0.0.1` default.

On the host, with Tailscale already installed and `server.py` running:

```sh
./tailscale.sh                    # logs in if needed, then publishes port 8000 (or $PORT)
```

It prints an address like `https://<machine>.<tailnet>.ts.net`. Open that on any tailnet device. The setting survives reboots and the script is safe to re-run.

The first run may ask you to turn on **MagicDNS** and **HTTPS certificates** in the Tailscale admin console.

Undo with `sudo tailscale serve reset`.

## Routes

| Method     | Path                | What it does |
|------------|---------------------|--------------|
| GET/HEAD   | `/`                 | The form |
| POST       | `/`                 | Queue a download, then redirect back to `/` |
| GET/HEAD   | `/downloads`        | HTML list of finished files |
| GET/HEAD   | `/downloads/<name>` | Download one file (saved as an attachment) |

Everything else returns 404.

## What you manage

- **Deleting old files** in `DOWNLOAD_DIR`. The server never deletes anything.
- **Settings:** the `HOST`, `PORT` and `DOWNLOAD_DIR` environment variables (defaults above).
- **Installing and updating** `yt-dlp` and `ffmpeg`. YouTube changes often, so keep `yt-dlp` current.
- **Running and stopping** the server.
- **Tailscale** (if used): your account, installing Tailscale on the host, who may access the service (invite users or share the device), ACLs, and MagicDNS + HTTPS in the admin console.

## Security

- Links must be `http(s)` on a YouTube host and at most 500 characters. Formats come from a whitelist.
- `yt-dlp` is started with an argument list and `--` before the link. It never runs through a shell.
- At most 2 downloads run at once and 10 can be queued. Beyond that the server answers 503.
- `/downloads/<name>` rejects names that contain `/` or start with `.`, so `../` traversal and hidden files return 404.
- File names on the list page are HTML-escaped.
- Responses carry CSP, `nosniff` and `no-referrer` headers. Idle connections are dropped after 10 s.
- **No HTTPS and no login.** Anyone who can reach the port can queue downloads and fetch files. Fine on a trusted home LAN. Do not expose it to the internet without a reverse proxy (Caddy or nginx) with authentication.

## Known limitations

- No HTTP Range support: interrupted downloads restart from zero, and browsers can't seek before the file is saved.
- `public/index.html` mentions JavaScript status messages, but the CSP (`default-src 'none'`) blocks all scripts, so none run.

## License

GPL-3.0. See [LICENSE](LICENSE).
