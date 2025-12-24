#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║               TRADINGBOT AI V5 - DEPLOYMENT SCRIPT FOR HETZNER              ║
# ║                                                                              ║
# ║  Usage: curl -fsSL https://raw.githubusercontent.com/omario75013/           ║
# ║         tradingbot-v5/main/deploy_hetzner.sh | bash                         ║
# ║                                                                              ║
# ║  Ou: chmod +x deploy_hetzner.sh && sudo ./deploy_hetzner.sh                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

REPO_URL="https://github.com/omario75013/tradingbot-v5.git"
INSTALL_DIR="/opt/tradingbot-v5"
SERVICE_NAME="tradingbot-v5"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                              ║"
    echo "║   ████████╗██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗                     ║"
    echo "║   ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝                     ║"
    echo "║      ██║   ██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███╗                    ║"
    echo "║      ██║   ██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║                    ║"
    echo "║      ██║   ██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝                    ║"
    echo "║      ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝                    ║"
    echo "║                                                                              ║"
    echo "║                    ██████╗  ██████╗ ████████╗    ██╗   ██╗███████╗           ║"
    echo "║                    ██╔══██╗██╔═══██╗╚══██╔══╝    ██║   ██║██╔════╝           ║"
    echo "║                    ██████╔╝██║   ██║   ██║       ██║   ██║███████╗           ║"
    echo "║                    ██╔══██╗██║   ██║   ██║       ╚██╗ ██╔╝╚════██║           ║"
    echo "║                    ██████╔╝╚██████╔╝   ██║        ╚████╔╝ ███████║           ║"
    echo "║                    ╚═════╝  ╚═════╝    ╚═╝         ╚═══╝  ╚══════╝           ║"
    echo "║                                                                              ║"
    echo "║                      🚀 AI-POWERED CRYPTO TRADING 🚀                         ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Ce script doit être exécuté en tant que root"
        print_info "Utilisez: sudo $0"
        exit 1
    fi
}

check_system() {
    print_section "📋 VÉRIFICATION DU SYSTÈME"
    
    # Check OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VERSION=$VERSION_ID
        print_step "OS: $OS $VERSION"
    else
        print_warning "OS non détecté, continuons..."
    fi
    
    # Check architecture
    ARCH=$(uname -m)
    print_step "Architecture: $ARCH"
    
    # Check RAM
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    print_step "RAM: ${TOTAL_RAM}MB"
    
    if [ $TOTAL_RAM -lt 2000 ]; then
        print_warning "RAM < 2GB - Performances potentiellement limitées"
    fi
    
    # Check disk space
    DISK_FREE=$(df -h / | awk 'NR==2{print $4}')
    print_step "Espace disque libre: $DISK_FREE"
}

# ══════════════════════════════════════════════════════════════════════════════
# INSTALLATION DES DÉPENDANCES
# ══════════════════════════════════════════════════════════════════════════════

install_dependencies() {
    print_section "📦 INSTALLATION DES DÉPENDANCES"
    
    # Update system
    print_info "Mise à jour du système..."
    apt-get update -qq
    apt-get upgrade -y -qq
    print_step "Système mis à jour"
    
    # Install essentials
    print_info "Installation des paquets essentiels..."
    apt-get install -y -qq \
        curl \
        wget \
        git \
        htop \
        vim \
        nano \
        jq \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        ufw \
        fail2ban
    print_step "Paquets essentiels installés"
}

install_docker() {
    print_section "🐳 INSTALLATION DE DOCKER"
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        print_warning "Docker déjà installé (version $DOCKER_VERSION)"
    else
        print_info "Installation de Docker..."
        
        # Remove old versions
        apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
        
        # Add Docker's official GPG key
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        
        # Add repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
        # Start Docker
        systemctl start docker
        systemctl enable docker
        
        print_step "Docker installé et démarré"
    fi
    
    # Verify Docker
    docker --version
    docker compose version
}

install_python() {
    print_section "🐍 INSTALLATION DE PYTHON"
    
    if command -v python3.11 &> /dev/null; then
        PYTHON_VERSION=$(python3.11 --version | cut -d' ' -f2)
        print_warning "Python 3.11 déjà installé (version $PYTHON_VERSION)"
    else
        print_info "Installation de Python 3.11..."
        add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
        apt-get update -qq
        apt-get install -y -qq python3.11 python3.11-venv python3.11-dev python3-pip 2>/dev/null || \
        apt-get install -y -qq python3 python3-venv python3-dev python3-pip
        print_step "Python installé"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SÉCURITÉ
# ══════════════════════════════════════════════════════════════════════════════

configure_firewall() {
    print_section "🔒 CONFIGURATION DU FIREWALL"
    
    print_info "Configuration UFW..."
    
    # Reset UFW
    ufw --force reset > /dev/null 2>&1
    
    # Default policies
    ufw default deny incoming > /dev/null 2>&1
    ufw default allow outgoing > /dev/null 2>&1
    
    # Allow SSH
    ufw allow 22/tcp comment 'SSH' > /dev/null 2>&1
    
    # Allow Grafana
    ufw allow 3000/tcp comment 'Grafana' > /dev/null 2>&1
    
    # Allow Prometheus
    ufw allow 9090/tcp comment 'Prometheus' > /dev/null 2>&1
    
    # Allow Prometheus metrics
    ufw allow 8000/tcp comment 'TradingBot Metrics' > /dev/null 2>&1
    
    # Enable UFW
    ufw --force enable > /dev/null 2>&1
    
    print_step "Firewall configuré"
}

configure_fail2ban() {
    print_section "🛡️ CONFIGURATION FAIL2BAN"
    
    print_info "Configuration de Fail2Ban..."
    
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400
EOF

    systemctl restart fail2ban
    systemctl enable fail2ban
    
    print_step "Fail2Ban configuré"
}

# ══════════════════════════════════════════════════════════════════════════════
# INSTALLATION DU TRADINGBOT
# ══════════════════════════════════════════════════════════════════════════════

clone_repository() {
    print_section "📥 CLONAGE DU REPOSITORY"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Répertoire existant, mise à jour..."
        cd "$INSTALL_DIR"
        git fetch origin
        git reset --hard origin/main
    else
        print_info "Clonage depuis GitHub..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    print_step "Repository cloné dans $INSTALL_DIR"
}

configure_environment() {
    print_section "⚙️ CONFIGURATION DE L'ENVIRONNEMENT"
    
    cd "$INSTALL_DIR"
    
    # Create .env if not exists
    if [ ! -f ".env" ]; then
        if [ -f ".env.template" ]; then
            cp .env.template .env
            print_step "Fichier .env créé depuis le template"
        else
            print_warning "Template .env non trouvé, création manuelle nécessaire"
        fi
    else
        print_warning "Fichier .env existant conservé"
    fi
    
    # Create directories
    mkdir -p logs models/current models/archive data
    mkdir -p grafana/provisioning/datasources
    mkdir -p grafana/provisioning/dashboards
    print_step "Répertoires créés"
    
    # Set permissions
    [ -f ".env" ] && chmod 600 .env
    print_step "Permissions configurées"
}

setup_grafana_provisioning() {
    print_section "📊 CONFIGURATION GRAFANA"
    
    cd "$INSTALL_DIR"
    
    # Datasource configuration
    cat > grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

    # Dashboard provisioning
    cat > grafana/provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'TradingBot'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
EOF

    print_step "Provisioning Grafana configuré"
}

create_systemd_service() {
    print_section "🔧 CRÉATION DU SERVICE SYSTEMD"
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=TradingBot AI V5 - Crypto Trading Bot
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    print_step "Service systemd créé: $SERVICE_NAME"
}

create_management_scripts() {
    print_section "📝 CRÉATION DES SCRIPTS DE GESTION"
    
    # Start script
    cat > /usr/local/bin/tradingbot-start << 'EOF'
#!/bin/bash
cd /opt/tradingbot-v5
docker compose up -d
echo "✅ TradingBot V5 démarré"
docker compose ps
EOF
    chmod +x /usr/local/bin/tradingbot-start
    
    # Stop script
    cat > /usr/local/bin/tradingbot-stop << 'EOF'
#!/bin/bash
cd /opt/tradingbot-v5
docker compose down
echo "🛑 TradingBot V5 arrêté"
EOF
    chmod +x /usr/local/bin/tradingbot-stop
    
    # Restart script
    cat > /usr/local/bin/tradingbot-restart << 'EOF'
#!/bin/bash
cd /opt/tradingbot-v5
docker compose restart
echo "🔄 TradingBot V5 redémarré"
docker compose ps
EOF
    chmod +x /usr/local/bin/tradingbot-restart
    
    # Logs script
    cat > /usr/local/bin/tradingbot-logs << 'EOF'
#!/bin/bash
cd /opt/tradingbot-v5
docker compose logs -f --tail=100 tradingbot
EOF
    chmod +x /usr/local/bin/tradingbot-logs
    
    # Status script
    cat > /usr/local/bin/tradingbot-status << 'EOF'
#!/bin/bash
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║               TRADINGBOT V5 - STATUS                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
cd /opt/tradingbot-v5
echo "📦 Containers:"
docker compose ps
echo ""
echo "💾 Ressources:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || true
echo ""
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "📊 Métriques: http://${SERVER_IP}:8000/metrics"
echo "📈 Grafana:   http://${SERVER_IP}:3000"
EOF
    chmod +x /usr/local/bin/tradingbot-status
    
    # Update script
    cat > /usr/local/bin/tradingbot-update << 'EOF'
#!/bin/bash
echo "🔄 Mise à jour de TradingBot V5..."
cd /opt/tradingbot-v5
docker compose down
git fetch origin
git reset --hard origin/main
docker compose build --no-cache
docker compose up -d
echo "✅ Mise à jour terminée"
docker compose ps
EOF
    chmod +x /usr/local/bin/tradingbot-update
    
    # Config edit script
    cat > /usr/local/bin/tradingbot-config << 'EOF'
#!/bin/bash
nano /opt/tradingbot-v5/.env
echo ""
echo "⚠️  Redémarrez le bot pour appliquer les changements:"
echo "    tradingbot-restart"
EOF
    chmod +x /usr/local/bin/tradingbot-config
    
    print_step "Scripts de gestion créés"
}

setup_log_rotation() {
    print_section "📋 CONFIGURATION DE LA ROTATION DES LOGS"
    
    cat > /etc/logrotate.d/tradingbot << EOF
$INSTALL_DIR/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
}
EOF
    
    print_step "Rotation des logs configurée (14 jours)"
}

build_and_start() {
    print_section "🚀 BUILD ET DÉMARRAGE"
    
    cd "$INSTALL_DIR"
    
    print_info "Construction des images Docker..."
    docker compose build
    print_step "Images construites"
    
    # Check if .env is configured
    if [ -f ".env" ]; then
        if grep -q "ANTHROPIC_API_KEY=sk-ant-xxxxx" .env 2>/dev/null || \
           grep -q "ANTHROPIC_API_KEY=$" .env 2>/dev/null; then
            print_warning "⚠️  Le fichier .env n'est pas configuré!"
            print_info "Le bot ne sera pas démarré automatiquement."
            print_info "Configurez .env puis lancez: tradingbot-start"
        else
            print_info "Démarrage des services..."
            docker compose up -d
            print_step "Services démarrés"
            
            # Wait for services
            sleep 5
            
            # Show status
            docker compose ps
        fi
    else
        print_warning "Fichier .env manquant, bot non démarré"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# AFFICHAGE FINAL
# ══════════════════════════════════════════════════════════════════════════════

show_summary() {
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✅ INSTALLATION TERMINÉE AVEC SUCCÈS!                    ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}📍 Répertoire d'installation:${NC} $INSTALL_DIR"
    echo ""
    echo -e "${CYAN}🔗 URLs d'accès:${NC}"
    echo "   • Grafana Dashboard: http://$SERVER_IP:3000"
    echo "   • Prometheus:        http://$SERVER_IP:9090"
    echo "   • Metrics:           http://$SERVER_IP:8000/metrics"
    echo ""
    echo -e "${CYAN}🔑 Identifiants Grafana par défaut:${NC}"
    echo "   • Username: admin"
    echo "   • Password: tradingbot"
    echo ""
    echo -e "${CYAN}📝 Commandes disponibles:${NC}"
    echo "   • tradingbot-start   - Démarrer le bot"
    echo "   • tradingbot-stop    - Arrêter le bot"
    echo "   • tradingbot-restart - Redémarrer le bot"
    echo "   • tradingbot-logs    - Voir les logs"
    echo "   • tradingbot-status  - Voir le statut"
    echo "   • tradingbot-update  - Mettre à jour"
    echo "   • tradingbot-config  - Éditer la configuration"
    echo ""
    echo -e "${YELLOW}⚠️  PROCHAINES ÉTAPES IMPORTANTES:${NC}"
    echo ""
    echo "   1. Configurez vos clés API:"
    echo -e "      ${CYAN}tradingbot-config${NC}"
    echo ""
    echo "   2. Démarrez le bot:"
    echo -e "      ${CYAN}tradingbot-start${NC}"
    echo ""
    echo "   3. Vérifiez les logs:"
    echo -e "      ${CYAN}tradingbot-logs${NC}"
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}                   🎉 Bon trading avec TradingBot AI V5! 🎉                   ${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

main() {
    print_banner
    
    check_root
    check_system
    
    install_dependencies
    install_docker
    install_python
    
    configure_firewall
    configure_fail2ban
    
    clone_repository
    configure_environment
    setup_grafana_provisioning
    create_systemd_service
    create_management_scripts
    setup_log_rotation
    
    build_and_start
    
    show_summary
}

# Run main function
main "$@"
