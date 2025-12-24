#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               CLAUDE CAPITAL ALLOCATOR - V5                                  ║
║                                                                              ║
║  Allocation dynamique du capital par Claude AI:                              ║
║  • Arbitrage (cross-exchange, triangulaire, funding)                         ║
║  • Trading directionnel (long/short)                                         ║
║  • Reserve (stablecoins)                                                     ║
║                                                                              ║
║  Basé sur:                                                                   ║
║  • Conditions de marché (volatilité, régime)                                 ║
║  • Sentiment (news, social, fear & greed)                                    ║
║  • Performance historique                                                    ║
║  • Opportunités d'arbitrage disponibles                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import numpy as np
from loguru import logger

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


@dataclass
class AllocationDecision:
    """Décision d'allocation"""
    timestamp: datetime
    
    # Répartition en %
    arbitrage_pct: float
    trading_pct: float
    reserve_pct: float
    
    # Budgets absolus
    arbitrage_budget: float
    trading_budget: float
    reserve_budget: float
    
    # Détails
    risk_level: str  # 'low', 'medium', 'high'
    arbitrage_focus: List[str]  # Types d'arbitrage à privilégier
    trading_bias: str  # 'long', 'short', 'neutral'
    
    # Métadonnées
    reasoning: str
    confidence: float
    rebalance_in_hours: int


class ClaudeCapitalAllocator:
    """Allocateur de capital piloté par Claude AI"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        # Claude AI
        self.claude = None
        if Anthropic and config.anthropic_api_key:
            self.claude = Anthropic(api_key=config.anthropic_api_key)
        
        # Limites
        self.min_reserve = config.min_reserve_pct / 100
        self.max_arbitrage = config.max_arbitrage_pct / 100
        self.max_trading = config.max_trading_pct / 100
        
        # Historique des allocations
        self.allocation_history: List[AllocationDecision] = []
        
        # Dernière allocation
        self.last_allocation: Optional[AllocationDecision] = None
    
    async def decide_allocation(self) -> AllocationDecision:
        """Décider de l'allocation optimale du capital"""
        
        logger.info("💰 Réévaluation allocation capital...")
        
        # Collecter le contexte
        context = await self._gather_context()
        
        # Décision par Claude ou règles par défaut
        if self.claude:
            decision = await self._claude_decide(context)
        else:
            decision = await self._rules_based_decide(context)
        
        # Valider et ajuster
        decision = self._validate_allocation(decision)
        
        # Sauvegarder
        self.last_allocation = decision
        self.allocation_history.append(decision)
        
        await self._save_allocation(decision)
        
        logger.info(f"""
💰 NOUVELLE ALLOCATION
   Arbitrage: {decision.arbitrage_pct:.0f}% (${decision.arbitrage_budget:,.2f})
   Trading: {decision.trading_pct:.0f}% (${decision.trading_budget:,.2f})
   Reserve: {decision.reserve_pct:.0f}% (${decision.reserve_budget:,.2f})
   Risk Level: {decision.risk_level}
        """)
        
        # Alerte Telegram
        from monitoring.telegram_alerts import TelegramAlertEngine
        alert_engine = TelegramAlertEngine(self.config, self.state)
        await alert_engine.send_allocation_update(decision)
        
        return decision
    
    async def _gather_context(self) -> Dict:
        """Collecter le contexte pour la décision"""
        
        # État du marché
        market_state = await self.state.get_market_state()
        
        # Performance
        performance = await self.state.get_performance()
        
        # Sentiment
        sentiment = await self.state.get('sentiment_data', {})
        
        # Stats arbitrage
        arb_stats = await self.state.get('arbitrage_stats', {})
        
        # Stress tests
        stress_results = await self.state.get('stress_test_results', {})
        
        # Info modèle
        model_info = await self.state.get_model_info()
        
        return {
            'market': market_state,
            'performance': performance,
            'sentiment': sentiment,
            'arbitrage': arb_stats,
            'stress_tests': stress_results,
            'model': model_info,
            'total_budget': self.config.total_budget,
            'paper_trading': self.config.paper_trading
        }
    
    async def _claude_decide(self, context: Dict) -> AllocationDecision:
        """Décision d'allocation par Claude AI"""
        
        prompt = f"""Tu es un gestionnaire de portefeuille crypto expert. Tu dois décider de l'allocation optimale du capital entre:

1. ARBITRAGE (cross-exchange, triangulaire, funding rate)
   - Risque faible, rendements stables
   - Dépend de la liquidité et des spreads disponibles
   
2. TRADING DIRECTIONNEL (long/short avec ML)
   - Risque plus élevé, potentiel de gains supérieur
   - Dépend des conditions de marché et de la qualité du modèle
   
3. RESERVE (stablecoins)
   - Sécurité, dry powder pour opportunités
   - Minimum {self.min_reserve*100:.0f}%

CONTEXTE ACTUEL:
================
📊 MARCHÉ:
- BTC: ${context['market'].get('btc_price', 0):,.2f} ({context['market'].get('btc_change_24h', 0):+.2f}% 24h)
- Volatilité: {context['market'].get('volatility_level', 'MEDIUM')}
- Régime: {context['market'].get('regime', 'UNKNOWN')}

📰 SENTIMENT:
- Score: {context['sentiment'].get('composite_score', 0):+.2f}
- Level: {context['sentiment'].get('level', 'neutral')}
- Fear & Greed: {context['market'].get('fear_greed', 50)}

📈 PERFORMANCE:
- PnL Total: ${context['performance'].get('total_pnl', 0):+,.2f}
- Win Rate: {context['performance'].get('win_rate', 0.5):.1%}
- Sharpe: {context['performance'].get('sharpe_ratio', 0):.2f}
- Max Drawdown: {context['performance'].get('max_drawdown', 0):.1%}

🔄 ARBITRAGE:
- Scans: {context['arbitrage'].get('total_scans', 0)}
- Opportunités trouvées: {context['arbitrage'].get('total_opportunities', 0)}
- Profit arbitrage: ${context['arbitrage'].get('total_profit', 0):,.2f}

🧠 MODÈLE ML:
- Version: {context['model'].get('version', 'N/A')}
- Accuracy: {context['model'].get('accuracy', 0):.1%}
- Sharpe backtest: {context['model'].get('sharpe', 0):.2f}

🧪 STRESS TESTS:
- Status: {context['stress_tests'].get('overall_status', 'unknown')}
- VaR 95%: {context['stress_tests'].get('var_95', 0):.1%}

💵 BUDGET TOTAL: ${context['total_budget']:,.2f}
Mode: {"PAPER" if context['paper_trading'] else "LIVE"}

CONTRAINTES:
- Reserve minimum: {self.min_reserve*100:.0f}%
- Arbitrage maximum: {self.max_arbitrage*100:.0f}%
- Trading maximum: {self.max_trading*100:.0f}%
- Total = 100%

RÉPONDS UNIQUEMENT avec un JSON valide:
{{
    "arbitrage_pct": <number 0-80>,
    "trading_pct": <number 0-70>,
    "reserve_pct": <number 10-100>,
    "risk_level": "low" | "medium" | "high",
    "arbitrage_focus": ["cross_exchange", "triangular", "funding_rate"],
    "trading_bias": "long" | "short" | "neutral",
    "reasoning": "<explication courte>",
    "confidence": <0.0-1.0>,
    "rebalance_in_hours": <1-24>
}}
"""
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            
            # Parser le JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                return AllocationDecision(
                    timestamp=datetime.now(),
                    arbitrage_pct=result.get('arbitrage_pct', 40),
                    trading_pct=result.get('trading_pct', 40),
                    reserve_pct=result.get('reserve_pct', 20),
                    arbitrage_budget=context['total_budget'] * result.get('arbitrage_pct', 40) / 100,
                    trading_budget=context['total_budget'] * result.get('trading_pct', 40) / 100,
                    reserve_budget=context['total_budget'] * result.get('reserve_pct', 20) / 100,
                    risk_level=result.get('risk_level', 'medium'),
                    arbitrage_focus=result.get('arbitrage_focus', ['cross_exchange']),
                    trading_bias=result.get('trading_bias', 'neutral'),
                    reasoning=result.get('reasoning', 'Allocation par Claude AI'),
                    confidence=result.get('confidence', 0.7),
                    rebalance_in_hours=result.get('rebalance_in_hours', 4)
                )
                
        except Exception as e:
            logger.error(f"Claude allocation error: {e}")
        
        # Fallback
        return await self._rules_based_decide(context)
    
    async def _rules_based_decide(self, context: Dict) -> AllocationDecision:
        """Décision basée sur des règles (fallback)"""
        
        # Paramètres par défaut
        arb_pct = 40
        trading_pct = 40
        reserve_pct = 20
        risk_level = 'medium'
        trading_bias = 'neutral'
        
        # Ajuster selon la volatilité
        volatility = context['market'].get('volatility_level', 'MEDIUM')
        if volatility == 'HIGH':
            arb_pct = 50  # Plus d'arbitrage en volatilité
            trading_pct = 25
            reserve_pct = 25
            risk_level = 'low'
        elif volatility == 'LOW':
            arb_pct = 30
            trading_pct = 50
            reserve_pct = 20
            risk_level = 'medium'
        
        # Ajuster selon le sentiment
        sentiment_score = context['sentiment'].get('composite_score', 0)
        if sentiment_score > 0.3:
            trading_bias = 'long'
        elif sentiment_score < -0.3:
            trading_bias = 'short'
            reserve_pct = min(reserve_pct + 10, 40)
            trading_pct = max(trading_pct - 10, 20)
        
        # Ajuster selon le drawdown
        max_dd = context['performance'].get('max_drawdown', 0)
        if max_dd > 0.10:  # > 10% drawdown
            reserve_pct = min(reserve_pct + 15, 50)
            trading_pct = max(trading_pct - 15, 10)
            risk_level = 'low'
        
        # Normaliser à 100%
        total = arb_pct + trading_pct + reserve_pct
        arb_pct = arb_pct / total * 100
        trading_pct = trading_pct / total * 100
        reserve_pct = reserve_pct / total * 100
        
        return AllocationDecision(
            timestamp=datetime.now(),
            arbitrage_pct=arb_pct,
            trading_pct=trading_pct,
            reserve_pct=reserve_pct,
            arbitrage_budget=context['total_budget'] * arb_pct / 100,
            trading_budget=context['total_budget'] * trading_pct / 100,
            reserve_budget=context['total_budget'] * reserve_pct / 100,
            risk_level=risk_level,
            arbitrage_focus=['cross_exchange', 'funding_rate'],
            trading_bias=trading_bias,
            reasoning='Allocation basée sur les règles (volatilité + sentiment + drawdown)',
            confidence=0.6,
            rebalance_in_hours=4
        )
    
    def _validate_allocation(self, decision: AllocationDecision) -> AllocationDecision:
        """Valider et ajuster l'allocation"""
        
        # Vérifier le minimum de reserve
        if decision.reserve_pct < self.min_reserve * 100:
            diff = self.min_reserve * 100 - decision.reserve_pct
            decision.reserve_pct = self.min_reserve * 100
            
            # Réduire proportionnellement
            if decision.arbitrage_pct >= decision.trading_pct:
                decision.arbitrage_pct -= diff
            else:
                decision.trading_pct -= diff
        
        # Vérifier les max
        if decision.arbitrage_pct > self.max_arbitrage * 100:
            excess = decision.arbitrage_pct - self.max_arbitrage * 100
            decision.arbitrage_pct = self.max_arbitrage * 100
            decision.reserve_pct += excess
        
        if decision.trading_pct > self.max_trading * 100:
            excess = decision.trading_pct - self.max_trading * 100
            decision.trading_pct = self.max_trading * 100
            decision.reserve_pct += excess
        
        # Normaliser à 100%
        total = decision.arbitrage_pct + decision.trading_pct + decision.reserve_pct
        if total != 100:
            factor = 100 / total
            decision.arbitrage_pct *= factor
            decision.trading_pct *= factor
            decision.reserve_pct *= factor
        
        # Recalculer les budgets
        decision.arbitrage_budget = self.config.total_budget * decision.arbitrage_pct / 100
        decision.trading_budget = self.config.total_budget * decision.trading_pct / 100
        decision.reserve_budget = self.config.total_budget * decision.reserve_pct / 100
        
        return decision
    
    async def _save_allocation(self, decision: AllocationDecision):
        """Sauvegarder l'allocation"""
        
        allocation_dict = {
            'timestamp': decision.timestamp.isoformat(),
            'arbitrage_pct': decision.arbitrage_pct,
            'trading_pct': decision.trading_pct,
            'reserve_pct': decision.reserve_pct,
            'arbitrage_budget': decision.arbitrage_budget,
            'trading_budget': decision.trading_budget,
            'reserve_budget': decision.reserve_budget,
            'risk_level': decision.risk_level,
            'arbitrage_focus': decision.arbitrage_focus,
            'trading_bias': decision.trading_bias,
            'reasoning': decision.reasoning,
            'confidence': decision.confidence,
            'rebalance_in_hours': decision.rebalance_in_hours
        }
        
        await self.state.set_allocation(allocation_dict)
    
    async def get_current_allocation(self) -> Optional[AllocationDecision]:
        """Récupérer l'allocation actuelle"""
        return self.last_allocation
    
    def get_allocation_trend(self, metric: str = 'arbitrage_pct', periods: int = 10) -> List[float]:
        """Récupérer la tendance d'une métrique d'allocation"""
        
        if not self.allocation_history:
            return []
        
        recent = self.allocation_history[-periods:]
        return [getattr(a, metric, 0) for a in recent]
