#!/usr/bin/env bash
# Mac-only: create a locally-trusted HTTPS cert so a tablet on the LAN gets a secure
# context (camera + microphone need https off `localhost`). Uses mkcert — a tiny local
# CA, no public/internet certificate, which fits Buddy's local-first privacy stance.
#
#   brew install mkcert nss   # one-time (nss = Firefox trust, optional)
#   ./scripts/make_cert.sh
#
# Then trust the CA on the iPad: AirDrop the file printed by `mkcert -CAROOT`
# (rootCA.pem), open it, install the profile, and enable it under
# Settings → General → About → Certificate Trust Settings.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert not found. Install it first:  brew install mkcert nss" >&2
  exit 1
fi

mkdir -p certs
mkcert -install  # create + trust the local CA on this Mac

# Cover localhost and this Mac's LAN identity so both the desk and the iPad work.
IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
HOST="$(hostname)"

mkcert -cert-file certs/buddy.pem -key-file certs/buddy-key.pem \
  localhost 127.0.0.1 ::1 "$HOST" ${IP:+"$IP"}

echo
echo "==> Wrote certs/buddy.pem + certs/buddy-key.pem"
[ -n "$IP" ] && echo "    LAN address: https://$IP:8765/app/   (parent app: /parent/)"
echo "    Run with TLS:  ./scripts/run_mac.sh   (auto-detects ./certs/)"
echo "    iPad: trust the CA at  $(mkcert -CAROOT)/rootCA.pem"
