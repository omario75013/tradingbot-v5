# 📚 DOCUMENTATION TECHNIQUE - TRADINGBOT AI V5

## Table des Matières

1. [Architecture Système](#architecture-système)
2. [Modules Détaillés](#modules-détaillés)
3. [Flux de Données](#flux-de-données)
4. [Configuration](#configuration)
5. [Déploiement](#déploiement)
6. [Monitoring](#monitoring)
7. [Sécurité](#sécurité)
8. [Troubleshooting](#troubleshooting)

---

## 1. Architecture Système

### Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TRADINGBOT AI V5 ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         MAIN ORCHESTRATOR                             │   │
│  │                         (main_v5.py)                                  │   │
│  └──────────────────────────┬───────────────────────────────────────────┘   │
│                             │                                                │
│  ┌──────────────────────────┼───────────────────────────────────────────┐   │
│  │                    PARALLEL ENGINES                                   │   │
│  │                                                                       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │  TRADING    │ │ ARBITRAGE   │ │  TRAINING   │ │  BACKTEST   │    │   │
│  │  │  ENGINE     │ │  SCANNER    │ │  CONTINU    │ │  CONTINU    │    │   │
│  │  │  (60s)      │ │  (5s)       │ │  (1h)       │ │  (30m)      │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  │                                                                       │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │ SENTIMENT   │ │ ALLOCATION  │ │   STRESS    │ │  METRICS    │    │   │
│  │  │  ENGINE     │ │  CLAUDE AI  │ │   TESTS     │ │  EXPORTER   │    │   │
│  │  │  (60s)      │ │  (2h)       │ │  (6h)       │ │  (15s)      │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       SHARED STATE (Redis)                            │   │
│  │  • Market State • Allocation • Performance • Model Info • Trades     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        EXTERNAL SERVICES                              │   │
│  │                                                                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ BINANCE  │ │  BYBIT   │ │   OKX    │ │ TELEGRAM │ │  CLAUDE  │   │   │
│  │  │   API    │ │   API    │ │   API    │ │   BOT    │ │   API    │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  │                                                                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                │   │
│  │  │ NEWSAPI  │ │CRYPTOPANIC│ │LUNARCRUSH│ │ FINNHUB  │                │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘                │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       MONITORING STACK                                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                             │   │
│  │  │PROMETHEUS│ │ GRAFANA  │ │ALERTMNGR │                             │   │
│  │  │  :9090   │ │  :3000   │ │  :9093   │                             │   │
│  │  └──────────┘ └──────────┘ └──────────┘                             │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Principes de Design

1. **Parallélisme** - Tous les engines tournent de manière asynchrone et indépendante
2. **État Partagé** - Redis centralise toutes les données pour la cohérence
3. **Résilience** - Chaque composant gère ses propres erreurs
4. **Observabilité** - Métriques Prometheus pour tout monitoring
5. **Sécurité** - Paper trading par défaut, double confirmation pour live

---

## 2. Modules Détaillés

### 2.1 Trading Engine (`engines/trading_engine.py`)

**Responsabilités:**
- Analyse des opportunités de trading
- Décision avec Claude AI
- Validation ML
- Exécution des trades
- Gestion des positions

**Cycle de Trading (60s):**
```
1. Fetch market data → OHLCV + Indicateurs
2. Update positions → Prix actuels
3. Check exits → SL/TP/Trailing
4. Can open new? → Limites atteintes?
5. Analyze with Claude → Signal généré
6. Validate with ML → Confirmation
7. Execute trade → Market order
```

**Indicateurs Techniques:**
- SMA (20, 50)
- EMA (12, 26)
- MACD + Signal + Histogramme
- RSI (14)
- Bollinger Bands (20, 2σ)
- ATR (14)
- Volume SMA (20)

### 2.2 Arbitrage Engine (`engines/arbitrage_engine.py`)

**Types d'Arbitrage:**

| Type | Description | Complexité | Profit Typique |
|------|-------------|------------|----------------|
| Cross-Exchange | Prix différent entre exchanges | Moyenne | 0.1-0.5% |
| Triangulaire | BTC→ETH→USDT→BTC | Haute | 0.05-0.2% |
| Funding Rate | Long Spot + Short Perp | Moyenne | 0.05-0.3%/8h |
| Stablecoin | Désancrage USDT/USDC/DAI | Basse | 0.1-1% |

**Cycle de Scan (5s):**
```
1. Fetch prices all exchanges
2. Calculate spreads
3. Filter profitable (> min_profit)
4. Validate liquidity
5. Execute if confirmed
6. Record opportunity
```

### 2.3 Training Engine (`engines/training_engine.py`)

**Modèle ML:**
- Type: Gradient Boosting Classifier
- Features: 30+ indicateurs techniques
- Target: Direction 1h (up/down)
- Validation: Walk-Forward Analysis

**Cycle d'Entraînement (1h):**
```
1. Fetch historical data
2. Generate features
3. Train new model
4. Walk-forward validation
5. Compare with current
6. Hot-swap if better (>2% improvement)
7. Archive old model
```

### 2.4 Backtest Engine (`engines/backtest_engine.py`)

**Objectifs:**
- Détecter la dégradation du modèle
- Valider les performances récentes
- Alerter si underperformance

**Métriques Surveillées:**
- Accuracy (seuil: 52%)
- Sharpe Ratio (seuil: 0.3)
- Max Drawdown (seuil: 15%)
- Win Rate (seuil: 45%)

### 2.5 Sentiment Engine (`sentiment/sentiment_aggregator.py`)

**Sources:**
- CryptoPanic (news crypto)
- NewsAPI (news générales)
- LunarCrush (métriques sociales)
- Fear & Greed Index
- Finnhub (news financières)

**Score Composite:**
```python
composite = (
    0.3 * news_score +      # -1 to 1
    0.2 * social_score +    # -1 to 1
    0.5 * fear_greed_norm   # (fg-50)/50
)
```

### 2.6 Allocation Engine (`allocation/claude_allocator.py`)

**Décision par Claude AI:**

```
INPUTS:
- Market state (prix, volatilité, régime)
- Sentiment score
- Performance récente
- Stress test results
- Opportunités arbitrage

OUTPUTS:
- arbitrage_pct (0-80%)
- trading_pct (0-70%)
- reserve_pct (10-100%)
- risk_level (low/medium/high)
- trading_bias (long/short/neutral)
- arbitrage_focus (types prioritaires)
```

---

## 3. Flux de Données

### 3.1 Cycle Principal

```
                    ┌─────────────────┐
                    │  Market Data    │
                    │  (Exchanges)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Trading Engine │  │Arbitrage Engine│  │Sentiment Engine│
│                │  │                │  │                │
│ • Analysis     │  │ • Scan         │  │ • Collect      │
│ • ML Validate  │  │ • Compare      │  │ • Aggregate    │
│ • Claude AI    │  │ • Execute      │  │ • Score        │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │  Shared State   │
                    │    (Redis)      │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│Allocation Engn │  │ Metrics Export │  │ Telegram Alerts│
│                │  │                │  │                │
│ Claude decides │  │ → Prometheus   │  │ → User         │
│ new allocation │  │ → Grafana      │  │                │
└────────────────┘  └────────────────┘  └────────────────┘
```

### 3.2 Trade Execution Flow

```
┌──────────────┐
│ Opportunity  │
│  Detected    │
└──────┬───────┘
       │
       ▼
┌──────────────┐     No      ┌──────────────┐
│ Claude AI    │────────────>│   Reject     │
│ Confidence?  │             └──────────────┘
└──────┬───────┘
       │ Yes (>60%)
       ▼
┌──────────────┐     No      ┌──────────────┐
│ ML Validate  │────────────>│   Reject     │
│ Confidence?  │             └──────────────┘
└──────┬───────┘
       │ Yes (>55%)
       ▼
┌──────────────┐     No      ┌──────────────┐
│ Risk Check   │────────────>│   Reject     │
│ Limits OK?   │             └──────────────┘
└──────┬───────┘
       │ Yes
       ▼
┌──────────────┐
│  Execute     │
│  Trade       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Monitor      │
│ Position     │
└──────────────┘
```

---

## 4. Configuration

### 4.1 Variables Essentielles

```env
# Mode
PAPER_TRADING=true          # TOUJOURS commencer en paper
TOTAL_BUDGET=10000          # Budget total

# APIs Obligatoires
ANTHROPIC_API_KEY=sk-ant-xxx
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx

# Alertes
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx
```

### 4.2 Paramètres de Trading

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| MAX_POSITION_PCT | 2.0 | % max par position |
| MAX_DRAWDOWN_PCT | 15.0 | Drawdown max avant pause |
| KELLY_FRACTION | 0.25 | Fraction de Kelly utilisée |
| MAX_DAILY_TRADES | 20 | Trades max par jour |
| MAX_CONSECUTIVE_LOSSES | 5 | Pertes consécutives avant pause |

### 4.3 Paramètres d'Arbitrage

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| MIN_ARBITRAGE_PROFIT_PCT | 0.08 | Profit min pour exécuter |
| ARBITRAGE_SCAN_INTERVAL | 5 | Secondes entre scans |
| MAX_ARBITRAGE_PCT | 80 | % max du budget en arbitrage |

---

## 5. Déploiement

### 5.1 Avec Docker (Recommandé)

```bash
# Cloner
git clone https://github.com/yourrepo/tradingbot-v5.git
cd tradingbot-v5

# Configuration
cp .env.template .env
nano .env  # Éditer les clés API

# Lancer
docker-compose up -d

# Logs
docker-compose logs -f tradingbot

# Arrêter
docker-compose down
```

### 5.2 Sans Docker

```bash
# Environnement virtuel
python -m venv venv
source venv/bin/activate

# Dépendances
pip install -r requirements.txt

# Configuration
cp .env.template .env
nano .env

# Lancer
python main_v5.py --paper
```

### 5.3 Sur Serveur (Production)

```bash
# Installer Docker
curl -fsSL https://get.docker.com | sh

# Configurer
git clone https://github.com/yourrepo/tradingbot-v5.git
cd tradingbot-v5
cp .env.template .env
nano .env

# Service systemd (optionnel)
sudo cp tradingbot.service /etc/systemd/system/
sudo systemctl enable tradingbot
sudo systemctl start tradingbot
```

---

## 6. Monitoring

### 6.1 Dashboard Grafana

Accessible à `http://localhost:3000` (ou URL cloud)

**Sections:**
1. Vue d'Ensemble - KPIs principaux
2. Allocation - Répartition du capital
3. Arbitrage - Opportunités et profits
4. Sentiment - Score et tendances
5. ML Model - Accuracy et Sharpe
6. Health - Status des composants

### 6.2 Alertes Telegram

**Types d'alertes:**
- 🚀 Startup/Shutdown
- 📈 Trades exécutés
- 🔄 Arbitrage
- 💰 Changement allocation
- ⚠️ Sentiment extrême
- 📊 Report périodique (4h)
- ❌ Erreurs système

### 6.3 Métriques Prometheus

```
# Performance
tradingbot_total_pnl_usd
tradingbot_win_rate
tradingbot_sharpe_ratio

# Allocation
tradingbot_allocation_pct{category="arbitrage|trading|reserve"}

# Arbitrage  
tradingbot_arb_profit_usd
tradingbot_arb_opportunities{type="..."}

# Sentiment
tradingbot_sentiment_score
tradingbot_fear_greed_index

# Health
tradingbot_running
tradingbot_component_health{component="..."}
tradingbot_uptime_seconds
```

---

## 7. Sécurité

### 7.1 Bonnes Pratiques

✅ **DO:**
- Utiliser Paper Trading pour tous les tests
- Limiter les permissions API (lecture seule si possible)
- Whitelister les IPs sur les exchanges
- Activer 2FA sur tous les comptes
- Stocker les clés dans des variables d'environnement
- Utiliser des secrets Docker en production

❌ **DON'T:**
- Ne jamais commiter `.env`
- Ne jamais hardcoder des clés API
- Ne pas utiliser de mots de passe faibles
- Ne pas ignorer les alertes de sécurité

### 7.2 Permissions API Recommandées

| Exchange | Read | Trade | Withdraw |
|----------|------|-------|----------|
| Binance  | ✅   | ✅    | ❌       |
| Bybit    | ✅   | ✅    | ❌       |
| OKX      | ✅   | ✅    | ❌       |

---

## 8. Troubleshooting

### 8.1 Problèmes Courants

**Bot ne démarre pas:**
```bash
# Vérifier les logs
docker-compose logs tradingbot

# Vérifier les variables d'environnement
cat .env | grep -v "^#" | grep -v "^$"

# Tester la connexion Redis
docker-compose exec redis redis-cli ping
```

**Pas de trades:**
```bash
# Vérifier les limites
- Trades aujourd'hui >= MAX_DAILY_TRADES?
- Consecutive losses >= MAX_CONSECUTIVE_LOSSES?
- Budget trading épuisé?
```

**Erreurs d'API:**
```bash
# Vérifier les clés
- Clé expirée?
- IP non whitelistée?
- Permissions insuffisantes?
```

### 8.2 Logs

```bash
# Logs en temps réel
docker-compose logs -f tradingbot

# Logs par fichier
tail -f logs/tradingbot_v5_*.log

# Filtrer les erreurs
grep -i error logs/tradingbot_v5_*.log
```

### 8.3 Reset

```bash
# Reset Redis (perte des données!)
docker-compose exec redis redis-cli FLUSHALL

# Reset complet
docker-compose down -v
docker-compose up -d
```

---

## Contact & Support

- **GitHub Issues:** Pour les bugs et demandes de fonctionnalités
- **Telegram:** @TradingBotSupport
- **Email:** support@tradingbot.ai

---

*Documentation générée le 24 Décembre 2024 - Version 5.0.0*
