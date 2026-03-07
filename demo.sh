#!/usr/bin/env bash
# Start KnowledgeOS demo environment.
# Usage: ./demo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Copy env file if not already present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit it to add GEMINI_API_KEY / STRIPE_SECRET_KEY."
fi

echo "Starting KnowledgeOS..."
docker compose -f docker-compose.dev.yml up -d --build

echo "Waiting for services to be healthy..."
sleep 30

echo "Running seed data..."
docker compose -f docker-compose.dev.yml --profile seed up seed

echo ""
echo "==================================="
echo "  KnowledgeOS is ready!"
echo ""
echo "  App : http://localhost:3001"
echo "  API : http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo ""
echo "  Demo credentials:"
echo "    demo@acme.com / demo123"
echo "==================================="
