#!/usr/bin/env bash
# Start ngrok tunnel for local webhook development.
#
# Prerequisites:
#   1. Install ngrok: https://ngrok.com/download
#   2. Authenticate: ngrok config add-authtoken <token>
#   3. Start the runtime: uvicorn runtime.app:app --reload --port 8000
#
# Usage:
#   ./scripts/ngrok_dev.sh [port]
#
# Default port: 8000
# Output: Public HTTPS URL to paste into Notion webhook subscription.

set -euo pipefail

PORT="${1:-8000}"

echo "=== AuDHD Agents: ngrok Development Tunnel ==="
echo ""
echo "Starting ngrok tunnel to localhost:${PORT}..."
echo "Copy the HTTPS URL below into Notion's webhook subscription form."
echo ""
echo "Endpoints available:"
echo "  <ngrok-url>/webhooks/notion    Notion webhook receiver"
echo "  <ngrok-url>/webhooks/test      Echo endpoint (staging)"
echo "  <ngrok-url>/healthz            Health check"
echo "  <ngrok-url>/readyz             Readiness check"
echo "  <ngrok-url>/execute            Skill execution"
echo ""
echo "Press Ctrl+C to stop."
echo ""

ngrok http "${PORT}" --log stdout
