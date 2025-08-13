import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .strategies import BaseStrategy

@dataclass
class BacktestResults:
    """Container for backtest results."""
    returns: pd.Series
    positions: pd.Series
    trades: pd.DataFrame
    metrics: Dict[str, float]
    equity_curve: pd.Series

class Backtester:
    """Vectorized backtesting engine."""
    
    def __init__(self, initial_capital: float = 100000, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_backtest(
        self, 
        data: pd.DataFrame, 
        strategy: BaseStrategy,
        position_size: float = 1.0
    ) -> BacktestResults:
        """
        Run backtest for a strategy on given data.
        
        Args:
            data: OHLCV data
            strategy: Strategy instance
            position_size: Fraction of capital to risk per trade (0.0 to 1.0)
        """
        # Generate signals
        signals = strategy.generate_signals(data)
        
        # Calculate positions (forward-fill signals)
        positions = signals.replace(0, np.nan).fillna(method='ffill').fillna(0)
        
        # Calculate returns
        returns = data['close'].pct_change()
        strategy_returns = positions.shift(1) * returns * position_size
        
        # Apply commission costs
        trades = positions.diff().abs()
        commission_costs = trades * self.commission
        strategy_returns = strategy_returns - commission_costs
        
        # Calculate equity curve
        equity_curve = (1 + strategy_returns).cumprod() * self.initial_capital
        
        # Generate trade log
        trade_signals = signals[signals != 0]
        trades_df = pd.DataFrame({
            'date': trade_signals.index,
            'signal': trade_signals.values,
            'price': data.loc[trade_signals.index, 'close'],
            'position': positions.loc[trade_signals.index]
        })
        
        # Calculate performance metrics
        metrics = self._calculate_metrics(strategy_returns, equity_curve)
        
        return BacktestResults(
            returns=strategy_returns,
            positions=positions,
            trades=trades_df,
            metrics=metrics,
            equity_curve=equity_curve
        )
    
    def _calculate_metrics(self, returns: pd.Series, equity_curve: pd.Series) -> Dict[str, float]:
        """Calculate performance metrics."""
        # Remove any NaN values
        returns_clean = returns.dropna()
        
        if len(returns_clean) == 0:
            return {
                'total_return': 0.0,
                'annual_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'num_trades': 0
            }
        
        # Basic metrics
        total_return = (equity_curve.iloc[-1] / self.initial_capital) - 1
        annual_return = (1 + total_return) ** (252 / len(returns_clean)) - 1
        volatility = returns_clean.std() * np.sqrt(252)
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0.0
        
        # Maximum drawdown
        peak = equity_curve.expanding().max()
        drawdown = (equity_curve - peak) / peak
        max_drawdown = drawdown.min()
        
        # Win rate
        winning_trades = (returns_clean > 0).sum()
        total_trades = (returns_clean != 0).sum()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        return {
            'total_return': round(total_return * 100, 2),
            'annual_return': round(annual_return * 100, 2),
            'volatility': round(volatility * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'win_rate': round(win_rate * 100, 2),
            'num_trades': int(total_trades)
        }
