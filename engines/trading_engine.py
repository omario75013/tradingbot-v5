#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               LIVE TRADING ENGINE - V5                                       ║
║                                                                              ║
║  Trading directionnel avec:                                                  ║
║  • Analyse technique multi-timeframe                                         ║
║  • Validation ML                                                             ║
║  • Décision finale par Claude AI                                             ║
║  • Risk management intégré                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json

import pandas as pd
import numpy as np
from loguru import logger

try:
    import ccxt.async_support as ccxt
except ImportError:
    ccxt = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


@dataclass
class TradeSignal:
    """Signal de trading"""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    size: float
    reasoning: str
    technical_score: float
    ml_score: float
    sentiment_score: float


@dataclass 
class Position:
    """Position ouverte"""
    id: str
    symbol: str
    side: str
    entry_price: float
    current_price: float
    size: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    opened_at: datetime


class LiveTradingEngine:
    """Moteur de trading live"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        # Claude AI client
        self.claude = None
        if Anthropic and config.anthropic_api_key:
            self.claude = Anthropic(api_key=config.anthropic_api_key)
        
        # Exchange clients
        self.exchanges: Dict[str, Any] = {}
        
        # Positions ouvertes
        self.positions: Dict[str, Position] = {}
        
        # Risk limits
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.last_reset_date = datetime.now().date()
        
    async def initialize_exchanges(self):
        """Initialiser les connexions exchanges"""
        
        if not ccxt:
            logger.warning("⚠️ ccxt non disponible")
            return
        
        exchange_configs = {
            'binance': {
                'apiKey': self.config.binance_api_key,
                'secret': self.config.binance_api_secret,
                'sandbox': self.config.paper_trading
            },
            'bybit': {
                'apiKey': self.config.bybit_api_key,
                'secret': self.config.bybit_api_secret,
                'sandbox': self.config.paper_trading
            }
        }
        
        for name, cfg in exchange_configs.items():
            if cfg.get('apiKey'):
                try:
                    exchange_class = getattr(ccxt, name)
                    self.exchanges[name] = exchange_class(cfg)
                    await self.exchanges[name].load_markets()
                    logger.info(f"✅ {name} connecté")
                except Exception as e:
                    logger.error(f"❌ {name} erreur: {e}")
    
    async def run_cycle(self):
        """Cycle principal de trading"""
        
        # Reset quotidien
        if datetime.now().date() != self.last_reset_date:
            self.daily_trades = 0
            self.last_reset_date = datetime.now().date()
        
        # Vérifier les limites de risque
        if not await self._check_risk_limits():
            logger.warning("⚠️ Limites de risque atteintes - pause trading")
            return
        
        # Récupérer l'allocation
        allocation = await self.state.get_allocation()
        trading_budget = allocation.get('trading_budget', 0)
        
        if trading_budget <= 0:
            logger.debug("Pas de budget trading alloué")
            return
        
        # Mettre à jour les positions existantes
        await self._update_positions()
        
        # Chercher de nouvelles opportunités
        for symbol in self.config.trading_pairs:
            try:
                signal = await self._analyze_symbol(symbol, trading_budget)
                
                if signal and signal.confidence >= 0.6:
                    # Valider avec Claude AI
                    validated = await self._validate_with_claude(signal)
                    
                    if validated:
                        await self._execute_trade(signal)
                        
            except Exception as e:
                logger.error(f"Erreur analyse {symbol}: {e}")
        
        # Gérer les positions existantes
        await self._manage_positions()
    
    async def _check_risk_limits(self) -> bool:
        """Vérifier les limites de risque"""
        
        # Trades quotidiens
        if self.daily_trades >= self.config.max_daily_trades:
            return False
        
        # Pertes consécutives
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            return False
        
        # Drawdown
        perf = await self.state.get_performance()
        if perf.get('max_drawdown', 0) >= self.config.max_drawdown_pct / 100:
            return False
        
        return True
    
    async def _analyze_symbol(self, symbol: str, budget: float) -> Optional[TradeSignal]:
        """Analyser un symbole pour signal de trading"""
        
        # Récupérer les données
        ohlcv = await self._fetch_ohlcv(symbol)
        if ohlcv is None or len(ohlcv) < 50:
            return None
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Analyse technique
        technical_signal = self._calculate_technical_indicators(df)
        
        # Score ML
        ml_score = await self._get_ml_prediction(symbol, df)
        
        # Score sentiment
        sentiment = await self.state.get('sentiment_data', {})
        sentiment_score = sentiment.get('composite_score', 0)
        
        # Combiner les scores
        combined_score = (
            technical_signal['score'] * 0.4 +
            ml_score * 0.35 +
            sentiment_score * 0.25
        )
        
        # Déterminer la direction
        if combined_score > 0.2:
            side = 'long'
        elif combined_score < -0.2:
            side = 'short'
        else:
            return None
        
        current_price = df['close'].iloc[-1]
        atr = self._calculate_atr(df)
        
        # Position sizing (Kelly Criterion simplifié)
        win_rate = await self._get_win_rate()
        position_size = self._calculate_position_size(budget, win_rate, abs(combined_score))
        
        # Stop loss et take profit
        if side == 'long':
            stop_loss = current_price - (2 * atr)
            take_profit = current_price + (3 * atr)
        else:
            stop_loss = current_price + (2 * atr)
            take_profit = current_price - (3 * atr)
        
        return TradeSignal(
            symbol=symbol,
            side=side,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=min(abs(combined_score), 1.0),
            size=position_size,
            reasoning=f"Technical: {technical_signal['reason']}, ML: {ml_score:.2f}, Sentiment: {sentiment_score:.2f}",
            technical_score=technical_signal['score'],
            ml_score=ml_score,
            sentiment_score=sentiment_score
        )
    
    async def _fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[List]:
        """Récupérer les données OHLCV"""
        
        if not self.exchanges:
            await self.initialize_exchanges()
        
        for name, exchange in self.exchanges.items():
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                return ohlcv
            except Exception as e:
                logger.debug(f"{name} fetch error: {e}")
        
        return None
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculer les indicateurs techniques"""
        
        signals = []
        
        # EMA Cross
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        
        if df['ema_20'].iloc[-1] > df['ema_50'].iloc[-1]:
            signals.append(('EMA bullish', 0.3))
        else:
            signals.append(('EMA bearish', -0.3))
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        if rsi.iloc[-1] < 30:
            signals.append(('RSI oversold', 0.4))
        elif rsi.iloc[-1] > 70:
            signals.append(('RSI overbought', -0.4))
        else:
            signals.append(('RSI neutral', 0))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9).mean()
        
        if macd.iloc[-1] > signal_line.iloc[-1]:
            signals.append(('MACD bullish', 0.3))
        else:
            signals.append(('MACD bearish', -0.3))
        
        # Calculer score total
        total_score = sum(s[1] for s in signals) / len(signals)
        reasons = [s[0] for s in signals if s[1] != 0]
        
        return {
            'score': total_score,
            'reason': ', '.join(reasons),
            'rsi': rsi.iloc[-1],
            'macd': macd.iloc[-1],
            'signal': signal_line.iloc[-1]
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculer l'ATR"""
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr.iloc[-1]
    
    async def _get_ml_prediction(self, symbol: str, df: pd.DataFrame) -> float:
        """Obtenir la prédiction du modèle ML"""
        
        model_info = await self.state.get_model_info()
        
        # Simulation - en production, charger le vrai modèle
        # return model.predict(features)
        
        # Pour l'instant, retourner un score basé sur momentum
        returns = df['close'].pct_change()
        momentum = returns.tail(10).mean()
        
        return np.clip(momentum * 10, -1, 1)
    
    async def _get_win_rate(self) -> float:
        """Récupérer le win rate historique"""
        
        perf = await self.state.get_performance()
        return perf.get('win_rate', 0.5)
    
    def _calculate_position_size(self, budget: float, win_rate: float, edge: float) -> float:
        """Calculer la taille de position (Kelly Criterion)"""
        
        # Kelly = W - (1-W)/R où W = win rate, R = reward/risk ratio
        R = 1.5  # Risk/reward ratio cible
        kelly = win_rate - ((1 - win_rate) / R)
        
        # Fraction du Kelly pour être conservateur
        fractional_kelly = kelly * self.config.kelly_fraction
        
        # Limiter à max_position_pct
        max_pct = self.config.max_position_pct / 100
        position_pct = min(max(fractional_kelly, 0.01), max_pct)
        
        return budget * position_pct
    
    async def _validate_with_claude(self, signal: TradeSignal) -> bool:
        """Valider le signal avec Claude AI"""
        
        if not self.claude:
            return True  # Pas de validation si Claude non disponible
        
        market_state = await self.state.get_market_state()
        sentiment = await self.state.get('sentiment_data', {})
        
        prompt = f"""Tu es un trader crypto expert. Évalue ce signal de trading:

SIGNAL:
- Symbole: {signal.symbol}
- Direction: {signal.side.upper()}
- Prix d'entrée: ${signal.entry_price:,.4f}
- Stop Loss: ${signal.stop_loss:,.4f}
- Take Profit: ${signal.take_profit:,.4f}
- Taille: ${signal.size:,.2f}
- Confiance: {signal.confidence:.1%}

SCORES:
- Technique: {signal.technical_score:+.2f}
- ML: {signal.ml_score:+.2f}
- Sentiment: {signal.sentiment_score:+.2f}

CONTEXTE MARCHÉ:
- BTC: ${market_state.get('btc_price', 0):,.2f}
- Fear & Greed: {market_state.get('fear_greed', 50)}
- Régime: {market_state.get('regime', 'UNKNOWN')}
- Sentiment global: {sentiment.get('level', 'neutral')}

Réponds UNIQUEMENT par un JSON:
{{"approved": true/false, "reason": "explication courte"}}
"""
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            
            # Parser la réponse JSON
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                logger.info(f"Claude validation: {'✅' if result['approved'] else '❌'} - {result['reason']}")
                
                return result.get('approved', False)
                
        except Exception as e:
            logger.error(f"Claude validation error: {e}")
        
        return False
    
    async def _execute_trade(self, signal: TradeSignal):
        """Exécuter le trade"""
        
        if self.config.paper_trading:
            # Paper trading - simuler l'exécution
            trade_id = f"paper_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            position = Position(
                id=trade_id,
                symbol=signal.symbol,
                side=signal.side,
                entry_price=signal.entry_price,
                current_price=signal.entry_price,
                size=signal.size,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                unrealized_pnl=0,
                opened_at=datetime.now()
            )
            
            self.positions[trade_id] = position
            
            logger.info(f"""
📈 TRADE EXÉCUTÉ (Paper)
   {signal.side.upper()} {signal.symbol}
   Entry: ${signal.entry_price:,.4f}
   Size: ${signal.size:,.2f}
   SL: ${signal.stop_loss:,.4f} | TP: ${signal.take_profit:,.4f}
            """)
            
        else:
            # Live trading
            # TODO: Implémenter l'exécution réelle
            pass
        
        self.daily_trades += 1
        
        # Enregistrer le trade
        trade_record = {
            'id': signal.symbol + '_' + datetime.now().isoformat(),
            'symbol': signal.symbol,
            'side': signal.side,
            'entry_price': signal.entry_price,
            'size': signal.size,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'confidence': signal.confidence,
            'reasoning': signal.reasoning,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.state.add_trade(trade_record)
        
        # Alerte Telegram
        from monitoring.telegram_alerts import TelegramAlertEngine
        alert_engine = TelegramAlertEngine(self.config, self.state)
        await alert_engine.send_trade_alert(trade_record)
    
    async def _update_positions(self):
        """Mettre à jour les positions avec les prix actuels"""
        
        for pos_id, position in list(self.positions.items()):
            try:
                ohlcv = await self._fetch_ohlcv(position.symbol, limit=1)
                if ohlcv:
                    current_price = ohlcv[-1][4]  # Close price
                    position.current_price = current_price
                    
                    # Calculer PnL non réalisé
                    if position.side == 'long':
                        position.unrealized_pnl = (current_price - position.entry_price) / position.entry_price * position.size
                    else:
                        position.unrealized_pnl = (position.entry_price - current_price) / position.entry_price * position.size
                        
            except Exception as e:
                logger.error(f"Update position error: {e}")
    
    async def _manage_positions(self):
        """Gérer les positions existantes (SL/TP)"""
        
        for pos_id, position in list(self.positions.items()):
            should_close = False
            close_reason = ""
            
            if position.side == 'long':
                if position.current_price <= position.stop_loss:
                    should_close = True
                    close_reason = "Stop Loss hit"
                elif position.current_price >= position.take_profit:
                    should_close = True
                    close_reason = "Take Profit hit"
            else:
                if position.current_price >= position.stop_loss:
                    should_close = True
                    close_reason = "Stop Loss hit"
                elif position.current_price <= position.take_profit:
                    should_close = True
                    close_reason = "Take Profit hit"
            
            if should_close:
                await self._close_position(position, close_reason)
    
    async def _close_position(self, position: Position, reason: str):
        """Fermer une position"""
        
        pnl = position.unrealized_pnl
        
        # Mettre à jour les stats
        if pnl > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        logger.info(f"""
📊 POSITION FERMÉE
   {position.symbol} {position.side.upper()}
   Entry: ${position.entry_price:,.4f} → Exit: ${position.current_price:,.4f}
   PnL: ${pnl:+,.2f}
   Raison: {reason}
        """)
        
        # Enregistrer
        trade_record = {
            'symbol': position.symbol,
            'side': position.side,
            'entry_price': position.entry_price,
            'exit_price': position.current_price,
            'pnl': pnl,
            'reason': reason,
            'closed_at': datetime.now().isoformat()
        }
        
        await self.state.add_trade(trade_record)
        
        # Mise à jour performance
        perf = await self.state.get_performance()
        perf['total_pnl'] = perf.get('total_pnl', 0) + pnl
        perf['total_trades'] = perf.get('total_trades', 0) + 1
        
        trades = await self.state.get_trades_history()
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        perf['win_rate'] = wins / len(trades) if trades else 0.5
        
        await self.state.update_performance(perf)
        
        # Supprimer la position
        del self.positions[position.id]
        
        # Alerte
        from monitoring.telegram_alerts import TelegramAlertEngine
        alert_engine = TelegramAlertEngine(self.config, self.state)
        await alert_engine.send_trade_closed_alert(trade_record)
