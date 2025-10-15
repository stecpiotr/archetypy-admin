#!/usr/bin/env bash
set -euxo pipefail

# Prosty test: zapisz datę na serwerze w HOME użytkownika archetypy
date > ~/last_deploy.txt

# (tu później dołożymy co ma się faktycznie deployować)
