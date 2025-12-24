# 🚀 GUIDE DE DÉPLOIEMENT HETZNER - TRADINGBOT V5

## Table des Matières

1. [Prérequis](#1-prérequis)
2. [Déploiement Automatique (Recommandé)](#2-déploiement-automatique-recommandé)
3. [Déploiement Manuel](#3-déploiement-manuel)
4. [Configuration Post-Déploiement](#4-configuration-post-déploiement)
5. [Commandes Utiles](#5-commandes-utiles)
6. [Maintenance](#6-maintenance)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prérequis

### Serveur Hetzner Recommandé

| Spécification | Minimum | Recommandé |
|--------------|---------|------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Stockage | 40 GB SSD | 80 GB NVMe |
| OS | Ubuntu 22.04 | Ubuntu 24.04 |

### APIs Requises

Avant le déploiement, préparez vos clés API:

- ✅ **Anthropic** (Claude AI) - [console.anthropic.com](https://console.anthropic.com)
- ✅ **Binance** - [binance.com/en/my/settings/api-management](https://www.binance.com/en/my/settings/api-management)
- ✅ **Bybit** - [bybit.com/app/user/api-management](https://www.bybit.com/app/user/api-management)
- ✅ **Telegram Bot** - [@BotFather](https://t.me/BotFather)
- ⭐ **NewsAPI** (optionnel) - [newsapi.org](https://newsapi.org)
- ⭐ **CryptoPanic** (optionnel) - [cryptopanic.com/developers/api](https://cryptopanic.com/developers/api)

---

## 2. Déploiement Automatique (Recommandé)

### Option A: One-Liner (Plus Rapide)

Connectez-vous en SSH à votre serveur et exécutez:

```bash
curl -sSL https://raw.githubusercontent.com/omario75013/tradingbot-v5/main/quick_deploy.sh | sudo bash
```

### Option B: Script Complet (Plus Sécurisé)

```bash
# 1. Télécharger le script
wget https://raw.githubusercontent.com/omario75013/tradingbot-v5/main/deploy_hetzner.sh

# 2. Vérifier le contenu (optionnel mais recommandé)
cat deploy_hetzner.sh

# 3. Exécuter
sudo bash deploy_hetzner.sh
```

### Ce que fait le script automatiquement:

1. ✅ Met à jour le système Ubuntu
2. ✅ Installe Docker et Docker Compose
3. ✅ Clone le repository GitHub
4. ✅ Configure l'environnement (.env)
5. ✅ Configure Grafana avec le dashboard
6. ✅ Configure le firewall (UFW)
7. ✅ Crée un service systemd (auto-restart)
8. ✅ Configure la rotation des logs
9. ✅ Démarre tous les services
10. ✅ Configure les backups automatiques

---

## 3. Déploiement Manuel

Si vous préférez un contrôle total:

### 3.1 Mise à jour système

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Installation Docker

```bash
# Installer Docker
curl -fsSL https://get.docker.com | sh

# Ajouter votre utilisateur au groupe docker
sudo usermod -aG docker $USER

# Redémarrer la session (ou logout/login)
newgrp docker
```

### 3.3 Cloner le repository

```bash
sudo git clone https://github.com/omario75013/tradingbot-v5.git /opt/tradingbot-v5
cd /opt/tradingbot-v5
```

### 3.4 Configuration

```bash
# Copier le template
cp .env.template .env

# Éditer avec vos clés API
nano .env
```

### 3.5 Démarrage

```bash
# Créer les dossiers
mkdir -p logs models/current models/archive data

# Démarrer les services
docker compose up -d

# Vérifier le status
docker compose ps
```

---

## 4. Configuration Post-Déploiement

### 4.1 Configurer les Clés API

```bash
# Éditer le fichier .env
sudo nano /opt/tradingbot-v5/.env
```

**Configuration minimale requise:**

```env
# Mode (garder true pour commencer!)
PAPER_TRADING=true
TOTAL_BUDGET=10000

# Claude AI (OBLIGATOIRE)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Au moins un exchange (OBLIGATOIRE)
BINANCE_API_KEY=xxxxx
BINANCE_API_SECRET=xxxxx

# Telegram (Recommandé)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

### 4.2 Redémarrer après configuration

```bash
cd /opt/tradingbot-v5
docker compose restart
```

### 4.3 Whitelister l'IP du serveur

**TRÈS IMPORTANT!** Sur chaque exchange, whitelistez l'IP de votre serveur:

```bash
# Obtenir l'IP du serveur
curl ifconfig.me
```

- **Binance**: API Management → Restrict access to trusted IPs only
- **Bybit**: API Management → IP restriction
- **OKX**: API → IP whitelist

### 4.4 Changer le mot de passe Grafana

1. Ouvrez `http://VOTRE_IP:3000`
2. Connectez-vous avec `admin` / `tradingbot2024`
3. Allez dans Profile → Change Password

---

## 5. Commandes Utiles

### Services Docker

```bash
cd /opt/tradingbot-v5

# Status de tous les services
docker compose ps

# Logs en temps réel
docker compose logs -f tradingbot

# Logs d'un service spécifique
docker compose logs -f grafana
docker compose logs -f prometheus

# Redémarrer tous les services
docker compose restart

# Redémarrer un service spécifique
docker compose restart tradingbot

# Arrêter tout
docker compose down

# Arrêter et supprimer les volumes (⚠️ perd les données!)
docker compose down -v
```

### Service Systemd

```bash
# Status
sudo systemctl status tradingbot

# Logs système
sudo journalctl -u tradingbot -f

# Redémarrer
sudo systemctl restart tradingbot

# Arrêter
sudo systemctl stop tradingbot

# Désactiver au boot
sudo systemctl disable tradingbot
```

### Scripts de maintenance

```bash
cd /opt/tradingbot-v5

# Voir le status complet
./status.sh

# Logs en temps réel
./logs.sh

# Redémarrage rapide
./restart.sh

# Backup manuel
./backup.sh

# Mise à jour depuis GitHub
./update.sh
```

---

## 6. Maintenance

### 6.1 Backups

Les backups automatiques sont configurés pour s'exécuter à 3h du matin:

```bash
# Backups stockés dans:
ls -la /opt/tradingbot-backups/

# Backup manuel
/opt/tradingbot-v5/backup.sh
```

### 6.2 Mises à jour

```bash
cd /opt/tradingbot-v5

# Mettre à jour depuis GitHub
./update.sh

# Ou manuellement:
git pull origin main
docker compose pull
docker compose up -d --build
```

### 6.3 Monitoring

| Service | URL | Identifiants |
|---------|-----|--------------|
| Grafana | http://IP:3000 | admin / tradingbot2024 |
| Prometheus | http://IP:9090 | - |

### 6.4 Vérification Santé

```bash
# Vérifier les containers
docker compose ps

# Vérifier les ressources
docker stats --no-stream

# Vérifier les logs d'erreur
docker compose logs --tail=100 tradingbot | grep -i error
```

---

## 7. Troubleshooting

### Problème: Bot ne démarre pas

```bash
# Vérifier les logs
docker compose logs tradingbot

# Vérifier le fichier .env
cat /opt/tradingbot-v5/.env | grep -v "^#" | grep -v "^$"

# Vérifier les permissions
ls -la /opt/tradingbot-v5/.env
```

### Problème: Erreur API Exchange

```bash
# 1. Vérifier que l'IP est whitelistée sur l'exchange
curl ifconfig.me

# 2. Vérifier les clés API dans .env
grep -E "BINANCE|BYBIT" /opt/tradingbot-v5/.env

# 3. Tester la connexion
docker compose exec tradingbot python -c "import ccxt; print(ccxt.binance().fetch_time())"
```

### Problème: Grafana inaccessible

```bash
# Vérifier que le port est ouvert
sudo ufw status

# Ouvrir le port si nécessaire
sudo ufw allow 3000/tcp

# Vérifier que le container tourne
docker compose ps grafana
```

### Problème: Mémoire insuffisante

```bash
# Vérifier l'utilisation mémoire
free -h

# Ajouter du swap (si pas déjà fait)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Problème: Redémarrage après crash

Le service systemd redémarre automatiquement le bot. Pour vérifier:

```bash
# Voir les redémarrages récents
sudo journalctl -u tradingbot --since "1 hour ago"

# Vérifier la configuration systemd
cat /etc/systemd/system/tradingbot.service
```

### Reset complet

```bash
cd /opt/tradingbot-v5

# Sauvegarder la config
cp .env .env.backup

# Tout arrêter et supprimer
docker compose down -v
docker system prune -af

# Recloner
cd /opt
rm -rf tradingbot-v5
git clone https://github.com/omario75013/tradingbot-v5.git
cd tradingbot-v5

# Restaurer la config
cp .env.backup .env

# Redémarrer
docker compose up -d
```

---

## Contacts & Support

- **GitHub Issues**: [github.com/omario75013/tradingbot-v5/issues](https://github.com/omario75013/tradingbot-v5/issues)
- **Documentation**: Voir `DOCUMENTATION_TECHNIQUE.md`

---

*Guide mis à jour le 24 Décembre 2024 - Version 5.0.0*
