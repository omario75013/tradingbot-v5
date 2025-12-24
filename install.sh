#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║               TRADINGBOT AI V5 - INSTALLATION SCRIPT                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║               🚀 TRADINGBOT AI V5 - INSTALLATION                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction d'aide
print_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 1. Vérifier Python
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Vérification des prérequis..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_step "Python $PYTHON_VERSION trouvé"
else
    print_error "Python 3 non trouvé. Veuillez l'installer."
    exit 1
fi

# 2. Vérifier pip
if command -v pip3 &> /dev/null; then
    print_step "pip3 trouvé"
else
    print_warning "pip3 non trouvé, installation..."
    python3 -m ensurepip --upgrade
fi

# 3. Créer environnement virtuel
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Création de l'environnement virtuel..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_step "Environnement virtuel créé"
else
    print_warning "Environnement virtuel existe déjà"
fi

# Activer l'environnement
source venv/bin/activate
print_step "Environnement activé"

# 4. Installer les dépendances
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 Installation des dépendances..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
print_step "Dépendances installées"

# 5. Configurer le fichier .env
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️ Configuration..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f ".env" ]; then
    cp .env.template .env
    print_step "Fichier .env créé depuis le template"
    print_warning "⚠️  IMPORTANT: Éditez .env avec vos clés API!"
else
    print_warning "Fichier .env existe déjà"
fi

# 6. Créer les dossiers nécessaires
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 Création des dossiers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p logs models/current models/archive data
print_step "Dossiers créés"

# 7. Vérification finale
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation terminée!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Prochaines étapes:"
echo ""
echo "   1. Éditez le fichier .env avec vos clés API:"
echo "      nano .env"
echo ""
echo "   2. Lancez le bot en mode paper:"
echo "      source venv/bin/activate"
echo "      python main_v5.py --paper"
echo ""
echo "   3. (Optionnel) Lancez avec Docker:"
echo "      docker-compose up -d"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 Documentation: DOCUMENTATION_TECHNIQUE.md"
echo "📊 Dashboard: http://localhost:3000 (Grafana)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
