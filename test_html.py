"""
Test HTML report generation using cached/mock JUP data.
NO API CALLS — uses hardcoded data from the v1 run.
Uses FULL-LENGTH addresses (44 chars for Solana) so Solscan links work.
"""
from html_report import generate_html_report
from pathlib import Path

# Mock data from the actual JUP v1 run
SYMBOL = "JUP"
TOKEN = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
CHAIN = "solana"

screener_entry = {
    "token_address": TOKEN,
    "token_symbol": "JUP",
    "market_cap_usd": 1_200_000_000,
    "price_usd": 0.442,
    "price_change": -0.032,
    "volume": 45_600_000,
    "liquidity": 12_400_000,
    "token_age_days": 420,
}

# SM entry — was empty/zero in v1 (JUP wasn't in top 20 SM netflow)
sm_entry = None  # Accurately represents that JUP wasn't in the SM netflow list

flow_intel = [{
    "token_symbol": "JUP",
    "whale_net_flow_usd": -76400,
    "smart_trader_net_flow_usd": 0,
    "exchange_net_flow_usd": 60900,
    "fresh_wallets_net_flow_usd": 417500,
    "top_pnl_net_flow_usd": 468.96,
    "public_figure_net_flow_usd": 0,
    "whale_wallet_count": 3,
    "smart_trader_wallet_count": 0,
    "exchange_wallet_count": 2,
    "fresh_wallets_wallet_count": 15,
}]

# Full-length Solana addresses (44 chars) — Fix 1
who_bought_sold = [
    {"address": "E2itUS7P9bX5KkRqAm3CwJFn8v4pQx2LmYTzdqsvR1AB", "address_label": "High Balance", "bought_volume_usd": 170200, "sold_volume_usd": 0, "trade_volume_usd": 170200},
    {"address": "9EEjTLk8xQz4vF7nMpRWs3KhYcDuBjN6Xt9fGw1z2GAB", "address_label": "vfxpro88.sol", "bought_volume_usd": 114300, "sold_volume_usd": 0, "trade_volume_usd": 114300},
    {"address": "EeT7ogR5pQ1nH4Km8Ys2vWxBfDc6Lr3JtZq9AukxJfAB", "address_label": "goldzebra.sol", "bought_volume_usd": 45500, "sold_volume_usd": 0, "trade_volume_usd": 45500},
    {"address": "GJvewfT9mQr2Xn5Kp8Lc3YdBhVs6Wt1Jz4FoRaN4T4YA", "address_label": "Trading Bot", "bought_volume_usd": 226800, "sold_volume_usd": 184100, "trade_volume_usd": 42700},
    {"address": "FwcSBpL8qN3Rv6Km2Yt7Xd5Hj9Wg1Zs4Bn8FoTc6gSPAB", "address_label": "JTO Airdrop Recipient", "bought_volume_usd": 29500, "sold_volume_usd": 0, "trade_volume_usd": 29500},
]

indicators = {
    "data": {
        "token_info": {
            "token_symbol": "JUP",
            "market_cap_group": "large_cap",
            "is_stablecoin": False,
        },
        "risk_indicators": [
            {"indicator_type": "btc-reflexivity", "score": "medium", "signal": 0.45, "signal_percentile": 62.3, "last_trigger_on": "2026-03-18"},
            {"indicator_type": "cex-flows", "score": "high", "signal": 0.78, "signal_percentile": 85.1, "last_trigger_on": "2026-03-20"},
            {"indicator_type": "liquidity-risk", "score": "low", "signal": 0.12, "signal_percentile": 15.4, "last_trigger_on": "2026-02-28"},
            {"indicator_type": "token-supply-inflation", "score": "low", "signal": 0.08, "signal_percentile": 10.2, "last_trigger_on": "2026-01-15"},
        ],
        "reward_indicators": [
            {"indicator_type": "concentration-risk", "score": "medium", "signal": 0.52, "signal_percentile": 55.0, "last_trigger_on": "2026-03-19"},
            {"indicator_type": "funding-rate", "score": "bullish", "signal": 0.65, "signal_percentile": 72.1, "last_trigger_on": "2026-03-20"},
            {"indicator_type": "price-momentum", "score": "bearish", "signal": -0.38, "signal_percentile": 28.5, "last_trigger_on": "2026-03-20"},
            {"indicator_type": "trading-range", "score": "neutral", "signal": 0.01, "signal_percentile": 50.0, "last_trigger_on": "2026-03-19"},
        ],
    }
}

# Full-length addresses for holders — Fix 1
holders = [
    {"address": "EXJHiMGFnp4K8qZ2Rv7Xd5Hj9Wg1Bs3Lm6Yt8NcHm6TAB", "token_amount": 1_700_000_000, "label": "Team Treasury"},
    {"address": "61aq58Rn7pVx3Km9Ys2Wt5Bd8Hj1Fv4Lz6Xc0GqxHXVAB", "token_amount": 1_682_700_001, "label": "Staking Contract"},
    {"address": "Any5gLp9qRv2Xn7Km3Ys8Bd1Wt4Hj6Fz0LcVsNaT7izAB", "token_amount": 349_350_312, "label": ""},
    {"address": "FVhQ3QmLk4p8Rv2Xn5Km7Ys9Bd1Wt3Hj6Fz0LcNafekfAB", "token_amount": 321_492_923, "label": "Fund"},
    {"address": "9WzDXwR4n3Km7Ys2Xd5Bd8Hj1Wt9Fv4Lz6Qc0GpAWWMAB", "token_amount": 164_970_200, "label": ""},
]

# Mock OHLCV data (24 hourly candles)
ohlcv = [
    {"timestamp": "2026-03-20T00:00:00Z", "open": 0.458, "high": 0.462, "low": 0.455, "close": 0.460, "volume": 1_800_000},
    {"timestamp": "2026-03-20T01:00:00Z", "open": 0.460, "high": 0.463, "low": 0.457, "close": 0.458, "volume": 1_500_000},
    {"timestamp": "2026-03-20T02:00:00Z", "open": 0.458, "high": 0.461, "low": 0.454, "close": 0.455, "volume": 1_200_000},
    {"timestamp": "2026-03-20T03:00:00Z", "open": 0.455, "high": 0.458, "low": 0.450, "close": 0.451, "volume": 2_100_000},
    {"timestamp": "2026-03-20T04:00:00Z", "open": 0.451, "high": 0.456, "low": 0.449, "close": 0.453, "volume": 1_900_000},
    {"timestamp": "2026-03-20T05:00:00Z", "open": 0.453, "high": 0.455, "low": 0.448, "close": 0.449, "volume": 1_600_000},
    {"timestamp": "2026-03-20T06:00:00Z", "open": 0.449, "high": 0.452, "low": 0.445, "close": 0.446, "volume": 2_300_000},
    {"timestamp": "2026-03-20T07:00:00Z", "open": 0.446, "high": 0.450, "low": 0.443, "close": 0.448, "volume": 2_000_000},
    {"timestamp": "2026-03-20T08:00:00Z", "open": 0.448, "high": 0.453, "low": 0.447, "close": 0.452, "volume": 2_500_000},
    {"timestamp": "2026-03-20T09:00:00Z", "open": 0.452, "high": 0.458, "low": 0.451, "close": 0.457, "volume": 3_100_000},
    {"timestamp": "2026-03-20T10:00:00Z", "open": 0.457, "high": 0.460, "low": 0.454, "close": 0.455, "volume": 2_200_000},
    {"timestamp": "2026-03-20T11:00:00Z", "open": 0.455, "high": 0.458, "low": 0.452, "close": 0.453, "volume": 1_800_000},
    {"timestamp": "2026-03-20T12:00:00Z", "open": 0.453, "high": 0.456, "low": 0.449, "close": 0.450, "volume": 2_000_000},
    {"timestamp": "2026-03-20T13:00:00Z", "open": 0.450, "high": 0.454, "low": 0.447, "close": 0.448, "volume": 1_700_000},
    {"timestamp": "2026-03-20T14:00:00Z", "open": 0.448, "high": 0.452, "low": 0.445, "close": 0.446, "volume": 1_500_000},
    {"timestamp": "2026-03-20T15:00:00Z", "open": 0.446, "high": 0.449, "low": 0.442, "close": 0.443, "volume": 2_400_000},
    {"timestamp": "2026-03-20T16:00:00Z", "open": 0.443, "high": 0.448, "low": 0.441, "close": 0.447, "volume": 2_800_000},
    {"timestamp": "2026-03-20T17:00:00Z", "open": 0.447, "high": 0.451, "low": 0.445, "close": 0.449, "volume": 2_100_000},
    {"timestamp": "2026-03-20T18:00:00Z", "open": 0.449, "high": 0.453, "low": 0.446, "close": 0.448, "volume": 1_900_000},
    {"timestamp": "2026-03-20T19:00:00Z", "open": 0.448, "high": 0.450, "low": 0.443, "close": 0.444, "volume": 1_600_000},
    {"timestamp": "2026-03-20T20:00:00Z", "open": 0.444, "high": 0.447, "low": 0.440, "close": 0.441, "volume": 2_200_000},
    {"timestamp": "2026-03-20T21:00:00Z", "open": 0.441, "high": 0.445, "low": 0.439, "close": 0.443, "volume": 1_800_000},
    {"timestamp": "2026-03-20T22:00:00Z", "open": 0.443, "high": 0.446, "low": 0.440, "close": 0.441, "volume": 1_500_000},
    {"timestamp": "2026-03-20T23:00:00Z", "open": 0.441, "high": 0.444, "low": 0.438, "close": 0.442, "volume": 1_400_000},
]

sm_holdings = [
    {"token_symbol": "RENDER", "total_value_usd": 4_330_000},
    {"token_symbol": "META", "total_value_usd": 3_480_000},
    {"token_symbol": "JUP", "total_value_usd": 2_890_000},
    {"token_symbol": "PUMP", "total_value_usd": 1_820_000},
    {"token_symbol": "PENGU", "total_value_usd": 869_800},
    {"token_symbol": "PUNCH", "total_value_usd": 315_900},
    {"token_symbol": "WOJAK", "total_value_usd": 185_700},
]

top_buyer_addr = "E2itUS7P9bX5KkRqAm3CwJFn8v4pQx2LmYTzdqsvR1AB"
top_buyer_balance = [
    {"token_symbol": "SOL", "token_amount": 2052.93, "value_usd": 181_700},
    {"token_symbol": "PENGU", "token_amount": 735223.5, "value_usd": 5_200},
    {"token_symbol": "$WIF", "token_amount": 3871.59, "value_usd": 682.54},
    {"token_symbol": "FARTCOIN", "token_amount": 472.69, "value_usd": 90.21},
    {"token_symbol": "HOUSE", "token_amount": 28189.44, "value_usd": 40.06},
]

# Mock API call log
api_log = [
    {"command": "nansen research token screener --chain solana --timeframe 24h", "status": "OK"},
    {"command": "nansen research smart-money netflow --chain solana", "status": "OK"},
    {"command": "nansen research smart-money holdings --chain solana", "status": "OK"},
    {"command": "nansen research smart-money dex-trades --chain solana", "status": "OK"},
    {"command": "nansen research token info --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token flow-intelligence --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token who-bought-sold --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token indicators --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token holders --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token pnl --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token dex-trades --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token flows --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research token ohlcv --chain solana --token JUPy...DvCN", "status": "OK"},
    {"command": "nansen research profiler balance --address E2itUS... --chain solana", "status": "OK"},
]

# Generate
html = generate_html_report(
    symbol=SYMBOL,
    token=TOKEN,
    chain=CHAIN,
    api_calls=14,
    api_log=api_log,
    screener_entry=screener_entry,
    sm_entry=sm_entry,
    flow_intel=flow_intel,
    who_bought_sold=who_bought_sold,
    indicators=indicators,
    holders=holders,
    ohlcv=ohlcv,
    sm_holdings=sm_holdings,
    top_buyer_addr=top_buyer_addr,
    top_buyer_balance=top_buyer_balance,
)

outpath = Path(__file__).parent / "reports" / "JUP_solana_v2_test.html"
outpath.parent.mkdir(parents=True, exist_ok=True)
outpath.write_text(html)
print(f"✅ Report generated: {outpath}")
print(f"   Size: {len(html):,} bytes")

# Verify Fix 1: check all solscan links have full addresses
import re
links = re.findall(r'href="(https://solscan\.io/[^"]+)"', html)
print(f"\n🔗 Solscan links found: {len(links)}")
for link in links:
    addr_part = link.split("/")[-1]
    status = "✅" if len(addr_part) >= 32 else "❌ SHORT"
    print(f"   {status} {link}")

# Verify Fix 2: price display
price_match = re.search(r'<div class="value">\$([^<]+)</div>', html)
if price_match:
    print(f"\n💰 Price display: ${price_match.group(1)}")

# Verify Fix 3: conviction score
conv_match = re.search(r'<div class="value [^"]*">(\d+)/100</div>', html)
if conv_match:
    print(f"\n📊 Conviction score: {conv_match.group(1)}/100")

# Verify Fix 4: check for empty label cells
empty_labels = html.count('<td></td>')
print(f"\n🏷️ Empty <td></td> cells: {empty_labels}")

# Verify Fix 5: SM holdings % column
has_pct = "% of Portfolio" in html or "sm-pct" in html
print(f"\n📈 SM Holdings has % column: {has_pct}")

# Verify Fix 6: Holdings USD value
has_usd_col = "Value (USD)" in html and "holders" in html.lower()
print(f"\n💵 Holdings has USD value: {has_usd_col}")
