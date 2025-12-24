#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               CONTINUOUS BACKTEST ENGINE - V5                                ║
║                                                                              ║
║  Fonctionnalités:                                                            ║
║  • Backtests périodiques sur données récentes                                ║
║  • Détection de dégradation de performance                                   ║
║  • Alertes automatiques                                                      ║
║  • Comparaison avec benchmarks                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
from loguru import logger


@dataclass
class BacktestResult:
    """Résultat de backtest"""
    period_start: datetime
    period_end: datetime
    
    # Performance
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    
    # Stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    
    # Comparaison
    vs_btc: float  # Performance vs BTC buy & hold
    vs_benchmark: float  # vs stratégie benchmark
    
    # Alertes
    degradation_detected: bool
    alerts: List[Dict] = field(default_factory=list)


@dataclass
class DegradationAlert:
    """Alerte de dégradation"""
    metric: str
    current_value: float
    threshold: float
    severity: str  # 'warning', 'critical'
    message: str


class ContinuousBacktestEngine:
    """Moteur de backtest continu"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        # Historique des backtests
        self.backtest_history: List[BacktestResult] = []
        
        # Seuils de dégradation
        self.thresholds = {
            'sharpe_min': 0.5,
            'win_rate_min': 0.45,
            'max_drawdown_max': 0.15,
            'profit_factor_min': 1.2,
            'vs_btc_min': -0.10  # Pas plus de 10% en dessous de BTC
        }
        
        # Benchmarks
        self.benchmark_sharpe = 1.0
        self.benchmark_win_rate = 0.55
    
    async def run_continuous_backtest(self):
        """Exécuter un backtest continu"""
        
        logger.debug("📊 Démarrage backtest continu...")
        
        try:
            # Récupérer les données récentes
            trades = await self.state.get_trades_history(limit=500)
            
            if len(trades) < 10:
                logger.debug("Pas assez de trades pour le backtest")
                return
            
            # Récupérer les données de marché
            market_data = await self._get_market_data()
            
            # Exécuter le backtest
            result = await self._run_backtest(trades, market_data)
            
            # Vérifier la dégradation
            alerts = self._check_degradation(result)
            result.alerts = alerts
            result.degradation_detected = len(alerts) > 0
            
            # Sauvegarder le résultat
            self.backtest_history.append(result)
            if len(self.backtest_history) > 100:
                self.backtest_history = self.backtest_history[-100:]
            
            # Mettre à jour le state
            await self._update_performance_metrics(result)
            
            if result.degradation_detected:
                logger.warning(f"⚠️ Dégradation détectée: {len(alerts)} alertes")
                
                # Envoyer alerte
                from monitoring.telegram_alerts import TelegramAlertEngine
                alert_engine = TelegramAlertEngine(self.config, self.state)
                await alert_engine.send_degradation_alert({
                    'alerts': [{'message': a.message} for a in alerts],
                    'result': result
                })
            else:
                logger.debug(f"✅ Backtest OK - Sharpe: {result.sharpe_ratio:.2f}, WR: {result.win_rate:.1%}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur backtest: {e}")
            return None
    
    async def _get_market_data(self) -> Optional[pd.DataFrame]:
        """Récupérer les données de marché pour le benchmark"""
        
        market_state = await self.state.get_market_state()
        
        # Simuler des données de marché
        # En production, récupérer via l'API exchange
        return pd.DataFrame({
            'btc_price': [market_state.get('btc_price', 50000)],
            'btc_change_24h': [market_state.get('btc_change_24h', 0)]
        })
    
    async def _run_backtest(self, trades: List[Dict], market_data: Optional[pd.DataFrame]) -> BacktestResult:
        """Exécuter le backtest sur les trades"""
        
        if not trades:
            return self._empty_result()
        
        # Convertir en DataFrame
        df = pd.DataFrame(trades)
        
        # Calculer les métriques
        pnls = []
        for trade in trades:
            pnl = trade.get('pnl', 0)
            if pnl != 0:
                pnls.append(pnl)
        
        if not pnls:
            return self._empty_result()
        
        pnls = np.array(pnls)
        
        # Performance
        total_return = np.sum(pnls) / self.config.total_budget if self.config.total_budget > 0 else 0
        
        # Sharpe ratio (annualisé)
        if len(pnls) > 1 and np.std(pnls) > 0:
            sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252 * 24)  # Hourly data
        else:
            sharpe = 0
        
        # Max drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / (running_max + 1e-10)
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        # Win rate
        winning = pnls > 0
        win_rate = np.sum(winning) / len(pnls) if len(pnls) > 0 else 0.5
        
        # Profit factor
        gross_profit = np.sum(pnls[pnls > 0])
        gross_loss = np.abs(np.sum(pnls[pnls < 0]))
        profit_factor = gross_profit / (gross_loss + 1e-10)
        
        # Stats détaillées
        avg_win = np.mean(pnls[pnls > 0]) if np.sum(winning) > 0 else 0
        avg_loss = np.mean(pnls[pnls < 0]) if np.sum(~winning) > 0 else 0
        
        # Vs BTC (simplifié)
        btc_return = 0
        if market_data is not None and 'btc_change_24h' in market_data.columns:
            btc_return = market_data['btc_change_24h'].iloc[0] / 100
        
        vs_btc = total_return - btc_return
        
        # Vs benchmark
        vs_benchmark = sharpe - self.benchmark_sharpe
        
        # Période
        timestamps = [t.get('timestamp') or t.get('closed_at') for t in trades if t.get('timestamp') or t.get('closed_at')]
        if timestamps:
            period_start = min(pd.to_datetime(timestamps))
            period_end = max(pd.to_datetime(timestamps))
        else:
            period_start = datetime.now() - timedelta(days=7)
            period_end = datetime.now()
        
        return BacktestResult(
            period_start=period_start,
            period_end=period_end,
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(pnls),
            winning_trades=int(np.sum(winning)),
            losing_trades=int(np.sum(~winning)),
            avg_win=avg_win,
            avg_loss=avg_loss,
            vs_btc=vs_btc,
            vs_benchmark=vs_benchmark,
            degradation_detected=False,
            alerts=[]
        )
    
    def _empty_result(self) -> BacktestResult:
        """Résultat vide"""
        return BacktestResult(
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            total_return=0,
            sharpe_ratio=0,
            max_drawdown=0,
            win_rate=0.5,
            profit_factor=1,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=0,
            avg_loss=0,
            vs_btc=0,
            vs_benchmark=0,
            degradation_detected=False,
            alerts=[]
        )
    
    def _check_degradation(self, result: BacktestResult) -> List[DegradationAlert]:
        """Vérifier les signes de dégradation"""
        
        alerts = []
        
        # Sharpe ratio
        if result.sharpe_ratio < self.thresholds['sharpe_min']:
            severity = 'critical' if result.sharpe_ratio < 0 else 'warning'
            alerts.append(DegradationAlert(
                metric='sharpe_ratio',
                current_value=result.sharpe_ratio,
                threshold=self.thresholds['sharpe_min'],
                severity=severity,
                message=f"Sharpe ratio faible: {result.sharpe_ratio:.2f} (seuil: {self.thresholds['sharpe_min']})"
            ))
        
        # Win rate
        if result.win_rate < self.thresholds['win_rate_min']:
            alerts.append(DegradationAlert(
                metric='win_rate',
                current_value=result.win_rate,
                threshold=self.thresholds['win_rate_min'],
                severity='warning',
                message=f"Win rate faible: {result.win_rate:.1%} (seuil: {self.thresholds['win_rate_min']:.1%})"
            ))
        
        # Max drawdown
        if result.max_drawdown > self.thresholds['max_drawdown_max']:
            severity = 'critical' if result.max_drawdown > 0.20 else 'warning'
            alerts.append(DegradationAlert(
                metric='max_drawdown',
                current_value=result.max_drawdown,
                threshold=self.thresholds['max_drawdown_max'],
                severity=severity,
                message=f"Drawdown élevé: {result.max_drawdown:.1%} (seuil: {self.thresholds['max_drawdown_max']:.1%})"
            ))
        
        # Profit factor
        if result.profit_factor < self.thresholds['profit_factor_min']:
            alerts.append(DegradationAlert(
                metric='profit_factor',
                current_value=result.profit_factor,
                threshold=self.thresholds['profit_factor_min'],
                severity='warning',
                message=f"Profit factor faible: {result.profit_factor:.2f} (seuil: {self.thresholds['profit_factor_min']})"
            ))
        
        # Vs BTC
        if result.vs_btc < self.thresholds['vs_btc_min']:
            alerts.append(DegradationAlert(
                metric='vs_btc',
                current_value=result.vs_btc,
                threshold=self.thresholds['vs_btc_min'],
                severity='warning',
                message=f"Sous-performance vs BTC: {result.vs_btc:.1%}"
            ))
        
        # Tendance historique
        if len(self.backtest_history) >= 3:
            recent = self.backtest_history[-3:]
            sharpes = [r.sharpe_ratio for r in recent]
            
            if all(sharpes[i] > sharpes[i+1] for i in range(len(sharpes)-1)):
                alerts.append(DegradationAlert(
                    metric='trend',
                    current_value=sharpes[-1],
                    threshold=sharpes[0],
                    severity='warning',
                    message=f"Tendance baissière du Sharpe: {sharpes}"
                ))
        
        return alerts
    
    async def _update_performance_metrics(self, result: BacktestResult):
        """Mettre à jour les métriques de performance"""
        
        await self.state.update_performance({
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'total_trades': result.total_trades,
            'last_backtest': datetime.now().isoformat()
        })
    
    async def get_summary(self) -> Dict:
        """Récupérer un résumé des backtests"""
        
        if not self.backtest_history:
            return {
                'status': 'no_data',
                'message': 'Pas encore de backtests'
            }
        
        latest = self.backtest_history[-1]
        
        return {
            'status': 'degraded' if latest.degradation_detected else 'healthy',
            'sharpe': latest.sharpe_ratio,
            'win_rate': latest.win_rate,
            'max_drawdown': latest.max_drawdown,
            'vs_btc': latest.vs_btc,
            'alerts_count': len(latest.alerts),
            'total_backtests': len(self.backtest_history)
        }
    
    def get_trend(self, metric: str = 'sharpe_ratio', periods: int = 10) -> List[float]:
        """Récupérer la tendance d'une métrique"""
        
        if not self.backtest_history:
            return []
        
        recent = self.backtest_history[-periods:]
        
        return [getattr(r, metric, 0) for r in recent]
