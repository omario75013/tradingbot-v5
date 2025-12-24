#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               ARBITRAGE SCANNER ENGINE - V5                                  ║
║                                                                              ║
║  Types d'arbitrage:                                                          ║
║  • Cross-Exchange (même paire, exchanges différents)                         ║
║  • Triangulaire (BTC→ETH→USDT→BTC)                                          ║
║  • Funding Rate (long spot + short perp)                                     ║
║  • Stablecoin (désancrage USDT/USDC/DAI)                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

import pandas as pd
import numpy as np
from loguru import logger

try:
    import ccxt.async_support as ccxt
except ImportError:
    ccxt = None


class ArbitrageType(Enum):
    CROSS_EXCHANGE = "cross_exchange"
    TRIANGULAR = "triangular"
    FUNDING_RATE = "funding_rate"
    STABLECOIN = "stablecoin"


@dataclass
class ArbitrageOpportunity:
    """Opportunité d'arbitrage"""
    id: str
    arb_type: ArbitrageType
    symbol: str
    
    # Prix
    buy_exchange: str
    buy_price: float
    sell_exchange: str
    sell_price: float
    
    # Profit
    spread: float  # En %
    net_profit: float  # Après frais
    gross_profit: float
    
    # Exécution
    max_size: float
    execution_time_ms: int
    
    # Métadonnées
    timestamp: datetime
    confidence: float
    details: Dict = field(default_factory=dict)


@dataclass
class FundingRateOpportunity:
    """Opportunité Funding Rate"""
    symbol: str
    exchange: str
    funding_rate: float  # %
    next_funding_time: datetime
    annual_rate: float  # Taux annualisé
    direction: str  # 'long_spot_short_perp' ou inverse
    estimated_profit: float


class ArbitrageScannerEngine:
    """Moteur de scan d'arbitrage multi-type"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        # Exchanges
        self.exchanges: Dict[str, Any] = {}
        
        # Stats
        self.total_scans = 0
        self.total_opportunities = 0
        self.total_profit = 0.0
        
        # Frais par exchange (en %)
        self.fee_rates = {
            'binance': 0.075,  # Avec BNB discount
            'bybit': 0.075,
            'okx': 0.08,
            'kucoin': 0.1,
            'mexc': 0.1
        }
        
        # Triangular paths
        self.triangular_paths = [
            ['BTC/USDT', 'ETH/BTC', 'ETH/USDT'],
            ['BTC/USDT', 'SOL/BTC', 'SOL/USDT'],
            ['ETH/USDT', 'SOL/ETH', 'SOL/USDT'],
        ]
        
        # Stablecoins
        self.stablecoins = ['USDT', 'USDC', 'DAI', 'BUSD']
    
    async def initialize(self):
        """Initialiser les connexions exchanges"""
        
        if not ccxt:
            logger.warning("⚠️ ccxt non disponible")
            return
        
        exchange_configs = {
            'binance': {
                'apiKey': self.config.binance_api_key,
                'secret': self.config.binance_api_secret,
                'options': {'defaultType': 'spot'}
            },
            'bybit': {
                'apiKey': self.config.bybit_api_key,
                'secret': self.config.bybit_api_secret
            },
            'okx': {
                'apiKey': self.config.okx_api_key,
                'secret': self.config.okx_api_secret,
                'password': self.config.okx_passphrase
            }
        }
        
        for name in self.config.arbitrage_exchanges:
            if name in exchange_configs:
                cfg = exchange_configs[name]
                if cfg.get('apiKey') or name == 'binance':  # Binance peut fonctionner sans clé pour les prix
                    try:
                        exchange_class = getattr(ccxt, name)
                        self.exchanges[name] = exchange_class(cfg)
                        await self.exchanges[name].load_markets()
                        logger.info(f"✅ Arbitrage: {name} connecté")
                    except Exception as e:
                        logger.error(f"❌ Arbitrage: {name} erreur: {e}")
    
    async def scan_all(self) -> List[ArbitrageOpportunity]:
        """Scanner toutes les opportunités d'arbitrage"""
        
        if not self.exchanges:
            await self.initialize()
        
        self.total_scans += 1
        
        all_opportunities = []
        
        # Récupérer le budget arbitrage
        allocation = await self.state.get_allocation()
        arb_budget = allocation.get('arbitrage_budget', 0)
        
        if arb_budget <= 0:
            logger.debug("Pas de budget arbitrage alloué")
            return []
        
        # Scanner les différents types
        tasks = [
            self._scan_cross_exchange(),
            self._scan_triangular(),
            self._scan_funding_rates(),
            self._scan_stablecoins()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_opportunities.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Scan error: {result}")
        
        # Filtrer par profit minimum
        min_profit = self.config.min_arbitrage_profit_pct / 100
        profitable = [o for o in all_opportunities if o.spread >= min_profit]
        
        # Trier par profit
        profitable.sort(key=lambda x: x.net_profit, reverse=True)
        
        self.total_opportunities += len(profitable)
        
        # Exécuter les meilleures opportunités
        for opp in profitable[:3]:  # Max 3 simultanées
            if opp.confidence >= 0.7:
                await self._execute_arbitrage(opp, arb_budget)
        
        # Sauvegarder stats
        await self._save_stats()
        
        if profitable:
            logger.info(f"🔄 Scan #{self.total_scans}: {len(profitable)} opportunités trouvées")
        
        return profitable
    
    async def _scan_cross_exchange(self) -> List[ArbitrageOpportunity]:
        """Scanner les opportunités cross-exchange"""
        
        opportunities = []
        
        if len(self.exchanges) < 2:
            return opportunities
        
        for symbol in self.config.trading_pairs:
            prices = {}
            
            # Récupérer les prix de tous les exchanges
            for name, exchange in self.exchanges.items():
                try:
                    ticker = await exchange.fetch_ticker(symbol)
                    prices[name] = {
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'volume': ticker.get('quoteVolume', 0)
                    }
                except Exception as e:
                    logger.debug(f"{name} ticker error for {symbol}: {e}")
            
            if len(prices) < 2:
                continue
            
            # Comparer toutes les paires d'exchanges
            exchange_names = list(prices.keys())
            for i in range(len(exchange_names)):
                for j in range(i + 1, len(exchange_names)):
                    ex1, ex2 = exchange_names[i], exchange_names[j]
                    
                    # Acheter sur ex1, vendre sur ex2
                    spread_1to2 = (prices[ex2]['bid'] - prices[ex1]['ask']) / prices[ex1]['ask']
                    
                    # Acheter sur ex2, vendre sur ex1
                    spread_2to1 = (prices[ex1]['bid'] - prices[ex2]['ask']) / prices[ex2]['ask']
                    
                    # Vérifier si profitable
                    total_fees = self.fee_rates.get(ex1, 0.1) + self.fee_rates.get(ex2, 0.1)
                    
                    if spread_1to2 > total_fees / 100:
                        net_profit = spread_1to2 - (total_fees / 100)
                        opp = ArbitrageOpportunity(
                            id=f"cross_{symbol}_{ex1}_{ex2}_{datetime.now().timestamp()}",
                            arb_type=ArbitrageType.CROSS_EXCHANGE,
                            symbol=symbol,
                            buy_exchange=ex1,
                            buy_price=prices[ex1]['ask'],
                            sell_exchange=ex2,
                            sell_price=prices[ex2]['bid'],
                            spread=spread_1to2 * 100,
                            net_profit=net_profit * 100,
                            gross_profit=spread_1to2 * 100,
                            max_size=min(prices[ex1]['volume'], prices[ex2]['volume']) * 0.01,
                            execution_time_ms=500,
                            timestamp=datetime.now(),
                            confidence=0.8 if spread_1to2 > 0.002 else 0.6,
                            details={'fees': total_fees}
                        )
                        opportunities.append(opp)
                    
                    if spread_2to1 > total_fees / 100:
                        net_profit = spread_2to1 - (total_fees / 100)
                        opp = ArbitrageOpportunity(
                            id=f"cross_{symbol}_{ex2}_{ex1}_{datetime.now().timestamp()}",
                            arb_type=ArbitrageType.CROSS_EXCHANGE,
                            symbol=symbol,
                            buy_exchange=ex2,
                            buy_price=prices[ex2]['ask'],
                            sell_exchange=ex1,
                            sell_price=prices[ex1]['bid'],
                            spread=spread_2to1 * 100,
                            net_profit=net_profit * 100,
                            gross_profit=spread_2to1 * 100,
                            max_size=min(prices[ex1]['volume'], prices[ex2]['volume']) * 0.01,
                            execution_time_ms=500,
                            timestamp=datetime.now(),
                            confidence=0.8 if spread_2to1 > 0.002 else 0.6,
                            details={'fees': total_fees}
                        )
                        opportunities.append(opp)
        
        return opportunities
    
    async def _scan_triangular(self) -> List[ArbitrageOpportunity]:
        """Scanner les opportunités triangulaires"""
        
        opportunities = []
        
        for name, exchange in self.exchanges.items():
            for path in self.triangular_paths:
                try:
                    # Récupérer les prix pour chaque paire du triangle
                    prices = {}
                    for pair in path:
                        ticker = await exchange.fetch_ticker(pair)
                        prices[pair] = {
                            'bid': ticker['bid'],
                            'ask': ticker['ask']
                        }
                    
                    # Calculer le profit du triangle
                    # Exemple: BTC/USDT → ETH/BTC → ETH/USDT
                    # 1. Acheter ETH avec USDT
                    # 2. Vendre ETH pour BTC
                    # 3. Vendre BTC pour USDT
                    
                    # Direction 1
                    start_amount = 1000  # USDT
                    
                    # Acheter le premier asset
                    amount1 = start_amount / prices[path[0]]['ask']
                    
                    # Échanger via la deuxième paire
                    amount2 = amount1 * prices[path[1]]['bid']
                    
                    # Revenir en USDT
                    final_amount = amount2 * prices[path[2]]['bid']
                    
                    profit = (final_amount - start_amount) / start_amount
                    
                    # Déduire les frais (3 trades)
                    fees = 3 * self.fee_rates.get(name, 0.1) / 100
                    net_profit = profit - fees
                    
                    if net_profit > self.config.min_arbitrage_profit_pct / 100:
                        opp = ArbitrageOpportunity(
                            id=f"tri_{name}_{path[0]}_{datetime.now().timestamp()}",
                            arb_type=ArbitrageType.TRIANGULAR,
                            symbol=f"{path[0]}->{path[1]}->{path[2]}",
                            buy_exchange=name,
                            buy_price=prices[path[0]]['ask'],
                            sell_exchange=name,
                            sell_price=prices[path[2]]['bid'],
                            spread=profit * 100,
                            net_profit=net_profit * 100,
                            gross_profit=profit * 100,
                            max_size=1000,  # Limiter la taille
                            execution_time_ms=300,
                            timestamp=datetime.now(),
                            confidence=0.7,
                            details={'path': path, 'prices': prices}
                        )
                        opportunities.append(opp)
                        
                except Exception as e:
                    logger.debug(f"Triangular scan error on {name}: {e}")
        
        return opportunities
    
    async def _scan_funding_rates(self) -> List[ArbitrageOpportunity]:
        """Scanner les opportunités de funding rate"""
        
        opportunities = []
        
        # Binance funding rates
        if 'binance' in self.exchanges:
            try:
                # Utiliser l'API publique pour les funding rates
                exchange = self.exchanges['binance']
                
                for symbol in ['BTC/USDT', 'ETH/USDT']:
                    try:
                        # Récupérer le funding rate
                        futures_symbol = symbol.replace('/', '')
                        
                        # Note: En production, utiliser l'API funding rate
                        # Pour la simulation, on utilise une valeur estimée
                        funding_rate = 0.0001  # 0.01% par 8h
                        
                        annual_rate = funding_rate * 3 * 365  # 3 fois par jour * 365
                        
                        if abs(funding_rate) > 0.0005:  # > 0.05%
                            direction = 'long_spot_short_perp' if funding_rate > 0 else 'short_spot_long_perp'
                            
                            opp = ArbitrageOpportunity(
                                id=f"funding_{symbol}_{datetime.now().timestamp()}",
                                arb_type=ArbitrageType.FUNDING_RATE,
                                symbol=symbol,
                                buy_exchange='binance_spot',
                                buy_price=0,
                                sell_exchange='binance_futures',
                                sell_price=0,
                                spread=abs(funding_rate) * 100,
                                net_profit=abs(funding_rate) * 100,
                                gross_profit=abs(funding_rate) * 100,
                                max_size=10000,
                                execution_time_ms=1000,
                                timestamp=datetime.now(),
                                confidence=0.6,
                                details={
                                    'funding_rate': funding_rate,
                                    'annual_rate': annual_rate,
                                    'direction': direction
                                }
                            )
                            opportunities.append(opp)
                            
                    except Exception as e:
                        logger.debug(f"Funding rate error for {symbol}: {e}")
                        
            except Exception as e:
                logger.debug(f"Funding rates scan error: {e}")
        
        return opportunities
    
    async def _scan_stablecoins(self) -> List[ArbitrageOpportunity]:
        """Scanner les opportunités de désancrage stablecoin"""
        
        opportunities = []
        
        stablecoin_pairs = ['USDC/USDT', 'DAI/USDT', 'BUSD/USDT']
        
        for name, exchange in self.exchanges.items():
            for pair in stablecoin_pairs:
                try:
                    if pair in exchange.markets:
                        ticker = await exchange.fetch_ticker(pair)
                        
                        price = ticker['last']
                        deviation = abs(price - 1.0)
                        
                        if deviation > 0.002:  # > 0.2% de déviation
                            direction = 'buy' if price < 1.0 else 'sell'
                            
                            opp = ArbitrageOpportunity(
                                id=f"stable_{pair}_{name}_{datetime.now().timestamp()}",
                                arb_type=ArbitrageType.STABLECOIN,
                                symbol=pair,
                                buy_exchange=name,
                                buy_price=ticker['ask'] if direction == 'buy' else ticker['bid'],
                                sell_exchange=name,
                                sell_price=1.0,  # Prix cible
                                spread=deviation * 100,
                                net_profit=(deviation - 0.001) * 100,  # Moins les frais
                                gross_profit=deviation * 100,
                                max_size=50000,  # Limiter la taille
                                execution_time_ms=200,
                                timestamp=datetime.now(),
                                confidence=0.5,  # Risque de non-convergence
                                details={
                                    'current_price': price,
                                    'deviation': deviation,
                                    'direction': direction
                                }
                            )
                            opportunities.append(opp)
                            
                except Exception as e:
                    logger.debug(f"Stablecoin scan error {pair} on {name}: {e}")
        
        return opportunities
    
    async def _execute_arbitrage(self, opportunity: ArbitrageOpportunity, budget: float):
        """Exécuter une opportunité d'arbitrage"""
        
        # Calculer la taille
        size = min(
            opportunity.max_size,
            budget * 0.1  # Max 10% du budget par opportunité
        )
        
        if size < 10:  # Minimum $10
            return
        
        estimated_profit = size * (opportunity.net_profit / 100)
        
        if self.config.paper_trading:
            # Paper trading - simuler l'exécution
            logger.info(f"""
🔄 ARBITRAGE SIMULÉ ({opportunity.arb_type.value})
   {opportunity.symbol}
   Buy: {opportunity.buy_exchange} @ ${opportunity.buy_price:,.4f}
   Sell: {opportunity.sell_exchange} @ ${opportunity.sell_price:,.4f}
   Spread: {opportunity.spread:.3f}%
   Size: ${size:,.2f}
   Profit estimé: ${estimated_profit:,.2f}
            """)
            
            # Simuler le profit
            self.total_profit += estimated_profit
            
        else:
            # Live execution
            # TODO: Implémenter l'exécution réelle
            pass
        
        # Alerte Telegram
        from monitoring.telegram_alerts import TelegramAlertEngine
        alert_engine = TelegramAlertEngine(self.config, self.state)
        await alert_engine.send_arbitrage_alert({
            'arb_type': opportunity.arb_type.value,
            'symbol': opportunity.symbol,
            'buy_exchange': opportunity.buy_exchange,
            'buy_price': opportunity.buy_price,
            'sell_exchange': opportunity.sell_exchange,
            'sell_price': opportunity.sell_price,
            'spread': opportunity.spread,
            'profit': estimated_profit
        })
    
    async def _save_stats(self):
        """Sauvegarder les statistiques"""
        
        stats = {
            'total_scans': self.total_scans,
            'total_opportunities': self.total_opportunities,
            'total_profit': self.total_profit,
            'last_scan': datetime.now().isoformat()
        }
        
        await self.state.set('arbitrage_stats', stats, expire=86400)
    
    async def get_stats(self) -> Dict:
        """Récupérer les statistiques"""
        
        return await self.state.get('arbitrage_stats', {
            'total_scans': 0,
            'total_opportunities': 0,
            'total_profit': 0
        })
    
    async def close(self):
        """Fermer les connexions"""
        for exchange in self.exchanges.values():
            await exchange.close()
