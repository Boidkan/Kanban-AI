#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
docker compose up --build -d
echo "App started at http://127.0.0.1:8000"
