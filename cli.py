import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from openalpha.data import market_data
from openalpha.strategies import get_strategy, STRATEGIES
from openalpha.backtest import Backtester

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

if __name__ == "__main__":
    app()
