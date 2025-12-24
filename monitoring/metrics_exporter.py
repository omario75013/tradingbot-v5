#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               METRICS EXPORTER - V5                                          ║
║                                                                              ║
║  Exporte les métriques pour Prometheus/Grafana:                              ║
║  • Performance (PnL, Win Rate, Sharpe)                                       ║
║  • Arbitrage Stats                                                           ║
║  • Trading Stats                                                             ║
║  • Sentiment                                                                 ║
║  • Health                                                                    ║
║  • Model Info                                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Optional
from prometheus_client import (
    Gauge, Counter, Histogram, Info,
    CollectorRegistry, generate_latest, start_http_server
)
from loguru import logger

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MetricsExporter:
    """Exporteur de métriques Prometheus"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        # Registry
        self.registry = CollectorRegistry()
        
        # ══════════════════════════════════════════════════════════════════════
        # PERFORMANCE METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.total_pnl = Gauge(
            'tradingbot_total_pnl_usd',
            'Total PnL in USD',
            registry=self.registry
        )
        
        self.today_pnl = Gauge(
            'tradingbot_today_pnl_usd',
            'Today PnL in USD',
            registry=self.registry
        )
        
        self.win_rate = Gauge(
            'tradingbot_win_rate',
            'Win rate (0-1)',
            registry=self.registry
        )
        
        self.sharpe_ratio = Gauge(
            'tradingbot_sharpe_ratio',
            'Sharpe ratio',
            registry=self.registry
        )
        
        self.max_drawdown = Gauge(
            'tradingbot_max_drawdown',
            'Maximum drawdown (0-1)',
            registry=self.registry
        )
        
        self.total_trades = Counter(
            'tradingbot_trades_total',
            'Total number of trades',
            ['side', 'outcome'],
            registry=self.registry
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # TRADING METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.trading_budget = Gauge(
            'tradingbot_trading_budget_usd',
            'Trading budget in USD',
            registry=self.registry
        )
        
        self.open_positions = Gauge(
            'tradingbot_open_positions',
            'Number of open positions',
            registry=self.registry
        )
        
        self.position_pnl = Gauge(
            'tradingbot_position_pnl_usd',
            'Unrealized PnL of open positions',
            ['symbol'],
            registry=self.registry
        )
        
        self.daily_trades_count = Gauge(
            'tradingbot_daily_trades',
            'Number of trades today',
            registry=self.registry
        )
        
        self.consecutive_losses = Gauge(
            'tradingbot_consecutive_losses',
            'Number of consecutive losses',
            registry=self.registry
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # ARBITRAGE METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.arb_budget = Gauge(
            'tradingbot_arb_budget_usd',
            'Arbitrage budget in USD',
            registry=self.registry
        )
        
        self.arb_opportunities = Gauge(
            'tradingbot_arb_opportunities',
            'Active arbitrage opportunities',
            ['type'],
            registry=self.registry
        )
        
        self.arb_profit = Gauge(
            'tradingbot_arb_profit_usd',
            'Total arbitrage profit in USD',
            registry=self.registry
        )
        
        self.arb_scans = Counter(
            'tradingbot_arb_scans_total',
            'Total arbitrage scans',
            registry=self.registry
        )
        
        self.arb_spread = Gauge(
            'tradingbot_arb_avg_spread',
            'Average arbitrage spread %',
            ['exchange_pair'],
            registry=self.registry
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # ALLOCATION METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.allocation_pct = Gauge(
            'tradingbot_allocation_pct',
            'Allocation percentage',
            ['category'],
            registry=self.registry
        )
        
        self.risk_level = Gauge(
            'tradingbot_risk_level',
            'Risk level (0=low, 1=medium, 2=high)',
            registry=self.registry
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # SENTIMENT METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.sentiment_score = Gauge(
            'tradingbot_sentiment_score',
            'Composite sentiment score (-1 to 1)',
            registry=self.registry
        )
        
        self.fear_greed = Gauge(
            'tradingbot_fear_greed_index',
            'Fear & Greed Index (0-100)',
            registry=self.registry
        )
        
        self.news_count = Gauge(
            'tradingbot_news_count',
            'Number of recent news items',
            registry=self.registry
        )
        
        self.sentiment_trend = Gauge(
            'tradingbot_sentiment_trend_1h',
            'Sentiment trend over 1 hour',
            registry=self.registry
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # MARKET METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.btc_price = Gauge(
            'tradingbot_btc_price_usd',
            'BTC price in USD',
            registry=self.registry
        )
        
        self.btc_change_24h = Gauge(
            'tradingbot_btc_change_24h_pct',
            'BTC 24h change %',
            registry=self.registry
        )
        
        self.market_volatility = Gauge(
            'tradingbot_market_volatility',
            'Market volatility level (0=low, 1=medium, 2=high)',
            registry=self.registry
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # MODEL METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.model_accuracy = Gauge(
            'tradingbot_model_accuracy',
            'ML model accuracy',
            registry=self.registry
        )
        
        self.model_sharpe = Gauge(
            'tradingbot_model_sharpe',
            'ML model backtest Sharpe',
            registry=self.registry
        )
        
        self.model_version = Info(
            'tradingbot_model',
            'ML model information',
            registry=self.registry
        )
        
        # ══════════════════════════════════════════════════════════════════════
        # HEALTH METRICS
        # ══════════════════════════════════════════════════════════════════════
        
        self.bot_running = Gauge(
            'tradingbot_running',
            'Bot running status (1=running, 0=stopped)',
            registry=self.registry
        )
        
        self.uptime_seconds = Gauge(
            'tradingbot_uptime_seconds',
            'Bot uptime in seconds',
            registry=self.registry
        )
        
        self.component_health = Gauge(
            'tradingbot_component_health',
            'Component health (1=healthy, 0=unhealthy)',
            ['component'],
            registry=self.registry
        )
        
        self.last_update = Gauge(
            'tradingbot_last_update_timestamp',
            'Last metrics update timestamp',
            registry=self.registry
        )
        
        # HTTP Server
        self.server_started = False
    
    async def start_server(self):
        """Démarrer le serveur HTTP pour Prometheus"""
        if not self.server_started:
            try:
                start_http_server(self.config.prometheus_port, registry=self.registry)
                self.server_started = True
                logger.info(f"✅ Metrics server démarré sur port {self.config.prometheus_port}")
            except Exception as e:
                logger.error(f"❌ Erreur démarrage metrics server: {e}")
    
    async def export_all_metrics(self):
        """Exporter toutes les métriques"""
        
        if not self.server_started:
            await self.start_server()
        
        try:
            # Performance
            perf = await self.state.get_performance()
            self.total_pnl.set(perf.get('total_pnl', 0))
            self.today_pnl.set(perf.get('today_pnl', 0))
            self.win_rate.set(perf.get('win_rate', 0))
            self.sharpe_ratio.set(perf.get('sharpe_ratio', 0))
            self.max_drawdown.set(perf.get('max_drawdown', 0))
            
            # Allocation
            allocation = await self.state.get_allocation()
            self.allocation_pct.labels(category='arbitrage').set(allocation.get('arbitrage_pct', 0))
            self.allocation_pct.labels(category='trading').set(allocation.get('trading_pct', 0))
            self.allocation_pct.labels(category='reserve').set(allocation.get('reserve_pct', 0))
            self.trading_budget.set(allocation.get('trading_budget', 0))
            self.arb_budget.set(allocation.get('arbitrage_budget', 0))
            
            risk_map = {'low': 0, 'medium': 1, 'high': 2}
            self.risk_level.set(risk_map.get(allocation.get('risk_level', 'medium'), 1))
            
            # Market
            market = await self.state.get_market_state()
            self.btc_price.set(market.get('btc_price', 0))
            self.btc_change_24h.set(market.get('btc_change_24h', 0))
            
            volatility_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
            self.market_volatility.set(volatility_map.get(market.get('volatility_level', 'MEDIUM'), 1))
            
            # Sentiment
            sentiment = await self.state.get('sentiment_data', {})
            self.sentiment_score.set(sentiment.get('composite_score', 0))
            self.fear_greed.set(sentiment.get('fear_greed', 50))
            self.news_count.set(sentiment.get('news_count', 0))
            self.sentiment_trend.set(sentiment.get('trend_1h', 0))
            
            # Arbitrage
            arb_stats = await self.state.get('arbitrage_stats', {})
            self.arb_profit.set(arb_stats.get('total_profit', 0))
            self.arb_opportunities.labels(type='cross_exchange').set(arb_stats.get('active_opportunities', 0))
            self.arb_opportunities.labels(type='funding').set(arb_stats.get('funding_opportunities', 0))
            
            # Model
            model_info = await self.state.get_model_info()
            self.model_accuracy.set(model_info.get('accuracy', 0))
            self.model_sharpe.set(model_info.get('sharpe', 0))
            self.model_version.info({
                'version': model_info.get('version', 'unknown'),
                'last_trained': model_info.get('last_trained', 'never')
            })
            
            # Health
            health = await self.state.get('health_status', {})
            self.bot_running.set(1 if health.get('all_healthy', True) else 0)
            self.uptime_seconds.set(health.get('uptime_hours', 0) * 3600)
            
            for name, data in health.get('components', {}).items():
                self.component_health.labels(component=name).set(1 if data.get('running') else 0)
            
            # Timestamp
            self.last_update.set(datetime.now().timestamp())
            
        except Exception as e:
            logger.error(f"❌ Erreur export metrics: {e}")
    
    def get_metrics(self) -> bytes:
        """Récupérer les métriques au format Prometheus"""
        return generate_latest(self.registry)
