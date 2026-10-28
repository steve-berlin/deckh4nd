#!/usr/bin/env python3
"""Tiny web server: a 3-box form that downloads the audio of a YouTube link.

Run it:  python3 server.py   then open http://localhost:8000
(Details about each setting are written right next to that setting below.)
"""

# --- Imports: ready-made tools that ship with Python (nothing to install) ---
import logging  # prints status/error messages with a timestamp
import os  # reads settings (environment variables) passed in from the shell
import subprocess  # starts other programs; we use it to start yt-dlp (must be installed, plus ffmpeg)
import threading  # gives us a "counter with a limit" (used for `slots` below)
from concurrent.futures import ThreadPoolExecutor  # runs jobs in the background
from http import HTTPStatus  # named status codes, e.g. HTTPStatus.NOT_FOUND = 404
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # the web server parts
from pathlib import Path  # handles file/folder paths the same way on every OS
from urllib.parse import parse_qs  # turns "youtubeUrl=a&format=b" into {"youtubeUrl": ["a"], "format": ["b"]}
from urllib.parse import urlparse  # splits a link into parts (scheme, host, ...)

# --- Settings ---
# os.environ.get("NAME", default) uses the setting if you typed one before the command
# (e.g. PORT=9000 python3 server.py), otherwise the default after the comma.
# 127.0.0.1 = only this computer may connect. This page has NO password, so use
# HOST=0.0.0.0 (everyone on your network) only on a network you trust.
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))  # the "door" to listen on; int() turns the text "8000" into a number

# Path(__file__) is this script's own location, so the paths below work no matter
# which folder you started the script from.
BASE = Path(__file__).resolve().parent  # the folder that contains this script
# Where downloads are saved. Default: "public/downloads" next to this script.
DOWNLOADS = Path(os.environ.get("DOWNLOAD_DIR", BASE / "public/downloads"))
DOWNLOADS.mkdir(parents=True, exist_ok=True)  # create that folder if it doesn't exist yet

FIELDS = ("youtubeUrl", "format", "playlist")  # names of the form's boxes; must match name="..." in index.html
MAX_URL = 500  # longest link we accept; longer ones are rejected, not silently cut short
MAX_BODY = 4096  # most bytes we accept per form submission; stops huge uploads

# Whitelists: we ONLY accept values from these sets. Safer than trying to list everything forbidden.
FORMATS = {"mp3", "m4a", "opus", "wav", "flac", "aac", "vorbis"}  # audio formats the visitor may choose
YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}  # allowed link websites

# Read index.html (the form) ONCE at startup and keep it in memory: faster than opening the file on every visit.
PAGE = (BASE / "public/index.html").read_bytes()

# Extra safety rules sent with every reply. Browsers obey them.
HEADERS = {
    # Only allow the form to send data back to us; block scripts/images/styles
    # from anywhere else, and stop other sites from embedding this page.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none';",
    "X-Content-Type-Options": "nosniff",  # don't let the browser "guess" a file type different from what we say
    "Referrer-Policy": "no-referrer",  # don't tell other sites which page a visitor came from
}

# A download can take minutes. If we did it while the browser waited, the page would
# hang, so we hand each download to background workers and answer the browser at once.
pool = ThreadPoolExecutor(max_workers=2)  # at most 2 downloads at the same time
# A "semaphore" is a counter with a limit: 10 tickets. Each queued download takes one
# and gives it back when finished. With none left we answer "busy" instead of piling up work.
slots = threading.BoundedSemaphore(10)
log = logging.getLogger("pyweb")  # our named "message printer"


def download(args):
    """Runs in the background: starts yt-dlp with the given command and logs the result."""
    try:
        # subprocess.run starts the program and waits for it to finish.
        # check=True: raise an error if yt-dlp fails | timeout=600: give up after 10 minutes
        # capture_output + text=True: keep yt-dlp's messages (as text) so we can log them
        subprocess.run(args, check=True, timeout=600, capture_output=True, text=True)
        log.info("Done: %s", args[-1])  # args[-1] is the last item of the command: the link
    except subprocess.CalledProcessError as e:  # yt-dlp ran but failed (bad link, video unavailable...)
        log.error("yt-dlp failed for %s: %s", args[-1], e.stderr[-300:])  # last 300 characters of its complaint
    except Exception as e:  # anything else: timeout, yt-dlp not installed, ...
        log.error("Download error for %s: %r", args[-1], e)
    finally:  # "finally" always runs, success or failure
        slots.release()  # give the ticket back


class Handler(BaseHTTPRequestHandler):
    """Decides how to answer each visitor. A fresh copy handles every request."""

    server_version = "pyweb"  # hides the exact Python version from visitors
    sys_version = ""  # same: hide it completely
    timeout = 10  # drop visitors who connect but go silent for 10 seconds

    def reply(self, status, body=b"", **headers):
        """Send one complete answer: status line, headers, then the body."""
        self.send_response(status)  # the status line, e.g. "200 OK"
        # Merge our safety headers with any extra ones passed in. Python argument names
        # can't contain "-", so Content_Type is turned into Content-Type here.
        for name, value in {**HEADERS, **headers}.items():
            self.send_header(name.replace("_", "-"), value)
        self.send_header("Content-Length", str(len(body)))  # body size in bytes
        self.end_headers()  # a blank line = "headers finished"
        if self.command != "HEAD":  # HEAD means "headers only, skip the body"
            self.wfile.write(body)  # wfile = the pipe back to the visitor

    def do_GET(self):
        """The browser asks to SEE a page (typing the address, clicking a link)."""
        if self.path.partition("?")[0] != "/":  # .partition("?")[0] ignores anything after "?" in the address
            return self.reply(HTTPStatus.NOT_FOUND, b"Not found")  # 404: no such page
        self.reply(HTTPStatus.OK, PAGE, Content_Type="text/html; charset=utf-8")  # 200: here is the form

    # HEAD = same as GET but without the page itself. Tools like "curl -I" and
    # uptime checkers use it to ask "are you alive?" cheaply.
    do_HEAD = do_GET

    def do_POST(self):
        """The browser SENDS data (the visitor pressed the form's button)."""
        if self.path.partition("?")[0] != "/":  # same address check as in do_GET
            return self.reply(HTTPStatus.NOT_FOUND, b"Not found")

        try:  # the browser says how many bytes are coming; never trust it blindly (may be missing or not a number)
            size = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.reply(HTTPStatus.LENGTH_REQUIRED, b"Length required")  # 411
        if not 0 <= size <= MAX_BODY:  # claimed size must be sensible
            return self.reply(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"Too large")  # 413

        try:
            # rfile = the pipe from the visitor: read exactly `size` bytes, turn them into text,
            # then split into a dictionary. keep_blank_values=True keeps empty boxes;
            # max_num_fields makes parse_qs refuse more boxes than we expect (ValueError).
            form = parse_qs(self.rfile.read(size).decode("utf-8", "replace"),
                            keep_blank_values=True, max_num_fields=len(FIELDS))
        except ValueError:
            return self.reply(HTTPStatus.BAD_REQUEST, b"Too many fields")  # 400

        def get(name):
            """Return the text of one box with spaces trimmed; "" if the box is missing."""
            return form.get(name, [""])[0].strip()

        link = get("youtubeUrl")  # box 1: the YouTube link
        fmt = get("format").lower() or "mp3"  # box 2: audio format; empty box -> default "mp3"
        # box 3: playlist. Counts as "yes" only if it holds one of these words (so a checkbox, which sends "on", works too).
        playlist = get("playlist").lower() in {"y", "yes", "on", "true", "1"}

        # Check the link: short enough, starts with http(s), and belongs to YouTube. This also
        # blocks text like "--exec something", which yt-dlp would treat as a dangerous option.
        try:
            url = urlparse(link)  # split the link into parts
            ok = len(link) <= MAX_URL and url.scheme in ("http", "https") and url.hostname in YT_HOSTS
        except ValueError:  # urlparse raises this for malformed links
            ok = False
        if not ok or fmt not in FORMATS:  # also check the format against the whitelist
            return self.reply(HTTPStatus.BAD_REQUEST, b"Invalid YouTube URL or format")  # 400: your input is wrong

        # Take one ticket; blocking=False means "don't wait, answer at once". None left -> ask to retry later.
        if not slots.acquire(blocking=False):
            return self.reply(HTTPStatus.SERVICE_UNAVAILABLE, b"Busy, try later", Retry_After="30")  # 503

        # Hand the job to the background workers. The command is a list, one item per word,
        # so the link can never be mistaken for extra commands by a shell.
        pool.submit(download, [
            "yt-dlp",
            "--verbose",
            "--ignore-config",  # ignore config files that could add unexpected options
            "--yes-playlist" if playlist else "--no-playlist",  # whole playlist, or just one video
            "-f", "bestaudio",  # pick the best audio quality
            "-x",  # extract audio (drop the video)
            "--audio-format", fmt,  # convert to the chosen format
            "-P", str(DOWNLOADS),  # save into the downloads folder
            "--", link,  # "--" = everything after this is a link, never an option
        ])
        log.info("Queued: %s (%s, playlist=%s)", link, fmt, playlist)  # note it in the terminal

        # Post/Redirect/Get: send the browser back to the empty form with "303 See Other".
        # Pressing refresh then won't resubmit the same data.
        self.reply(HTTPStatus.SEE_OTHER, Location="/")


# This block only runs when you start the file directly (python3 server.py),
# not when another Python file imports it.
if __name__ == "__main__":
    # Set up the message printer: time, level (INFO/ERROR), then the message.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # ThreadingHTTPServer answers many visitors at once (one thread each);
    # "with" makes sure the network port is released when we stop.
    with ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        print(f"Serving on http://{HOST}:{PORT}, saving to {DOWNLOADS} (Ctrl+C to stop)", flush=True)
        try:
            httpd.serve_forever()  # wait for visitors, forever
        except KeyboardInterrupt:  # Ctrl+C pressed
            print("\nStopped.")
