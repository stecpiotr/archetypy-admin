#!/usr/bin/env bash
set -euxo pipefail

echo "== deploy.sh =="
echo "whoami: $(whoami)"
echo "host: $(hostname)"

# TU wstawisz właściwe komendy deployu (restart usługi, docker compose itp.)
# Na próbę zostawmy tylko znacznik:
date | tee /home/archetypy/last_deploy.txt

echo "DEPLOY OK"
