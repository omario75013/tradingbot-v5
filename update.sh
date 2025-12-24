#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║               TRADINGBOT AI V5 - QUICK UPDATE SCRIPT                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

INSTALL_DIR="/opt/tradingbot-v5"

echo "🔄 Mise à jour de TradingBot V5..."
echo ""

cd "$INSTALL_DIR"

# Stop containers
echo "⏹️  Arrêt des containers..."
docker compose down

# Backup .env
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "💾 Backup de .env créé"
fi

# Pull latest
echo "📥 Récupération des mises à jour..."
git fetch origin
git reset --hard origin/main

# Restore .env
if [ -f ".env.backup" ]; then
    mv .env.backup .env
    echo "♻️  .env restauré"
fi

# Rebuild
echo "🔨 Reconstruction des images..."
docker compose build --no-cache

# Start
echo "🚀 Démarrage..."
docker compose up -d

echo ""
echo "✅ Mise à jour terminée!"
echo ""
docker compose ps
