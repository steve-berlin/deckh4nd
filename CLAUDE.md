# CLAUDE.md

Minimal Python stdlib web service. `public/index.html` is a form (YouTube link, format, playlist). `server.py` queues a `yt-dlp` audio download into `DOWNLOAD_DIR` (default `public/downloads`) and serves the finished files at `/downloads`. Optional `tailscale.sh` publishes it to the user's tailnet. Based on github.com/steve-berlin/pyweb-service-template (GPL-3.0). Remote: github.com/steve-berlin/deckh4nd.

## Rules

- Stdlib only. No pip packages, frameworks, JS, or CSS files. External programs: `yt-dlp` and `ffmpeg` only.
- Keep compatibility with Python 3.8 or newer. Target profile: Debian 13, Python 3.13, LAN host.
- Minimalism first: fewest lines, files, and dependencies. Then performance (the page is cached in memory at startup; files are sent with `socket.sendfile`).
- Every line gets ELI11-style comments (the user chose ELI11). No separate `docs/`.
- Form field names in `index.html` must match `FIELDS` in `server.py` (`youtubeUrl`, `format`, `playlist`).
- Start `yt-dlp` only as an argument list with `--` before the link. Never use a shell. Keep the `FORMATS` and `YT_HOSTS` whitelists.
- Keep the limits: `MAX_URL`, `MAX_BODY`, `max_num_fields`, pool `max_workers`, the `slots` semaphore, the subprocess `timeout`, and the handler `timeout`.
- Only `/`, `/downloads`, and `/downloads/<name>` are served. Everything else returns 404. Do not switch to `SimpleHTTPRequestHandler`.
- `/downloads/<name>` must reject names containing `/` or starting with `.`, plus anything that is not a regular file. The list page must `html.escape` names and `quote` links.
- The server never deletes files. The user manages cleanup, the env vars (`HOST`, `PORT`, `DOWNLOAD_DIR`; defaults must stay), and installing yt-dlp and ffmpeg.
- `tailscale.sh` (bash, `set -euo pipefail`, must pass `shellcheck`): configure-only and idempotent. It never installs Tailscale. Use `tailscale serve` only, never `funnel` (that would make the service public). Keep the `server.py` `HOST` default at `127.0.0.1`, since serve proxies to localhost. The user manages the Tailscale account, invites, ACLs, and MagicDNS/HTTPS.
- Known limitations (listed in README): no HTTP Range support; leftover JS mentions in `index.html` are dead code because CSP blocks scripts. If either changes, update the README section.

## Workflow

- Work in the smallest possible steps. Before each one, ask the user and explain it in simple terms.
- After each step: commit (conventional commits), then push to `origin master`.
- Keep `README.md` and this file current. Keep this file under 200 lines and 40 KB; if it grows past that, offer to compress it.

## Test

```sh
PORT=8765 python3 server.py &
curl -sI localhost:8765/                             # 200 + security headers
curl -s localhost:8765/downloads                     # HTML list of files
curl -s -o /dev/null --path-as-is -w '%{http_code}\n' localhost:8765/downloads/../server.py   # 404
curl -s -o /dev/null -w '%{http_code}\n' -d 'youtubeUrl=https://youtu.be/x&format=mp3' localhost:8765/   # 303
kill %1                                              # SIGINT is ignored by background jobs in scripts; use TERM
```
