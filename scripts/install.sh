#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Installing systemd service..."
sudo cp "$REPO_DIR/systemd/onto-server.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now onto-server

echo "Installing nginx config..."
sudo cp "$REPO_DIR/nginx/onto.degu.cl.conf" /etc/nginx/sites-available/onto.degu.cl
sudo ln -sf /etc/nginx/sites-available/onto.degu.cl /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "Done. Check status with:"
echo "  sudo systemctl status onto-server"
echo "  curl -s -o /dev/null -w '%{http_code}' http://localhost:3006/"
echo ""
echo "To add HTTPS:"
echo "  sudo certbot --nginx -d onto.degu.cl"
