#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               TRADINGBOT AI V5 - MAIN ORCHESTRATOR                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import asyncio
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import traceback

import pandas as pd
import numpy as np
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

@dataclass
class TradingBotV5Config:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY', ''))
    binance_api_key: str = field(default_factory=lambda: os.getenv('BINANCE_API_KEY', ''))
    binance_api_secret: str = field(default_factory=lambda: os.getenv('BINANCE_API_SECRET', ''))
    bybit_api_key: str = field(default_factory=lambda: os.getenv('BYBIT_API_KEY', ''))
    bybit_api_secret: str = field(default_factory=lambda: os.getenv('BYBIT_API_SECRET', ''))
    okx_api_key: str = field(default_factory=lambda: os.getenv('OKX_API_KEY', ''))
    okx_api_secret: str = field(default_factory=lambda: os.getenv('OKX_API_SECRET', ''))
    okx_passphrase: str = field(default_factory=lambda: os.getenv('OKX_PASSPHRASE', ''))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv('TELEGRAM_CHAT_ID', ''))
    newsapi_key: str = field(default_factory=lambda: os.getenv('NEWSAPI_KEY', ''))
    cryptopanic_key: str = field(default_factory=lambda: os.getenv('CRYPTOPANIC_API_KEY', ''))
    lunarcrush_key: str = field(default_factory=lambda: os.getenv('LUNARCRUSH_API_KEY', ''))
    finnhub_key: str = field(default_factory=lambda: os.getenv('FINNHUB_API_KEY', ''))
    total_budget: float = field(default_factory=lambda: float(os.getenv('TOTAL_BUDGET', '10000')))
    min_reserve_pct: float = 10.0
    max_arbitrage_pct: float = 80.0
    max_trading_pct: float = 70.0
    trading_pairs: List[str] = field(default_factory=lambda: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT'])
    arbitrage_exchanges: List[str] = field(default_factory=lambda: ['binance', 'bybit', 'okx'])
    max_position_pct: float = 2.0
    max_drawdown_pct: float = 15.0
    kelly_fraction: float = 0.25
    max_daily_trades: int = 20
    max_consecutive_losses: int = 5
    min_arbitrage_profit_pct: float = 0.08
    arbitrage_scan_interval: int = 5
    training_interval_hours: int = 1
    model_comparison_threshold: float = 1.02
    backtest_interval_minutes: int = 30
    stress_test_interval_hours: int = 6
    allocation_interval_hours: int = 2
    redis_url: str = field(default_factory=lambda: os.getenv('REDIS_URL', 'redis://localhost:6379'))
    grafana_url: str = field(default_factory=lambda: os.getenv('GRAFANA_URL', 'https://tradingbot75.grafana.net/'))
    prometheus_port: int = 8000
    paper_trading: bool = field(default_factory=lambda: os.getenv('PAPER_TRADING', 'true').lower() == 'true')


class SharedStateManager:
    def __init__(self, config: TradingBotV5Config):
        self.config = config
        self.redis = None
        self.local_cache: Dict = {}
        self._lock = asyncio.Lock()
        
    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self.redis = await aioredis.from_url(self.config.redis_url)
            await self.redis.ping()
            logger.info("✅ Redis connecté")
        except Exception as e:
            logger.warning(f"⚠️ Redis non disponible: {e}")
            self.redis = None
    
    async def set(self, key: str, value: Any, expire: int = 3600):
        async with self._lock:
            data = json.dumps(value, default=str)
            if self.redis:
                try:
                    await self.redis.set(f"tradingbot:{key}", data, ex=expire)
                except:
                    pass
            self.local_cache[key] = value
    
    async def get(self, key: str, default: Any = None) -> Any:
        if self.redis:
            try:
                data = await self.redis.get(f"tradingbot:{key}")
                if data:
                    return json.loads(data)
            except:
                pass
        return self.local_cache.get(key, default)
    
    async def get_market_state(self) -> Dict:
        return await self.get('market_state', {'btc_price': 0, 'fear_greed': 50, 'regime': 'UNKNOWN', 'sentiment_score': 0})
    
    async def set_market_state(self, state: Dict):
        await self.set('market_state', state, expire=300)
    
    async def get_allocation(self) -> Dict:
        return await self.get('allocation', {'arbitrage_pct': 40, 'trading_pct': 40, 'reserve_pct': 20, 'arbitrage_budget': self.config.total_budget * 0.4, 'trading_budget': self.config.total_budget * 0.4, 'reserve_budget': self.config.total_budget * 0.2})
    
    async def set_allocation(self, allocation: Dict):
        await self.set('allocation', allocation, expire=14400)
    
    async def get_performance(self) -> Dict:
        return await self.get('performance', {'total_pnl': 0, 'today_pnl': 0, 'win_rate': 0.5, 'sharpe_ratio': 0, 'max_drawdown': 0, 'total_trades': 0})
    
    async def update_performance(self, updates: Dict):
        current = await self.get_performance()
        current.update(updates)
        await self.set('performance', current, expire=86400)
    
    async def get_model_info(self) -> Dict:
        return await self.get('model_info', {'version': '1.0.0', 'accuracy': 0, 'sharpe': 0})
    
    async def set_model_info(self, info: Dict):
        await self.set('model_info', info, expire=86400)
    
    async def add_trade(self, trade: Dict):
        trades = await self.get('trades_history', [])
        trades.append(trade)
        if len(trades) > 1000:
            trades = trades[-1000:]
        await self.set('trades_history', trades, expire=604800)
    
    async def get_trades_history(self, limit: int = 100) -> List[Dict]:
        trades = await self.get('trades_history', [])
        return trades[-limit:]


class TradingBotV5:
    def __init__(self, config: Optional[TradingBotV5Config] = None):
        self.config = config or TradingBotV5Config()
        self.state = SharedStateManager(self.config)
        self.running = False
        self.start_time = None
        self.tasks: List[asyncio.Task] = []
        
    async def initialize(self):
        logger.info("🚀 Initialisation TradingBot V5...")
        await self.state.connect()
        
        from engines.trading_engine import LiveTradingEngine
        from engines.arbitrage_engine import ArbitrageScannerEngine
        from engines.training_engine import ContinuousTrainingEngine
        from engines.backtest_engine import ContinuousBacktestEngine
        from sentiment.sentiment_aggregator import RealTimeSentimentEngine
        from allocation.claude_allocator import ClaudeCapitalAllocator
        from monitoring.telegram_alerts import TelegramAlertEngine
        from monitoring.metrics_exporter import MetricsExporter
        from risk.stress_tester import StressTestEngine
        
        self.trading_engine = LiveTradingEngine(self.config, self.state)
        self.arbitrage_engine = ArbitrageScannerEngine(self.config, self.state)
        self.training_engine = ContinuousTrainingEngine(self.config, self.state)
        self.backtest_engine = ContinuousBacktestEngine(self.config, self.state)
        self.sentiment_engine = RealTimeSentimentEngine(self.config, self.state)
        self.allocation_engine = ClaudeCapitalAllocator(self.config, self.state)
        self.alert_engine = TelegramAlertEngine(self.config, self.state)
        self.metrics_engine = MetricsExporter(self.config, self.state)
        self.stress_tester = StressTestEngine(self.config, self.state)
        
        logger.info("✅ Tous les composants initialisés")
    
    async def run(self):
        self.running = True
        self.start_time = datetime.now()
        await self.initialize()
        await self.alert_engine.send_startup_message()
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               🚀 TRADINGBOT AI V5 - DÉMARRÉ 🚀                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Mode: {"PAPER TRADING ✅" if self.config.paper_trading else "⚠️  LIVE TRADING ⚠️"}                                                  ║
║  Budget: ${self.config.total_budget:,.2f}                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        self.tasks = [
            asyncio.create_task(self._run_engine(self.trading_engine.run_cycle, 60, "trading")),
            asyncio.create_task(self._run_engine(self.arbitrage_engine.scan_all, self.config.arbitrage_scan_interval, "arbitrage")),
            asyncio.create_task(self._run_engine(self.training_engine.run_training_cycle, self.config.training_interval_hours * 3600, "training")),
            asyncio.create_task(self._run_engine(self.backtest_engine.run_continuous_backtest, self.config.backtest_interval_minutes * 60, "backtest")),
            asyncio.create_task(self._run_engine(self.sentiment_engine.collect_all_sources, 60, "sentiment")),
            asyncio.create_task(self._run_engine(self.allocation_engine.decide_allocation, self.config.allocation_interval_hours * 3600, "allocation")),
            asyncio.create_task(self._run_engine(self.stress_tester.run_all_stress_tests, self.config.stress_test_interval_hours * 3600, "stress_tests")),
            asyncio.create_task(self._run_engine(self.metrics_engine.export_all_metrics, 15, "metrics")),
            asyncio.create_task(self._run_health_monitor()),
            asyncio.create_task(self._run_periodic_reports()),
        ]
        
        logger.info(f"✅ {len(self.tasks)} processus lancés")
        
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()
    
    async def _run_engine(self, func, interval, name):
        await asyncio.sleep(5)
        while self.running:
            try:
                await func()
            except Exception as e:
                logger.error(f"❌ {name} Error: {e}")
            await asyncio.sleep(interval)
    
    async def _run_health_monitor(self):
        while self.running:
            try:
                health = {'timestamp': datetime.now().isoformat(), 'uptime_hours': (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0, 'components': {}, 'all_healthy': True}
                for task in self.tasks:
                    name = task.get_name() if hasattr(task, 'get_name') else str(task)
                    health['components'][name] = {'running': not task.done(), 'error': str(task.exception()) if task.done() and task.exception() else None}
                    if not health['components'][name]['running']:
                        health['all_healthy'] = False
                await self.state.set('health_status', health)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _run_periodic_reports(self):
        while self.running:
            await asyncio.sleep(4 * 3600)
            try:
                await self.alert_engine.send_periodic_report()
            except Exception as e:
                logger.error(f"Report error: {e}")
    
    async def shutdown(self):
        logger.info("🛑 Arrêt de TradingBot V5...")
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        if hasattr(self, 'alert_engine'):
            await self.alert_engine.send_shutdown_message()
        logger.info("✅ TradingBot V5 arrêté")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='TradingBot AI V5')
    parser.add_argument('--paper', action='store_true', help='Paper trading mode')
    parser.add_argument('--live', action='store_true', help='Live trading mode')
    parser.add_argument('--budget', type=float, default=10000, help='Trading budget')
    args = parser.parse_args()
    
    config = TradingBotV5Config()
    if args.live:
        config.paper_trading = False
        confirm = input("⚠️  LIVE TRADING - Tapez 'JE CONFIRME': ")
        if confirm != 'JE CONFIRME':
            print("Annulé.")
            return
    if args.budget:
        config.total_budget = args.budget
    
    logger.add("logs/tradingbot_v5_{time}.log", rotation="1 day", level="INFO")
    bot = TradingBotV5(config)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def signal_handler(sig, frame):
        asyncio.create_task(bot.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        loop.run_until_complete(bot.shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
