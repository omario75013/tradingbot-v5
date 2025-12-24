#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               REAL-TIME SENTIMENT ENGINE - V5                                ║
║                                                                              ║
║  Sources:                                                                    ║
║  • CryptoPanic API (agrégateur news crypto)                                 ║
║  • NewsAPI (actualités générales)                                           ║
║  • LunarCrush (métriques sociales)                                          ║
║  • Finnhub (news financières)                                               ║
║  • Fear & Greed Index                                                        ║
║  • Analyse on-chain basique                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from collections import deque

from loguru import logger

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SentimentLevel(Enum):
    """Niveaux de sentiment"""
    EXTREME_FEAR = "extreme_fear"
    FEAR = "fear"
    NEUTRAL = "neutral"
    GREED = "greed"
    EXTREME_GREED = "extreme_greed"


@dataclass
class NewsItem:
    """Item de news"""
    id: str
    source: str
    title: str
    url: str
    published_at: datetime
    sentiment_score: float  # -1 to 1
    impact_level: str  # 'low', 'medium', 'high', 'critical'
    symbols: List[str]
    raw_data: Dict = field(default_factory=dict)


@dataclass
class SocialMetrics:
    """Métriques sociales"""
    symbol: str
    timestamp: datetime
    social_volume: int
    social_score: float
    galaxy_score: float
    sentiment: float
    influencer_mentions: int
    trending_rank: int


@dataclass
class AggregatedSentiment:
    """Sentiment agrégé"""
    timestamp: datetime
    
    # Score global
    composite_score: float  # -1 to 1
    composite_level: SentimentLevel
    confidence: float
    
    # Par source
    news_score: float
    news_count: int
    social_score: float
    social_volume: int
    fear_greed_index: int
    
    # Tendance
    trend_1h: float  # Changement sur 1h
    trend_24h: float  # Changement sur 24h
    
    # Alertes
    alert_triggered: bool
    alert_reason: str
    
    # Détails
    top_news: List[NewsItem] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)


class RealTimeSentimentEngine:
    """Moteur de sentiment temps réel"""
    
    def __init__(self, config, state):
        self.config = config
        self.state = state
        
        # API clients
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Cache
        self.news_cache: deque = deque(maxlen=500)
        self.sentiment_history: deque = deque(maxlen=1440)  # 24h de données minute par minute
        
        # Seuils d'alerte
        self.alert_thresholds = {
            'extreme_fear': -0.6,
            'extreme_greed': 0.6,
            'rapid_change': 0.3,  # Changement de 30% en 1h
        }
        
        # Mots-clés impact
        self.impact_keywords = {
            'critical': ['hack', 'exploit', 'breach', 'sec', 'lawsuit', 'ban', 'crash', 'bankrupt'],
            'high': ['regulation', 'etf', 'fed', 'rate', 'whale', 'institutional', 'halving'],
            'medium': ['update', 'partnership', 'launch', 'upgrade', 'adoption'],
        }
    
    async def initialize(self):
        """Initialiser le client HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def collect_all_sources(self) -> AggregatedSentiment:
        """Collecter sentiment de toutes les sources"""
        
        await self.initialize()
        
        logger.debug("📰 Collecte sentiment multi-sources...")
        
        # Collecter en parallèle
        tasks = [
            self._fetch_cryptopanic(),
            self._fetch_newsapi(),
            self._fetch_fear_greed(),
            self._fetch_lunarcrush(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Agréger les résultats
        news_items = []
        social_metrics = None
        fear_greed = 50
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"Source {i} error: {result}")
                continue
            
            if isinstance(result, list):
                news_items.extend(result)
            elif isinstance(result, int):
                fear_greed = result
            elif isinstance(result, SocialMetrics):
                social_metrics = result
        
        # Calculer scores
        news_score = self._calculate_news_sentiment(news_items)
        social_score = social_metrics.sentiment if social_metrics else 0
        
        # Score composite pondéré
        weights = {'news': 0.3, 'social': 0.2, 'fear_greed': 0.5}
        fear_greed_normalized = (fear_greed - 50) / 50  # -1 to 1
        
        composite = (
            weights['news'] * news_score +
            weights['social'] * social_score +
            weights['fear_greed'] * fear_greed_normalized
        )
        
        # Niveau de sentiment
        level = self._score_to_level(composite)
        
        # Calculer tendance
        trend_1h = self._calculate_trend(60)
        trend_24h = self._calculate_trend(1440)
        
        # Vérifier alertes
        alert_triggered, alert_reason = self._check_alerts(
            composite, fear_greed, news_items, trend_1h
        )
        
        # Créer résultat
        sentiment = AggregatedSentiment(
            timestamp=datetime.now(),
            composite_score=composite,
            composite_level=level,
            confidence=0.7,  # TODO: calculer vraie confiance
            news_score=news_score,
            news_count=len(news_items),
            social_score=social_score,
            social_volume=social_metrics.social_volume if social_metrics else 0,
            fear_greed_index=fear_greed,
            trend_1h=trend_1h,
            trend_24h=trend_24h,
            alert_triggered=alert_triggered,
            alert_reason=alert_reason,
            top_news=sorted(news_items, key=lambda x: x.published_at, reverse=True)[:5],
            key_events=self._extract_key_events(news_items)
        )
        
        # Sauvegarder historique
        self.sentiment_history.append({
            'timestamp': datetime.now(),
            'score': composite
        })
        
        # Mettre à jour state
        market_state = await self.state.get_market_state()
        market_state['sentiment_score'] = composite
        market_state['fear_greed'] = fear_greed
        await self.state.set_market_state(market_state)
        
        await self.state.set('sentiment_data', {
            'composite_score': composite,
            'level': level.value,
            'fear_greed': fear_greed,
            'news_count': len(news_items),
            'trend_1h': trend_1h,
            'alert': alert_reason if alert_triggered else None,
            'last_update': datetime.now().isoformat()
        }, expire=300)
        
        if alert_triggered:
            logger.warning(f"⚠️ Alerte Sentiment: {alert_reason}")
        
        return sentiment
    
    async def _fetch_cryptopanic(self) -> List[NewsItem]:
        """Récupérer news de CryptoPanic"""
        
        if not self.config.cryptopanic_key:
            return []
        
        try:
            url = f"https://cryptopanic.com/api/v1/posts/?auth_token={self.config.cryptopanic_key}&currencies=BTC,ETH,SOL,XRP&filter=hot"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    news = []
                    for item in data.get('results', [])[:20]:
                        sentiment = self._analyze_text_sentiment(item.get('title', ''))
                        impact = self._determine_impact(item.get('title', ''))
                        
                        news.append(NewsItem(
                            id=str(item.get('id')),
                            source='cryptopanic',
                            title=item.get('title', ''),
                            url=item.get('url', ''),
                            published_at=datetime.fromisoformat(item.get('published_at', '').replace('Z', '+00:00')),
                            sentiment_score=sentiment,
                            impact_level=impact,
                            symbols=[c.get('code') for c in item.get('currencies', [])],
                            raw_data=item
                        ))
                    
                    return news
                    
        except Exception as e:
            logger.debug(f"CryptoPanic error: {e}")
        
        return []
    
    async def _fetch_newsapi(self) -> List[NewsItem]:
        """Récupérer news de NewsAPI"""
        
        if not self.config.newsapi_key:
            return []
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': 'bitcoin OR ethereum OR cryptocurrency',
                'sortBy': 'publishedAt',
                'pageSize': 20,
                'apiKey': self.config.newsapi_key
            }
            
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    news = []
                    for item in data.get('articles', []):
                        title = item.get('title', '')
                        sentiment = self._analyze_text_sentiment(title)
                        impact = self._determine_impact(title)
                        
                        published = item.get('publishedAt', '')
                        try:
                            pub_dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                        except:
                            pub_dt = datetime.now()
                        
                        news.append(NewsItem(
                            id=item.get('url', ''),
                            source='newsapi',
                            title=title,
                            url=item.get('url', ''),
                            published_at=pub_dt,
                            sentiment_score=sentiment,
                            impact_level=impact,
                            symbols=self._extract_symbols(title),
                            raw_data=item
                        ))
                    
                    return news
                    
        except Exception as e:
            logger.debug(f"NewsAPI error: {e}")
        
        return []
    
    async def _fetch_fear_greed(self) -> int:
        """Récupérer Fear & Greed Index"""
        
        try:
            url = "https://api.alternative.me/fng/"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return int(data.get('data', [{}])[0].get('value', 50))
                    
        except Exception as e:
            logger.debug(f"Fear & Greed error: {e}")
        
        return 50
    
    async def _fetch_lunarcrush(self) -> Optional[SocialMetrics]:
        """Récupérer métriques LunarCrush"""
        
        if not self.config.lunarcrush_key:
            return None
        
        try:
            url = "https://lunarcrush.com/api3/coins/btc"
            headers = {'Authorization': f'Bearer {self.config.lunarcrush_key}'}
            
            async with self.session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    d = data.get('data', {})
                    
                    return SocialMetrics(
                        symbol='BTC',
                        timestamp=datetime.now(),
                        social_volume=d.get('social_volume', 0),
                        social_score=d.get('social_score', 0),
                        galaxy_score=d.get('galaxy_score', 0),
                        sentiment=(d.get('sentiment', 50) - 50) / 50,  # Normalize to -1 to 1
                        influencer_mentions=d.get('social_contributors', 0),
                        trending_rank=d.get('alt_rank', 0)
                    )
                    
        except Exception as e:
            logger.debug(f"LunarCrush error: {e}")
        
        return None
    
    def _analyze_text_sentiment(self, text: str) -> float:
        """Analyse de sentiment basique sur le texte"""
        
        text_lower = text.lower()
        
        # Mots positifs
        positive_words = [
            'bullish', 'surge', 'rally', 'gain', 'high', 'up', 'rise', 'growth',
            'adoption', 'approval', 'partnership', 'launch', 'upgrade', 'success',
            'record', 'breakthrough', 'support', 'boost', 'positive'
        ]
        
        # Mots négatifs
        negative_words = [
            'bearish', 'crash', 'drop', 'fall', 'down', 'decline', 'loss',
            'hack', 'exploit', 'scam', 'fraud', 'ban', 'lawsuit', 'sec',
            'warning', 'risk', 'fear', 'sell', 'dump', 'bankrupt', 'collapse'
        ]
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0
        
        return (pos_count - neg_count) / total
    
    def _determine_impact(self, text: str) -> str:
        """Déterminer le niveau d'impact d'une news"""
        
        text_lower = text.lower()
        
        for level, keywords in self.impact_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return level
        
        return 'low'
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extraire les symboles mentionnés"""
        
        symbols = []
        text_upper = text.upper()
        
        known_symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'DOT', 'LINK', 'AVAX']
        
        for symbol in known_symbols:
            if symbol in text_upper or symbol.lower() in text.lower():
                symbols.append(symbol)
        
        return symbols
    
    def _calculate_news_sentiment(self, news: List[NewsItem]) -> float:
        """Calculer le sentiment agrégé des news"""
        
        if not news:
            return 0
        
        # Pondérer par impact
        impact_weights = {'critical': 3, 'high': 2, 'medium': 1.5, 'low': 1}
        
        weighted_sum = 0
        total_weight = 0
        
        for item in news:
            weight = impact_weights.get(item.impact_level, 1)
            weighted_sum += item.sentiment_score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def _score_to_level(self, score: float) -> SentimentLevel:
        """Convertir score en niveau"""
        
        if score <= -0.5:
            return SentimentLevel.EXTREME_FEAR
        elif score <= -0.2:
            return SentimentLevel.FEAR
        elif score <= 0.2:
            return SentimentLevel.NEUTRAL
        elif score <= 0.5:
            return SentimentLevel.GREED
        else:
            return SentimentLevel.EXTREME_GREED
    
    def _calculate_trend(self, minutes: int) -> float:
        """Calculer la tendance sur X minutes"""
        
        if len(self.sentiment_history) < 2:
            return 0
        
        recent = list(self.sentiment_history)
        
        # Filtrer par temps
        cutoff = datetime.now() - timedelta(minutes=minutes)
        filtered = [s for s in recent if s['timestamp'] > cutoff]
        
        if len(filtered) < 2:
            return 0
        
        first = filtered[0]['score']
        last = filtered[-1]['score']
        
        return last - first
    
    def _check_alerts(
        self, 
        composite: float, 
        fear_greed: int, 
        news: List[NewsItem],
        trend_1h: float
    ) -> Tuple[bool, str]:
        """Vérifier les conditions d'alerte"""
        
        alerts = []
        
        # Extreme fear
        if composite < self.alert_thresholds['extreme_fear']:
            alerts.append(f"Sentiment extrêmement négatif ({composite:.2f})")
        
        # Extreme greed
        if composite > self.alert_thresholds['extreme_greed']:
            alerts.append(f"Sentiment extrêmement positif ({composite:.2f})")
        
        # Changement rapide
        if abs(trend_1h) > self.alert_thresholds['rapid_change']:
            direction = "hausse" if trend_1h > 0 else "baisse"
            alerts.append(f"Changement rapide ({direction}: {abs(trend_1h):.2f} en 1h)")
        
        # News critique
        critical_news = [n for n in news if n.impact_level == 'critical']
        if critical_news:
            alerts.append(f"News critique: {critical_news[0].title[:50]}...")
        
        if alerts:
            return True, "; ".join(alerts)
        
        return False, ""
    
    def _extract_key_events(self, news: List[NewsItem]) -> List[str]:
        """Extraire les événements clés"""
        
        events = []
        
        high_impact = [n for n in news if n.impact_level in ['critical', 'high']]
        
        for item in high_impact[:5]:
            events.append(f"[{item.impact_level.upper()}] {item.title[:100]}")
        
        return events
    
    async def get_summary(self) -> Dict:
        """Récupérer un résumé du sentiment actuel"""
        
        data = await self.state.get('sentiment_data', {})
        
        return {
            'score': data.get('composite_score', 0),
            'level': data.get('level', 'neutral'),
            'fear_greed': data.get('fear_greed', 50),
            'news_count': data.get('news_count', 0),
            'trend': 'up' if data.get('trend_1h', 0) > 0 else 'down',
            'alert': data.get('alert'),
            'last_update': data.get('last_update')
        }
    
    async def close(self):
        """Fermer la session HTTP"""
        if self.session:
            await self.session.close()
