#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               TRADINGBOT V5 - HELPERS                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from typing import Optional, Union


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division sécurisée évitant les divisions par zéro"""
    if denominator == 0:
        return default
    return numerator / denominator


def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """Formater un montant en devise"""
    if currency == "USD":
        return f"${amount:,.{decimals}f}"
    elif currency == "EUR":
        return f"€{amount:,.{decimals}f}"
    else:
        return f"{amount:,.{decimals}f} {currency}"


def format_percentage(value: float, decimals: int = 2, include_sign: bool = True) -> str:
    """Formater un pourcentage"""
    if include_sign and value > 0:
        return f"+{value:.{decimals}f}%"
    return f"{value:.{decimals}f}%"


def calculate_pnl_percentage(entry_price: float, current_price: float, side: str = "long") -> float:
    """Calculer le PnL en pourcentage"""
    if entry_price == 0:
        return 0.0
    
    if side.lower() == "long":
        return ((current_price - entry_price) / entry_price) * 100
    else:  # short
        return ((entry_price - current_price) / entry_price) * 100


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """Convertir un timestamp en datetime"""
    # Si timestamp en millisecondes
    if timestamp > 1e12:
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime, milliseconds: bool = False) -> int:
    """Convertir un datetime en timestamp"""
    ts = dt.timestamp()
    if milliseconds:
        return int(ts * 1000)
    return int(ts)


def calculate_position_size(
    account_balance: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float,
    leverage: float = 1.0
) -> float:
    """
    Calculer la taille de position basée sur le risque
    
    Args:
        account_balance: Solde du compte
        risk_per_trade: % du compte à risquer (ex: 2.0 pour 2%)
        entry_price: Prix d'entrée
        stop_loss_price: Prix du stop loss
        leverage: Levier utilisé
        
    Returns:
        Taille de la position en unités
    """
    risk_amount = account_balance * (risk_per_trade / 100)
    price_diff = abs(entry_price - stop_loss_price)
    
    if price_diff == 0:
        return 0.0
    
    position_size = (risk_amount / price_diff) * leverage
    return position_size


def calculate_kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.25
) -> float:
    """
    Calculer la fraction de Kelly pour le sizing
    
    Args:
        win_rate: Taux de réussite (0-1)
        avg_win: Gain moyen
        avg_loss: Perte moyenne (valeur absolue)
        fraction: Fraction de Kelly à utiliser (défaut 0.25 = quart Kelly)
        
    Returns:
        Pourcentage du capital à utiliser
    """
    if avg_loss == 0:
        return 0.0
    
    # Formule de Kelly: f* = (bp - q) / b
    # où b = ratio win/loss, p = prob win, q = prob loss
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - win_rate
    
    kelly = (b * p - q) / b
    
    # Limiter entre 0 et fraction max
    kelly = max(0, min(kelly, 1.0))
    
    return kelly * fraction


def normalize_symbol(symbol: str) -> str:
    """Normaliser un symbole de trading"""
    # Supprimer les espaces
    symbol = symbol.strip().upper()
    
    # Standardiser le séparateur
    for sep in ['-', '_', ' ']:
        symbol = symbol.replace(sep, '/')
    
    return symbol


def get_timeframe_seconds(timeframe: str) -> int:
    """Convertir un timeframe en secondes"""
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
    }
    
    unit = timeframe[-1].lower()
    value = int(timeframe[:-1])
    
    return value * multipliers.get(unit, 60)


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Limiter une valeur entre min et max"""
    return max(min_value, min(value, max_value))
