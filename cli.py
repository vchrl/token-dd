#!/usr/bin/env python3
"""
CLI Wrapper for Protocol Due Diligence Engine.
Rich terminal UI around the existing due_diligence.py pipeline.
"""
import sys
import time
import webbrowser
import argparse
from pathlib import Path
from datetime import datetime, timezone

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, IntPrompt
    from rich.table import Table
    from rich.live import Live
    from rich import box
except ImportError:
    print("\n  ❌ 'rich' library required. Install with: pip install rich\n")
    sys.exit(1)

import due_diligence as dd
from html_report import generate_html_report

console = Console()

# ─── Banner ──────────────────────────────────────────────────────────
BANNER = """
[bold cyan]╔══════════════════════════════════════════════╗
║   Protocol Due Diligence Engine              ║
║   ─────────────────────────────              ║
║   Powered by Nansen CLI + x402              ║
╚══════════════════════════════════════════════╝[/]"""


def format_usd_short(value):
    """Format USD value for CLI display."""
    if value is None:
        return "N/A"
    if abs(value) >= 1e9:
        return f"${value/1e9:,.1f}B"
    if abs(value) >= 1e6:
        return f"${value/1e6:,.1f}M"
    if abs(value) >= 1e3:
        return f"${value/1e3:,.1f}K"
    return f"${value:,.2f}"


def snippet_screener(data: list, token: str) -> str:
    """Extract snippet from token screener data."""
    for entry in data:
        if entry.get("token_address", "").lower() == token.lower():
            sym = entry.get("token_symbol", "?")
            mcap = format_usd_short(entry.get("market_cap_usd", 0))
            pc = entry.get("price_change", 0)
            pc_str = f"{pc*100:+.1f}%" if pc else ""
            return f"{sym} · {mcap} market cap {pc_str}"
    if data:
        return f"{len(data)} tokens scanned"
    return "No data"


def snippet_sm_netflow(data: list, token: str) -> str:
    """Extract snippet from smart money netflow."""
    for entry in data:
        if entry.get("token_address", "").lower() == token.lower():
            net_7d = entry.get("net_flow_7d_usd", 0)
            traders = entry.get("trader_count", 0)
            direction = "inflow" if net_7d >= 0 else "outflow"
            return f"{format_usd_short(abs(net_7d))} net {direction} (7d) · {traders} traders"
    return f"{len(data)} tokens tracked, target not in top"


def snippet_sm_holdings(data: list) -> str:
    """Extract snippet from SM holdings."""
    if not data:
        return "No data"
    total = sum(h.get("total_value_usd", h.get("value_usd", 0)) for h in data)
    return f"{format_usd_short(total)} across {len(data)} tokens"


def snippet_sm_dex(data: list) -> str:
    """Extract snippet from SM DEX trades."""
    if not data:
        return "No data"
    total_vol = sum(t.get("volume_usd", 0) for t in data)
    return f"{len(data)} recent trades · {format_usd_short(total_vol)} volume"


def snippet_token_info(data) -> str:
    """Extract snippet from token info."""
    if not data:
        return "No data"
    if isinstance(data, dict):
        info = data.get("data", data)
        if isinstance(info, list) and info:
            info = info[0]
        if isinstance(info, dict):
            sym = info.get("token_symbol", "?")
            return f"{sym} token metadata loaded"
    return "Token info loaded"


def snippet_flow_intel(data: list) -> str:
    """Extract snippet from flow intelligence."""
    if not data:
        return "No data"
    fi = data[0] if isinstance(data, list) else data
    if not isinstance(fi, dict):
        return "No data"
    whale = fi.get("whale_net_flow_usd", 0)
    exchange = fi.get("exchange_net_flow_usd", 0)
    whale_str = f"+{format_usd_short(whale)}" if whale >= 0 else f"-{format_usd_short(abs(whale))}"
    exch_str = f"+{format_usd_short(exchange)}" if exchange >= 0 else f"-{format_usd_short(abs(exchange))}"
    return f"Whales {whale_str}, Exchanges {exch_str}"


def snippet_who_bought_sold(data: list) -> str:
    """Extract snippet from who bought/sold."""
    if not data:
        return "No data"
    total_buy = sum(e.get("bought_volume_usd", 0) for e in data)
    total_sell = sum(e.get("sold_volume_usd", 0) for e in data)
    return f"{format_usd_short(total_buy)} bought vs {format_usd_short(total_sell)} sold"


def snippet_indicators(data) -> str:
    """Extract snippet from Nansen Score indicators."""
    if not data:
        return "No data"
    ind_data = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(ind_data, dict):
        return "No data"
    risks = ind_data.get("risk_indicators", [])
    high_risks = [r for r in risks if r.get("score", "").lower() == "high"]
    if high_risks:
        names = ", ".join(r.get("indicator_type", "").replace("-", " ").title() for r in high_risks)
        return f"⚠ HIGH risk: {names}"
    rewards = ind_data.get("reward_indicators", [])
    bullish = [r for r in rewards if r.get("score", "").lower() == "bullish"]
    if bullish:
        names = ", ".join(r.get("indicator_type", "").replace("-", " ").title() for r in bullish)
        return f"Bullish: {names}"
    return f"{len(risks)} risk + {len(rewards)} reward signals"


def snippet_holders(data: list) -> str:
    """Extract snippet from holders."""
    if not data:
        return "No data"
    top = data[0]
    total = sum(h.get("token_amount", 0) for h in data)
    top_amt = top.get("token_amount", 0)
    top_pct = (top_amt / total * 100) if total > 0 else 0
    label = top.get("label", top.get("address_label", ""))
    label_str = f" ({label})" if label else ""
    return f"Top holder: {top_pct:.0f}%{label_str}"


def snippet_pnl(data: list) -> str:
    """Extract snippet from PnL leaderboard."""
    if not data:
        return "No data"
    top = data[0]
    pnl = top.get("realized_pnl_usd", top.get("pnl_usd", 0))
    return f"Top trader: {format_usd_short(pnl)} realized PnL"


def snippet_dex_trades(data: list) -> str:
    """Extract snippet from DEX trades."""
    if not data:
        return "No data"
    total = sum(t.get("volume_usd", t.get("trade_volume_usd", 0)) for t in data)
    return f"{len(data)} trades · {format_usd_short(total)} volume"


def snippet_flows(data) -> str:
    """Extract snippet from token flows."""
    if not data:
        return "No data"
    if isinstance(data, dict):
        inflow = data.get("inflow_usd", 0)
        outflow = data.get("outflow_usd", 0)
        if inflow or outflow:
            return f"In: {format_usd_short(inflow)} · Out: {format_usd_short(outflow)}"
    return "Flow data loaded"


def snippet_ohlcv(data: list) -> str:
    """Extract snippet from OHLCV."""
    if not data:
        return "No data"
    valid = [c for c in data if c.get("close") is not None]
    if not valid:
        return f"{len(data)} candles (no valid prices)"
    prices = [c["close"] for c in valid]
    return f"{len(valid)} candles · ${min(prices):.6f} – ${max(prices):.6f}"


def snippet_balance(data: list) -> str:
    """Extract snippet from profiler balance."""
    if not data:
        return "No data"
    total = sum(h.get("value_usd", 0) for h in data)
    return f"{len(data)} tokens · {format_usd_short(total)} total"


def snippet_counterparties(data: list) -> str:
    """Extract snippet from profiler counterparties."""
    if not data:
        return "No data"
    return f"{len(data)} counterparties identified"


# ─── Pipeline Steps ──────────────────────────────────────────────────
def build_steps(token: str, chain: str):
    """Define pipeline steps with their collect functions and snippet extractors."""
    return [
        ("Token Overview", lambda: dd.collect_token_screener(chain, limit=20), lambda d: snippet_screener(d, token)),
        ("Smart Money Net Flows", lambda: dd.collect_smart_money_netflow(chain, limit=20), lambda d: snippet_sm_netflow(d, token)),
        ("Smart Money Holdings", lambda: dd.collect_smart_money_holdings(chain, limit=10), snippet_sm_holdings),
        ("Smart Money DEX Trades", lambda: dd.collect_smart_money_dex_trades(chain, limit=5), snippet_sm_dex),
        ("Token Info", lambda: dd.collect_token_info(chain, token), snippet_token_info),
        ("Flow Intelligence", lambda: dd.collect_flow_intelligence(chain, token, days=7), snippet_flow_intel),
        ("Who Bought / Sold", lambda: dd.collect_who_bought_sold(chain, token, days=7, limit=10), snippet_who_bought_sold),
        ("Nansen Score", lambda: dd.collect_token_indicators(chain, token), snippet_indicators),
        ("Holder Distribution", lambda: dd.collect_token_holders(chain, token, limit=10), snippet_holders),
        ("PnL Leaderboard", lambda: dd.collect_token_pnl(chain, token, days=30, limit=10), snippet_pnl),
        ("DEX Trades", lambda: dd.collect_token_dex_trades(chain, token, days=7, limit=10), snippet_dex_trades),
        ("Token Flows", lambda: dd.collect_token_flows(chain, token, days=7), snippet_flows),
        ("Price History (OHLCV)", lambda: dd.collect_token_ohlcv(chain, token), snippet_ohlcv),
    ]


# ─── Main ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Protocol Due Diligence Engine CLI")
    parser.add_argument("--from-cache", action="store_true", help="Use cached data (zero API calls)")
    parser.add_argument("--token", type=str, help="Token address (skip prompt)")
    parser.add_argument("--chain", type=str, help="Chain name (skip prompt)")
    args = parser.parse_args()

    console.print(BANNER)
    console.print()

    # Get token address
    if args.token:
        token = args.token
        console.print(f"  Token: [bold cyan]{token}[/]")
    else:
        token = Prompt.ask("  [bold]Enter token address[/]")
        if not token or len(token) < 10:
            console.print("  [red]Invalid token address.[/]")
            sys.exit(1)

    # Get chain
    chains = list(dd.SUPPORTED_CHAINS)
    if args.chain and args.chain in chains:
        chain = args.chain
        console.print(f"  Chain: [bold cyan]{chain}[/]")
    else:
        console.print()
        for i, c in enumerate(chains, 1):
            console.print(f"    [cyan]{i}[/]. {c.capitalize()}")
        console.print()
        choice = IntPrompt.ask("  [bold]Select chain[/]", default=1)
        if choice < 1 or choice > len(chains):
            console.print("  [red]Invalid choice.[/]")
            sys.exit(1)
        chain = chains[choice - 1]

    console.print()

    # Set up due_diligence globals
    dd.USE_CACHE = args.from_cache
    dd.API_CALL_COUNT = 0
    dd.API_CALL_LOG = []
    token_short = token[:8] if len(token) > 8 else token
    dd.CACHE_DIR = dd.REPORTS_DIR / f"{token_short}_{chain}_raw"

    mode_text = "[yellow]CACHE MODE[/] — zero API calls" if args.from_cache else "[green]LIVE MODE[/] — x402 micropayments"
    console.print(Panel(
        f"  Running Due Diligence Pipeline\n  {mode_text}\n  Token: [cyan]{token[:12]}...{token[-6:]}[/]\n  Chain: [cyan]{chain.capitalize()}[/]",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()

    # Run pipeline with progress
    results = {}
    steps = build_steps(token, chain)

    table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    table.add_column("status", width=3)
    table.add_column("step", width=25)
    table.add_column("detail", ratio=1)

    step_rows = []
    for name, _, _ in steps:
        step_rows.append(["⠋", f"[dim]{name}[/]", "[dim]waiting...[/]"])
        table.add_row(*step_rows[-1])

    with Live(table, console=console, refresh_per_second=10) as live:
        for i, (name, collect_fn, snippet_fn) in enumerate(steps):
            # Show spinner
            step_rows[i] = ["⠋", f"[bold]{name}[/]", "[dim]fetching...[/]"]
            table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
            table.add_column("status", width=3)
            table.add_column("step", width=25)
            table.add_column("detail", ratio=1)
            for row in step_rows:
                table.add_row(*row)
            live.update(table)

            # Execute
            try:
                data = collect_fn()
                snippet = snippet_fn(data)
                step_rows[i] = ["[green]✓[/]", f"[green]{name}[/]", f"[white]{snippet}[/]"]
            except Exception as e:
                data = None
                step_rows[i] = ["[red]✗[/]", f"[red]{name}[/]", f"[dim]{str(e)[:50]}[/]"]

            results[name] = data

            # Rebuild table
            table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
            table.add_column("status", width=3)
            table.add_column("step", width=25)
            table.add_column("detail", ratio=1)
            for row in step_rows:
                table.add_row(*row)
            live.update(table)

            time.sleep(0.3)

    # Top buyer deep dive
    console.print()
    who_bs = results.get("Who Bought / Sold", [])
    top_buyer_addr = ""
    top_buyer_balance = []

    if who_bs and isinstance(who_bs, list) and who_bs:
        top_buyer_addr = who_bs[0].get("address", "")
        if top_buyer_addr:
            console.print("  [dim]⠋ Profiling top buyer...[/]")
            top_buyer_balance = dd.collect_profiler_balance(top_buyer_addr, chain)
            dd.collect_profiler_counterparties(top_buyer_addr, chain)
            bal_snippet = snippet_balance(top_buyer_balance)
            console.print(f"  [green]✓[/] [green]Top Buyer Profile[/]  {bal_snippet}")
            time.sleep(0.3)

    # Resolve symbol
    screener = results.get("Token Overview", [])
    sm_netflow = results.get("Smart Money Net Flows", [])

    symbol = "UNKNOWN"
    screener_entry = None
    for entry in (screener or []):
        if entry.get("token_address", "").lower() == token.lower():
            symbol = entry.get("token_symbol", symbol)
            screener_entry = entry
            break

    sm_entry = None
    for entry in (sm_netflow or []):
        if entry.get("token_address", "").lower() == token.lower():
            symbol = entry.get("token_symbol", symbol)
            sm_entry = entry
            break

    if symbol == "UNKNOWN":
        token_info = results.get("Token Info")
        if token_info and isinstance(token_info, dict):
            info = token_info.get("data", token_info)
            if isinstance(info, list) and info:
                symbol = info[0].get("token_symbol", symbol)
            elif isinstance(info, dict):
                symbol = info.get("token_symbol", symbol)

    # Reconstruct API call log for cached mode
    if args.from_cache and not dd.API_CALL_LOG:
        token_short_log = token[:8] + "..." if len(token) > 8 else token
        top_addr_short = top_buyer_addr[:8] + "..." if top_buyer_addr and len(top_buyer_addr) > 8 else "unknown"
        cached_commands = [
            (f"nansen research token screener --chain {chain} --timeframe 24h --limit 20", "token_screener"),
            (f"nansen research smart-money netflow --chain {chain} --limit 20", "sm_netflow"),
            (f"nansen research smart-money holdings --chain {chain} --limit 10", "sm_holdings"),
            (f"nansen research smart-money dex-trades --chain {chain} --limit 5", "sm_dex_trades"),
            (f"nansen research token info --chain {chain} --token {token_short_log}", "token_info"),
            (f"nansen research token flow-intelligence --chain {chain} --token {token_short_log} --days 7", "flow_intelligence"),
            (f"nansen research token who-bought-sold --chain {chain} --token {token_short_log} --days 7 --limit 10", "who_bought_sold"),
            (f"nansen research token indicators --chain {chain} --token {token_short_log}", "token_indicators"),
            (f"nansen research token holders --chain {chain} --token {token_short_log} --limit 10", "token_holders"),
            (f"nansen research token pnl --chain {chain} --token {token_short_log} --days 30 --limit 10", "token_pnl"),
            (f"nansen research token dex-trades --chain {chain} --token {token_short_log} --days 7 --limit 10", "token_dex_trades"),
            (f"nansen research token flows --chain {chain} --token {token_short_log} --days 7", "token_flows"),
            (f"nansen research token ohlcv --chain {chain} --token {token_short_log} --timeframe 1h", "token_ohlcv"),
            (f"nansen research profiler balance --address {top_addr_short} --chain {chain} --limit 10", "profiler_balance"),
            (f"nansen research profiler counterparties --address {top_addr_short} --chain {chain} --days 30 --limit 5", "profiler_counterparties"),
        ]
        for cmd, cache_name in cached_commands:
            cache_file = dd.CACHE_DIR / f"{cache_name}.json"
            status = "OK" if cache_file.exists() else "No Data"
            dd.API_CALL_LOG.append({"command": cmd, "status": status})
        dd.API_CALL_COUNT = sum(1 for e in dd.API_CALL_LOG if e["status"] == "OK")

    # Generate HTML report
    console.print()
    console.print("  [dim]Generating report...[/]")

    html_report = generate_html_report(
        symbol=symbol,
        token=token,
        chain=chain,
        api_calls=dd.API_CALL_COUNT,
        api_log=dd.API_CALL_LOG,
        screener_entry=screener_entry,
        sm_entry=sm_entry,
        flow_intel=results.get("Flow Intelligence"),
        who_bought_sold=who_bs,
        indicators=results.get("Nansen Score"),
        holders=results.get("Holder Distribution", []),
        ohlcv=results.get("Price History (OHLCV)", []),
        sm_holdings=results.get("Smart Money Holdings", []),
        top_buyer_addr=top_buyer_addr,
        top_buyer_balance=top_buyer_balance,
    )

    # Save
    dd.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_filename = f"{symbol}_{chain}_{timestamp}.html"
    html_filepath = dd.REPORTS_DIR / html_filename
    html_filepath.write_text(html_report)

    # Compute verdict for display
    conviction = 0
    if sm_entry:
        if sm_entry.get("net_flow_1h_usd", 0) > 0: conviction += 15
        if sm_entry.get("net_flow_24h_usd", 0) > 0: conviction += 25
        if sm_entry.get("net_flow_7d_usd", 0) > 0: conviction += 35
        if sm_entry.get("net_flow_30d_usd", 0) > 0: conviction += 25
    else:
        fi = results.get("Flow Intelligence")
        if fi:
            fi_data = fi[0] if isinstance(fi, list) and fi else fi
            if isinstance(fi_data, dict):
                if fi_data.get("whale_net_flow_usd", 0) > 0: conviction += 20
                if fi_data.get("smart_trader_net_flow_usd", 0) > 0: conviction += 25
                if fi_data.get("exchange_net_flow_usd", 0) < 0: conviction += 15
                conviction = min(conviction, 70)

    if conviction >= 75:
        verdict_text = "[bold green]BULLISH[/]"
    elif conviction >= 50:
        verdict_text = "[bold green]CAUTIOUSLY BULLISH[/]"
    elif conviction >= 25:
        verdict_text = "[bold yellow]NEUTRAL[/]"
    else:
        verdict_text = "[bold red]BEARISH[/]"

    conv_color = "green" if conviction >= 50 else "yellow" if conviction >= 25 else "red"

    # Summary panel
    console.print()
    summary = (
        f"  [bold green]✅ Report Ready![/]\n"
        f"\n"
        f"  Token:                [bold white]{symbol}[/]\n"
        f"  Verdict:              {verdict_text}\n"
        f"  Smart Money Conviction: [{conv_color}]{conviction}/100[/]\n"
        f"  API Calls:            {dd.API_CALL_COUNT} | Cost: ~${dd.API_CALL_COUNT * 0.03:.2f}\n"
    )

    console.print(Panel(
        summary,
        border_style="green",
        padding=(1, 2),
        title="[bold] Results [/]",
        title_align="left",
    ))

    console.print(f"\n  [dim]Report saved to:[/] [bold cyan]{html_filepath}[/]")

    # Try to open in browser
    try:
        webbrowser.open(f"file://{html_filepath.resolve()}")
        console.print("  [dim]Opening in browser...[/]")
    except Exception:
        console.print("  [dim]Could not open browser automatically.[/]")

    console.print()


if __name__ == "__main__":
    main()
