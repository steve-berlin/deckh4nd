# CLAUDE.md

Minimal Python stdlib web service: `index.html` form with 5 inputs, `server.py` prints submissions to stdout. Template repo: github.com/steve-berlin/pyweb-service-template (public, GPL-3.0).

## Rules

- Stdlib only. No pip packages, frameworks, JS, or CSS files.
- Keep compatibility with Python 3.8 or newer. Target profile: Debian 13, Python 3.13, LAN host.
- Minimalism first: fewest lines, files, and dependencies. Then performance (the page is cached in memory at startup).
- Every file gets detailed, beginner-friendly comments. No separate `docs/` (the user chose comments over ELI docs).
- Field names `i1`–`i5` in `index.html` must match `FIELDS` in `server.py`.
- The echo must stay a single `print(..., flush=True)` line using `!r`. That escaping blocks log forgery and terminal escape injection. Never use a shell or `subprocess` to echo.
- Keep the limits: `MAX_LEN`, `MAX_BODY`, `max_num_fields`, handler `timeout`.
- Only `/` is served; everything else returns 404. Do not switch to `SimpleHTTPRequestHandler`, which lists files.

## Workflow

- Work in the smallest possible steps. Before each one, ask the user and explain it in simple terms.
- After each step: commit (conventional commits), then push to `origin main`.
- Keep `README.md` and this file current. Keep this file under 200 lines and 40 KB; if it grows past that, offer to compress it.

## Test

```sh
PORT=8765 python3 server.py &
curl -sI localhost:8765/                 # 200 + security headers
curl -s -o /dev/null -w '%{http_code}\n' -d 'i1=a%0Ab' localhost:8765/   # 303, host prints i1='a\nb'
kill %1                                  # SIGINT is ignored by background jobs in scripts; use TERM
```
