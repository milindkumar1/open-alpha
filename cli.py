import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from src.data import market_data
from src.strategies import get_strategy, STRATEGIES
from src.backtest import Backtester
from src.live_trading import LiveTrader
from src.broker import broker

app = typer.Typer(help="OpenAlpha Trading Platform CLI")
console = Console()

@app.command()
def backtest(
    ticker: str = typer.Argument(..., help="Stock ticker symbol (e.g., AAPL)"),
    strategy: str = typer.Option("sma", help=f"Strategy to use: {list(STRATEGIES.keys())}"),
    period: str = typer.Option("1y", help="Time period for data"),
    capital: float = typer.Option(100000, help="Initial capital"),
    fast: int = typer.Option(20, help="Fast window for SMA strategy"),
    slow: int = typer.Option(50, help="Slow window for SMA strategy"),
    lookback: int = typer.Option(14, help="Lookback period for momentum strategy"),
    threshold: float = typer.Option(0.02, help="Threshold for momentum strategy"),
):
    """Run a backtest for a given ticker and strategy."""
    
    console.print(f"\n[bold blue]Running backtest for {ticker.upper()}[/bold blue]")
    console.print(f"Strategy: {strategy}")
    console.print(f"Period: {period}")
    console.print(f"Initial Capital: ${capital:,.2f}\n")
    
    try:
        # Fetch data
        with console.status("[bold green]Fetching market data..."):
            data = market_data.get_historical_data(ticker, period=period)
        
        console.print(f"✅ Fetched {len(data)} days of data")
        
        # Initialize strategy
        strategy_params = {}
        if strategy == "sma":
            strategy_params = {"fast_window": fast, "slow_window": slow}
        elif strategy == "momentum":
            strategy_params = {"lookback_period": lookback, "threshold": threshold}
        
        strat = get_strategy(strategy, **strategy_params)
        console.print(f"📊 {strat.get_description()}")
        
        # Run backtest
        with console.status("[bold green]Running backtest..."):
            backtester = Backtester(initial_capital=capital)
            results = backtester.run_backtest(data, strat)
        
        # Display results
        _display_results(results)
        
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise typer.Exit(1)

def _display_results(results):
    """Display backtest results in a formatted table."""
    
    # Performance metrics table
    table = Table(title="📈 Backtest Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    metrics = results.metrics
    table.add_row("Total Return", f"{metrics['total_return']:.2f}%")
    table.add_row("Annual Return", f"{metrics['annual_return']:.2f}%")
    table.add_row("Volatility", f"{metrics['volatility']:.2f}%")
    table.add_row("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    table.add_row("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")
    table.add_row("Win Rate", f"{metrics['win_rate']:.2f}%")
    table.add_row("Number of Trades", str(metrics['num_trades']))
    
    console.print(table)
    
    # Final equity value
    final_equity = results.equity_curve.iloc[-1]
    initial_equity = results.equity_curve.iloc[0]
    profit_loss = final_equity - initial_equity
    
    console.print(f"\n[bold]Final Portfolio Value: [green]${final_equity:,.2f}[/green][/bold]")
    console.print(f"[bold]Profit/Loss: [{'green' if profit_loss >= 0 else 'red'}]${profit_loss:,.2f}[/{'green' if profit_loss >= 0 else 'red'}][/bold]")

@app.command()
def list_strategies():
    """List available trading strategies."""
    console.print("\n[bold blue]Available Trading Strategies:[/bold blue]\n")
    
    for name, strategy_class in STRATEGIES.items():
        console.print(f"• [cyan]{name}[/cyan]: {strategy_class.__doc__ or 'No description'}")

@app.command()
def live_trade(
    symbols: str = typer.Argument(..., help="Comma-separated symbols (e.g., AAPL,MSFT,GOOGL)"),
    strategy: str = typer.Option("sma", help=f"Strategy to use: {list(STRATEGIES.keys())}"),
    interval: int = typer.Option(60, help="Check interval in minutes"),
    position_size: float = typer.Option(0.1, help="Position size as fraction of portfolio"),
    fast: int = typer.Option(20, help="Fast window for SMA strategy"),
    slow: int = typer.Option(50, help="Slow window for SMA strategy"),
):
    """Start live trading with paper money."""
    
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    
    console.print(f"\n[bold blue]🚀 Starting Live Trading[/bold blue]")
    console.print(f"Symbols: {symbol_list}")
    console.print(f"Strategy: {strategy}")
    console.print(f"Position Size: {position_size * 100}% per symbol")
    
    try:
        # Check broker connection
        if not broker.api:
            console.print("[bold red]❌ Alpaca API not available. Please check:[/bold red]")
            console.print("1. Install alpaca-trade-api: pip install alpaca-trade-api")
            console.print("2. Create .env file with your Alpaca credentials")
            console.print("3. Make sure credentials are valid")
            raise typer.Exit(1)
            
        account = broker.get_account_info()
        console.print(f"✅ Connected to Alpaca")
        console.print(f"💰 Buying Power: ${account['buying_power']:,.2f}")
        
        # Initialize strategy
        strategy_params = {}
        if strategy == "sma":
            strategy_params = {"fast_window": fast, "slow_window": slow}
        
        strat = get_strategy(strategy, **strategy_params)
        console.print(f"📊 {strat.get_description()}")
        
        # Start live trader
        trader = LiveTrader(
            strategy=strat,
            symbols=symbol_list,
            position_size=position_size
        )
        
        trader.start(interval_minutes=interval)
        
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        raise typer.Exit(1)

@app.command()
def account():
    """Show account information."""
    try:
        if not broker.api:
            console.print("[bold red]❌ Alpaca API not available.[/bold red]")
            console.print("Please install alpaca-trade-api and set up .env file with credentials.")
            raise typer.Exit(1)
            
        account = broker.get_account_info()
        positions = broker.get_positions()
        
        # Account info table
        table = Table(title="💰 Account Information", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Portfolio Value", f"${account['portfolio_value']:,.2f}")
        table.add_row("Buying Power", f"${account['buying_power']:,.2f}")
        table.add_row("Cash", f"${account['cash']:,.2f}")
        table.add_row("Status", account['status'])
        
        # Only show day trade count if it exists and is > 0
        if account.get('day_trade_count', 0) > 0:
            table.add_row("Day Trade Count", str(account['day_trade_count']))
        
        console.print(table)
        
        # Positions table
        if positions:
            pos_table = Table(title="📊 Current Positions", show_header=True)
            pos_table.add_column("Symbol", style="cyan")
            pos_table.add_column("Quantity", style="white")
            pos_table.add_column("Market Value", style="green")
            pos_table.add_column("Unrealized P&L", style="magenta")
            
            for pos in positions:
                pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"
                pos_table.add_row(
                    pos.symbol,
                    f"{pos.quantity:.2f}",
                    f"${pos.market_value:,.2f}",
                    f"[{pnl_color}]${pos.unrealized_pnl:,.2f}[/{pnl_color}]"
                )
            
            console.print(pos_table)
        else:
            console.print("📭 No open positions")
            
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")

if __name__ == "__main__":
    app()
