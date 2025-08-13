from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, **params):
        self.params = params
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on market data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Series with 1 (buy), -1 (sell), 0 (hold) signals
        """
        pass
    
    def get_description(self) -> str:
        """Return a description of the strategy and its parameters."""
        return f"{self.name} with parameters: {self.params}"

class SMAStrategy(BaseStrategy):
    """Simple Moving Average Crossover Strategy."""
    
    def __init__(self, fast_window: int = 20, slow_window: int = 50):
        super().__init__(fast_window=fast_window, slow_window=slow_window)
        self.fast_window = fast_window
        self.slow_window = slow_window
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on SMA crossover."""
        # Calculate moving averages
        fast_ma = data['close'].rolling(window=self.fast_window).mean()
        slow_ma = data['close'].rolling(window=self.slow_window).mean()
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy when fast MA crosses above slow MA
        signals[(fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))] = 1
        
        # Sell when fast MA crosses below slow MA
        signals[(fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))] = -1
        
        return signals

class MomentumStrategy(BaseStrategy):
    """Price Momentum Strategy."""
    
    def __init__(self, lookback_period: int = 14, threshold: float = 0.02):
        super().__init__(lookback_period=lookback_period, threshold=threshold)
        self.lookback_period = lookback_period
        self.threshold = threshold
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on price momentum."""
        # Calculate momentum (rate of change)
        momentum = data['close'].pct_change(periods=self.lookback_period)
        
        # Generate signals
        signals = pd.Series(0, index=data.index)
        
        # Buy on strong positive momentum
        signals[momentum > self.threshold] = 1
        
        # Sell on strong negative momentum
        signals[momentum < -self.threshold] = -1
        
        return signals

class BuyAndHoldStrategy(BaseStrategy):
    """Simple buy and hold strategy for benchmarking."""
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate buy signal on first day, hold thereafter."""
        signals = pd.Series(0, index=data.index)
        signals.iloc[0] = 1  # Buy on first day
        return signals

# Strategy registry for easy access
STRATEGIES = {
    'sma': SMAStrategy,
    'momentum': MomentumStrategy,
    'buy_hold': BuyAndHoldStrategy,
}

def get_strategy(name: str, **params) -> BaseStrategy:
    """Get a strategy instance by name."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    
    return STRATEGIES[name](**params)
