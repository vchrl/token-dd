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
LANDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>token-dd</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: #0a0e17;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; padding: 16px;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace;
  }
  .window {
    width: 100%; max-width: 780px;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 16px 70px rgba(0,0,0,0.5), 0 0 40px rgba(0,212,170,0.06);
  }
  .titlebar {
    background: #161b22;
    padding: 10px 16px;
    display: flex; align-items: center; gap: 8px;
    border-bottom: 1px solid #21262d;
    user-select: none;
  }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .dot.r { background: #ff5f57; }
  .dot.y { background: #febc2e; }
  .dot.g { background: #28c840; }
  .titlebar-text {
    flex: 1; text-align: center;
    color: #484f58; font-size: 12px;
  }
  .terminal {
    padding: 20px;
    min-height: 480px;
    color: #c9d1d9;
    font-size: 14px;
    line-height: 1.7;
    overflow-y: auto;
    max-height: 80vh;
  }
  @media (max-width: 600px) {
    .terminal { font-size: 11px; padding: 12px; }
    .ascii-art { font-size: 4.5px !important; letter-spacing: 0.5px !important; }
    .ascii-sub { font-size: 11px !important; }
  }
  @media (min-width: 601px) and (max-width: 780px) {
    .ascii-art { font-size: 6.5px !important; }
  }
  .g { color: #00D4AA; }
  .y { color: #ffa502; }
  .r { color: #ff4757; }
  .d { color: #484f58; }
  .w { color: #e6edf3; font-weight: bold; }
  .line { min-height: 1.7em; }
  .prompt { color: #00D4AA; }
  .cursor {
    display: inline-block;
    width: 8px; height: 16px;
    background: #00D4AA;
    vertical-align: text-bottom;
    animation: blink 1s step-end infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }
  .input-line { display: flex; align-items: center; }
  .input-line input {
    flex: 1;
    background: none; border: none; outline: none;
    color: #e6edf3; font-family: inherit; font-size: inherit;
    caret-color: #00D4AA;
  }
  .input-line input::placeholder { color: #30363d; }
  .separator { color: #21262d; }
  .spinner { display: inline-block; }
  @keyframes spin {
    0% { content: "\2807"; } 10% { content: "\2819"; } 20% { content: "\2839"; }
    30% { content: "\2838"; } 40% { content: "\283c"; } 50% { content: "\2834"; }
    60% { content: "\2826"; } 70% { content: "\2827"; } 80% { content: "\2807"; } 90% { content: "\280f"; }
  }
  .spinner::before {
    content: "\2807";
    animation: spin 0.8s linear infinite;
    color: #ffa502;
  }
  .hidden { display: none; }
  .ascii-art {
    color: #00D4AA;
    font-size: 8px;
    line-height: 1.15;
    letter-spacing: 1px;
    white-space: pre;
    margin-bottom: 4px;
    text-shadow: 0 0 10px rgba(0,212,170,0.3);
  }
  .ascii-sub {
    color: #9ca3af;
    font-size: 13px;
    letter-spacing: 3px;
    margin-bottom: 16px;
  }
  .typing-cursor {
    display: inline-block;
    width: 7px; height: 14px;
    background: #00D4AA;
    vertical-align: text-bottom;
    margin-left: 1px;
    animation: blink 0.7s step-end infinite;
  }
  .report-btn {
    display: inline-block;
    margin-top: 8px;
    padding: 8px 24px;
    border: 1px solid #00D4AA;
    border-radius: 4px;
    color: #00D4AA;
    text-decoration: none;
    font-family: inherit;
    font-size: 14px;
    font-weight: bold;
    background: rgba(0,212,170,0.06);
    cursor: pointer;
    transition: all 0.2s;
  }
  .report-btn:hover {
    background: rgba(0,212,170,0.15);
    box-shadow: 0 0 15px rgba(0,212,170,0.2);
    text-shadow: 0 0 8px rgba(0,212,170,0.4);
  }
</style>
</head>
<body>
<div class="window">
  <div class="titlebar">
    <div class="dot r"></div>
    <div class="dot y"></div>
    <div class="dot g"></div>
    <div class="titlebar-text">token-dd — bash</div>
  </div>
  <div class="terminal" id="term">
    <div id="output"></div>
    <div id="inputArea" class="hidden">
      <div class="input-line">
        <span class="prompt">$ </span>
        <input type="text" id="tokenInput" placeholder="paste token address..." autofocus autocomplete="off" spellcheck="false">
      </div>
    </div>
  </div>
</div>

<script>
const output = document.getElementById('output');
const inputArea = document.getElementById('inputArea');
const tokenInput = document.getElementById('tokenInput');

const DEMO_TOKEN = 'pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn';

const STEPS = [
  ["Token overview",           "PUMP \u00b7 $1.1B market cap +0.9%"],
  ["Smart money netflow",      "$728.4K net inflow (7d) \u00b7 4 traders"],
  ["Smart money holdings",     "$14.1M across 10 tokens"],
  ["Smart money DEX trades",   "5 recent trades"],
  ["Token info",               "PUMP metadata loaded"],
  ["Flow intelligence",        "Whales +$236.3K, Exchanges -$815.5K"],
  ["Who bought/sold",          "$52.1M bought vs $37.8M sold"],
  ["Nansen Score",             "\u26a0 HIGH risk: BTC Reflexivity"],
  ["Holder distribution",      "Top holder: 49% (pump.fun custody)"],
  ["PnL leaderboard",          "Top traders mapped"],
  ["DEX trades",               "10 trades analyzed"],
  ["Token flows",              "Flow data loaded"],
  ["Price history",            "721 candles \u00b7 $0.0017 \u2013 $0.0022"],
  ["Profiler balance",         "Top buyer portfolio: $40.87"],
  ["Profiler counterparties",  "5 counterparties identified"],
];

const ASCII_BANNER = `\
 \u2588\u2588\u2588\u2557   \u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2557   \u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2557      \u2588\u2588\u2557
 \u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551  \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d \u2588\u2588\u2551      \u2588\u2588\u2551
 \u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2554\u2588\u2588\u2557 \u2588\u2588\u2551  \u2588\u2588\u2551     \u2588\u2588\u2551      \u2588\u2588\u2551
 \u2588\u2588\u2551\u255a\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2551\u255a\u2588\u2588\u2557\u2588\u2588\u2551\u255a\u2550\u2550\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u255d  \u2588\u2588\u2551\u255a\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551     \u2588\u2588\u2551      \u2588\u2588\u2551
 \u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551 \u255a\u2588\u2588\u2588\u2588\u2551  \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551
 \u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u2550\u2550\u255d   \u255a\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d`;

function addLine(html, cls) {
  const div = document.createElement('div');
  div.className = 'line ' + (cls || '');
  div.innerHTML = html;
  output.appendChild(div);
  div.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return div;
}

function addRaw(html, cls) {
  const div = document.createElement('div');
  if (cls) div.className = cls;
  div.innerHTML = html;
  output.appendChild(div);
  return div;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function typeText(text, speed) {
  const line = addLine('');
  for (let i = 0; i < text.length; i++) {
    // skip inside HTML tags
    if (text[i] === '<') {
      const close = text.indexOf('>', i);
      if (close !== -1) { line.innerHTML += text.substring(i, close + 1); i = close; continue; }
    }
    line.innerHTML += text[i];
    await sleep(speed || 30);
  }
  return line;
}

async function showBanner() {
  // ASCII art — instant
  addRaw('<pre>' + ASCII_BANNER + '</pre>', 'ascii-art');
  addRaw('token due diligence engine', 'ascii-sub');
  addLine('');

  // Typewriter text
  await typeText('<span class="d">Powered by Nansen CLI + x402 micropayments</span>', 30);
  await typeText('<span class="d">Built by <a href="https://linktr.ee/vincent.charles" target="_blank" style="color:#00D4AA;text-decoration:none">Vincent Charles</a> \u00b7 #NansenCLI</span>', 30);
  addLine('<span class="separator">\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500</span>');
  addLine('');
  await typeText('<span class="d">Enter a token address to run 15 Nansen CLI</span>', 30);
  await typeText('<span class="d">calls and generate a due diligence report.</span>', 30);
  addLine('');
}

async function showPrompt() {
  inputArea.classList.remove('hidden');
  tokenInput.focus();

  const params = new URLSearchParams(window.location.search);
  const autoDemo = params.get('demo') === 'true';
  let demoTimer = null;

  if (autoDemo) {
    demoTimer = setTimeout(() => runDemo(), 500);
  } else {
    demoTimer = setTimeout(() => {
      if (!tokenInput.value) runDemo();
    }, 5000);
  }

  tokenInput.addEventListener('input', () => {
    if (demoTimer) { clearTimeout(demoTimer); demoTimer = null; }
  });

  tokenInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      if (demoTimer) { clearTimeout(demoTimer); demoTimer = null; }
      const val = tokenInput.value.trim();
      if (val.length >= 10) {
        inputArea.classList.add('hidden');
        addLine('<span class="prompt">$ </span>' + val);
        runPipeline(val);
      }
    }
  });
}

async function runDemo() {
  inputArea.classList.add('hidden');
  const line = addLine('<span class="prompt">$ </span>');
  for (let i = 0; i < DEMO_TOKEN.length; i++) {
    line.innerHTML += DEMO_TOKEN[i];
    await sleep(12);
  }
  await sleep(400);
  runPipeline(DEMO_TOKEN);
}

async function runPipeline(token) {
  addLine('');
  addLine('<span class="d">Select chain [solana]: </span><span class="w">solana</span>');
  addLine('');
  await sleep(800);
  addLine('<span class="g">Initializing pipeline...</span>');
  addLine('');

  // POST to /run in background
  const formData = new FormData();
  formData.append('token', token);
  formData.append('chain', 'solana');
  const reportPromise = fetch('/run', {
    method: 'POST', body: formData, redirect: 'follow'
  }).then(r => r.url).catch(() => '/sample');

  // Hacker typewriter: type out each step character by character
  async function hackerType(el, text, baseDelay) {
    // Create a cursor element that follows the text
    const cur = document.createElement('span');
    cur.className = 'typing-cursor';
    el.appendChild(cur);
    let buf = '';
    for (let i = 0; i < text.length; i++) {
      // Skip HTML tags instantly
      if (text[i] === '<') {
        const close = text.indexOf('>', i);
        if (close !== -1) { buf += text.substring(i, close + 1); i = close; continue; }
      }
      buf += text[i];
      // Update text before cursor
      while (el.lastChild !== cur && el.lastChild) el.removeChild(el.lastChild);
      if (el.firstChild === cur) { el.insertBefore(document.createRange().createContextualFragment(buf), cur); }
      else { cur.insertAdjacentHTML('beforebegin', ''); el.innerHTML = ''; el.insertAdjacentHTML('beforeend', buf); el.appendChild(cur); }
      // Random delay: mostly fast, occasional micro-pause
      const r = Math.random();
      const delay = r < 0.15 ? baseDelay * 3 : r < 0.4 ? baseDelay * 1.5 : baseDelay;
      await sleep(delay);
    }
    // Remove cursor when done
    if (cur.parentNode) cur.remove();
  }

  for (let i = 0; i < STEPS.length; i++) {
    const [name, snippet] = STEPS[i];
    const num = String(i + 1).padStart(2, ' ');

    // Show spinner line first
    const stepLine = addLine(
      '<span class="d">[' + num + '/15]</span> <span class="spinner"></span> <span class="d">' + name + '</span>'
    );
    await sleep(500);

    // Replace with completed line, typed out hacker-style
    stepLine.innerHTML = '';
    const fullText = '<span class="d">[' + num + '/15]</span> <span class="g">\u2713</span> <span class="w">' + name + '</span>  <span class="d">' + snippet + '</span>';
    await hackerType(stepLine, fullText, 8);
    stepLine.scrollIntoView({ behavior: 'smooth', block: 'end' });

    // Brief "thinking" pause between steps
    if (i < STEPS.length - 1) {
      const thinkLine = addLine('<span class="typing-cursor"></span>');
      await sleep(300 + Math.random() * 200);
      thinkLine.remove();
    }
  }

  addLine('');
  addLine('<span class="g">\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550</span>');
  addLine('<span class="w">  \u2705 REPORT READY</span>');
  addLine('<span class="d">  Token:</span> <span class="w">PUMP</span> <span class="d">|</span> <span class="d">Verdict:</span> <span class="g">BULLISH</span>');
  addLine('<span class="d">  Smart Money Conviction:</span> <span class="y">60/100</span>');
  addLine('<span class="d">  API Calls: 15 | Cost: ~$0.45</span>');
  addLine('<span class="g">\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550</span>');
  addLine('');

  // Store report URL, show button
  const reportUrl = await reportPromise;
  const btnLine = addLine('');
  const btn = document.createElement('a');
  btn.href = reportUrl;
  btn.className = 'report-btn';
  btn.textContent = '[ View Full Report \u2192 ]';
  btnLine.appendChild(btn);
  btn.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

// Boot
(async () => {
  await showBanner();
  await showPrompt();
})();

// Click anywhere focuses input
document.querySelector('.terminal').addEventListener('click', () => {
  if (!inputArea.classList.contains('hidden')) tokenInput.focus();
});
</script>
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
