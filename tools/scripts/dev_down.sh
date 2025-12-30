#!/usr/bin/env bash
set -euo pipefail
docker compose -f docker-compose.dev.yml down -v
echo "✓ dev-api stopped and volume removed"
