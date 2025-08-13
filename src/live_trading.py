import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
from .strategies import BaseStrategy
from .data import market_data
from .broker import broker, Order

class LiveTrader:
    """Executes strategies against live market using paper trading."""
    
    def __init__(self, strategy: BaseStrategy, symbols: list, position_size: float = 0.1):
        self.strategy = strategy
        self.symbols = symbols
        self.position_size = position_size  # Fraction of portfolio per position
        self.running = False
        self.positions = {}
        
    def start(self, interval_minutes: int = 60):
        """Start live trading loop."""
        print(f"🚀 Starting live trader with {self.strategy.name}")
        print(f"📊 Symbols: {self.symbols}")
        print(f"⏰ Check interval: {interval_minutes} minutes")
        
        if not broker.api:
            print("❌ Cannot start live trading - Alpaca API not available")
            return
        
        self.running = True
        
        try:
            while self.running:
                if self._is_market_open():
                    print("🔔 Market is OPEN - executing trading logic")
                    self._trading_loop()
                else:
                    market_status = self._get_market_status()
                    print(f"🔕 Market is CLOSED - {market_status}")
                    print("💡 You can still analyze positions and prepare for next session")
                    self._analysis_loop()
                
                print(f"💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n⏹️ Stopping live trader...")
            self.stop()
    
    def stop(self):
        """Stop live trading."""
        self.running = False
        print("🛑 Live trader stopped")
    
    def _is_market_open(self) -> bool:
        """Check if US stock market is currently open."""
        try:
            # Get market clock from Alpaca
            clock = broker.api.get_clock()
            return clock.is_open
        except Exception as e:
            print(f"⚠️ Could not check market status: {e}")
            # Fallback: check basic market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
            return self._is_market_hours_basic()
    
    def _is_market_hours_basic(self) -> bool:
        """Basic market hours check (fallback)."""
        et = pytz.timezone('US/Eastern')
        now_et = datetime.now(et)
        
        # Check if it's a weekday
        if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check if it's during market hours (9:30 AM - 4:00 PM ET)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now_et <= market_close
    
    def _get_market_status(self) -> str:
        """Get detailed market status."""
        try:
            clock = broker.api.get_clock()
            if not clock.is_open:
                next_open = clock.next_open.astimezone(pytz.timezone('US/Eastern'))
                return f"Next market open: {next_open.strftime('%Y-%m-%d %H:%M %Z')}"
        except:
            pass
        
        et = pytz.timezone('US/Eastern')
        now_et = datetime.now(et)
        
        if now_et.weekday() >= 5:
            # Weekend
            days_until_monday = (7 - now_et.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 1
            next_monday = now_et + timedelta(days=days_until_monday)
            next_open = next_monday.replace(hour=9, minute=30, second=0, microsecond=0)
            return f"Weekend - Next open: {next_open.strftime('%A %Y-%m-%d %H:%M %Z')}"
        else:
            # Weekday but after hours
            if now_et.hour >= 16:
                # After market close, next open is tomorrow
                tomorrow = now_et + timedelta(days=1)
                next_open = tomorrow.replace(hour=9, minute=30, second=0, microsecond=0)
                return f"After hours - Next open: {next_open.strftime('%Y-%m-%d %H:%M %Z')}"
            else:
                # Before market open
                today_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                return f"Pre-market - Opens at: {today_open.strftime('%H:%M %Z')}"
    
    def _trading_loop(self):
        """Single iteration of trading logic (when market is open)."""
        print(f"\n🔄 Trading loop at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Get account info
            account = broker.get_account_info()
            portfolio_value = account['portfolio_value']
            
            print(f"💰 Portfolio Value: ${portfolio_value:,.2f}")
            
            for symbol in self.symbols:
                try:
                    self._process_symbol(symbol, portfolio_value, execute_orders=True)
                except Exception as e:
                    print(f"❌ Error processing {symbol}: {e}")
                    
        except Exception as e:
            print(f"❌ Error in trading loop: {e}")
    
    def _analysis_loop(self):
        """Analysis mode when market is closed (no order execution)."""
        print(f"\n🔍 Analysis mode at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Get account info
            account = broker.get_account_info()
            portfolio_value = account['portfolio_value']
            
            print(f"💰 Portfolio Value: ${portfolio_value:,.2f}")
            
            # Show current positions
            positions = broker.get_positions()
            if positions:
                print("\n📊 Current Positions:")
                for pos in positions:
                    pnl_emoji = "📈" if pos.unrealized_pnl >= 0 else "📉"
                    print(f"  {pnl_emoji} {pos.symbol}: {pos.quantity:.2f} shares, "
                          f"P&L: ${pos.unrealized_pnl:.2f}")
            
            for symbol in self.symbols:
                try:
                    self._process_symbol(symbol, portfolio_value, execute_orders=False)
                except Exception as e:
                    print(f"❌ Error analyzing {symbol}: {e}")
                    
        except Exception as e:
            print(f"❌ Error in analysis loop: {e}")
    
    def _process_symbol(self, symbol: str, portfolio_value: float, execute_orders: bool = True):
        """Process trading signals for a single symbol."""
        action_text = "Trading" if execute_orders else "Analyzing"
        print(f"\n📈 {action_text} {symbol}...")
        
        # Get recent data for signal generation
        data = market_data.get_historical_data(symbol, period="1mo")
        
        # Generate signals
        signals = self.strategy.generate_signals(data)
        latest_signal = signals.iloc[-1] if len(signals) > 0 else 0
        
        # Get current position
        positions = broker.get_positions()
        current_position = next((p for p in positions if p.symbol == symbol), None)
        current_qty = current_position.quantity if current_position else 0
        
        print(f"🎯 Signal: {latest_signal}, Current Position: {current_qty}")
        
        # Calculate target position size
        target_value = portfolio_value * self.position_size * latest_signal
        current_price = market_data.get_current_price(symbol)
        target_qty = target_value / current_price if current_price > 0 else 0
        
        # Calculate order quantity
        order_qty = target_qty - current_qty
        
        if abs(order_qty) > 0.1:  # Minimum order threshold
            side = 'buy' if order_qty > 0 else 'sell'
            
            if execute_orders:
                order = Order(
                    symbol=symbol,
                    quantity=abs(order_qty),
                    side=side
                )
                
                try:
                    order_id = broker.place_order(order)
                    print(f"✅ Order executed: {order_id}")
                except Exception as e:
                    print(f"❌ Order failed for {symbol}: {e}")
            else:
                print(f"📝 Would {side.upper()} {abs(order_qty):.2f} shares of {symbol} (market closed)")
        else:
            print(f"😴 No action needed for {symbol}")
