"""
FastAPI Web Interface for Protocol Due Diligence Engine.
Thin wrapper around due_diligence.py — no logic duplication.
"""
import time
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse

import due_diligence as dd
from html_report import generate_html_report

app = FastAPI(title="Protocol Due Diligence Engine")

REPORTS_DIR = Path(__file__).parent / "reports"
LAST_LIVE_RUN = 0.0  # timestamp of last live run
RATE_LIMIT_SECONDS = 300  # 5 minutes


# ─── Landing Page ────────────────────────────────────────────────────
LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Protocol Due Diligence Engine</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0e17;
    --card: #0d1320;
    --border: #1a2332;
    --text: #e5e7eb;
    --text-dim: #8899aa;
    --accent: #00D4AA;
    --accent-dim: rgba(0,212,170,0.12);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    min-height: 100vh;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 24px;
  }
  .container { max-width: 520px; width: 100%; text-align: center; }
  .logo {
    font-size: 48px; margin-bottom: 16px;
    filter: drop-shadow(0 0 20px rgba(0,212,170,0.3));
  }
  h1 {
    font-size: 32px; font-weight: 800; color: #fff;
    letter-spacing: -0.5px; margin-bottom: 8px;
  }
  .subtitle {
    font-size: 14px; color: var(--text-dim); margin-bottom: 40px;
    line-height: 1.5;
  }
  .subtitle a { color: var(--accent); text-decoration: none; }
  .subtitle a:hover { text-decoration: underline; }
  .form-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px;
    text-align: left;
  }
  label {
    display: block; font-size: 12px; font-weight: 600;
    color: var(--text-dim); text-transform: uppercase;
    letter-spacing: 0.8px; margin-bottom: 8px;
  }
  input[type="text"], select {
    width: 100%; padding: 12px 16px;
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 10px; color: #fff;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 14px; outline: none;
    transition: border-color 0.2s;
  }
  input[type="text"]:focus, select:focus {
    border-color: var(--accent);
  }
  input::placeholder { color: #4a5568; }
  select { font-family: 'Inter', sans-serif; cursor: pointer; appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L6 6L11 1' stroke='%238899aa' stroke-width='2'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 16px center;
  }
  select option { background: var(--bg); color: #fff; }
  .field { margin-bottom: 20px; }
  button {
    width: 100%; padding: 14px;
    background: var(--accent); color: #0a0e17;
    border: none; border-radius: 10px;
    font-family: 'Inter', sans-serif;
    font-size: 15px; font-weight: 700;
    cursor: pointer; transition: all 0.2s;
    letter-spacing: 0.3px;
  }
  button:hover { background: #33e6c0; transform: translateY(-1px); box-shadow: 0 4px 20px rgba(0,212,170,0.3); }
  button:active { transform: translateY(0); }
  .cost-note {
    text-align: center; margin-top: 14px;
    font-size: 12px; color: var(--text-dim);
  }
  .sample-link {
    display: inline-block; margin-top: 28px;
    padding: 10px 24px; border: 1px solid var(--border);
    border-radius: 10px; color: var(--accent);
    text-decoration: none; font-size: 13px; font-weight: 600;
    transition: all 0.2s;
  }
  .sample-link:hover {
    border-color: var(--accent); background: var(--accent-dim);
  }
  .footer {
    margin-top: 48px; font-size: 12px; color: var(--text-dim);
    text-align: center; line-height: 1.8;
  }
  .footer a { color: var(--accent); text-decoration: none; }
  .footer a:hover { text-decoration: underline; }
  .badge {
    display: inline-block; padding: 3px 10px;
    background: var(--accent-dim); border: 1px solid rgba(0,212,170,0.2);
    border-radius: 20px; font-size: 11px; font-weight: 600;
    color: var(--accent); margin-bottom: 20px;
  }
</style>
</head>
<body>
<div class="container">
  <div class="logo">🔬</div>
  <div class="badge">#NansenCLI Challenge</div>
  <h1>Protocol Due Diligence</h1>
  <div class="subtitle">
    15 Nansen CLI calls → one actionable report<br>
    Powered by <a href="https://nansen.ai" target="_blank">Nansen CLI</a> + x402 micropayments
  </div>

  <div class="form-card">
    <form action="/run" method="post">
      <div class="field">
        <label>Token Address</label>
        <input type="text" name="token" placeholder="JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN" required>
      </div>
      <div class="field">
        <label>Chain</label>
        <select name="chain">
          <option value="solana">Solana</option>
          <option value="ethereum">Ethereum</option>
          <option value="base">Base</option>
          <option value="arbitrum">Arbitrum</option>
          <option value="bnb">BNB Chain</option>
          <option value="polygon">Polygon</option>
          <option value="optimism">Optimism</option>
          <option value="avalanche">Avalanche</option>
        </select>
      </div>
      <button type="submit">Run Due Diligence</button>
      <div class="cost-note">~30 seconds · 15 API calls · ~$0.45 via x402</div>
    </form>
  </div>

  <a href="/sample" class="sample-link">View Sample Report →</a>

  <div class="footer">
    Built by <a href="https://twitter.com/0x_vcharles" target="_blank">Vincent Charles</a> · #NansenCLI<br>
    <a href="https://github.com/vchrl/token-dd" target="_blank">GitHub</a>
  </div>
</div>
</body>
</html>"""


# ─── Routes ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing():
    return LANDING_HTML


@app.get("/sample")
async def sample_report():
    """Redirect to the latest cached PUMP report."""
    pump_reports = sorted(REPORTS_DIR.glob("PUMP_solana_*.html"), reverse=True)
    if pump_reports:
        return RedirectResponse(f"/reports/{pump_reports[0].name}")
    return HTMLResponse("<h1>No sample report available</h1>", status_code=404)


@app.get("/reports/{filename}")
async def serve_report(filename: str):
    """Serve generated HTML reports."""
    filepath = REPORTS_DIR / filename
    if not filepath.exists() or not filepath.suffix == ".html":
        return HTMLResponse("<h1>Report not found</h1>", status_code=404)
    return FileResponse(filepath, media_type="text/html")


@app.post("/run")
async def run_pipeline(token: str = Form(...), chain: str = Form("solana")):
    """Run the DD pipeline and redirect to the report."""
    global LAST_LIVE_RUN

    if not token or len(token) < 10:
        return HTMLResponse("<h1>Invalid token address</h1>", status_code=400)

    if chain not in dd.SUPPORTED_CHAINS:
        return HTMLResponse(f"<h1>Unsupported chain: {chain}</h1>", status_code=400)

    # Check cache first
    token_short = token[:8] if len(token) > 8 else token
    cache_dir = REPORTS_DIR / f"{token_short}_{chain}_raw"
    use_cache = cache_dir.exists() and any(cache_dir.glob("*.json"))

    if not use_cache:
        # Live run — check rate limit
        now = time.time()
        if now - LAST_LIVE_RUN < RATE_LIMIT_SECONDS:
            remaining = int(RATE_LIMIT_SECONDS - (now - LAST_LIVE_RUN))
            return JSONResponse(
                {"error": f"Rate limited. Please wait {remaining} seconds before next live run."},
                status_code=429
            )
        LAST_LIVE_RUN = now

    # Set up globals
    dd.USE_CACHE = use_cache
    dd.API_CALL_COUNT = 0
    dd.API_CALL_LOG = []
    dd.CACHE_DIR = cache_dir

    # Run pipeline (same logic as cli.py)
    screener = dd.collect_token_screener(chain, limit=20)
    sm_netflow = dd.collect_smart_money_netflow(chain, limit=20)
    sm_holdings = dd.collect_smart_money_holdings(chain, limit=10)
    dd.collect_smart_money_dex_trades(chain, limit=5)
    dd.collect_token_info(chain, token)
    flow_intel = dd.collect_flow_intelligence(chain, token, days=7)
    who_bs = dd.collect_who_bought_sold(chain, token, days=7, limit=10)
    indicators = dd.collect_token_indicators(chain, token)
    holders = dd.collect_token_holders(chain, token, limit=10)
    dd.collect_token_pnl(chain, token, days=30, limit=10)
    dd.collect_token_dex_trades(chain, token, days=7, limit=10)
    dd.collect_token_flows(chain, token, days=7)
    ohlcv = dd.collect_token_ohlcv(chain, token)

    # Top buyer
    top_buyer_addr = ""
    top_buyer_balance = []
    if who_bs:
        top_buyer_addr = who_bs[0].get("address", "")
        if top_buyer_addr:
            top_buyer_balance = dd.collect_profiler_balance(top_buyer_addr, chain)
            dd.collect_profiler_counterparties(top_buyer_addr, chain)

    # Resolve symbol
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

    # Reconstruct log for cache mode
    if use_cache and not dd.API_CALL_LOG:
        token_log = token[:8] + "..." if len(token) > 8 else token
        top_log = top_buyer_addr[:8] + "..." if top_buyer_addr else "unknown"
        cmds = [
            ("token screener", "token_screener"), ("smart-money netflow", "sm_netflow"),
            ("smart-money holdings", "sm_holdings"), ("smart-money dex-trades", "sm_dex_trades"),
            ("token info", "token_info"), ("token flow-intelligence", "flow_intelligence"),
            ("token who-bought-sold", "who_bought_sold"), ("token indicators", "token_indicators"),
            ("token holders", "token_holders"), ("token pnl", "token_pnl"),
            ("token dex-trades", "token_dex_trades"), ("token flows", "token_flows"),
            ("token ohlcv", "token_ohlcv"), ("profiler balance", "profiler_balance"),
            ("profiler counterparties", "profiler_counterparties"),
        ]
        for cmd, fname in cmds:
            exists = (cache_dir / f"{fname}.json").exists()
            dd.API_CALL_LOG.append({"command": f"nansen research {cmd} --chain {chain}", "status": "OK" if exists else "No Data"})
        dd.API_CALL_COUNT = sum(1 for e in dd.API_CALL_LOG if e["status"] == "OK")

    # Generate report
    html = generate_html_report(
        symbol=symbol, token=token, chain=chain,
        api_calls=dd.API_CALL_COUNT, api_log=dd.API_CALL_LOG,
        screener_entry=screener_entry, sm_entry=sm_entry,
        flow_intel=flow_intel, who_bought_sold=who_bs,
        indicators=indicators, holders=holders, ohlcv=ohlcv,
        sm_holdings=sm_holdings, top_buyer_addr=top_buyer_addr,
        top_buyer_balance=top_buyer_balance,
    )

    # Save
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{chain}_{ts}.html"
    (REPORTS_DIR / filename).write_text(html)

    return RedirectResponse(f"/reports/{filename}", status_code=303)
