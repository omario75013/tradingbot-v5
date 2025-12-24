"""
TRADINGBOT V5 - CONFIGURATION CENTRALISÉE
==========================================
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ConfigV5:
    """Configuration centralisée pour TradingBot V5"""
    
    # API Keys
    anthropic_api_key: str = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY', ''))
    binance_api_key: str = field(default_factory=lambda: os.getenv('BINANCE_API_KEY', ''))
    binance_api_secret: str = field(default_factory=lambda: os.getenv('BINANCE_API_SECRET', ''))
    bybit_api_key: str = field(default_factory=lambda: os.getenv('BYBIT_API_KEY', ''))
    bybit_api_secret: str = field(default_factory=lambda: os.getenv('BYBIT_API_SECRET', ''))
    okx_api_key: str = field(default_factory=lambda: os.getenv('OKX_API_KEY', ''))
    okx_api_secret: str = field(default_factory=lambda: os.getenv('OKX_API_SECRET', ''))
    okx_passphrase: str = field(default_factory=lambda: os.getenv('OKX_PASSPHRASE', ''))
    kucoin_api_key: str = field(default_factory=lambda: os.getenv('KUCOIN_API_KEY', ''))
    kucoin_api_secret: str = field(default_factory=lambda: os.getenv('KUCOIN_API_SECRET', ''))
    kucoin_passphrase: str = field(default_factory=lambda: os.getenv('KUCOIN_PASSPHRASE', ''))
    gate_api_key: str = field(default_factory=lambda: os.getenv('GATE_API_KEY', ''))
    gate_api_secret: str = field(default_factory=lambda: os.getenv('GATE_API_SECRET', ''))
    mexc_api_key: str = field(default_factory=lambda: os.getenv('MEXC_API_KEY', ''))
    mexc_api_secret: str = field(default_factory=lambda: os.getenv('MEXC_API_SECRET', ''))
    
    # News & Sentiment
    newsapi_key: str = field(default_factory=lambda: os.getenv('NEWSAPI_KEY', ''))
    cryptopanic_key: str = field(default_factory=lambda: os.getenv('CRYPTOPANIC_KEY', ''))
    lunarcrush_key: str = field(default_factory=lambda: os.getenv('LUNARCRUSH_KEY', ''))
    finnhub_key: str = field(default_factory=lambda: os.getenv('FINNHUB_KEY', ''))
    twitter_bearer_token: str = field(default_factory=lambda: os.getenv('TWITTER_BEARER_TOKEN', ''))
    reddit_client_id: str = field(default_factory=lambda: os.getenv('REDDIT_CLIENT_ID', ''))
    reddit_client_secret: str = field(default_factory=lambda: os.getenv('REDDIT_CLIENT_SECRET', ''))
    
    # Telegram
    telegram_bot_token: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv('TELEGRAM_CHAT_ID', ''))
    
    # Infrastructure
    redis_url: str = field(default_factory=lambda: os.getenv('REDIS_URL', 'redis://localhost:6379'))
    prometheus_port: int = 8000
    grafana_url: str = 'https://tradingbot75.grafana.net/'
    
    # Trading
    paper_trading: bool = True
    use_testnet: bool = True
    initial_capital: float = 10000.0
    default_trading_pairs: List[str] = field(default_factory=lambda: [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT'
    ])
    primary_timeframe: str = '1h'
    min_confidence: float = 0.65
    min_risk_reward: float = 2.5
    
    # Risk
    max_position_size_pct: float = 2.0
    max_portfolio_exposure_pct: float = 20.0
    kelly_fraction: float = 0.25
    max_drawdown_pct: float = 15.0
    kill_switch_daily_loss_pct: float = 10.0
    kill_switch_drawdown_pct: float = 20.0
    max_daily_trades: int = 10
    max_consecutive_losses: int = 3
    
    # Arbitrage
    arbitrage_exchanges: List[str] = field(default_factory=lambda: [
        'binance', 'bybit', 'okx', 'kucoin', 'gate', 'mexc'
    ])
    min_arbitrage_spread: float = 0.08
    min_volume_24h: float = 1000000
    arbitrage_scan_interval: int = 5
    arbitrage_types: Dict[str, bool] = field(default_factory=lambda: {
        'cross_exchange': True,
        'triangular': True,
        'funding_rate': True,
        'stablecoin': True
    })
    
    # Training
    training_interval_hours: int = 1
    model_update_threshold: float = 1.02
    
    # Backtest
    backtest_interval_minutes: int = 30
    stress_test_interval_hours: int = 6
    
    # Sentiment
    sentiment_update_interval: int = 60
    fud_threshold: float = 0.8
    fomo_threshold: float = 0.8
    
    # Allocation
    default_allocation: Dict[str, float] = field(default_factory=lambda: {
        'trading': 40, 'arbitrage': 40, 'reserve': 20
    })


config = ConfigV5()
