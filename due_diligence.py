#!/usr/bin/env python3
"""
Protocol Due Diligence Engine
Built with Nansen CLI for the #NansenCLI Challenge

One command. 15+ API calls. A full protocol due diligence report
that would take an analyst 4 hours.

Usage:
    python due_diligence.py <token_address> --chain <chain>
    python due_diligence.py <token_symbol> --chain solana
    python due_diligence.py --scan --chain solana   # discover + analyze top movers

Example:
    python due_diligence.py So11111111111111111111111111111111111111112 --chain solana
    python due_diligence.py 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 --chain ethereum
    python due_diligence.py --scan --chain solana --top 5

Author: Vincent Charles (@0x_vcharles) / Unchain Data
Built by Lens (AI agent) on OpenClaw
"""

import json
import subprocess
import sys
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Config ──────────────────────────────────────────────────────────
SUPPORTED_CHAINS = [
    "ethereum", "solana", "base", "bnb", "arbitrum", "polygon",
    "optimism", "avalanche", "linea", "scroll", "mantle", "ronin",
    "sei", "plasma", "sonic", "monad", "hyperevm", "iotaevm"
]

REPORTS_DIR = Path(__file__).parent / "reports"
API_CALL_COUNT = 0
API_CALL_LOG = []
CACHE_DIR = None  # Set per-run in run_due_diligence


# ─── Cache helpers ───────────────────────────────────────────────────
def cache_save(name: str, data) -> None:
    """Save raw API response to cache directory."""
    if CACHE_DIR is None:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    filepath = CACHE_DIR / f"{name}.json"
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  [cache] Saved {name}.json")


def cache_load(name: str):
    """Load cached API response. Returns _CACHE_MISS sentinel if not found."""
    if CACHE_DIR is None:
        return _CACHE_MISS
    filepath = CACHE_DIR / f"{name}.json"
    if not filepath.exists():
        return _CACHE_MISS
    with open(filepath) as f:
        data = json.load(f)
    print(f"  [cache] Loaded {name}.json")
    return data  # Can be None/null — that's a valid cached "no data" response


_CACHE_MISS = object()  # Sentinel to distinguish "not cached" from "cached as None"


# ─── Nansen CLI Wrapper ─────────────────────────────────────────────
def nansen_call(command: list[str], description: str = "") -> dict | None:
    """Execute a Nansen CLI command and return parsed JSON."""
    global API_CALL_COUNT, API_CALL_LOG
    
    full_cmd = ["nansen"] + command
    desc = description or " ".join(command[:3])
    cmd_str = " ".join(full_cmd)
    
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout or result.stderr or ""
        
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            if result.returncode != 0:
                print(f"  [{desc}] Error: {output[:100]}")
            API_CALL_LOG.append({"command": cmd_str, "status": "Parse Error"})
            return None
        
        if not data.get("success", False):
            code = data.get("code", "")
            status = data.get("status", result.returncode)
            err_msg = data.get("error", "Unknown")
            if code == "CREDITS_EXHAUSTED":
                print(f"  [{desc}] Skipped (needs credits/x402)")
                API_CALL_LOG.append({"command": cmd_str, "status": "x402 Payment"})
            elif status == 429 or code == "RATE_LIMITED":
                print(f"  [{desc}] Rate limited, skipping")
                API_CALL_LOG.append({"command": cmd_str, "status": "Rate Limited"})
            elif "No API key" in str(err_msg) or "UNAUTHORIZED" in str(code):
                print(f"  [{desc}] Skipped (auth issue, x402 may not support this endpoint)")
                API_CALL_LOG.append({"command": cmd_str, "status": "Auth Error"})
            else:
                print(f"  [{desc}] Error: {err_msg}")
                API_CALL_LOG.append({"command": cmd_str, "status": f"Error: {err_msg}"})
            return None
        
        API_CALL_COUNT += 1
        print(f"  [{desc}] OK (call #{API_CALL_COUNT})")
        API_CALL_LOG.append({"command": cmd_str, "status": "OK"})
        return data.get("data", {})
            
    except subprocess.TimeoutExpired:
        print(f"  [{desc}] Timeout")
        API_CALL_LOG.append({"command": cmd_str, "status": "Timeout"})
        return None
    except Exception as e:
        print(f"  [{desc}] Exception: {e}")
        API_CALL_LOG.append({"command": cmd_str, "status": f"Exception: {e}"})
        return None


# ─── Data Collection (with cache support) ────────────────────────────
USE_CACHE = False  # Set to True via --from-cache flag


def _collect(cache_name: str, command: list[str], desc: str, extract_key: str | None = "data"):
    """Generic collect: check cache first, else call API and cache result."""
    if USE_CACHE:
        cached = cache_load(cache_name)
        if cached is not _CACHE_MISS:
            return cached  # Could be None, [], etc. — all valid cached results
        print(f"  [cache] MISS: {cache_name} — no cached data")
        return [] if extract_key == "data" else None

    data = nansen_call(command, desc)
    if data is not None:
        result = data.get(extract_key, []) if extract_key and isinstance(data, dict) else data
        cache_save(cache_name, result)
        return result
    return [] if extract_key == "data" else None


def collect_token_screener(chain: str, limit: int = 20) -> list:
    """Get top tokens by smart money activity."""
    return _collect(
        "token_screener",
        ["research", "token", "screener", "--chain", chain,
         "--timeframe", "24h", "--limit", str(limit)],
        "Token Screener"
    )


def collect_smart_money_netflow(chain: str, limit: int = 20) -> list:
    """Get smart money net flows."""
    return _collect(
        "sm_netflow",
        ["research", "smart-money", "netflow", "--chain", chain,
         "--limit", str(limit)],
        "SM Netflow"
    )


def collect_flow_intelligence(chain: str, token: str, days: int = 7) -> list:
    """Get flow intelligence broken down by label type."""
    return _collect(
        "flow_intelligence",
        ["research", "token", "flow-intelligence", "--chain", chain,
         "--token", token, "--days", str(days)],
        "Flow Intelligence"
    )


def collect_who_bought_sold(chain: str, token: str, days: int = 7, limit: int = 10) -> list:
    """Get top buyers and sellers."""
    return _collect(
        "who_bought_sold",
        ["research", "token", "who-bought-sold", "--chain", chain,
         "--token", token, "--days", str(days), "--limit", str(limit)],
        "Who Bought/Sold"
    )


def collect_token_info(chain: str, token: str) -> dict | None:
    """Get token info."""
    return _collect(
        "token_info",
        ["research", "token", "info", "--chain", chain, "--token", token],
        "Token Info",
        extract_key=None
    )


def collect_token_indicators(chain: str, token: str) -> dict | None:
    """Get Nansen Score / risk indicators."""
    return _collect(
        "token_indicators",
        ["research", "token", "indicators", "--chain", chain, "--token", token],
        "Nansen Score",
        extract_key=None
    )


def collect_token_holders(chain: str, token: str, limit: int = 10) -> list:
    """Get holder analysis."""
    return _collect(
        "token_holders",
        ["research", "token", "holders", "--chain", chain,
         "--token", token, "--limit", str(limit)],
        "Holders"
    )


def collect_token_pnl(chain: str, token: str, days: int = 30, limit: int = 10) -> list:
    """Get PnL leaderboard."""
    return _collect(
        "token_pnl",
        ["research", "token", "pnl", "--chain", chain,
         "--token", token, "--days", str(days), "--limit", str(limit)],
        "PnL Leaderboard"
    )


def collect_token_dex_trades(chain: str, token: str, days: int = 7, limit: int = 10) -> list:
    """Get DEX trades."""
    return _collect(
        "token_dex_trades",
        ["research", "token", "dex-trades", "--chain", chain,
         "--token", token, "--days", str(days), "--limit", str(limit)],
        "DEX Trades"
    )


def collect_token_flows(chain: str, token: str, days: int = 7) -> dict | None:
    """Get token flow metrics."""
    return _collect(
        "token_flows",
        ["research", "token", "flows", "--chain", chain,
         "--token", token, "--days", str(days)],
        "Token Flows",
        extract_key=None
    )


def collect_token_ohlcv(chain: str, token: str, timeframe: str = "4h") -> list:
    """Get OHLCV candle data. 4h timeframe × 42 candles = ~7 days."""
    return _collect(
        "token_ohlcv",
        ["research", "token", "ohlcv", "--chain", chain,
         "--token", token, "--timeframe", timeframe, "--limit", "42"],
        "OHLCV"
    )


def collect_profiler_balance(address: str, chain: str) -> list:
    """Get wallet balance."""
    return _collect(
        "profiler_balance",
        ["research", "profiler", "balance", "--address", address,
         "--chain", chain, "--limit", "10"],
        f"Balance {address[:8]}..."
    )


def collect_profiler_labels(address: str, chain: str) -> dict | None:
    """Get wallet labels."""
    return _collect(
        "profiler_labels",
        ["research", "profiler", "labels", "--address", address,
         "--chain", chain],
        f"Labels {address[:8]}...",
        extract_key=None
    )


def collect_smart_money_holdings(chain: str, limit: int = 20) -> list:
    """Get aggregated SM holdings."""
    return _collect(
        "sm_holdings",
        ["research", "smart-money", "holdings", "--chain", chain,
         "--limit", str(limit)],
        "SM Holdings"
    )


def collect_smart_money_dex_trades(chain: str, limit: int = 10) -> list:
    """Get SM DEX trades."""
    return _collect(
        "sm_dex_trades",
        ["research", "smart-money", "dex-trades", "--chain", chain,
         "--limit", str(limit)],
        "SM DEX Trades"
    )


def collect_profiler_counterparties(address: str, chain: str, days: int = 30) -> list:
    """Get top counterparties."""
    return _collect(
        "profiler_counterparties",
        ["research", "profiler", "counterparties", "--address", address,
         "--chain", chain, "--days", str(days), "--limit", "5"],
        f"Counterparties {address[:8]}..."
    )


# ─── Cross-Chain Smart Money Scanner ─────────────────────────────────
def scan_cross_chain_sm(chains: list[str] = None) -> dict:
    """Scan multiple chains for smart money flows and identify convergence."""
    if chains is None:
        chains = ["ethereum", "solana", "base", "arbitrum", "bnb"]
    
    print("\n" + "="*60)
    print("CROSS-CHAIN SMART MONEY SCANNER")
    print("="*60)
    
    all_flows = {}
    for chain in chains:
        print(f"\nScanning {chain.upper()}...")
        flows = collect_smart_money_netflow(chain, limit=10)
        if flows:
            all_flows[chain] = flows
    
    return all_flows


# ─── Report Generator ────────────────────────────────────────────────
def format_usd(value: float | None) -> str:
    """Format USD values."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:,.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"${value/1_000:,.1f}K"
    return f"${value:,.2f}"


def format_pct(value: float | None) -> str:
    """Format percentage values."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value*100:.2f}%"


def generate_report(
    token: str,
    chain: str,
    screener_data: list,
    sm_netflow: list,
    flow_intel: list,
    who_bought_sold: list,
    token_info: dict | None,
    indicators: dict | None,
    holders: list,
    pnl_leaders: list,
    dex_trades: list,
    token_flows: dict | None,
    ohlcv: list,
    sm_holdings: list,
    sm_dex_trades: list,
    top_buyer_balance: list,
    top_buyer_counterparties: list,
) -> str:
    """Generate the full due diligence report in markdown."""
    
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Find our token in screener data
    token_screener_entry = None
    for entry in screener_data:
        if entry.get("token_address", "").lower() == token.lower():
            token_screener_entry = entry
            break
    
    # Find in SM netflow
    token_sm_entry = None
    for entry in sm_netflow:
        if entry.get("token_address", "").lower() == token.lower():
            token_sm_entry = entry
            break
    
    # Build report
    report = []
    
    # ─── Header ──────────────────────────────────
    symbol = "UNKNOWN"
    if token_screener_entry:
        symbol = token_screener_entry.get("token_symbol", "UNKNOWN")
    elif token_sm_entry:
        symbol = token_sm_entry.get("token_symbol", "UNKNOWN")
    
    # Try token_info for symbol if still unknown
    if symbol == "UNKNOWN" and token_info and isinstance(token_info, dict):
        info_data = token_info.get("data", token_info)
        if isinstance(info_data, list) and len(info_data) > 0:
            symbol = info_data[0].get("token_symbol", symbol)
        elif isinstance(info_data, dict):
            symbol = info_data.get("token_symbol", symbol)
    
    # Try who_bought_sold data for symbol  
    if symbol == "UNKNOWN" and who_bought_sold:
        for entry in who_bought_sold:
            if entry.get("token_symbol"):
                symbol = entry["token_symbol"]
                break
    
    # Try flow intelligence
    if symbol == "UNKNOWN" and flow_intel:
        fi = flow_intel[0] if isinstance(flow_intel, list) and flow_intel else flow_intel
        if isinstance(fi, dict) and fi.get("token_symbol"):
            symbol = fi["token_symbol"]
    
    # Try indicators
    if symbol == "UNKNOWN" and indicators:
        ind_data = indicators.get("data", indicators)
        if isinstance(ind_data, dict):
            ti = ind_data.get("token_info", {})
            if ti.get("token_symbol"):
                symbol = ti["token_symbol"]
    
    report.append(f"# Due Diligence Report: {symbol}")
    report.append(f"**Chain:** {chain.capitalize()} | **Token:** `{token[:16]}...{token[-6:]}`")
    report.append(f"**Generated:** {now} | **API Calls:** {API_CALL_COUNT}")
    report.append(f"**Powered by:** Nansen CLI + x402 | **Built by:** Unchain Data")
    report.append("")
    report.append("---")
    report.append("")
    
    # ─── Executive Summary ───────────────────────
    report.append("## 1. Executive Summary")
    report.append("")
    
    if token_screener_entry:
        mcap = token_screener_entry.get("market_cap_usd")
        price = token_screener_entry.get("price_usd")
        price_chg = token_screener_entry.get("price_change")
        volume = token_screener_entry.get("volume")
        netflow = token_screener_entry.get("netflow")
        liq = token_screener_entry.get("liquidity")
        age = token_screener_entry.get("token_age_days")
        
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| Market Cap | {format_usd(mcap)} |")
        report.append(f"| Price | ${price:,.6f} |" if price else "| Price | N/A |")
        report.append(f"| 24h Change | {format_pct(price_chg)} |")
        report.append(f"| 24h Volume | {format_usd(volume)} |")
        report.append(f"| 24h Net Flow | {format_usd(netflow)} |")
        report.append(f"| Liquidity | {format_usd(liq)} |")
        report.append(f"| Token Age | {age} days |" if age else "| Token Age | N/A |")
    else:
        report.append("*Token not found in 24h screener. May have low activity.*")
    report.append("")
    
    # ─── Smart Money Conviction ──────────────────
    report.append("## 2. Smart Money Conviction")
    report.append("")
    
    if token_sm_entry:
        net_1h = token_sm_entry.get("net_flow_1h_usd", 0)
        net_24h = token_sm_entry.get("net_flow_24h_usd", 0)
        net_7d = token_sm_entry.get("net_flow_7d_usd", 0)
        net_30d = token_sm_entry.get("net_flow_30d_usd", 0)
        traders = token_sm_entry.get("trader_count", 0)
        sectors = token_sm_entry.get("token_sectors", [])
        
        report.append(f"| Timeframe | SM Net Flow | Signal |")
        report.append(f"|-----------|-------------|--------|")
        report.append(f"| 1 Hour | {format_usd(net_1h)} | {'🟢 Accumulating' if net_1h > 0 else '🔴 Distributing'} |")
        report.append(f"| 24 Hours | {format_usd(net_24h)} | {'🟢 Accumulating' if net_24h > 0 else '🔴 Distributing'} |")
        report.append(f"| 7 Days | {format_usd(net_7d)} | {'🟢 Accumulating' if net_7d > 0 else '🔴 Distributing'} |")
        report.append(f"| 30 Days | {format_usd(net_30d)} | {'🟢 Accumulating' if net_30d > 0 else '🔴 Distributing'} |")
        report.append(f"")
        report.append(f"**SM Trader Count:** {traders}")
        if sectors:
            report.append(f"**Sectors:** {', '.join(sectors)}")
        
        # Conviction score
        score = 0
        if net_1h > 0: score += 15
        if net_24h > 0: score += 25
        if net_7d > 0: score += 35
        if net_30d > 0: score += 25
        
        if score >= 75:
            conviction = "HIGH - Smart money is strongly accumulating across all timeframes"
        elif score >= 50:
            conviction = "MODERATE - Mixed signals, SM accumulating on some timeframes"
        elif score >= 25:
            conviction = "LOW - SM mostly distributing, some short-term buying"
        else:
            conviction = "BEARISH - SM distributing across all timeframes"
        
        report.append(f"")
        report.append(f"**Conviction Score: {score}/100 - {conviction}**")
    else:
        report.append("*No smart money flow data found for this token.*")
    report.append("")
    
    # ─── Flow Intelligence by Label ──────────────
    report.append("## 3. Flow Intelligence (by Wallet Label)")
    report.append("")
    
    if flow_intel:
        fi = flow_intel[0] if isinstance(flow_intel, list) and flow_intel else flow_intel
        if isinstance(fi, dict):
            report.append(f"| Label | Net Flow (7d) | Avg Flow | Wallet Count |")
            report.append(f"|-------|--------------|----------|--------------|")
            
            labels = [
                ("Whales", "whale"),
                ("Smart Traders", "smart_trader"),
                ("Public Figures", "public_figure"),
                ("Top PnL", "top_pnl"),
                ("Exchanges", "exchange"),
                ("Fresh Wallets", "fresh_wallets"),
            ]
            
            for label_name, prefix in labels:
                net = fi.get(f"{prefix}_net_flow_usd")
                avg = fi.get(f"{prefix}_avg_flow_usd")
                count = fi.get(f"{prefix}_wallet_count")
                if net is not None:
                    signal = "🟢" if net > 0 else "🔴"
                    report.append(
                        f"| {signal} {label_name} | {format_usd(net)} | "
                        f"{format_usd(avg)} | {count or 'N/A'} |"
                    )
            
            # Key insight
            whale_flow = fi.get("whale_net_flow_usd", 0)
            smart_flow = fi.get("smart_trader_net_flow_usd", 0)
            exchange_flow = fi.get("exchange_net_flow_usd", 0)
            
            report.append("")
            insights = []
            if whale_flow > 0 and smart_flow > 0:
                insights.append("Both whales AND smart traders are accumulating. Strong signal.")
            elif whale_flow > 0 and smart_flow < 0:
                insights.append("Whales accumulating while smart traders sell. Possible insider buying.")
            elif whale_flow < 0 and smart_flow > 0:
                insights.append("Smart traders buying the whale dump. Potential rotation play.")
            
            if exchange_flow > 0:
                insights.append("Positive exchange inflow suggests potential sell pressure ahead.")
            elif exchange_flow < 0:
                insights.append("Negative exchange flow: tokens moving OFF exchanges. Bullish storage signal.")
            
            for insight in insights:
                report.append(f"> {insight}")
    else:
        report.append("*Flow intelligence data not available.*")
    report.append("")
    
    # ─── Top Buyers & Sellers ────────────────────
    report.append("## 4. Top Buyers & Sellers (7d)")
    report.append("")
    
    if who_bought_sold:
        report.append(f"| Address | Label | Bought | Sold | Net (USD) |")
        report.append(f"|---------|-------|--------|------|-----------|")
        
        for entry in who_bought_sold[:10]:
            addr = entry.get("address", "Unknown")
            label = entry.get("address_label", "Unlabeled")
            bought = entry.get("bought_volume_usd", 0)
            sold = entry.get("sold_volume_usd", 0)
            net = entry.get("trade_volume_usd", bought - sold)
            
            addr_short = f"`{addr[:6]}...{addr[-4:]}`"
            report.append(
                f"| {addr_short} | {label} | {format_usd(bought)} | "
                f"{format_usd(sold)} | {format_usd(net)} |"
            )
    else:
        report.append("*Buyer/seller data not available.*")
    report.append("")
    
    # ─── Nansen Score / Risk Assessment ──────────
    report.append("## 5. Risk Assessment")
    report.append("")
    
    if indicators:
        ind_data = indicators.get("data", indicators)
        if isinstance(ind_data, dict):
            # Parse token info
            token_meta = ind_data.get("token_info", {})
            if token_meta:
                mcap_group = token_meta.get("market_cap_group") or "unknown"
                is_stable = token_meta.get("is_stablecoin", False)
                report.append(f"**Category:** {mcap_group.upper()} | **Stablecoin:** {'Yes' if is_stable else 'No'}")
                report.append("")
            
            # Parse risk indicators
            risk_inds = ind_data.get("risk_indicators", [])
            if risk_inds:
                report.append("### Risk Indicators")
                report.append("| Indicator | Score | Signal | Percentile | Last Triggered |")
                report.append("|-----------|-------|--------|------------|----------------|")
                for ri in risk_inds:
                    itype = ri.get("indicator_type", "").replace("-", " ").title()
                    score = ri.get("score", "N/A").upper()
                    sig = ri.get("signal", 0)
                    pct = ri.get("signal_percentile", 0)
                    trigger = ri.get("last_trigger_on", "N/A")
                    emoji = "🔴" if score == "HIGH" else ("🟡" if score == "MEDIUM" else "🟢")
                    report.append(f"| {emoji} {itype} | {score} | {sig:.3f} | {pct:.1f}% | {trigger} |")
                report.append("")
            
            # Parse reward indicators
            reward_inds = ind_data.get("reward_indicators", [])
            if reward_inds:
                report.append("### Reward Indicators")
                report.append("| Indicator | Score | Signal | Percentile | Last Triggered |")
                report.append("|-----------|-------|--------|------------|----------------|")
                for ri in reward_inds:
                    itype = ri.get("indicator_type", "").replace("-", " ").title()
                    score = ri.get("score", "N/A").capitalize()
                    sig = ri.get("signal", 0)
                    pct = ri.get("signal_percentile", 0)
                    trigger = ri.get("last_trigger_on", "N/A")
                    emoji = "🟢" if score == "Bullish" else ("🔴" if score == "Bearish" else "🟡")
                    report.append(f"| {emoji} {itype} | {score} | {sig:.3f} | {pct:.1f}% | {trigger} |")
                report.append("")
    else:
        # Generate our own risk flags
        report.append("### Risk Flags (Automated)")
        report.append("")
        
        risks = []
        if token_screener_entry:
            age = token_screener_entry.get("token_age_days", 999)
            liq = token_screener_entry.get("liquidity", 0)
            mcap = token_screener_entry.get("market_cap_usd", 0)
            fdv_mc = token_screener_entry.get("fdv_mc_ratio", 1)
            
            if age < 30:
                risks.append("⚠️ Token is less than 30 days old. High risk.")
            if liq and mcap and liq < mcap * 0.05:
                risks.append("⚠️ Low liquidity relative to market cap. Exit risk.")
            if fdv_mc > 5:
                risks.append("⚠️ High FDV/MC ratio. Significant future dilution expected.")
            if liq and liq < 100_000:
                risks.append("⚠️ Very low liquidity (<$100K). Slippage risk.")
        
        if token_sm_entry:
            traders = token_sm_entry.get("trader_count", 0)
            if traders < 3:
                risks.append("⚠️ Very few SM traders (<3). Could be noise.")
        
        if not risks:
            risks.append("✅ No major automated risk flags detected.")
        
        for risk in risks:
            report.append(f"- {risk}")
    report.append("")
    
    # ─── Holder Analysis ─────────────────────────
    if holders:
        report.append("## 6. Holder Analysis")
        report.append("")
        report.append(f"| Rank | Address | Label | Holdings |")
        report.append(f"|------|---------|-------|----------|")
        for i, h in enumerate(holders[:10], 1):
            addr = h.get("address", "")
            label = h.get("label", "Unlabeled")
            amount = h.get("token_amount", 0)
            report.append(f"| {i} | `{addr[:6]}...{addr[-4:]}` | {label} | {amount:,.2f} |")
        report.append("")
    
    # ─── PnL Leaderboard ─────────────────────────
    if pnl_leaders:
        report.append("## 7. PnL Leaderboard (30d)")
        report.append("")
        report.append(f"| Address | Label | Realized PnL | ROI |")
        report.append(f"|---------|-------|-------------|-----|")
        for entry in pnl_leaders[:10]:
            addr = entry.get("address", "Unknown")
            if not addr or len(addr) < 10:
                addr = "Unknown"
            label = entry.get("address_label", entry.get("label", "Unlabeled"))
            pnl = entry.get("realized_pnl_usd", entry.get("pnl_usd", entry.get("total_pnl_usd", 0)))
            roi = entry.get("roi", entry.get("total_roi", None))
            roi_str = f"{roi*100:.1f}%" if roi else "N/A"
            addr_display = f"`{addr[:6]}...{addr[-4:]}`" if len(addr) > 10 else addr
            if pnl == 0 and roi_str == "N/A":
                continue  # Skip empty entries
            report.append(
                f"| {addr_display} | {label} | "
                f"{format_usd(pnl)} | {roi_str} |"
            )
        report.append("")
    
    # ─── Top Buyer Deep Dive ─────────────────────
    if top_buyer_balance:
        report.append("## 8. Top Buyer Wallet Deep Dive")
        report.append("")
        top_addr = who_bought_sold[0].get("address", "") if who_bought_sold else "Unknown"
        report.append(f"**Profiling top buyer:** `{top_addr[:10]}...`")
        report.append("")
        report.append("### Current Holdings")
        report.append(f"| Token | Amount | Value (USD) |")
        report.append(f"|-------|--------|-------------|")
        for h in top_buyer_balance[:10]:
            sym = h.get("token_symbol", "?")
            amt = h.get("token_amount", 0)
            val = h.get("value_usd", 0)
            report.append(f"| {sym} | {amt:,.4f} | {format_usd(val)} |")
        report.append("")
    
    # ─── Cross-Chain Context ─────────────────────
    if sm_holdings:
        report.append("## 9. Cross-Chain SM Context")
        report.append("")
        report.append("Top Smart Money holdings on this chain:")
        report.append(f"| Token | SM Holdings | Traders |")
        report.append(f"|-------|-------------|---------|")
        for h in sm_holdings[:10]:
            sym = h.get("token_symbol", "?")
            val = h.get("total_value_usd", h.get("value_usd", 0))
            traders = h.get("trader_count", "N/A")
            report.append(f"| {sym} | {format_usd(val)} | {traders} |")
        report.append("")
    
    # ─── Conclusion ──────────────────────────────
    report.append("## Conclusion")
    report.append("")
    
    # Auto-generate conclusion based on signals
    signals = {
        "sm_conviction": 0,
        "whale_signal": 0,
        "risk_level": "UNKNOWN"
    }
    
    if token_sm_entry:
        net_24h = token_sm_entry.get("net_flow_24h_usd", 0)
        net_7d = token_sm_entry.get("net_flow_7d_usd", 0)
        if net_24h > 0 and net_7d > 0:
            signals["sm_conviction"] = 2
        elif net_24h > 0 or net_7d > 0:
            signals["sm_conviction"] = 1
    
    if flow_intel:
        fi = flow_intel[0] if isinstance(flow_intel, list) else flow_intel
        if isinstance(fi, dict):
            if fi.get("whale_net_flow_usd", 0) > 0:
                signals["whale_signal"] = 1
    
    total_signal = signals["sm_conviction"] + signals["whale_signal"]
    
    if total_signal >= 3:
        report.append("**VERDICT: BULLISH** - Strong smart money accumulation with whale backing.")
    elif total_signal >= 2:
        report.append("**VERDICT: CAUTIOUSLY BULLISH** - Positive SM signals but mixed whale activity.")
    elif total_signal >= 1:
        report.append("**VERDICT: NEUTRAL** - Some SM interest but insufficient conviction.")
    else:
        report.append("**VERDICT: BEARISH/INSUFFICIENT DATA** - No clear SM accumulation signal.")
    
    report.append("")
    report.append("---")
    report.append(f"*Report generated with {API_CALL_COUNT} Nansen API calls via CLI.*")
    report.append(f"*Powered by x402 micropayments. Total cost: ~${API_CALL_COUNT * 0.03:.2f}*")
    report.append(f"*Built by Unchain Data (@0x_vcharles) for #NansenCLI challenge*")
    report.append(f"*This is NOT financial advice. Always DYOR.*")
    
    return "\n".join(report)


# ─── Main Pipeline ───────────────────────────────────────────────────
def run_due_diligence(token: str, chain: str):
    """Run the full due diligence pipeline for a token."""
    global API_CALL_COUNT, API_CALL_LOG, CACHE_DIR
    API_CALL_COUNT = 0
    API_CALL_LOG = []
    
    # Set cache directory for this token
    token_short = token[:8] if len(token) > 8 else token
    CACHE_DIR = REPORTS_DIR / f"{token_short}_{chain}_raw"
    
    mode = "CACHE" if USE_CACHE else "LIVE"
    print(f"\n{'='*60}")
    print(f"PROTOCOL DUE DILIGENCE ENGINE v2 [{mode}]")
    print(f"Token: {token}")
    print(f"Chain: {chain}")
    print(f"Cache: {CACHE_DIR}")
    print(f"{'='*60}")
    print(f"\nCollecting data from Nansen CLI...\n")
    
    # 1. Token Screener (context)
    print("Phase 1: Market Overview")
    screener = collect_token_screener(chain, limit=20)
    
    # 2. Smart Money Netflow
    print("\nPhase 2: Smart Money Analysis")
    sm_netflow = collect_smart_money_netflow(chain, limit=20)
    sm_holdings = collect_smart_money_holdings(chain, limit=10)
    sm_dex = collect_smart_money_dex_trades(chain, limit=5)
    
    # 3. Token-specific deep dive
    print("\nPhase 3: Token Deep Dive")
    token_info = collect_token_info(chain, token)
    flow_intel = collect_flow_intelligence(chain, token, days=7)
    who_bs = collect_who_bought_sold(chain, token, days=7, limit=10)
    indicators = collect_token_indicators(chain, token)
    holders = collect_token_holders(chain, token, limit=10)
    pnl = collect_token_pnl(chain, token, days=30, limit=10)
    dex_trades = collect_token_dex_trades(chain, token, days=7, limit=10)
    flows = collect_token_flows(chain, token, days=7)
    ohlcv = collect_token_ohlcv(chain, token)
    
    # 4. Top buyer deep dive
    print("\nPhase 4: Wallet Forensics")
    top_buyer_addr = ""
    top_buyer_balance = []
    top_buyer_cp = []
    if who_bs:
        top_buyer_addr = who_bs[0].get("address", "")
        if top_buyer_addr:
            top_buyer_balance = collect_profiler_balance(top_buyer_addr, chain)
            top_buyer_cp = collect_profiler_counterparties(top_buyer_addr, chain)
    
    # Resolve symbol
    symbol = "UNKNOWN"
    for entry in screener:
        if entry.get("token_address", "").lower() == token.lower():
            symbol = entry.get("token_symbol", "UNKNOWN")
            break
    for entry in sm_netflow:
        if entry.get("token_address", "").lower() == token.lower():
            symbol = entry.get("token_symbol", symbol)
            break
    if symbol == "UNKNOWN" and token_info:
        info_data = token_info.get("data", token_info)
        if isinstance(info_data, list) and info_data:
            symbol = info_data[0].get("token_symbol", symbol)
        elif isinstance(info_data, dict):
            symbol = info_data.get("token_symbol", symbol)
    if symbol == "UNKNOWN" and who_bs:
        for entry in who_bs:
            if entry.get("token_symbol"):
                symbol = entry["token_symbol"]
                break
    if symbol == "UNKNOWN" and indicators:
        ind_data = indicators.get("data", indicators)
        if isinstance(ind_data, dict):
            ti = ind_data.get("token_info", {})
            if ti.get("token_symbol"):
                symbol = ti["token_symbol"]

    # Find token in screener/SM data
    screener_entry = None
    for entry in screener:
        if entry.get("token_address", "").lower() == token.lower():
            screener_entry = entry
            break

    sm_entry = None
    for entry in sm_netflow:
        if entry.get("token_address", "").lower() == token.lower():
            sm_entry = entry
            break

    # Generate reports
    print(f"\n{'='*60}")
    print(f"Generating reports... ({API_CALL_COUNT} API calls made)")
    print(f"{'='*60}\n")
    
    # Markdown report (keep for compatibility)
    report = generate_report(
        token=token,
        chain=chain,
        screener_data=screener,
        sm_netflow=sm_netflow,
        flow_intel=flow_intel,
        who_bought_sold=who_bs,
        token_info=token_info,
        indicators=indicators,
        holders=holders,
        pnl_leaders=pnl,
        dex_trades=dex_trades,
        token_flows=flows,
        ohlcv=ohlcv,
        sm_holdings=sm_holdings,
        sm_dex_trades=sm_dex,
        top_buyer_balance=top_buyer_balance,
        top_buyer_counterparties=top_buyer_cp,
    )
    
    # Reconstruct API call log from cached files when running from cache
    if USE_CACHE and not API_CALL_LOG:
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
            cache_file = CACHE_DIR / f"{cache_name}.json"
            status = "OK" if cache_file.exists() else "No Data"
            API_CALL_LOG.append({"command": cmd, "status": status})
        API_CALL_COUNT = sum(1 for e in API_CALL_LOG if e["status"] == "OK")

    # HTML report (v2 — the good one)
    from html_report import generate_html_report
    html_report = generate_html_report(
        symbol=symbol,
        token=token,
        chain=chain,
        api_calls=API_CALL_COUNT,
        api_log=API_CALL_LOG,
        screener_entry=screener_entry,
        sm_entry=sm_entry,
        flow_intel=flow_intel,
        who_bought_sold=who_bs,
        indicators=indicators,
        holders=holders,
        ohlcv=ohlcv,
        sm_holdings=sm_holdings,
        top_buyer_addr=top_buyer_addr,
        top_buyer_balance=top_buyer_balance,
    )
    
    # Save reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    md_filename = f"{symbol}_{chain}_{timestamp}.md"
    md_filepath = REPORTS_DIR / md_filename
    md_filepath.write_text(report)
    
    html_filename = f"{symbol}_{chain}_{timestamp}.html"
    html_filepath = REPORTS_DIR / html_filename
    html_filepath.write_text(html_report)
    
    print(report)
    print(f"\n{'='*60}")
    print(f"Markdown: {md_filepath}")
    print(f"HTML:     {html_filepath}")
    print(f"Total API calls: {API_CALL_COUNT}")
    print(f"Estimated cost (x402): ~${API_CALL_COUNT * 0.03:.2f}")
    print(f"{'='*60}")
    
    return report, html_filepath


def run_scan_mode(chain: str, top_n: int = 5, chains: list[str] = None):
    """Scan mode: discover top movers and run DD on the most interesting ones."""
    global API_CALL_COUNT
    API_CALL_COUNT = 0
    
    print(f"\n{'='*60}")
    print(f"SCAN MODE: Cross-Chain Smart Money Discovery")
    print(f"{'='*60}\n")
    
    # Scan multiple chains for SM activity
    scan_chains = chains or ["ethereum", "solana", "base", "arbitrum", "bnb"]
    
    all_signals = []
    
    for c in scan_chains:
        print(f"\nScanning {c.upper()}...")
        screener = collect_token_screener(c, limit=10)
        sm_flows = collect_smart_money_netflow(c, limit=10)
        
        # Find tokens with strong SM accumulation
        for flow in sm_flows:
            net_24h = flow.get("net_flow_24h_usd", 0)
            net_7d = flow.get("net_flow_7d_usd", 0)
            traders = flow.get("trader_count", 0)
            
            if net_24h > 0 and net_7d > 0 and traders >= 2:
                # Match with screener for more context
                token_addr = flow.get("token_address", "")
                screener_match = next(
                    (s for s in screener if s.get("token_address", "").lower() == token_addr.lower()),
                    None
                )
                
                signal = {
                    "chain": c,
                    "token_address": token_addr,
                    "token_symbol": flow.get("token_symbol", "?"),
                    "net_flow_24h": net_24h,
                    "net_flow_7d": net_7d,
                    "trader_count": traders,
                    "market_cap": screener_match.get("market_cap_usd") if screener_match else None,
                    "price_change": screener_match.get("price_change") if screener_match else None,
                    "convergence_score": 0,
                }
                
                # Score: higher = more interesting
                score = 0
                score += min(net_24h / 10000, 30)  # Flow magnitude
                score += min(traders * 5, 30)  # More traders = more conviction
                if screener_match:
                    pc = screener_match.get("price_change", 0)
                    if pc and pc < 0:  # SM buying while price drops = divergence
                        score += 20
                    liq = screener_match.get("liquidity", 0)
                    if liq and liq > 100000:
                        score += 10
                
                signal["convergence_score"] = round(score, 1)
                all_signals.append(signal)
    
    # Sort by convergence score
    all_signals.sort(key=lambda x: x["convergence_score"], reverse=True)
    
    # Print discovery results
    print(f"\n{'='*60}")
    print(f"DISCOVERY RESULTS ({len(all_signals)} signals found)")
    print(f"{'='*60}\n")
    
    report_lines = ["# Cross-Chain Smart Money Discovery Report", ""]
    report_lines.append(f"**Chains scanned:** {', '.join(scan_chains)}")
    report_lines.append(f"**Signals found:** {len(all_signals)}")
    report_lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    report_lines.append("")
    report_lines.append("| Rank | Token | Chain | SM Flow 24h | SM Flow 7d | Traders | Score |")
    report_lines.append("|------|-------|-------|-------------|------------|---------|-------|")
    
    for i, sig in enumerate(all_signals[:20], 1):
        report_lines.append(
            f"| {i} | {sig['token_symbol']} | {sig['chain']} | "
            f"{format_usd(sig['net_flow_24h'])} | {format_usd(sig['net_flow_7d'])} | "
            f"{sig['trader_count']} | {sig['convergence_score']} |"
        )
    
    report_text = "\n".join(report_lines)
    print(report_text)
    
    # Save scan report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = REPORTS_DIR / f"scan_{timestamp}.md"
    filepath.write_text(report_text)
    
    print(f"\nScan saved to: {filepath}")
    print(f"Total API calls: {API_CALL_COUNT}")
    
    # Run DD on top signals
    if all_signals and top_n > 0:
        print(f"\nRunning Due Diligence on top {min(top_n, len(all_signals))} signals...\n")
        for sig in all_signals[:top_n]:
            print(f"\n{'='*60}")
            print(f"DD: {sig['token_symbol']} on {sig['chain']}")
            print(f"{'='*60}")
            run_due_diligence(sig["token_address"], sig["chain"])
    
    return all_signals


# ─── CLI Entry Point ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Protocol Due Diligence Engine - Powered by Nansen CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python due_diligence.py So111...111112 --chain solana
  python due_diligence.py 0xC02...756Cc2 --chain ethereum
  python due_diligence.py --scan --chain solana --top 3
  python due_diligence.py --scan --chains ethereum,solana,base
        """
    )
    
    parser.add_argument("token", nargs="?", help="Token address to analyze")
    parser.add_argument("--chain", default="solana", choices=SUPPORTED_CHAINS,
                       help="Blockchain (default: solana)")
    parser.add_argument("--from-cache", action="store_true",
                       help="Use cached API responses instead of live calls (zero cost)")
    parser.add_argument("--scan", action="store_true",
                       help="Scan mode: discover top movers across chains")
    parser.add_argument("--chains", type=str, default=None,
                       help="Comma-separated chains for scan mode")
    parser.add_argument("--top", type=int, default=3,
                       help="Number of top signals to run DD on in scan mode")
    
    args = parser.parse_args()
    
    global USE_CACHE
    USE_CACHE = args.from_cache
    
    if args.scan:
        chains = args.chains.split(",") if args.chains else None
        run_scan_mode(args.chain, top_n=args.top, chains=chains)
    elif args.token:
        run_due_diligence(args.token, args.chain)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
