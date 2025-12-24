#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               STRESS TEST ENGINE - V5                                        ║
║                                                                              ║
║  Scénarios:                                                                  ║
║  • Flash Crash (-20% en 1h)                                                  ║
║  • Bear Market prolongé                                                      ║
║  • Volatilité extrême                                                        ║
║  • Corrélation breakdown                                                     ║
║  • Liquidity crisis                                                          ║
║  • Exchange failure                                                          ║
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

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class StressScenario:
    """Scénario de stress test"""
    name: str
    description: str
    price_shock: float  # % change
    volatility_multiplier: float
    liquidity_reduction: float  # 0-1
    duration_hours: int
    correlation_break: bool = False


@dataclass
class StressTestResult:
    """Résultat d'un stress test"""
    scenario: str
    passed: bool
    max_loss: float
    max_drawdown: float
    time_to_recovery: Optional[int]  # hours
    margin_call: bool
    liquidation: bool
    details: Dict = field(default_factory=dict)


class StressTestEngine:
    """Moteur de stress tests"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        # Scénarios prédéfinis
        self.scenarios = [
            StressScenario(
                name="flash_crash",
                description="Flash crash -20% en 1h",
                price_shock=-0.20,
                volatility_multiplier=5.0,
                liquidity_reduction=0.7,
                duration_hours=2
            ),
            StressScenario(
                name="bear_market",
                description="Bear market -40% sur 30 jours",
                price_shock=-0.40,
                volatility_multiplier=2.0,
                liquidity_reduction=0.3,
                duration_hours=720  # 30 days
            ),
            StressScenario(
                name="extreme_volatility",
                description="Volatilité 10x pendant 24h",
                price_shock=0,
                volatility_multiplier=10.0,
                liquidity_reduction=0.5,
                duration_hours=24
            ),
            StressScenario(
                name="correlation_breakdown",
                description="Corrélations crypto inversées",
                price_shock=-0.15,
                volatility_multiplier=3.0,
                liquidity_reduction=0.4,
                duration_hours=48,
                correlation_break=True
            ),
            StressScenario(
                name="liquidity_crisis",
                description="Crise de liquidité majeure",
                price_shock=-0.10,
                volatility_multiplier=4.0,
                liquidity_reduction=0.9,
                duration_hours=12
            ),
            StressScenario(
                name="exchange_failure",
                description="Panne d'un exchange majeur",
                price_shock=-0.05,
                volatility_multiplier=2.0,
                liquidity_reduction=0.5,
                duration_hours=6
            ),
        ]
        
        # Seuils
        self.max_acceptable_loss = 0.20  # 20%
        self.margin_call_threshold = 0.50  # 50% de perte
    
    async def run_all_stress_tests(self) -> Dict:
        """Exécuter tous les stress tests"""
        
        logger.info("🧪 Démarrage des stress tests...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'scenarios': {},
            'overall_status': 'passed',
            'var_95': 0,
            'var_99': 0
        }
        
        # Portfolio actuel
        allocation = await self.state.get_allocation()
        portfolio = {
            'total': self.config.total_budget,
            'arbitrage': allocation.get('arbitrage_budget', 0),
            'trading': allocation.get('trading_budget', 0),
            'reserve': allocation.get('reserve_budget', 0)
        }
        
        # Exécuter chaque scénario
        for scenario in self.scenarios:
            try:
                result = await self._run_scenario(scenario, portfolio)
                results['scenarios'][scenario.name] = {
                    'passed': result.passed,
                    'max_loss': result.max_loss,
                    'max_drawdown': result.max_drawdown,
                    'margin_call': result.margin_call,
                    'liquidation': result.liquidation,
                    'description': scenario.description
                }
                
                if not result.passed:
                    results['overall_status'] = 'failed'
                elif result.max_loss > 0.10 and results['overall_status'] != 'failed':
                    results['overall_status'] = 'warning'
                    
            except Exception as e:
                logger.error(f"Erreur stress test {scenario.name}: {e}")
                results['scenarios'][scenario.name] = {
                    'passed': False,
                    'error': str(e)
                }
                results['overall_status'] = 'error'
        
        # Calculer VaR
        results['var_95'], results['var_99'] = await self._calculate_var(portfolio)
        
        # Sauvegarder résultats
        await self.state.set('stress_test_results', results, expire=86400)
        
        logger.info(f"""
🧪 STRESS TESTS TERMINÉS
Status: {results['overall_status'].upper()}
VaR 95%: {results['var_95']:.2%}
VaR 99%: {results['var_99']:.2%}
        """)
        
        return results
    
    async def _run_scenario(self, scenario: StressScenario, portfolio: Dict) -> StressTestResult:
        """Exécuter un scénario de stress test"""
        
        logger.debug(f"Testing scenario: {scenario.name}")
        
        total = portfolio['total']
        trading = portfolio['trading']
        arbitrage = portfolio['arbitrage']
        reserve = portfolio['reserve']
        
        # Simuler l'impact
        losses = []
        
        # Impact sur le trading directionnel
        if trading > 0:
            # Positions directionnelles subissent le choc de prix
            trading_loss = abs(scenario.price_shock) * 0.5  # 50% exposure moyenne
            trading_loss *= (1 + (scenario.volatility_multiplier - 1) * 0.1)  # Impact volatilité
            losses.append(('trading', trading * trading_loss))
        
        # Impact sur l'arbitrage
        if arbitrage > 0:
            # L'arbitrage est moins affecté mais la liquidité compte
            arb_loss = scenario.liquidity_reduction * 0.05  # Max 5% de perte si liquidity crisis
            if scenario.correlation_break:
                arb_loss += 0.02  # Risque supplémentaire
            losses.append(('arbitrage', arbitrage * arb_loss))
        
        # La réserve est safe (stablecoins)
        if reserve > 0 and abs(scenario.price_shock) > 0.3:
            # Risque de depeg en cas de crash majeur
            reserve_loss = 0.02
            losses.append(('reserve', reserve * reserve_loss))
        
        # Calculer perte totale
        total_loss = sum(l[1] for l in losses)
        max_loss_pct = total_loss / total if total > 0 else 0
        
        # Calculer drawdown (simplifié)
        max_drawdown = max_loss_pct * 1.2  # Approximation
        
        # Vérifier critères
        margin_call = max_loss_pct > self.margin_call_threshold
        liquidation = max_loss_pct > 0.80
        passed = max_loss_pct <= self.max_acceptable_loss and not liquidation
        
        return StressTestResult(
            scenario=scenario.name,
            passed=passed,
            max_loss=max_loss_pct,
            max_drawdown=max_drawdown,
            time_to_recovery=scenario.duration_hours * 2 if passed else None,
            margin_call=margin_call,
            liquidation=liquidation,
            details={
                'losses_breakdown': losses,
                'scenario_params': {
                    'price_shock': scenario.price_shock,
                    'volatility_mult': scenario.volatility_multiplier,
                    'liquidity_red': scenario.liquidity_reduction
                }
            }
        )
    
    async def _calculate_var(self, portfolio: Dict) -> Tuple[float, float]:
        """Calculer la Value at Risk (VaR)"""
        
        # Simulation Monte Carlo simplifiée
        np.random.seed(42)
        
        n_simulations = 10000
        daily_vol = 0.03  # 3% volatilité journalière moyenne crypto
        
        # Simuler returns
        returns = np.random.normal(0, daily_vol, n_simulations)
        
        # Appliquer l'exposition du portfolio
        allocation = await self.state.get_allocation()
        trading_pct = allocation.get('trading_pct', 40) / 100
        arb_pct = allocation.get('arbitrage_pct', 40) / 100
        
        # Trading est exposé au marché
        # Arbitrage a une exposition réduite
        exposure = trading_pct * 0.5 + arb_pct * 0.1
        
        portfolio_returns = returns * exposure
        portfolio_losses = -np.minimum(portfolio_returns, 0)
        
        # VaR
        var_95 = np.percentile(portfolio_losses, 95)
        var_99 = np.percentile(portfolio_losses, 99)
        
        return var_95, var_99
    
    async def run_custom_scenario(
        self,
        price_shock: float,
        volatility_mult: float,
        liquidity_red: float,
        duration: int
    ) -> StressTestResult:
        """Exécuter un scénario personnalisé"""
        
        scenario = StressScenario(
            name="custom",
            description=f"Custom: {price_shock:.0%} shock, {volatility_mult}x vol",
            price_shock=price_shock,
            volatility_multiplier=volatility_mult,
            liquidity_reduction=liquidity_red,
            duration_hours=duration
        )
        
        allocation = await self.state.get_allocation()
        portfolio = {
            'total': self.config.total_budget,
            'arbitrage': allocation.get('arbitrage_budget', 0),
            'trading': allocation.get('trading_budget', 0),
            'reserve': allocation.get('reserve_budget', 0)
        }
        
        return await self._run_scenario(scenario, portfolio)
    
    def get_risk_assessment(self, results: Dict) -> Dict:
        """Évaluer le risque global basé sur les stress tests"""
        
        if results.get('overall_status') == 'failed':
            return {
                'risk_score': 'HIGH',
                'recommendation': 'Réduire l\'exposition immédiatement',
                'suggested_reserve': 40
            }
        elif results.get('overall_status') == 'warning':
            return {
                'risk_score': 'MEDIUM',
                'recommendation': 'Augmenter la réserve et réduire le trading',
                'suggested_reserve': 30
            }
        else:
            return {
                'risk_score': 'LOW',
                'recommendation': 'Allocation actuelle acceptable',
                'suggested_reserve': 20
            }
