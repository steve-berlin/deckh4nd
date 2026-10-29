#!/usr/bin/env bash
# Publishes DECKH4ND to your Tailscale network ("tailnet"), so devices you have
# invited can open it from any Wi-Fi or mobile network, and nobody else can.
#
# Run it on the machine that runs server.py:  ./tailscale.sh
# Needs Tailscale already installed. Safe to run again: it just sets the same thing again.
# Undo it later with:  sudo tailscale serve reset

# The first line ("#!...") tells the computer to run this file with bash.

# Safety switches: -e stops at the first command that fails, -u treats a typo'd
# variable name as an error, and -o pipefail makes a failure inside "a | b" count too.
set -euo pipefail

# "command -v" looks for the tailscale program. ">/dev/null" hides what it prints.
# If it isn't found ("||" means "otherwise"), print an error to stderr (">&2") and quit with code 1.
command -v tailscale >/dev/null || { echo "error: tailscale not installed: https://tailscale.com/download/linux" >&2; exit 1; }

# "tailscale status" succeeds only when this machine is already connected to your tailnet.
# If it isn't, "tailscale up" connects it, printing a login link to open the first time.
tailscale status >/dev/null 2>&1 || sudo tailscale up

# The main step. Tailscale gives this machine an HTTPS address only tailnet devices can
# reach (https://<machine>.<tailnet>.ts.net) and passes each visit on to server.py at
# 127.0.0.1:PORT. "${PORT:-8000}" uses your PORT setting, or 8000 like server.py does.
# --bg keeps it running in the background, even after a reboot.
sudo tailscale serve --bg "${PORT:-8000}"

# Show what is being served, including the https:// address to open on your devices.
tailscale serve status
