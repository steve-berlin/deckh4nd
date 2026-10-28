# DECKH4ND

Minimal YouTube-to-audio web service in pure Python. Paste a link, pick a format, and the server downloads the audio with `yt-dlp`. Finished files are listed at `/downloads` and can be downloaded from there.

No pip packages. No frameworks. Two files: `server.py` and `public/index.html`.

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

## Security

- Links must be `http(s)` on a YouTube host and at most 500 characters. Formats come from a whitelist.
- `yt-dlp` is started with an argument list and `--` before the link. It never runs through a shell.
- At most 2 downloads run at once and 10 can be queued. Beyond that the server answers 503.
- `/downloads/<name>` rejects names that contain `/` or start with `.`, so `../` traversal and hidden files return 404.
- File names on the list page are HTML-escaped.
- Responses carry CSP, `nosniff` and `no-referrer` headers. Idle connections are dropped after 10 s.
- **No HTTPS and no login.** Anyone who can reach the port can queue downloads and fetch files. Fine on a trusted home LAN. Do not expose it to the internet without a reverse proxy (Caddy or nginx) with authentication.

## License

GPL-3.0. See [LICENSE](LICENSE).
