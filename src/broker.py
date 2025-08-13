import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    quantity: float
    market_value: float
    avg_entry_price: float
    unrealized_pnl: float
    side: str  # 'long' or 'short'

@dataclass
class Order:
    """Represents a trading order."""
    symbol: str
    quantity: float
    side: str  # 'buy' or 'sell'
    order_type: str = 'market'
    time_in_force: str = 'day'

class AlpacaBroker:
    """Alpaca broker integration for paper and live trading."""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
        if not self.api_key or not self.secret_key:
            print("⚠️ Warning: Missing Alpaca API credentials. Live trading features disabled.")
            self.api = None
            return
        
        try:
            import alpaca_trade_api as tradeapi
            
            # Initialize Alpaca API
            self.api = tradeapi.REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url,
                api_version='v2'
            )
            
            # Verify connection
            account = self.api.get_account()
            print(f"✅ Connected to Alpaca ({account.status})")
            print(f"💰 Buying Power: ${float(account.buying_power):,.2f}")
            
        except ImportError:
            print("⚠️ Warning: alpaca-trade-api not installed. Live trading features disabled.")
            self.api = None
        except Exception as e:
            print(f"⚠️ Warning: Failed to connect to Alpaca: {e}")
            self.api = None
    
    def get_account_info(self) -> Dict:
        """Get account information."""
        if not self.api:
            raise RuntimeError("Alpaca API not available. Check credentials and installation.")
            
        account = self.api.get_account()
        return {
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'portfolio_value': float(account.portfolio_value),
            'day_trade_count': getattr(account, 'day_trade_count', 0),  # Handle missing attribute
            'status': account.status
        }
    
    def get_positions(self) -> List[Position]:
        """Get all current positions."""
        if not self.api:
            return []
            
        positions = self.api.list_positions()
        return [
            Position(
                symbol=pos.symbol,
                quantity=float(pos.qty),
                market_value=float(pos.market_value),
                avg_entry_price=float(pos.avg_entry_price),
                unrealized_pnl=float(pos.unrealized_pnl),
                side=pos.side
            )
            for pos in positions
        ]
    
    def place_order(self, order: Order) -> str:
        """Place a trading order."""
        if not self.api:
            raise RuntimeError("Alpaca API not available. Check credentials and installation.")
            
        try:
            alpaca_order = self.api.submit_order(
                symbol=order.symbol,
                qty=abs(order.quantity),
                side=order.side,
                type=order.order_type,
                time_in_force=order.time_in_force
            )
            
            print(f"📝 Order placed: {order.side.upper()} {order.quantity} {order.symbol}")
            return alpaca_order.id
            
        except Exception as e:
            print(f"❌ Order failed: {e}")
            raise
    
    def cancel_all_orders(self):
        """Cancel all pending orders."""
        if not self.api:
            return
            
        try:
            self.api.cancel_all_orders()
            print("🚫 All pending orders cancelled")
        except Exception as e:
            print(f"❌ Failed to cancel orders: {e}")
    
    def close_all_positions(self):
        """Close all open positions."""
        if not self.api:
            return
            
        try:
            self.api.close_all_positions()
            print("🔚 All positions closed")
        except Exception as e:
            print(f"❌ Failed to close positions: {e}")

# Global broker instance
broker = AlpacaBroker()
