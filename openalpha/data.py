import yfinance as yf
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta

class MarketDataProvider:
    """Handles fetching and caching market data."""
    
    def __init__(self):
        self.cache = {}
    
    def get_historical_data(
        self, 
        ticker: str, 
        period: str = "1y", 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a ticker.
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL')
            period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
        """
        cache_key = f"{ticker}_{period}_{start_date}_{end_date}"
        
        if cache_key in self.cache:
            return self.cache[cache_key].copy()
        
        try:
            stock = yf.Ticker(ticker)
            
            if start_date and end_date:
                data = stock.history(start=start_date, end=end_date)
            else:
                data = stock.history(period=period)
            
            if data.empty:
                raise ValueError(f"No data found for ticker {ticker}")
            
            # Clean and standardize column names
            data.columns = data.columns.str.lower()
            data.index.name = 'date'
            
            # Cache the data
            self.cache[cache_key] = data.copy()
            
            return data
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data for {ticker}: {str(e)}")
    
    def get_current_price(self, ticker: str) -> float:
        """Get the most recent price for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.history(period="1d")
            if info.empty:
                raise ValueError(f"No current price data for {ticker}")
            return float(info['Close'].iloc[-1])
        except Exception as e:
            raise RuntimeError(f"Failed to get current price for {ticker}: {str(e)}")

# Global instance
market_data = MarketDataProvider()
