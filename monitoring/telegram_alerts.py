#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               TELEGRAM ALERT ENGINE - V5                                     ║
║                                                                              ║
║  Types d'alertes:                                                            ║
║  • Startup/Shutdown                                                          ║
║  • Trades exécutés                                                           ║
║  • Opportunités arbitrage                                                    ║
║  • Changements d'allocation                                                  ║
║  • Alertes sentiment                                                         ║
║  • Dégradation performance                                                   ║
║  • Stress tests                                                              ║
║  • Health checks                                                             ║
║  • Reports périodiques (4h)                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

from loguru import logger

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TelegramAlertEngine:
    """Moteur d'alertes Telegram enrichies"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        self.bot_token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.grafana_url = config.grafana_url
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("⚠️ Telegram non configuré - alertes désactivées")
    
    async def initialize(self):
        """Initialiser la session HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def _send_message(self, text: str, parse_mode: str = "HTML"):
        """Envoyer un message Telegram"""
        
        if not self.enabled:
            logger.debug(f"Telegram (disabled): {text[:100]}...")
            return
        
        await self.initialize()
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            async with self.session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.warning(f"Telegram error: {error}")
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # STARTUP / SHUTDOWN
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_startup_message(self):
        """Message de démarrage"""
        
        allocation = await self.state.get_allocation()
        
        mode = "📝 PAPER" if self.config.paper_trading else "🔴 LIVE"
        
        message = f"""
🚀 <b>TRADINGBOT V5 DÉMARRÉ</b>

━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>Configuration</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Mode: {mode}
• Budget: <code>${self.config.total_budget:,.2f}</code>
• Paires: {len(self.config.trading_pairs)}
• Exchanges: {len(self.config.arbitrage_exchanges)}

━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Allocation Initiale</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Arbitrage: {allocation.get('arbitrage_pct', 0):.0f}% (${allocation.get('arbitrage_budget', 0):,.2f})
• Trading: {allocation.get('trading_pct', 0):.0f}% (${allocation.get('trading_budget', 0):,.2f})
• Reserve: {allocation.get('reserve_pct', 0):.0f}% (${allocation.get('reserve_budget', 0):,.2f})

━━━━━━━━━━━━━━━━━━━━━━━
🔗 <b>Liens</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 <a href="{self.grafana_url}">Dashboard Grafana</a>

⏰ Démarré à: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self._send_message(message)
    
    async def send_shutdown_message(self):
        """Message d'arrêt"""
        
        perf = await self.state.get_performance()
        uptime = await self._get_uptime()
        
        message = f"""
🛑 <b>TRADINGBOT V5 ARRÊTÉ</b>

━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Session Summary</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Uptime: {uptime}
• Total PnL: <code>${perf.get('total_pnl', 0):+,.2f}</code>
• Trades: {perf.get('total_trades', 0)}
• Win Rate: {perf.get('win_rate', 0):.1%}

⏰ Arrêté à: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # TRADES
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_trade_alert(self, trade: Dict):
        """Alerte de trade exécuté"""
        
        side_emoji = "🟢" if trade.get('side') == 'long' else "🔴"
        
        message = f"""
{side_emoji} <b>TRADE EXÉCUTÉ</b>

━━━━━━━━━━━━━━━━━━━━━━━
• Symbol: <code>{trade.get('symbol')}</code>
• Side: <b>{trade.get('side', '').upper()}</b>
• Entry: <code>${trade.get('entry_price', 0):,.4f}</code>
• Size: <code>${trade.get('size', 0):,.2f}</code>
• Stop Loss: <code>${trade.get('stop_loss', 0):,.4f}</code>
• Confidence: {trade.get('confidence', 0):.1%}

💡 <i>{trade.get('reasoning', 'N/A')}</i>
"""
        await self._send_message(message)
    
    async def send_trade_closed_alert(self, trade: Dict):
        """Alerte de trade fermé"""
        
        pnl = trade.get('pnl', 0)
        pnl_emoji = "✅" if pnl > 0 else "❌"
        
        message = f"""
{pnl_emoji} <b>TRADE FERMÉ</b>

━━━━━━━━━━━━━━━━━━━━━━━
• Symbol: <code>{trade.get('symbol')}</code>
• Entry: <code>${trade.get('entry_price', 0):,.4f}</code>
• Exit: <code>${trade.get('exit_price', 0):,.4f}</code>
• PnL: <code>${pnl:+,.2f}</code>
• Raison: {trade.get('reason', 'N/A')}
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # ARBITRAGE
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_arbitrage_alert(self, opportunity: Dict):
        """Alerte d'opportunité d'arbitrage exécutée"""
        
        message = f"""
🔄 <b>ARBITRAGE EXÉCUTÉ</b>

━━━━━━━━━━━━━━━━━━━━━━━
• Type: <b>{opportunity.get('arb_type', 'N/A').upper()}</b>
• Symbol: <code>{opportunity.get('symbol')}</code>
• Buy: {opportunity.get('buy_exchange')} @ ${opportunity.get('buy_price', 0):,.4f}
• Sell: {opportunity.get('sell_exchange')} @ ${opportunity.get('sell_price', 0):,.4f}
• Spread: <code>{opportunity.get('spread', 0):.3f}%</code>
• Profit: <code>${opportunity.get('profit', 0):+,.2f}</code>
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # ALLOCATION
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_allocation_update(self, allocation):
        """Mise à jour d'allocation"""
        
        message = f"""
💰 <b>ALLOCATION MISE À JOUR</b>

━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Nouvelle Répartition</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Arbitrage: <code>{allocation.arbitrage_pct:.0f}%</code> (${allocation.arbitrage_budget:,.2f})
  └─ Focus: {', '.join(allocation.arbitrage_focus)}
• Trading: <code>{allocation.trading_pct:.0f}%</code> (${allocation.trading_budget:,.2f})
  └─ Bias: {allocation.trading_bias}
• Reserve: <code>{allocation.reserve_pct:.0f}%</code> (${allocation.reserve_budget:,.2f})

⚡ Risk Level: <b>{allocation.risk_level.upper()}</b>

💡 <i>{allocation.reasoning}</i>

🔄 Prochain rééquilibrage dans: {allocation.rebalance_in_hours}h
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # SENTIMENT
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_sentiment_alert(self, sentiment: Dict):
        """Alerte de changement de sentiment"""
        
        score = sentiment.get('composite_score', 0)
        
        if score < -0.3:
            emoji = "🔴"
            level = "FEAR"
        elif score > 0.3:
            emoji = "🟢"
            level = "GREED"
        else:
            emoji = "🟡"
            level = "NEUTRAL"
        
        message = f"""
{emoji} <b>ALERTE SENTIMENT</b>

━━━━━━━━━━━━━━━━━━━━━━━
• Score: <code>{score:+.2f}</code>
• Level: <b>{level}</b>
• Fear & Greed: {sentiment.get('fear_greed', 50)}
• Trend 1h: <code>{sentiment.get('trend_1h', 0):+.2f}</code>

⚠️ <b>Raison:</b>
<i>{sentiment.get('alert_reason', 'N/A')}</i>

📰 News récentes: {sentiment.get('news_count', 0)}
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # MODEL UPDATE
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_model_update_alert(self, result: Dict):
        """Alerte de mise à jour du modèle ML"""
        
        message = f"""
🧠 <b>MODÈLE ML MIS À JOUR</b>

━━━━━━━━━━━━━━━━━━━━━━━
• Version: <code>{result.get('old_version', 'N/A')} → {result.get('new_version', 'N/A')}</code>
• Amélioration: <code>{result.get('improvement_pct', 0):+.1f}%</code>

📊 <b>Métriques du nouveau modèle:</b>
• Accuracy: {result.get('new_metrics', {}).accuracy if hasattr(result.get('new_metrics', {}), 'accuracy') else 'N/A'}
• Sharpe: {result.get('new_metrics', {}).sharpe_backtest if hasattr(result.get('new_metrics', {}), 'sharpe_backtest') else 'N/A'}
• Win Rate: {result.get('new_metrics', {}).win_rate_backtest if hasattr(result.get('new_metrics', {}), 'win_rate_backtest') else 'N/A'}

🔄 Hot-swap effectué avec succès!
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # DEGRADATION
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_degradation_alert(self, result: Dict):
        """Alerte de dégradation de performance"""
        
        alerts = result.get('alerts', [])
        alert_text = "\n".join([f"• {a.get('message', 'N/A')}" for a in alerts])
        
        message = f"""
⚠️ <b>ALERTE DÉGRADATION</b>

━━━━━━━━━━━━━━━━━━━━━━━
{alert_text}

📊 <b>Action recommandée:</b>
Vérifier les conditions de marché et considérer une réduction de l'exposition.
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # STRESS TESTS
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_stress_test_report(self, results: Dict):
        """Rapport de stress tests"""
        
        overall = results.get('overall_status', 'unknown')
        status_emoji = "✅" if overall == 'passed' else "⚠️" if overall == 'warning' else "❌"
        
        scenarios = results.get('scenarios', {})
        scenario_text = ""
        for name, data in scenarios.items():
            s_emoji = "✅" if data.get('passed') else "❌"
            scenario_text += f"• {s_emoji} {name}: {data.get('max_loss', 0):.1%} max loss\n"
        
        message = f"""
🧪 <b>RAPPORT STRESS TESTS</b>

━━━━━━━━━━━━━━━━━━━━━━━
{status_emoji} Status Global: <b>{overall.upper()}</b>

📊 <b>Scénarios:</b>
{scenario_text}
📈 VaR 95%: <code>{results.get('var_95', 0):.2%}</code>
📈 VaR 99%: <code>{results.get('var_99', 0):.2%}</code>

🔗 <a href="{self.grafana_url}">Voir détails sur Grafana</a>
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # HEALTH
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_health_alert(self, health: Dict):
        """Alerte de santé système"""
        
        components = health.get('components', {})
        
        component_text = ""
        for name, data in components.items():
            emoji = "✅" if data.get('running') else "❌"
            error = f" - {data.get('error', '')[:50]}" if data.get('error') else ""
            component_text += f"• {emoji} {name}{error}\n"
        
        message = f"""
🏥 <b>ALERTE SANTÉ SYSTÈME</b>

━━━━━━━━━━━━━━━━━━━━━━━
⏱ Uptime: {health.get('uptime_hours', 0):.1f}h

📊 <b>Composants:</b>
{component_text}
⚠️ <b>Action requise:</b> Vérifier les logs du système.
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # PERIODIC REPORTS
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_periodic_report(self):
        """Rapport périodique (toutes les 4h)"""
        
        perf = await self.state.get_performance()
        allocation = await self.state.get_allocation()
        market = await self.state.get_market_state()
        arb_stats = await self.state.get('arbitrage_stats', {})
        sentiment = await self.state.get('sentiment_data', {})
        
        # Calcul du P&L
        total_pnl = perf.get('total_pnl', 0)
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        
        # Fear & Greed
        fg = market.get('fear_greed', 50)
        if fg <= 25:
            fg_emoji = "😱"
        elif fg <= 45:
            fg_emoji = "😨"
        elif fg <= 55:
            fg_emoji = "😐"
        elif fg <= 75:
            fg_emoji = "😊"
        else:
            fg_emoji = "🤑"
        
        message = f"""
📊 <b>RAPPORT PÉRIODIQUE</b>

━━━━━━━━━━━━━━━━━━━━━━━
{pnl_emoji} <b>Performance</b>
━━━━━━━━━━━━━━━━━━━━━━━
• PnL Total: <code>${total_pnl:+,.2f}</code>
• PnL Aujourd'hui: <code>${perf.get('today_pnl', 0):+,.2f}</code>
• Win Rate: <code>{perf.get('win_rate', 0):.1%}</code>
• Trades: {perf.get('total_trades', 0)}

━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Allocation Actuelle</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Arbitrage: {allocation.get('arbitrage_pct', 0):.0f}%
• Trading: {allocation.get('trading_pct', 0):.0f}%
• Reserve: {allocation.get('reserve_pct', 0):.0f}%

━━━━━━━━━━━━━━━━━━━━━━━
🔄 <b>Arbitrage Stats</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Scans: {arb_stats.get('total_scans', 0)}
• Opportunités: {arb_stats.get('total_opportunities', 0)}
• Profit: <code>${arb_stats.get('total_profit', 0):+,.2f}</code>

━━━━━━━━━━━━━━━━━━━━━━━
📰 <b>Sentiment</b>
━━━━━━━━━━━━━━━━━━━━━━━
• Score: <code>{sentiment.get('composite_score', 0):+.2f}</code>
• Level: {sentiment.get('level', 'N/A')}
• {fg_emoji} Fear & Greed: {fg}

━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>Marché</b>
━━━━━━━━━━━━━━━━━━━━━━━
• BTC: <code>${market.get('btc_price', 0):,.2f}</code> ({market.get('btc_change_24h', 0):+.2f}%)
• Volatilité: {market.get('volatility_level', 'N/A')}
• Régime: {market.get('regime', 'N/A')}

🔗 <a href="{self.grafana_url}">Dashboard Grafana</a>
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # ERRORS
    # ══════════════════════════════════════════════════════════════════════════
    
    async def send_error_alert(self, component: str, error: str):
        """Alerte d'erreur"""
        
        message = f"""
❌ <b>ERREUR SYSTÈME</b>

━━━━━━━━━━━━━━━━━━━━━━━
• Composant: <code>{component}</code>
• Erreur: <i>{error[:500]}</i>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self._send_message(message)
    
    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    
    async def _get_uptime(self) -> str:
        """Calculer l'uptime"""
        health = await self.state.get('health_status', {})
        hours = health.get('uptime_hours', 0)
        
        if hours < 1:
            return f"{int(hours * 60)}m"
        elif hours < 24:
            return f"{hours:.1f}h"
        else:
            days = hours / 24
            return f"{days:.1f}j"
    
    async def close(self):
        """Fermer la session HTTP"""
        if self.session:
            await self.session.close()
