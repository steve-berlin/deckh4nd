# pyweb-service-template

Minimal web service template in pure Python: a page with 5 text inputs, and whatever visitors submit is printed (echoed) on the host's terminal.

No dependencies. No frameworks. Two files: `server.py` and `index.html`.

## Requirements

- Python 3.8 or newer (developed on 3.13, Debian 13)

## Run

```sh
python3 server.py                      # http://localhost:8000
PORT=9000 python3 server.py            # another port
HOST=127.0.0.1 python3 server.py       # this computer only, hidden from the LAN
```

Stop with `Ctrl+C`.

Example host output after one submission:

```
i1='hello' | i2='world' | i3='' | i4='' | i5=''
```

## What you manage

- **Labels:** edit the `Input 1`–`Input 5` text in `index.html`.
- **Field names:** `name="i1"`–`"i5"` in `index.html` must match `FIELDS` in `server.py`.
- **Limits:** `MAX_LEN` (characters per field) and `MAX_BODY` (bytes per submission) in `server.py`.
- **Host and port:** the `HOST` and `PORT` environment variables.
- **Running and stopping** the server.

## Security

- Input is printed with `repr()`, so newlines and terminal escape codes appear as harmless text (`\n`, `\x1b`). It is never passed to a shell.
- Only `/` is served. Every other path returns 404, and no files are listed.
- Each submission is limited to 5 fields, 200 characters each, and 2 KB in total. Idle connections are dropped after 10 s.
- Responses carry CSP, `nosniff` and `no-referrer` headers.
- **No HTTPS and no login.** Fine on a home LAN. Do not expose it to the internet without a reverse proxy (Caddy or nginx) in front of it.

## License

GPL-3.0. See [LICENSE](LICENSE).
