#!/usr/bin/env bash
set -euxo pipefail

APP_DIR="/srv/panel"          # <— ścieżka do Twojej aplikacji
SERVICE="panel.service"       # <— nazwa usługi w systemd (zmień na swoją)

cd "$APP_DIR"

# Upewnij się, że to repo i ma remote do GitHuba po SSH:
git fetch --all
git reset --hard origin/main   # checkout dokładnie HEAD z main

# Virtualenv + zależności
python3 -m venv .venv || true
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# Restart aplikacji (jedno z poniższych – wybierz właściwe)
sudo systemctl restart "$SERVICE"           # jeżeli masz systemd + sudo NOPASSWD
# lub: systemctl --user restart "$SERVICE"
# lub (Streamlit bez systemd): pkill -f "streamlit run" || true; nohup .venv/bin/streamlit run admin_dashboard.py --server.port 8501 --server.headless true >/tmp/streamlit.log 2>&1 &
