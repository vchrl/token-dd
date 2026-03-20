"""
HTML Report Generator for Due Diligence Engine v2.
Generates actionable, explained reports — not data dumps.
"""
import json
from pathlib import Path
from datetime import datetime, timezone


def format_usd(value):
    if value is None: return "N/A"
    if abs(value) >= 1e9: return f"${value/1e9:,.2f}B"
    if abs(value) >= 1e6: return f"${value/1e6:,.2f}M"
    if abs(value) >= 1e3: return f"${value/1e3:,.1f}K"
    return f"${value:,.2f}"


def explorer_url(chain: str, address: str, addr_type: str = "account") -> str:
    """Generate block explorer URL for an address."""
    if chain == "solana":
        return f"https://solscan.io/{addr_type}/{address}"
    elif chain == "ethereum":
        return f"https://etherscan.io/{'token' if addr_type == 'token' else 'address'}/{address}"
    elif chain == "base":
        return f"https://basescan.org/{'token' if addr_type == 'token' else 'address'}/{address}"
    elif chain == "arbitrum":
        return f"https://arbiscan.io/{'token' if addr_type == 'token' else 'address'}/{address}"
    elif chain == "bnb":
        return f"https://bscscan.com/{'token' if addr_type == 'token' else 'address'}/{address}"
    elif chain == "polygon":
        return f"https://polygonscan.com/{'token' if addr_type == 'token' else 'address'}/{address}"
    elif chain == "optimism":
        return f"https://optimistic.etherscan.io/{'token' if addr_type == 'token' else 'address'}/{address}"
    elif chain == "avalanche":
        return f"https://snowtrace.io/{'token' if addr_type == 'token' else 'address'}/{address}"
    else:
        return f"https://etherscan.io/address/{address}"


def addr_link(chain: str, address: str) -> str:
    """Generate a clickable address link."""
    if not address or len(address) < 10:
        return '<span class="addr">Unknown</span>'
    url = explorer_url(chain, address)
    short = f"{address[:6]}...{address[-4:]}"
    return f'<a href="{url}" target="_blank" class="addr-link" title="{address}">{short}</a>'


# ─── Risk indicator explanations ─────────────────────────────────────
RISK_EXPLANATIONS = {
    "btc-reflexivity": "Measures how much this token's price mirrors Bitcoin's movements. HIGH means the token lacks independent price action and will dump harder when BTC drops.",
    "cex-flows": "Tracks tokens moving to/from centralized exchanges. HIGH means large amounts are flowing to exchanges, often a precursor to sell pressure.",
    "liquidity-risk": "Evaluates how easily you can exit a position without major slippage. HIGH means thin order books — large sells will crash the price.",
    "token-supply-inflation": "Measures how fast new tokens enter circulation (vesting, emissions). HIGH means your share gets diluted over time even if price stays flat.",
    "smart-money-outflow": "Tracks whether sophisticated traders are reducing exposure. HIGH means the people who usually know first are getting out.",
}

REWARD_EXPLANATIONS = {
    "concentration-risk": "Measures how concentrated holdings are among top wallets. Medium means moderate concentration — not ideal but not a red flag.",
    "funding-rate": "Perpetual futures funding rate. Bullish means shorts are paying longs, indicating the market expects upward movement.",
    "price-momentum": "Technical momentum indicators. Bearish means the trend is currently down across key timeframes.",
    "trading-range": "Where the price sits relative to its recent range. Neutral means it's mid-range with no clear breakout direction.",
    "smart-money-accumulation": "Whether smart money wallets are increasing positions. Bullish means sophisticated traders are buying.",
}


def generate_risk_html(indicators: dict | None) -> tuple[str, str, str, str]:
    """Generate risk and reward indicator HTML with explanations."""
    risk_html = ""
    reward_html = ""
    risk_explainer = "No Nansen Score data available for this token. Consider this a data gap — the token may be too new or too small for Nansen's scoring model."
    reward_explainer = risk_explainer

    if not indicators:
        risk_html = '<div class="risk-item"><div class="risk-item-header"><span class="ri-label">No data available</span></div></div>'
        reward_html = risk_html
        return risk_html, reward_html, risk_explainer, reward_explainer

    ind_data = indicators.get("data", indicators)
    if not isinstance(ind_data, dict):
        risk_html = '<div class="risk-item"><div class="risk-item-header"><span class="ri-label">No data available</span></div></div>'
        reward_html = risk_html
        return risk_html, reward_html, risk_explainer, reward_explainer

    # Risk indicators
    risk_inds = ind_data.get("risk_indicators", [])
    risk_alerts = []
    if risk_inds:
        for ri in risk_inds:
            itype = ri.get("indicator_type", "")
            name = itype.replace("-", " ").title()
            score = ri.get("score", "low")
            badge_class = score.lower() if score.lower() in ("high", "medium", "low") else "low"
            reason = RISK_EXPLANATIONS.get(itype, f"Nansen's proprietary {name} signal based on onchain data patterns.")

            risk_html += f'''<div class="risk-item">
                <div class="risk-item-header">
                    <span class="ri-label">{name}</span>
                    <span class="risk-badge {badge_class}">{score.upper()}</span>
                </div>
                <div class="ri-reason">{reason}</div>
            </div>'''

            if score.lower() == "high":
                risk_alerts.append(f"{name} is HIGH")
            elif score.lower() == "medium":
                risk_alerts.append(f"{name} is MEDIUM")

        if risk_alerts:
            risk_explainer = f"Watch these risk signals closely: {'; '.join(risk_alerts)}. Multiple HIGH risk indicators together suggest elevated caution. Consider reducing position size or setting tighter stops."
        else:
            risk_explainer = "All risk indicators are LOW. This is a positive sign, but don't mistake low risk scores for guaranteed safety. These indicators track known risk patterns — novel risks won't show up here."

    # Reward indicators
    reward_inds = ind_data.get("reward_indicators", [])
    reward_signals = []
    if reward_inds:
        for ri in reward_inds:
            itype = ri.get("indicator_type", "")
            name = itype.replace("-", " ").title()
            score = ri.get("score", "neutral")
            badge_class = score.lower() if score.lower() in ("bullish", "bearish") else "neutral2"
            reason = REWARD_EXPLANATIONS.get(itype, f"Nansen's proprietary {name} signal based on onchain activity patterns.")

            reward_html += f'''<div class="risk-item">
                <div class="risk-item-header">
                    <span class="ri-label">{name}</span>
                    <span class="risk-badge {badge_class}">{score.capitalize()}</span>
                </div>
                <div class="ri-reason">{reason}</div>
            </div>'''

            if score.lower() == "bullish":
                reward_signals.append(f"{name} is Bullish")
            elif score.lower() == "bearish":
                reward_signals.append(f"{name} is Bearish")

        bullish_count = sum(1 for s in reward_signals if "Bullish" in s)
        bearish_count = sum(1 for s in reward_signals if "Bearish" in s)
        if bullish_count > bearish_count:
            reward_explainer = f"Reward signals lean bullish ({bullish_count} bullish vs {bearish_count} bearish). This suggests the risk/reward may favor entry, but always cross-reference with smart money flows and your own thesis."
        elif bearish_count > bullish_count:
            reward_explainer = f"Reward signals lean bearish ({bearish_count} bearish vs {bullish_count} bullish). The data suggests headwinds ahead. Wait for momentum to shift before entering or adding."
        else:
            reward_explainer = "Reward signals are mixed. No clear directional edge from Nansen's model. This is a 'wait and see' zone — look for a catalyst before committing capital."

    if not risk_html:
        risk_html = '<div class="risk-item"><div class="risk-item-header"><span class="ri-label">No data available</span></div></div>'
    if not reward_html:
        reward_html = '<div class="risk-item"><div class="risk-item-header"><span class="ri-label">No data available</span></div></div>'

    return risk_html, reward_html, risk_explainer, reward_explainer


def generate_bull_bear_case(
    screener_entry: dict | None,
    sm_entry: dict | None,
    flow_intel_data: dict,
    indicators: dict | None,
    who_bought_sold: list,
    holders: list,
) -> tuple[str, str, str]:
    """Generate bull case, bear case, and key questions HTML."""
    bull_points = []
    bear_points = []
    questions = []

    # Smart money signals
    if sm_entry:
        net_24h = sm_entry.get("net_flow_24h_usd", 0)
        net_7d = sm_entry.get("net_flow_7d_usd", 0)
        net_30d = sm_entry.get("net_flow_30d_usd", 0)
        traders = sm_entry.get("trader_count", 0)

        if net_7d > 0:
            bull_points.append(f"Smart money net bought {format_usd(net_7d)} over 7 days")
        elif net_7d < 0:
            bear_points.append(f"Smart money net sold {format_usd(abs(net_7d))} over 7 days")

        if net_30d > 0 and net_7d > 0:
            bull_points.append("Sustained accumulation across both 7d and 30d timeframes")
        elif net_30d < 0 and net_7d < 0:
            bear_points.append("Consistent distribution across 7d and 30d — not a blip")

        if traders >= 5:
            bull_points.append(f"{traders} distinct smart money wallets active — broad conviction")
        elif traders <= 2 and traders > 0:
            bear_points.append(f"Only {traders} smart money trader(s) — could be noise, not signal")

        if net_24h > 0 and net_7d < 0:
            questions.append("24h flow turned positive while 7d is negative — is this a reversal or dead cat bounce?")
    else:
        bear_points.append("No smart money flow data found — token may be off smart money radar")
        questions.append("Why aren't sophisticated traders tracking this token?")

    # Flow intelligence
    whale_flow = flow_intel_data.get("whale_net_flow_usd", 0)
    exchange_flow = flow_intel_data.get("exchange_net_flow_usd", 0)
    fresh_flow = flow_intel_data.get("fresh_wallets_net_flow_usd", 0)

    if whale_flow > 0:
        bull_points.append(f"Whales accumulated {format_usd(whale_flow)} — large holders increasing exposure")
    elif whale_flow < 0:
        bear_points.append(f"Whales dumped {format_usd(abs(whale_flow))} — watch for more selling")

    if exchange_flow > 0:
        bear_points.append("Tokens moving TO exchanges — potential sell pressure incoming")
    elif exchange_flow < 0:
        bull_points.append("Tokens moving OFF exchanges — holders choosing cold storage (bullish)")

    if fresh_flow > 0 and fresh_flow > abs(whale_flow) * 0.5:
        bear_points.append(f"Fresh wallets bought {format_usd(fresh_flow)} — could be retail FOMO or wash trading")
        questions.append("Are the fresh wallet inflows organic retail demand or manufactured activity?")

    # Screener data
    if screener_entry:
        price_change = screener_entry.get("price_change", 0)
        liq = screener_entry.get("liquidity", 0)
        mcap = screener_entry.get("market_cap_usd", 0)
        age = screener_entry.get("token_age_days", 0)
        vol = screener_entry.get("volume", 0)

        if liq and mcap and liq > mcap * 0.05:
            bull_points.append("Healthy liquidity relative to market cap — exits are feasible")
        elif liq and mcap and liq < mcap * 0.02:
            bear_points.append("Very low liquidity vs market cap — exit risk is real")

        if age and age < 30:
            bear_points.append(f"Only {age} days old — insufficient track record")
            questions.append("What happens when early investor vesting unlocks?")

        if vol and mcap and vol > mcap * 0.1:
            bull_points.append("High volume-to-mcap ratio — active trading interest")

        if price_change and price_change < -0.05:
            sm_net = sm_entry.get("net_flow_7d_usd", 0) if sm_entry else 0
            if sm_net > 0:
                bull_points.append("Price dropping while smart money buys — classic accumulation divergence")
                questions.append("Is smart money front-running a catalyst, or catching a falling knife?")

    # Risk indicators
    if indicators:
        ind_data = indicators.get("data", indicators)
        if isinstance(ind_data, dict):
            for ri in ind_data.get("risk_indicators", []):
                if ri.get("score", "").lower() == "high":
                    name = ri.get("indicator_type", "").replace("-", " ").title()
                    bear_points.append(f"Nansen Score flags {name} as HIGH risk")

            bullish_rewards = sum(1 for ri in ind_data.get("reward_indicators", []) if ri.get("score", "").lower() == "bullish")
            if bullish_rewards >= 2:
                bull_points.append(f"{bullish_rewards} reward indicators are Bullish")

    # Holders
    if holders and len(holders) >= 2:
        top_holder_pct = holders[0].get("percentage", 0)
        if top_holder_pct and top_holder_pct > 20:
            bear_points.append(f"Top holder owns {top_holder_pct:.1f}% — high concentration risk")
            questions.append("Who is the top holder, and do they have incentive to dump?")

    # Buyers
    if who_bought_sold:
        total_buy = sum(e.get("bought_volume_usd", 0) for e in who_bought_sold)
        total_sell = sum(e.get("sold_volume_usd", 0) for e in who_bought_sold)
        if total_buy > total_sell * 2:
            bull_points.append("Labeled buyers significantly outweigh sellers in 7d")
        elif total_sell > total_buy * 2:
            bear_points.append("Labeled sellers significantly outweigh buyers in 7d")

    # Fallbacks
    if not bull_points:
        bull_points.append("Insufficient data for clear bull signals — proceed with caution")
    if not bear_points:
        bear_points.append("No obvious red flags detected — but absence of risk isn't safety")
    if not questions:
        questions.append("What catalyst could change the current trajectory?")
        questions.append("Is there a vesting schedule that could create supply pressure?")

    bull_html = "".join(f"<li>{p}</li>" for p in bull_points[:5])
    bear_html = "".join(f"<li>{p}</li>" for p in bear_points[:5])
    q_html = "".join(f"<li>{q}</li>" for q in questions[:4])

    return bull_html, bear_html, q_html


def generate_ohlcv_json(ohlcv: list) -> str:
    """Convert OHLCV data to JSON for Chart.js.
    Handles various timestamp field names and filters out bad data."""
    if not ohlcv:
        return "[]"

    points = []
    for candle in ohlcv:
        # Try multiple timestamp field names
        ts = candle.get("interval_start", candle.get("timestamp", candle.get("time", "")))
        close = candle.get("close", candle.get("price_close", None))
        volume = candle.get("volume_usd", candle.get("volume", 0))
        open_p = candle.get("open", candle.get("price_open", None))
        high = candle.get("high", candle.get("price_high", None))
        low = candle.get("low", candle.get("price_low", None))

        # Filter: skip candles with null/zero prices
        if close is None or close == 0:
            continue
        if open_p is None:
            open_p = close

        # Filter: skip future dates (garbage data)
        if ts and str(ts) > "2027":
            continue
        # Filter: skip very old pre-launch data if we have enough recent data
        # (handled after collection)

        # Format timestamp label
        label = ""
        if ts:
            try:
                ts_str = str(ts)
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                # Use "Mar 15" for daily, "Mar 15 04:00" for intraday
                label = dt.strftime("%b %d %H:%M") if "T" in ts_str else dt.strftime("%b %d")
            except Exception:
                label = str(ts)[:10]

        points.append({
            "label": label,
            "open": float(open_p) if open_p else 0,
            "high": float(high) if high else float(close),
            "low": float(low) if low else float(close),
            "close": float(close),
            "volume": float(volume) if volume else 0,
        })

    # If we have too many points, take the last 42 (roughly 7 days at 4h)
    if len(points) > 42:
        points = points[-42:]

    # If fewer than 3 valid points, chart won't be useful
    if len(points) < 3:
        return "[]"

    return json.dumps(points)


def generate_sm_flow_explainer(sm_entry: dict | None) -> str:
    """Generate dynamic explainer for smart money flows."""
    if not sm_entry:
        return ("Smart money flow data was not available for this specific token in Nansen's aggregated view. "
                "This doesn't necessarily mean smart money isn't trading it — they may be using DEX aggregators "
                "or the token may not meet Nansen's tracking threshold. Check the Who Bought/Sold section for individual wallet activity.")

    net_1h = sm_entry.get("net_flow_1h_usd", 0)
    net_24h = sm_entry.get("net_flow_24h_usd", 0)
    net_7d = sm_entry.get("net_flow_7d_usd", 0)
    net_30d = sm_entry.get("net_flow_30d_usd", 0)

    parts = []
    if net_7d > 0 and net_30d > 0:
        parts.append(f"Smart money has been consistently accumulating — {format_usd(net_7d)} in 7d and {format_usd(net_30d)} in 30d. This sustained buying across timeframes is the strongest bullish signal in onchain analysis.")
    elif net_7d < 0 and net_30d < 0:
        parts.append(f"Smart money is consistently distributing — selling {format_usd(abs(net_7d))} in 7d and {format_usd(abs(net_30d))} in 30d. When sophisticated traders exit across all timeframes, it's usually wise to pay attention.")
    elif net_24h > 0 and net_7d < 0:
        parts.append("Interesting divergence: 24h flows turned positive while 7d is still negative. This could signal the start of re-accumulation, or just noise. Watch if the 24h trend sustains into the 7d metric.")
    elif net_24h < 0 and net_7d > 0:
        parts.append("Short-term selling within a broader accumulation trend. Smart money may be taking partial profits or repositioning. The 7d trend is more reliable than 24h noise.")
    else:
        parts.append(f"Smart money flows are mixed: 1h={format_usd(net_1h)}, 24h={format_usd(net_24h)}, 7d={format_usd(net_7d)}, 30d={format_usd(net_30d)}. No clear directional conviction yet.")

    return " ".join(parts)


def generate_flow_intel_explainer(fi_data: dict) -> str:
    """Generate dynamic explainer for flow intelligence."""
    if not fi_data or all(fi_data.get(k, 0) == 0 for k in ["whale_net_flow_usd", "smart_trader_net_flow_usd", "exchange_net_flow_usd"]):
        return "Flow intelligence data shows minimal activity across wallet labels. This token may have limited institutional or whale interest, or the activity period was quiet."

    whale = fi_data.get("whale_net_flow_usd", 0)
    smart = fi_data.get("smart_trader_net_flow_usd", 0)
    exchange = fi_data.get("exchange_net_flow_usd", 0)
    fresh = fi_data.get("fresh_wallets_net_flow_usd", 0)

    parts = []
    if whale > 0 and smart > 0:
        parts.append("Both whales AND smart traders are accumulating. When two independent sophisticated groups agree, it's worth paying attention.")
    elif whale > 0 and smart < 0:
        parts.append("Whales are buying while smart traders sell. This could mean insider knowledge driving whale accumulation, or whales are the exit liquidity for smarter money.")
    elif whale < 0 and smart > 0:
        parts.append("Smart traders are buying what whales are selling. This rotation pattern can precede a trend change — smart traders often front-run the next move.")
    elif whale < 0 and smart < 0:
        parts.append("Both whales and smart traders are selling. Double negative signal — sophisticated money is heading for the exits.")

    if exchange > 0:
        parts.append(f"Exchange inflows of {format_usd(exchange)} suggest upcoming sell pressure — tokens move to exchanges to be sold.")
    elif exchange < 0:
        parts.append(f"Exchange outflows of {format_usd(abs(exchange))} — tokens moving to cold storage or DeFi. Reduces available supply.")

    if fresh > 0 and abs(fresh) > abs(whale):
        parts.append("Fresh wallet activity exceeds whale activity — could indicate retail FOMO or potential wash trading. Investigate further.")

    return " ".join(parts) if parts else "Flow intelligence data is available but shows no significant divergences between wallet types."


def generate_buyers_explainer(who_bought_sold: list) -> str:
    """Generate explainer for buyers/sellers section."""
    if not who_bought_sold:
        return "No buyer/seller data available for this token in the analyzed period."

    total_buy = sum(e.get("bought_volume_usd", 0) for e in who_bought_sold)
    total_sell = sum(e.get("sold_volume_usd", 0) for e in who_bought_sold)
    labeled_count = sum(1 for e in who_bought_sold if e.get("address_label") and e["address_label"] != "Unlabeled")

    parts = []
    if total_buy > total_sell * 1.5:
        parts.append(f"Buying pressure dominates: {format_usd(total_buy)} bought vs {format_usd(total_sell)} sold among tracked wallets.")
    elif total_sell > total_buy * 1.5:
        parts.append(f"Selling pressure dominates: {format_usd(total_sell)} sold vs {format_usd(total_buy)} bought among tracked wallets.")
    else:
        parts.append(f"Roughly balanced: {format_usd(total_buy)} bought vs {format_usd(total_sell)} sold.")

    if labeled_count > 0:
        parts.append(f"{labeled_count} of the top addresses have Nansen labels, helping identify their trading patterns.")

    # Check for notable patterns
    if who_bought_sold:
        top = who_bought_sold[0]
        bought = top.get("bought_volume_usd", 0)
        sold = top.get("sold_volume_usd", 0)
        label = top.get("address_label", "Unknown")
        if bought > 0 and sold == 0:
            parts.append(f"Top buyer ({label}) only bought with zero sells — conviction position, not trading.")

    return " ".join(parts)


def generate_holders_explainer(holders: list) -> str:
    """Generate explainer for holders section."""
    if not holders:
        return "No holder data available."

    parts = []
    total = sum(h.get("token_amount", 0) for h in holders)
    top1 = holders[0].get("token_amount", 0) if holders else 0
    top5 = sum(h.get("token_amount", 0) for h in holders[:5])

    if total > 0 and top1 > 0:
        top1_pct = (top1 / total * 100) if total > 0 else 0
        top5_pct = (top5 / total * 100) if total > 0 else 0
        parts.append(f"Top holder controls {top1_pct:.0f}% of tracked holdings, top 5 control {top5_pct:.0f}%.")

        if top1_pct > 30:
            parts.append("Very high concentration — a single wallet dump could crash the price. Check if it's a known contract (vesting, staking, or team treasury).")
        elif top1_pct > 15:
            parts.append("Moderate concentration. Worth identifying whether top holders are team/treasury wallets vs active traders.")
        else:
            parts.append("Relatively distributed holdings — no single entity dominates supply.")

    parts.append("Click any address to investigate on the block explorer — check transaction history, age, and other holdings for context.")

    return " ".join(parts)


def generate_top_buyer_explainer(top_buyer_balance: list, top_buyer_addr: str, bought_amount: float = 0) -> str:
    """Generate explainer for top buyer deep dive."""
    if not top_buyer_balance:
        return "Could not retrieve portfolio data for the top buyer."

    total_value = sum(h.get("value_usd", 0) for h in top_buyer_balance)
    token_count = len(top_buyer_balance)

    # Check if trader has exited
    if bought_amount > 0 and total_value < bought_amount * 0.01:
        return (f"This wallet bought {format_usd(bought_amount)} worth of this token but currently holds only "
                f"{format_usd(total_value)} total across all tokens. They have fully exited their position. "
                f"This is important context: the biggest buyer by volume was a short-term trader, not a conviction holder. "
                f"Look at buyers #2-5 in the table above for holders who may still be in.")

    parts = [f"This wallet holds {token_count} tokens worth approximately {format_usd(total_value)} total."]

    if total_value > 1_000_000:
        parts.append("This is a high-value wallet — likely a fund or sophisticated individual trader. Their conviction carries weight.")
    elif total_value > 100_000:
        parts.append("Mid-sized wallet. Could be a serious retail trader or small fund.")
    else:
        parts.append("Relatively small portfolio. Their position in this token may represent a significant bet relative to their total holdings.")

    if top_buyer_balance and total_value > 0:
        top_holding = max(top_buyer_balance, key=lambda x: x.get("value_usd", 0))
        top_pct = (top_holding.get("value_usd", 0) / total_value * 100) if total_value > 0 else 0
        if top_pct > 80:
            parts.append(f"Portfolio is heavily concentrated in {top_holding.get('token_symbol', '?')} ({top_pct:.0f}%). Single-bet trader or recent migration.")

    return " ".join(parts)


def generate_html_report(
    symbol: str,
    token: str,
    chain: str,
    api_calls: int,
    api_log: list,
    screener_entry: dict | None,
    sm_entry: dict | None,
    flow_intel: list | dict | None,
    who_bought_sold: list,
    indicators: dict | None,
    holders: list,
    ohlcv: list,
    sm_holdings: list,
    top_buyer_addr: str,
    top_buyer_balance: list,
) -> str:
    """Generate HTML dashboard from collected data."""

    template_path = Path(__file__).parent / "template.html"
    html = template_path.read_text()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Basic replacements
    html = html.replace("{{SYMBOL}}", symbol)
    html = html.replace("{{TOKEN_ADDRESS}}", token)
    html = html.replace("{{CHAIN}}", chain.capitalize())
    html = html.replace("{{TIMESTAMP}}", now)
    html = html.replace("{{API_CALLS}}", str(api_calls))
    html = html.replace("{{COST}}", f"{api_calls * 0.03:.2f}")

    # Explorer URLs
    html = html.replace("{{EXPLORER_TOKEN_URL}}", explorer_url(chain, token, "token"))
    html = html.replace("{{TOP_BUYER_EXPLORER_URL}}", explorer_url(chain, top_buyer_addr or "") if top_buyer_addr else "#")

    # Screener metrics
    if screener_entry:
        mcap = screener_entry.get("market_cap_usd", 0)
        price = screener_entry.get("price_usd", 0)
        pc = screener_entry.get("price_change", 0)
        vol = screener_entry.get("volume", 0)
        liq = screener_entry.get("liquidity", 0)
        age = screener_entry.get("token_age_days", 0)

        html = html.replace("{{MARKET_CAP}}", format_usd(mcap))
        # Fix 2: Smart price formatting — no unnecessary decimals
        if not price:
            price_str = "N/A"
        elif price < 0.001:
            price_str = f"${price:.6f}"
        elif price < 0.01:
            price_str = f"${price:.4f}"
        elif price < 1:
            price_str = f"${price:.2f}"
        else:
            price_str = f"${price:,.2f}"
        html = html.replace("{{PRICE}}", price_str)
        pc_str = f"{'+' if pc and pc > 0 else ''}{pc*100:.2f}%" if pc else "N/A"
        html = html.replace("{{PRICE_CHANGE}}", pc_str)
        html = html.replace("{{PRICE_CHANGE_CLASS}}", "positive" if pc and pc > 0 else "negative" if pc else "neutral")
        html = html.replace("{{VOLUME}}", format_usd(vol))
        html = html.replace("{{LIQUIDITY}}", format_usd(liq))
        html = html.replace("{{TOKEN_AGE}}", str(age) if age else "N/A")
    else:
        for key in ["MARKET_CAP", "PRICE", "VOLUME", "LIQUIDITY"]:
            html = html.replace("{{" + key + "}}", "N/A")
        html = html.replace("{{PRICE_CHANGE}}", "N/A")
        html = html.replace("{{PRICE_CHANGE_CLASS}}", "neutral")
        html = html.replace("{{TOKEN_AGE}}", "N/A")

    # SM Conviction — Fix 3: fall back to flow intelligence if no SM netflow match
    conviction = 0
    conviction_note = ""
    sm_1h = sm_entry.get("net_flow_1h_usd", 0) if sm_entry else 0
    sm_24h = sm_entry.get("net_flow_24h_usd", 0) if sm_entry else 0
    sm_7d = sm_entry.get("net_flow_7d_usd", 0) if sm_entry else 0
    sm_30d = sm_entry.get("net_flow_30d_usd", 0) if sm_entry else 0

    if sm_entry:
        if sm_1h > 0: conviction += 15
        if sm_24h > 0: conviction += 25
        if sm_7d > 0: conviction += 35
        if sm_30d > 0: conviction += 25
    else:
        # Fallback: derive partial conviction from flow intelligence
        fi_check = flow_intel[0] if isinstance(flow_intel, list) and flow_intel else flow_intel
        if isinstance(fi_check, dict):
            whale = fi_check.get("whale_net_flow_usd", 0)
            smart = fi_check.get("smart_trader_net_flow_usd", 0)
            exchange = fi_check.get("exchange_net_flow_usd", 0)
            fresh = fi_check.get("fresh_wallets_net_flow_usd", 0)
            if whale > 0: conviction += 20
            if smart > 0: conviction += 25
            if exchange < 0: conviction += 15  # outflow from exchanges = bullish
            if fresh > 0 and whale > 0: conviction += 10  # broad interest
            conviction = min(conviction, 70)  # cap at 70 — can't be "high" without direct SM data
            if conviction > 0:
                conviction_note = " (from flow intelligence — no direct smart money tracking)"

    html = html.replace("{{CONVICTION_SCORE}}", str(conviction))
    if conviction >= 75:
        html = html.replace("{{CONVICTION_CLASS}}", "positive")
        html = html.replace("{{CONVICTION_COLOR}}", "#10b981")
    elif conviction >= 50:
        html = html.replace("{{CONVICTION_CLASS}}", "neutral")
        html = html.replace("{{CONVICTION_COLOR}}", "#f59e0b")
    else:
        html = html.replace("{{CONVICTION_CLASS}}", "negative")
        html = html.replace("{{CONVICTION_COLOR}}", "#ef4444")

    html = html.replace("{{SM_FLOW_1H}}", str(round(sm_1h, 2)))
    html = html.replace("{{SM_FLOW_24H}}", str(round(sm_24h, 2)))
    html = html.replace("{{SM_FLOW_7D}}", str(round(sm_7d, 2)))
    html = html.replace("{{SM_FLOW_30D}}", str(round(sm_30d, 2)))

    # No-data overlays for charts
    sm_has_data = any(v != 0 for v in [sm_1h, sm_24h, sm_7d, sm_30d])
    html = html.replace("{{SM_FLOW_NO_DATA}}",
        "" if sm_has_data else '<div class="no-data-overlay"><span>Smart money flow data not available for this token</span></div>')

    # PRICE_CHART_NO_DATA is set later, after OHLCV filtering

    # Flow Intelligence
    fi_data = {}
    if flow_intel:
        fi_data = flow_intel[0] if isinstance(flow_intel, list) and flow_intel else flow_intel
        if not isinstance(fi_data, dict):
            fi_data = {}

    fi_whale = fi_data.get("whale_net_flow_usd", 0)
    fi_smart = fi_data.get("smart_trader_net_flow_usd", 0)
    fi_exchange = fi_data.get("exchange_net_flow_usd", 0)
    fi_fresh = fi_data.get("fresh_wallets_net_flow_usd", 0)
    fi_pnl = fi_data.get("top_pnl_net_flow_usd", 0)
    fi_public = fi_data.get("public_figure_net_flow_usd", 0)

    fi_has_data = any(v != 0 for v in [fi_whale, fi_smart, fi_exchange, fi_fresh, fi_pnl, fi_public])
    html = html.replace("{{FI_NO_DATA}}",
        "" if fi_has_data else '<div class="no-data-overlay"><span>Flow intelligence data not available</span></div>')

    html = html.replace("{{FI_WHALE}}", str(round(fi_whale, 2)))
    html = html.replace("{{FI_SMART}}", str(round(fi_smart, 2)))
    html = html.replace("{{FI_EXCHANGE}}", str(round(fi_exchange, 2)))
    html = html.replace("{{FI_FRESH}}", str(round(fi_fresh, 2)))
    html = html.replace("{{FI_PNL}}", str(round(fi_pnl, 2)))
    html = html.replace("{{FI_PUBLIC}}", str(round(fi_public, 2)))

    # Verdict
    whale_flow = fi_data.get("whale_net_flow_usd", 0)
    smart_flow = fi_data.get("smart_trader_net_flow_usd", 0)
    total_signal = conviction / 25
    if whale_flow > 0: total_signal += 1
    if smart_flow > 0: total_signal += 1

    # Check for price-SM divergence: SM accumulating while price drops
    price_dropping = False
    sm_accumulating = False
    if screener_entry:
        pc = screener_entry.get("price_change", 0)
        if pc and pc < -0.03:  # Price down more than 3%
            price_dropping = True
    if sm_entry:
        if sm_entry.get("net_flow_7d_usd", 0) > 0 or sm_entry.get("net_flow_30d_usd", 0) > 0:
            sm_accumulating = True
    # Also check SM holdings for the token
    if sm_holdings and symbol:
        for h in sm_holdings:
            if h.get("token_symbol", "") == symbol:
                sm_accumulating = True
                break

    divergence_signal = price_dropping and sm_accumulating

    if total_signal >= 4:
        verdict, verdict_desc = "BULLISH", "Strong smart money accumulation with whale backing"
        verdict_class, verdict_color = "bullish", "positive"
    elif divergence_signal:
        verdict = "DIVERGENCE"
        verdict_desc = "Smart money is accumulating while price drops — classic divergence signal. Sophisticated traders are buying what retail is selling."
        verdict_class, verdict_color = "bullish", "positive"
    elif total_signal >= 2.5:
        verdict, verdict_desc = "CAUTIOUSLY BULLISH", "Positive smart money signals but mixed whale activity"
        verdict_class, verdict_color = "bullish", "positive"
    elif total_signal >= 1.5:
        verdict, verdict_desc = "NEUTRAL", "Some smart money interest but insufficient conviction"
        verdict_class, verdict_color = "neutral", "neutral"
    else:
        verdict, verdict_desc = "BEARISH", "No clear smart money accumulation signal"
        verdict_class, verdict_color = "bearish", "negative"

    html = html.replace("{{VERDICT}}", verdict)
    html = html.replace("{{VERDICT_DESC}}", verdict_desc)
    html = html.replace("{{VERDICT_CLASS}}", verdict_class)
    html = html.replace("{{VERDICT_COLOR_CLASS}}", verdict_color)

    # Bull/Bear/Questions
    bull_html, bear_html, q_html = generate_bull_bear_case(
        screener_entry, sm_entry, fi_data, indicators, who_bought_sold, holders)
    html = html.replace("{{BULL_CASE_ITEMS}}", bull_html)
    html = html.replace("{{BEAR_CASE_ITEMS}}", bear_html)
    html = html.replace("{{KEY_QUESTIONS_ITEMS}}", q_html)

    # OHLCV Price Chart
    ohlcv_json_str = generate_ohlcv_json(ohlcv)
    ohlcv_has_data = ohlcv_json_str != "[]"
    html = html.replace("{{OHLCV_JSON}}", ohlcv_json_str)

    # Update price chart no-data overlay based on filtered data
    html = html.replace("{{PRICE_CHART_NO_DATA}}",
        "" if ohlcv_has_data else '<div class="no-data-overlay"><span>OHLCV price data not available for this token</span></div>')

    # Explainers
    html = html.replace("{{SM_FLOW_EXPLAINER}}", generate_sm_flow_explainer(sm_entry))
    html = html.replace("{{FLOW_INTEL_EXPLAINER}}", generate_flow_intel_explainer(fi_data))
    html = html.replace("{{BUYERS_EXPLAINER}}", generate_buyers_explainer(who_bought_sold))
    html = html.replace("{{HOLDERS_EXPLAINER}}", generate_holders_explainer(holders))
    buyer_bought_for_explainer = who_bought_sold[0].get("bought_volume_usd", 0) if who_bought_sold else 0
    html = html.replace("{{TOP_BUYER_EXPLAINER}}", generate_top_buyer_explainer(top_buyer_balance, top_buyer_addr or "", buyer_bought_for_explainer))

    # Risk indicators
    risk_html, reward_html, risk_explainer, reward_explainer = generate_risk_html(indicators)
    html = html.replace("{{RISK_INDICATORS_HTML}}", risk_html)
    html = html.replace("{{REWARD_INDICATORS_HTML}}", reward_html)
    html = html.replace("{{RISK_EXPLAINER}}", risk_explainer)
    html = html.replace("{{REWARD_EXPLAINER}}", reward_explainer)

    # Buyers & Sellers table — now with clickable addresses
    bs_rows = ""
    for entry in (who_bought_sold or [])[:10]:
        addr = entry.get("address", "")
        label = entry.get("address_label", "Unlabeled")
        bought = entry.get("bought_volume_usd", 0)
        sold = entry.get("sold_volume_usd", 0)
        net = entry.get("trade_volume_usd", bought - sold)
        net_class = "positive" if net > 0 else "negative"
        bs_rows += f'''<tr>
            <td>{addr_link(chain, addr)}</td>
            <td>{label}</td>
            <td>{format_usd(bought)}</td>
            <td>{format_usd(sold)}</td>
            <td class="{net_class}">{format_usd(net)}</td>
        </tr>'''
    if not bs_rows:
        bs_rows = '<tr><td colspan="5" style="text-align:center;color:var(--text-dim)">No buyer/seller data available for this period</td></tr>'
    html = html.replace("{{BUYERS_SELLERS_ROWS}}", bs_rows)

    # Holders table — Fix 1: clickable full addresses, Fix 4: unlabeled fallback, Fix 6: USD value
    token_price = screener_entry.get("price_usd", 0) if screener_entry else 0
    h_rows = ""
    for i, h in enumerate((holders or [])[:10], 1):
        addr = h.get("address", "")
        label = h.get("label", h.get("address_label", ""))
        amount = h.get("token_amount", 0)
        # Fix 4: show "Unlabeled" in dim text instead of empty
        label_display = label if label else '<span style="color:var(--text-dim)">Unlabeled</span>'
        # Fix 6: calculate USD value from holdings × price
        usd_value = format_usd(amount * token_price) if token_price and amount else "—"
        h_rows += f'''<tr>
            <td>{i}</td>
            <td>{addr_link(chain, addr)}</td>
            <td>{label_display}</td>
            <td>{amount:,.0f}</td>
            <td>{usd_value}</td>
        </tr>'''
    if not h_rows:
        h_rows = '<tr><td colspan="5" style="text-align:center;color:var(--text-dim)">No holder data available</td></tr>'
    html = html.replace("{{HOLDERS_ROWS}}", h_rows)

    # SM Holdings table — Fix 5: add % of portfolio + context line
    sm_total = sum(h.get("total_value_usd", h.get("value_usd", 0)) for h in (sm_holdings or []))
    sm_rows = ""
    token_rank = None
    for idx, h in enumerate((sm_holdings or [])[:10], 1):
        sym = h.get("token_symbol", "?")
        val = h.get("total_value_usd", h.get("value_usd", 0))
        pct = (val / sm_total * 100) if sm_total > 0 else 0
        highlight = ' style="color:#fff;font-weight:600"' if sym == symbol else ""
        sm_rows += f'<tr><td{highlight}>{sym}</td><td>{format_usd(val)}</td><td>{pct:.1f}%</td></tr>'
        if sym == symbol:
            token_rank = idx
    if not sm_rows:
        sm_rows = '<tr><td colspan="3" style="text-align:center;color:var(--text-dim)">No data available</td></tr>'
    html = html.replace("{{SM_HOLDINGS_ROWS}}", sm_rows)

    # SM Holdings context line
    if token_rank:
        sm_context = f"{symbol} ranks #{token_rank} out of {len(sm_holdings)} tracked smart money holdings on {chain.capitalize()}, representing {((sm_holdings[token_rank-1].get('total_value_usd', 0) / sm_total * 100) if sm_total else 0):.1f}% of tracked smart money portfolio value."
    elif sm_holdings:
        sm_context = f"{symbol} does not appear in the top {len(sm_holdings)} smart money holdings on {chain.capitalize()}. This may indicate limited institutional interest."
    else:
        sm_context = "No smart money holdings data available."
    html = html.replace("{{SM_HOLDINGS_CONTEXT}}", sm_context)

    # Top buyer deep dive — check if they still hold a meaningful position
    buyer_total_portfolio = sum(h.get("value_usd", 0) for h in (top_buyer_balance or []))
    buyer_bought_amount = who_bought_sold[0].get("bought_volume_usd", 0) if who_bought_sold else 0
    buyer_exited = buyer_bought_amount > 0 and buyer_total_portfolio < buyer_bought_amount * 0.01

    html = html.replace("{{TOP_BUYER_ADDR}}", top_buyer_addr or "N/A")
    tb_rows = ""
    if buyer_exited:
        tb_rows = f'''<tr><td colspan="3" style="text-align:center;color:var(--yellow);padding:20px;">
            ⚠️ This trader has exited their position. They bought {format_usd(buyer_bought_amount)} but currently hold only {format_usd(buyer_total_portfolio)}.
            This is a completed trade, not an active holder.
        </td></tr>'''
    else:
        for h in (top_buyer_balance or [])[:10]:
            sym = h.get("token_symbol", "?")
            amt = h.get("token_amount", 0)
            val = h.get("value_usd", 0)
            tb_rows += f'<tr><td>{sym}</td><td>{amt:,.4f}</td><td>{format_usd(val)}</td></tr>'
    if not tb_rows:
        tb_rows = '<tr><td colspan="3" style="text-align:center;color:var(--text-dim)">Portfolio data unavailable</td></tr>'
    html = html.replace("{{TOP_BUYER_ROWS}}", tb_rows)

    # API Call Log
    log_rows = ""
    for i, log_entry in enumerate(api_log or [], 1):
        cmd = log_entry.get("command", "unknown")
        status = log_entry.get("status", "unknown")
        status_class = "positive" if status == "OK" else "negative"
        log_rows += f'<tr><td>{i}</td><td><code style="font-size:11px">{cmd}</code></td><td class="{status_class}">{status}</td></tr>'
    if not log_rows:
        log_rows = '<tr><td colspan="3" style="text-align:center;color:var(--text-dim)">No log available</td></tr>'
    html = html.replace("{{API_LOG_ROWS}}", log_rows)

    return html
