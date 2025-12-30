#!/usr/bin/env bash
set -euo pipefail
docker compose -f docker-compose.dev.yml up --build -d
echo "✓ dev-api on http://localhost:5175 (Bearer dev)"
