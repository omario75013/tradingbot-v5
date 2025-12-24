#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               CONTINUOUS TRAINING ENGINE - V5                                ║
║                                                                              ║
║  Fonctionnalités:                                                            ║
║  • Entraînement continu sur nouvelles données                                ║
║  • Walk-forward analysis                                                     ║
║  • Comparaison nouveau vs ancien modèle                                      ║
║  • Hot-swap automatique si amélioration                                      ║
║  • Versioning des modèles                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import shutil

import pandas as pd
import numpy as np
from loguru import logger

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class ModelMetrics:
    """Métriques du modèle"""
    accuracy: float
    precision: float
    recall: float
    sharpe_backtest: float
    win_rate_backtest: float
    profit_factor: float
    max_drawdown: float


@dataclass
class TrainingResult:
    """Résultat d'entraînement"""
    success: bool
    model_version: str
    metrics: ModelMetrics
    training_time: float
    samples_used: int
    features_used: List[str]
    timestamp: datetime


class ContinuousTrainingEngine:
    """Moteur d'entraînement continu"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        self.model_dir = "models"
        self.current_model_path = os.path.join(self.model_dir, "current")
        self.archive_dir = os.path.join(self.model_dir, "archive")
        
        # Créer les dossiers si nécessaire
        os.makedirs(self.current_model_path, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
        
        # Modèle actuel
        self.model = None
        self.model_version = "1.0.0"
        self.model_metrics: Optional[ModelMetrics] = None
        
        # Features
        self.features = [
            'returns_1h', 'returns_4h', 'returns_24h',
            'volatility_1h', 'volatility_24h',
            'rsi_14', 'macd', 'macd_signal',
            'ema_20_ratio', 'ema_50_ratio',
            'volume_ratio', 'volume_ma_ratio',
            'fear_greed', 'sentiment_score',
            'btc_correlation'
        ]
    
    async def load_current_model(self):
        """Charger le modèle actuel"""
        
        if not SKLEARN_AVAILABLE:
            logger.warning("⚠️ sklearn non disponible")
            return False
        
        model_file = os.path.join(self.current_model_path, "model.joblib")
        
        if os.path.exists(model_file):
            try:
                self.model = joblib.load(model_file)
                
                # Charger les métadonnées
                meta_file = os.path.join(self.current_model_path, "metadata.json")
                if os.path.exists(meta_file):
                    with open(meta_file, 'r') as f:
                        meta = json.load(f)
                        self.model_version = meta.get('version', '1.0.0')
                        
                logger.info(f"✅ Modèle chargé: v{self.model_version}")
                return True
                
            except Exception as e:
                logger.error(f"Erreur chargement modèle: {e}")
        
        return False
    
    async def run_training_cycle(self):
        """Cycle d'entraînement complet"""
        
        if not SKLEARN_AVAILABLE:
            logger.debug("sklearn non disponible, skip training")
            return
        
        logger.info("🧠 Démarrage cycle d'entraînement...")
        start_time = datetime.now()
        
        try:
            # 1. Collecter les données
            data = await self._collect_training_data()
            
            if data is None or len(data) < 100:
                logger.warning("Pas assez de données pour l'entraînement")
                return
            
            # 2. Préparer les features
            X, y = self._prepare_features(data)
            
            if X is None or len(X) < 100:
                logger.warning("Pas assez de features pour l'entraînement")
                return
            
            # 3. Entraîner le nouveau modèle
            new_model, new_metrics = await self._train_model(X, y)
            
            if new_model is None:
                return
            
            # 4. Comparer avec le modèle actuel
            should_swap = await self._should_swap_model(new_metrics)
            
            if should_swap:
                # 5. Archiver l'ancien modèle
                await self._archive_current_model()
                
                # 6. Hot-swap
                await self._hot_swap_model(new_model, new_metrics)
                
                training_time = (datetime.now() - start_time).total_seconds()
                
                result = TrainingResult(
                    success=True,
                    model_version=self.model_version,
                    metrics=new_metrics,
                    training_time=training_time,
                    samples_used=len(X),
                    features_used=self.features,
                    timestamp=datetime.now()
                )
                
                # Alerte
                from monitoring.telegram_alerts import TelegramAlertEngine
                alert_engine = TelegramAlertEngine(self.config, self.state)
                
                improvement = 0
                if self.model_metrics:
                    improvement = (new_metrics.sharpe_backtest / self.model_metrics.sharpe_backtest - 1) * 100
                
                await alert_engine.send_model_update_alert({
                    'old_version': self._previous_version(),
                    'new_version': self.model_version,
                    'improvement_pct': improvement,
                    'new_metrics': new_metrics
                })
                
                logger.info(f"""
🧠 MODÈLE MIS À JOUR
   Version: v{self.model_version}
   Accuracy: {new_metrics.accuracy:.2%}
   Sharpe: {new_metrics.sharpe_backtest:.2f}
   Win Rate: {new_metrics.win_rate_backtest:.2%}
   Temps: {training_time:.1f}s
                """)
            else:
                logger.info("Nouveau modèle pas meilleur - conservation de l'actuel")
                
        except Exception as e:
            logger.error(f"Erreur cycle d'entraînement: {e}")
    
    async def _collect_training_data(self) -> Optional[pd.DataFrame]:
        """Collecter les données pour l'entraînement"""
        
        try:
            # Récupérer l'historique des trades
            trades = await self.state.get_trades_history(limit=1000)
            
            if not trades:
                # Générer des données synthétiques pour le démarrage
                return self._generate_synthetic_data()
            
            # Convertir en DataFrame
            df = pd.DataFrame(trades)
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur collecte données: {e}")
            return None
    
    def _generate_synthetic_data(self) -> pd.DataFrame:
        """Générer des données synthétiques pour le démarrage"""
        
        np.random.seed(42)
        n_samples = 1000
        
        data = {
            'timestamp': pd.date_range(end=datetime.now(), periods=n_samples, freq='1h'),
            'returns_1h': np.random.normal(0, 0.02, n_samples),
            'returns_4h': np.random.normal(0, 0.04, n_samples),
            'returns_24h': np.random.normal(0, 0.08, n_samples),
            'volatility_1h': np.random.uniform(0.01, 0.05, n_samples),
            'volatility_24h': np.random.uniform(0.02, 0.10, n_samples),
            'rsi_14': np.random.uniform(20, 80, n_samples),
            'macd': np.random.normal(0, 1, n_samples),
            'macd_signal': np.random.normal(0, 1, n_samples),
            'ema_20_ratio': np.random.normal(1, 0.02, n_samples),
            'ema_50_ratio': np.random.normal(1, 0.03, n_samples),
            'volume_ratio': np.random.uniform(0.5, 2, n_samples),
            'volume_ma_ratio': np.random.uniform(0.5, 2, n_samples),
            'fear_greed': np.random.uniform(20, 80, n_samples),
            'sentiment_score': np.random.uniform(-0.5, 0.5, n_samples),
            'btc_correlation': np.random.uniform(0.5, 0.95, n_samples),
        }
        
        # Target: direction du prochain mouvement
        data['target'] = np.where(
            np.random.random(n_samples) > 0.5,
            1,  # Up
            0   # Down
        )
        
        return pd.DataFrame(data)
    
    def _prepare_features(self, data: pd.DataFrame) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Préparer les features pour l'entraînement"""
        
        try:
            # Vérifier que toutes les features sont présentes
            available_features = [f for f in self.features if f in data.columns]
            
            if len(available_features) < len(self.features) / 2:
                # Pas assez de features
                return None, None
            
            X = data[available_features].values
            
            # Target
            if 'target' in data.columns:
                y = data['target'].values
            else:
                # Créer le target basé sur les returns futurs
                if 'returns_1h' in data.columns:
                    y = (data['returns_1h'].shift(-1) > 0).astype(int).values[:-1]
                    X = X[:-1]
                else:
                    return None, None
            
            # Supprimer les NaN
            mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
            X = X[mask]
            y = y[mask]
            
            return X, y
            
        except Exception as e:
            logger.error(f"Erreur préparation features: {e}")
            return None, None
    
    async def _train_model(self, X: np.ndarray, y: np.ndarray) -> Tuple[Optional[Any], Optional[ModelMetrics]]:
        """Entraîner un nouveau modèle"""
        
        try:
            # Walk-forward split
            tscv = TimeSeriesSplit(n_splits=5)
            
            accuracies = []
            precisions = []
            recalls = []
            
            for train_idx, test_idx in tscv.split(X):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]
                
                # Entraîner
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42
                )
                model.fit(X_train, y_train)
                
                # Évaluer
                y_pred = model.predict(X_test)
                accuracies.append(accuracy_score(y_test, y_pred))
                precisions.append(precision_score(y_test, y_pred, zero_division=0))
                recalls.append(recall_score(y_test, y_pred, zero_division=0))
            
            # Métriques moyennes
            avg_accuracy = np.mean(accuracies)
            avg_precision = np.mean(precisions)
            avg_recall = np.mean(recalls)
            
            # Entraîner le modèle final sur toutes les données
            final_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
            final_model.fit(X, y)
            
            # Backtest simplifié
            sharpe, win_rate, profit_factor, max_dd = self._backtest_model(final_model, X, y)
            
            metrics = ModelMetrics(
                accuracy=avg_accuracy,
                precision=avg_precision,
                recall=avg_recall,
                sharpe_backtest=sharpe,
                win_rate_backtest=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_dd
            )
            
            return final_model, metrics
            
        except Exception as e:
            logger.error(f"Erreur entraînement: {e}")
            return None, None
    
    def _backtest_model(self, model, X: np.ndarray, y: np.ndarray) -> Tuple[float, float, float, float]:
        """Backtest simplifié du modèle"""
        
        predictions = model.predict(X)
        
        # Simuler les returns
        returns = []
        for i, (pred, actual) in enumerate(zip(predictions, y)):
            if pred == actual:
                returns.append(0.01)  # Gain de 1%
            else:
                returns.append(-0.01)  # Perte de 1%
        
        returns = np.array(returns)
        
        # Sharpe
        sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252 * 24)
        
        # Win rate
        win_rate = np.sum(returns > 0) / len(returns)
        
        # Profit factor
        gains = np.sum(returns[returns > 0])
        losses = np.abs(np.sum(returns[returns < 0]))
        profit_factor = gains / (losses + 1e-10)
        
        # Max drawdown
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = running_max - cumulative
        max_dd = np.max(drawdowns)
        
        return sharpe, win_rate, profit_factor, max_dd
    
    async def _should_swap_model(self, new_metrics: ModelMetrics) -> bool:
        """Déterminer si le nouveau modèle est meilleur"""
        
        if self.model is None:
            return True
        
        if self.model_metrics is None:
            return True
        
        # Comparer le Sharpe ratio
        improvement = new_metrics.sharpe_backtest / (self.model_metrics.sharpe_backtest + 1e-10)
        
        return improvement >= self.config.model_comparison_threshold
    
    async def _archive_current_model(self):
        """Archiver le modèle actuel"""
        
        if self.model is None:
            return
        
        archive_path = os.path.join(
            self.archive_dir,
            f"model_v{self.model_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        try:
            if os.path.exists(self.current_model_path):
                shutil.copytree(self.current_model_path, archive_path)
                logger.info(f"📦 Modèle archivé: {archive_path}")
        except Exception as e:
            logger.error(f"Erreur archivage: {e}")
    
    async def _hot_swap_model(self, new_model, new_metrics: ModelMetrics):
        """Hot-swap du modèle"""
        
        # Incrémenter la version
        parts = self.model_version.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        self.model_version = '.'.join(parts)
        
        # Sauvegarder le nouveau modèle
        model_file = os.path.join(self.current_model_path, "model.joblib")
        joblib.dump(new_model, model_file)
        
        # Sauvegarder les métadonnées
        meta = {
            'version': self.model_version,
            'trained_at': datetime.now().isoformat(),
            'metrics': {
                'accuracy': new_metrics.accuracy,
                'precision': new_metrics.precision,
                'recall': new_metrics.recall,
                'sharpe': new_metrics.sharpe_backtest,
                'win_rate': new_metrics.win_rate_backtest
            },
            'features': self.features
        }
        
        meta_file = os.path.join(self.current_model_path, "metadata.json")
        with open(meta_file, 'w') as f:
            json.dump(meta, f, indent=2)
        
        # Mettre à jour les références
        self.model = new_model
        self.model_metrics = new_metrics
        
        # Mettre à jour le state
        await self.state.set_model_info({
            'version': self.model_version,
            'accuracy': new_metrics.accuracy,
            'sharpe': new_metrics.sharpe_backtest,
            'last_trained': datetime.now().isoformat()
        })
    
    def _previous_version(self) -> str:
        """Récupérer la version précédente"""
        parts = self.model_version.split('.')
        if int(parts[-1]) > 0:
            parts[-1] = str(int(parts[-1]) - 1)
        return '.'.join(parts)
    
    async def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """Prédiction avec le modèle actuel"""
        
        if self.model is None:
            await self.load_current_model()
        
        if self.model is None:
            return 0, 0.5
        
        try:
            prediction = self.model.predict(features.reshape(1, -1))[0]
            probability = self.model.predict_proba(features.reshape(1, -1))[0].max()
            return prediction, probability
        except Exception as e:
            logger.error(f"Erreur prédiction: {e}")
            return 0, 0.5
