# 🚀 TradingBot AI V5

> Bot de trading crypto intelligent avec arbitrage multi-exchange, ML en temps réel, et allocation dynamique par Claude AI.

[![Version](https://img.shields.io/badge/version-5.0.0-blue.svg)](https://github.com/tradingbot)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

---

## ✨ Fonctionnalités

### 🔄 Processus Parallèles
- **Trading Engine** - Trading directionnel avec ML
- **Arbitrage Scanner** - Multi-type (Cross-Exchange, Triangulaire, Funding Rate)
- **Training Continu** - Entraînement ML avec hot-swap automatique
- **Backtest Continu** - Détection de dégradation
- **Sentiment Engine** - Analyse multi-sources en temps réel
- **Allocation Engine** - Répartition dynamique par Claude AI
- **Stress Tests** - Tests périodiques de résistance

### 📊 Types d'Arbitrage
| Type | Description | Profit Typique |
|------|-------------|----------------|
| Cross-Exchange | Prix différent entre exchanges | 0.1-0.5% |
| Triangulaire | BTC→ETH→USDT→BTC | 0.05-0.2% |
| Funding Rate | Long Spot + Short Perp | 0.05-0.3%/8h |
| Stablecoin | Désancrage USDT/USDC/DAI | 0.1-1% |

### 🧠 Intelligence Artificielle
- **Claude AI** pour décisions de trading et allocation
- **ML Gradient Boosting** avec entraînement continu
- **Hot-Swap** automatique des modèles améliorés
- **Walk-Forward Analysis** pour validation

### 📱 Alertes Telegram Enrichies
- 🚀 Startup/Shutdown
- 📈 Trades exécutés
- 🔄 Opportunités arbitrage
- 💰 Changements d'allocation
- ⚠️ Alertes sentiment
- 📊 Reports périodiques (4h)

---

## 🛠️ Installation

### Prérequis
- Python 3.11+
- Docker & Docker Compose (recommandé)
- API Keys (Anthropic, Exchanges, Telegram)

### Installation Rapide

```bash
# Cloner le repo
git clone https://github.com/yourusername/tradingbot-v5.git
cd tradingbot-v5

# Copier la config
cp .env.template .env

# Éditer .env avec vos API keys
nano .env

# Lancer avec Docker
docker-compose up -d
```

### Installation Manuelle

```bash
# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Lancer
python main_v5.py --paper
```

---

## ⚙️ Configuration

### Variables Essentielles (.env)

```env
# Mode
PAPER_TRADING=true
TOTAL_BUDGET=10000

# Claude AI
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Exchanges
BINANCE_API_KEY=xxxxx
BINANCE_API_SECRET=xxxxx

# Telegram
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=xxxxx
```

### Paramètres Avancés

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `MAX_POSITION_PCT` | 2.0 | % max par position |
| `MAX_DRAWDOWN_PCT` | 15.0 | Drawdown max avant pause |
| `MIN_ARBITRAGE_PROFIT_PCT` | 0.08 | Profit min pour arbitrage |
| `TRAINING_INTERVAL_HOURS` | 1 | Fréquence entraînement ML |
| `ALLOCATION_INTERVAL_HOURS` | 2 | Fréquence rééquilibrage |

---

## 📊 Dashboard Grafana

Le dashboard est accessible à `https://tradingbot75.grafana.net/` ou localement sur `http://localhost:3000`.

### Sections
1. **Vue d'Ensemble** - PnL, Win Rate, Sharpe, Drawdown
2. **Allocation Capital** - Répartition Arbitrage/Trading/Reserve
3. **Arbitrage** - Opportunités et profits
4. **Sentiment & Marché** - Score, Fear & Greed, News
5. **Modèle ML** - Accuracy, Sharpe backtest
6. **Santé Système** - Status des composants

---

## 🏗️ Architecture

```
tradingbot_v5/
├── main_v5.py              # Orchestrateur principal
├── engines/
│   ├── trading_engine.py   # Trading directionnel
│   ├── arbitrage_engine.py # Scanner multi-type
│   ├── training_engine.py  # ML continu
│   └── backtest_engine.py  # Backtest & validation
├── sentiment/
│   └── sentiment_aggregator.py
├── allocation/
│   └── claude_allocator.py
├── risk/
│   └── stress_tester.py
├── monitoring/
│   ├── telegram_alerts.py
│   ├── metrics_exporter.py
│   └── grafana-dashboard-v5.json
└── models/
    ├── current/            # Modèle actif
    └── archive/            # Versions précédentes
```

---

## 🚦 Modes d'Exécution

```bash
# Paper Trading (défaut)
python main_v5.py --paper

# Live Trading (⚠️ ATTENTION!)
python main_v5.py --live

# Avec budget personnalisé
python main_v5.py --paper --budget 5000
```

---

## 📈 Métriques Prometheus

Le bot expose des métriques sur le port 8000:

```
# Performance
tradingbot_total_pnl_usd
tradingbot_win_rate
tradingbot_sharpe_ratio

# Allocation
tradingbot_allocation_pct{category="arbitrage|trading|reserve"}

# Arbitrage
tradingbot_arb_profit_usd
tradingbot_arb_opportunities{type="cross_exchange|funding"}

# Sentiment
tradingbot_sentiment_score
tradingbot_fear_greed_index

# Health
tradingbot_running
tradingbot_component_health{component="..."}
```

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest

# Tests avec couverture
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_arbitrage.py -v
```

---

## 🔒 Sécurité

- ✅ Ne jamais commiter `.env`
- ✅ Utiliser Paper Trading pour les tests
- ✅ Limiter les permissions API (lecture seule si possible)
- ✅ Whitelister les IPs sur les exchanges
- ✅ Activer 2FA sur tous les comptes

---

## 📝 Roadmap V5.x

- [ ] Support DEX (Uniswap, Curve)
- [ ] Deep Learning (LSTM, Transformer)
- [ ] Reinforcement Learning pour sizing
- [ ] Multi-GPU training
- [ ] WebSocket real-time data
- [ ] Mobile app (Flutter)

---

## 🤝 Contribution

1. Fork le repo
2. Créer une branche (`git checkout -b feature/amazing`)
3. Commiter (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Ouvrir une Pull Request

---

## 📄 License

MIT License - voir [LICENSE](LICENSE) pour plus de détails.

---

## ⚠️ Disclaimer

Ce logiciel est fourni "tel quel" sans garantie. Le trading de cryptomonnaies comporte des risques significatifs. N'investissez que ce que vous pouvez vous permettre de perdre.

---

<p align="center">
  Made with ❤️ by TradingBot AI Team
</p>
