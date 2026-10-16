#!/usr/bin/env python3
"""Tiny web server: shows a 5-box form and prints what people type into it.

Run it:   python3 server.py
Open:     http://localhost:8000
Settings: HOST and PORT environment variables, e.g. PORT=9000 python3 server.py

Everything here comes with Python itself (the "standard library"),
so there is nothing to install.
"""

# "import" borrows ready-made tools that ship with Python.
import os  # reads environment variables (settings passed in from the shell)
from http import HTTPStatus  # named status codes, e.g. HTTPStatus.NOT_FOUND = 404
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path  # handles file paths the same way on every OS
from urllib.parse import parse_qs  # turns "i1=hi&i2=yo" into {"i1": ["hi"], ...}

# --- Settings -------------------------------------------------------------
# os.environ.get("NAME", default) uses the variable if it is set, else default.
# "0.0.0.0" means "accept visitors from any network card", so other devices
# on your Wi-Fi can open the page. Use HOST=127.0.0.1 for this computer only.
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

FIELDS = ("i1", "i2", "i3", "i4", "i5")  # must match name="..." in index.html
MAX_LEN = 200  # max characters kept per box (same as maxlength in the HTML)
MAX_BODY = 2048  # max bytes we accept per form submission; stops huge uploads

# Read the page ONCE when the server starts and keep it in memory.
# Faster than opening the file on every visit. Path(__file__) is this
# script's own location, so it works no matter which folder you run it from.
PAGE = Path(__file__).with_name("index.html").read_bytes()

# Extra safety rules sent with every reply. Browsers obey them:
SECURITY_HEADERS = {
    # Only allow the form to send data back to us; block scripts, images,
    # styles from anywhere, and stop other sites from embedding this page.
    "Content-Security-Policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
    # Don't let the browser "guess" a file type different from what we say.
    "X-Content-Type-Options": "nosniff",
    # Don't tell other sites which page a visitor came from.
    "Referrer-Policy": "no-referrer",
}


class Handler(BaseHTTPRequestHandler):
    """Decides how to answer each visitor. One copy runs per request."""

    server_version = "pyweb"  # hide exact Python version from visitors
    sys_version = ""
    timeout = 10  # drop visitors who connect but go silent for 10 seconds

    def reply(self, status: HTTPStatus, body: bytes = b"", **headers: str) -> None:
        """Send one complete answer: status line, headers, then body."""
        self.send_response(status)
        for name, value in {**SECURITY_HEADERS, **headers}.items():
            self.send_header(name.replace("_", "-"), value)  # Content_Type -> Content-Type
        self.send_header("Content-Length", str(len(body)))  # body size in bytes
        self.end_headers()  # blank line = "headers finished"
        if self.command != "HEAD":  # HEAD = "headers only, skip the body"
            self.wfile.write(body)  # wfile = the pipe back to the visitor

    def do_GET(self) -> None:
        """Browser asks to SEE a page (typing the address, clicking a link)."""
        # partition("?")[0] ignores anything after "?" in the address.
        if self.path.partition("?")[0] != "/":
            return self.reply(HTTPStatus.NOT_FOUND, b"Not found")
        self.reply(HTTPStatus.OK, PAGE, Content_Type="text/html; charset=utf-8")

    # HEAD = same as GET but without the page itself. Tools like curl -I and
    # uptime checkers use it to ask "are you alive?" cheaply.
    do_HEAD = do_GET

    def do_POST(self) -> None:
        """Browser SENDS data (pressing the form's Send button)."""
        if self.path != "/":
            return self.reply(HTTPStatus.NOT_FOUND, b"Not found")

        # The browser tells us how many bytes it is about to send.
        # Never trust it blindly: it may be missing, not a number, or huge.
        try:
            size = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.reply(HTTPStatus.LENGTH_REQUIRED, b"Length required")
        if not 0 <= size <= MAX_BODY:
            return self.reply(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"Too large")

        # rfile = the pipe from the visitor. Read exactly `size` bytes,
        # turn bytes into text, then split "i1=a&i2=b" into a dictionary.
        # keep_blank_values=True keeps empty boxes so all 5 always print.
        body = self.rfile.read(size).decode("utf-8", errors="replace")
        # max_num_fields makes parse_qs refuse (ValueError) more than 5 boxes.
        try:
            form = parse_qs(body, keep_blank_values=True, max_num_fields=len(FIELDS))
        except ValueError:
            return self.reply(HTTPStatus.BAD_REQUEST, b"Too many fields")

        # THE ECHO: build one line and print it on the host.
        # form.get(f, [""])[0] = first value for that box ("" if missing).
        # [:MAX_LEN] cuts it to 200 characters.
        # !r prints it in quotes with invisible characters shown as codes
        # (Enter becomes \n). Without that, someone could type a fake extra
        # line into your output or send codes that mess up your terminal.
        # Building the whole line first means two visitors pressing Send at
        # the same moment can't get their words mixed together.
        # flush=True prints immediately instead of waiting in a buffer.
        line = " | ".join(f"{f}={form.get(f, [''])[0][:MAX_LEN]!r}" for f in FIELDS)
        print(line, flush=True)

        # Post/Redirect/Get: send the browser back to the empty form with
        # "303 See Other". Pressing refresh won't send the same data twice.
        self.reply(HTTPStatus.SEE_OTHER, Location="/")


# This block only runs when you start the file directly (python3 server.py),
# not when another Python file imports it.
if __name__ == "__main__":
    # ThreadingHTTPServer serves many visitors at once (one thread each).
    # "with" makes sure the network port is released when we stop.
    with ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        print(f"Serving on http://{HOST}:{PORT}  (Ctrl+C to stop)", flush=True)
        try:
            httpd.serve_forever()  # wait for visitors, forever
        except KeyboardInterrupt:  # Ctrl+C pressed
            print("\nStopped.")
