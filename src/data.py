import os
import pandas as pd
import requests
from typing import Optional
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv

load_dotenv()

class MarketDataProvider:
    """Handles fetching and caching market data using Tiingo."""
    
    def __init__(self):
        self.cache = {}
        self.tiingo_api_key = os.getenv('TIINGO_API_KEY')
        self.base_url = "https://api.tiingo.com/tiingo"
        
        if not self.tiingo_api_key:
            print("⚠️ Warning: Missing Tiingo API key. Get one free at https://api.tiingo.com/account/api/token")
            print("💡 Using demo mode with limited data access")
            self.tiingo_api_key = "demo"
        else:
            print("✅ Tiingo API configured")
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test Tiingo API connection."""
        try:
            response = requests.get(
                f"{self.base_url}/daily/AAPL/prices",
                params={
                    'token': self.tiingo_api_key,
                    'startDate': '2024-01-01',
                    'endDate': '2024-01-05'
                },
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Tiingo connection verified")
            else:
                print(f"⚠️ Tiingo connection issue: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Tiingo connection test failed: {e}")
    
    def get_historical_data(
        self, 
        ticker: str, 
        period: str = "1y", 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data using Tiingo."""
        cache_key = f"{ticker}_{period}_{start_date}_{end_date}"
        
        if cache_key in self.cache:
            return self.cache[cache_key].copy()
        
        # Calculate date range
        if start_date and end_date:
            start = start_date
            end = end_date
        else:
            end = datetime.now().strftime("%Y-%m-%d")
            if period == "1d":
                start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            elif period == "5d":
                start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            elif period == "1mo":
                start = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
            elif period == "3mo":
                start = (datetime.now() - timedelta(days=95)).strftime("%Y-%m-%d")
            elif period == "6mo":
                start = (datetime.now() - timedelta(days=190)).strftime("%Y-%m-%d")
            elif period == "1y":
                start = (datetime.now() - timedelta(days=370)).strftime("%Y-%m-%d")
            elif period == "2y":
                start = (datetime.now() - timedelta(days=740)).strftime("%Y-%m-%d")
            elif period == "5y":
                start = (datetime.now() - timedelta(days=1850)).strftime("%Y-%m-%d")
            else:
                start = (datetime.now() - timedelta(days=370)).strftime("%Y-%m-%d")
        
        print(f"📊 Fetching {ticker} data from {start} to {end} via Tiingo")
        
        try:
            # Make request to Tiingo
            url = f"{self.base_url}/daily/{ticker}/prices"
            params = {
                'token': self.tiingo_api_key,
                'startDate': start,
                'endDate': end,
                'format': 'json'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data_json = response.json()
            
            if not data_json:
                raise ValueError(f"No data returned for {ticker}")
            
            # Convert to DataFrame
            df = pd.DataFrame(data_json)
            
            if df.empty:
                raise ValueError(f"Empty dataset returned for {ticker}")
            
            # Parse and set date index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.sort_index()
            
            # Rename columns to match our standard
            column_mapping = {
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'adjOpen': 'adj_open',
                'adjHigh': 'adj_high',
                'adjLow': 'adj_low',
                'adjClose': 'adj_close',
                'adjVolume': 'adj_volume'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Keep only required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            available_columns = [col for col in required_columns if col in df.columns]
            
            if len(available_columns) < 5:
                raise ValueError(f"Missing required columns. Available: {available_columns}")
            
            df = df[required_columns]
            
            # Ensure numeric types
            df = df.astype(float)
            
            # Remove any rows with NaN values
            df = df.dropna()
            
            if df.empty:
                raise ValueError(f"No valid data found for ticker {ticker} after cleaning")
            
            print(f"✅ Successfully fetched {len(df)} data points for {ticker}")
            
            # Cache the data
            self.cache[cache_key] = df.copy()
            
            return df
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                raise RuntimeError(f"Invalid ticker symbol: {ticker}")
            elif e.response.status_code == 401:
                raise RuntimeError("Invalid Tiingo API key. Get one free at https://api.tiingo.com/account/api/token")
            elif e.response.status_code == 403:
                raise RuntimeError("Tiingo API key doesn't have required permissions")
            else:
                raise RuntimeError(f"Tiingo API error {e.response.status_code}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch data for {ticker}: {str(e)}")
    
    def get_current_price(self, ticker: str) -> float:
        """Get current price using Tiingo."""
        try:
            # Method 1: Try latest price endpoint
            url = f"{self.base_url}/daily/{ticker}/prices"
            params = {
                'token': self.tiingo_api_key,
                'startDate': (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
                'endDate': datetime.now().strftime("%Y-%m-%d")
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                latest = data[-1]  # Last element is most recent
                return float(latest['close'])
            
            # Method 2: Try IEX endpoint for real-time data
            iex_url = f"https://api.tiingo.com/iex/{ticker}"
            iex_params = {'token': self.tiingo_api_key}
            
            response = requests.get(iex_url, params=iex_params, timeout=10)
            response.raise_for_status()
            
            iex_data = response.json()
            
            if iex_data and len(iex_data) > 0:
                return float(iex_data[0]['last'])
            
            raise ValueError(f"No current price data available for {ticker}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to get current price for {ticker}: {str(e)}")
    
    def get_intraday_data(self, ticker: str, date: str = None) -> pd.DataFrame:
        """Get intraday data for a specific date."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        try:
            url = f"https://api.tiingo.com/iex/{ticker}/prices"
            params = {
                'token': self.tiingo_api_key,
                'startDate': date,
                'endDate': date,
                'resampleFreq': '1min'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Intraday data fetch failed: {e}")
            return pd.DataFrame()

# Global instance
market_data = MarketDataProvider()
