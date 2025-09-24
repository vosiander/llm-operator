#!/bin/sh
set -e

copy_and_update_certs() {
  if [ -d /cert ]; then
    found=0
    for f in /cert/*; do
      [ -f "$f" ] || continue
      found=1
      base=$(basename "$f")
      case "$base" in
        *.crt) cp "$f" "/usr/local/share/ca-certificates/$base" ;;
        *.pem) cp "$f" "/usr/local/share/ca-certificates/${base%.pem}.crt" ;;
        *) cp "$f" "/usr/local/share/ca-certificates/$base.crt" ;;
      esac
    done
    if [ "$found" = "1" ]; then
      update-ca-certificates || true
    fi
  fi
}

if [ "$(id -u)" = "0" ]; then
  copy_and_update_certs
  # Drop privileges to genai
  exec gosu genai "$@"
else
  exec "$@"
fi
