#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║               TRADINGBOT V5 - QUICK DEPLOY (One-Liner)                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: 
#   curl -sSL https://raw.githubusercontent.com/omario75013/tradingbot-v5/main/quick_deploy.sh | sudo bash
#
# Ou avec paramètres:
#   curl -sSL https://raw.githubusercontent.com/omario75013/tradingbot-v5/main/quick_deploy.sh | sudo bash -s -- --with-ssl

set -e

REPO="https://github.com/omario75013/tradingbot-v5.git"
INSTALL_DIR="/opt/tradingbot-v5"

echo "🚀 TradingBot V5 - Quick Deploy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Exécutez avec sudo"
    exit 1
fi

# Install Docker if needed
if ! command -v docker &> /dev/null; then
    echo "📦 Installation de Docker..."
    curl -fsSL https://get.docker.com | sh
fi

# Clone or update repo
if [ -d "$INSTALL_DIR" ]; then
    echo "🔄 Mise à jour du repository..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "📥 Clonage du repository..."
    git clone "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create .env if not exists
if [ ! -f ".env" ]; then
    cp .env.template .env
    echo "⚠️  Éditez .env avec vos clés API: nano $INSTALL_DIR/.env"
fi

# Create directories
mkdir -p logs models/current models/archive data grafana/provisioning/datasources grafana/provisioning/dashboards

# Setup Grafana
cat > grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# Start services
echo "🐳 Démarrage des services Docker..."
docker compose pull
docker compose up -d

# Show status
echo ""
echo "✅ Déploiement terminé!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
echo "📊 Grafana: http://$IP:3000 (admin/tradingbot2024)"
echo "📁 Config:  $INSTALL_DIR/.env"
echo ""
echo "⚡ Commandes:"
echo "   Logs:    cd $INSTALL_DIR && docker compose logs -f tradingbot"
echo "   Restart: cd $INSTALL_DIR && docker compose restart"
echo "   Stop:    cd $INSTALL_DIR && docker compose down"
