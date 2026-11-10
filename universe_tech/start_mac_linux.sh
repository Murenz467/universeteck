#!/usr/bin/env bash
# Run:  bash start_mac_linux.sh   (does everything in the right order, then starts the site)
cd "$(dirname "$0")"
[ -f .env ] || echo "DEBUG=1" > .env
python3 -m pip install -q -r requirements.txt || exit 1
python3 manage.py setup_site || exit 1
python3 manage.py runserver
