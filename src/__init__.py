"""OpenAlpha Trading Platform Core Module."""

__version__ = "0.1.0"

# Import main components for easier access
from .data import market_data
from .strategies import get_strategy, STRATEGIES
from .backtest import Backtester
from .broker import broker
from .live_trading import LiveTrader

# Define what gets imported with "from src import *"
__all__ = [
    'market_data',
    'get_strategy', 
    'STRATEGIES',
    'Backtester',
    'broker',
    'LiveTrader'
]
