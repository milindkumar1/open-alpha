from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn

from openalpha.data import market_data
from openalpha.strategies import get_strategy, STRATEGIES
from openalpha.backtest import Backtester

# Initialize FastAPI app
app = FastAPI(
    title="OpenAlpha Trading API",
    description="AI-powered trading platform API",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class BacktestRequest(BaseModel):
    ticker: str
    strategy: str
    period: str = "1y"
    initial_capital: float = 100000
    strategy_params: Dict[str, Any] = {}

class BacktestResponse(BaseModel):
    ticker: str
    strategy: str
    metrics: Dict[str, float]
    equity_curve: Dict[str, float]
    trades: list

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "OpenAlpha Trading API", "version": "0.1.0", "status": "running"}

@app.get("/strategies")
async def list_strategies():
    """Get list of available strategies."""
    return {
        "strategies": {
            name: {
                "name": name,
                "description": strategy_class.__doc__ or "No description",
                "class": strategy_class.__name__
            }
            for name, strategy_class in STRATEGIES.items()
        }
    }

@app.get("/market-data/{ticker}")
async def get_market_data(ticker: str, period: str = "1mo"):
    """Get historical market data for a ticker."""
    try:
        data = market_data.get_historical_data(ticker, period=period)
        
        # Convert to JSON-serializable format
        result = {
            "ticker": ticker.upper(),
            "period": period,
            "data_points": len(data),
            "date_range": {
                "start": data.index[0].strftime("%Y-%m-%d"),
                "end": data.index[-1].strftime("%Y-%m-%d")
            },
            "latest_price": float(data['close'].iloc[-1]),
            "data": [
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume'])
                }
                for date, row in data.iterrows()
            ]
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """Run a backtest for given parameters."""
    try:
        # Fetch market data
        data = market_data.get_historical_data(request.ticker, period=request.period)
        
        # Initialize strategy
        strategy = get_strategy(request.strategy, **request.strategy_params)
        
        # Run backtest
        backtester = Backtester(initial_capital=request.initial_capital)
        results = backtester.run_backtest(data, strategy)
        
        # Format response
        equity_curve = {
            date.strftime("%Y-%m-%d"): float(value)
            for date, value in results.equity_curve.items()
        }
        
        trades = [
            {
                "date": row['date'].strftime("%Y-%m-%d"),
                "signal": int(row['signal']),
                "price": float(row['price']),
                "position": float(row['position'])
            }
            for _, row in results.trades.iterrows()
        ]
        
        return BacktestResponse(
            ticker=request.ticker.upper(),
            strategy=request.strategy,
            metrics=results.metrics,
            equity_curve=equity_curve,
            trades=trades
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/price/{ticker}")
async def get_current_price(ticker: str):
    """Get current price for a ticker."""
    try:
        price = market_data.get_current_price(ticker)
        return {
            "ticker": ticker.upper(),
            "price": price,
            "timestamp": "now"  # You might want to add actual timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
