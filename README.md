# NANSEN CLI - Token Due Diligence Engine

🔴 **Live Demo: [https://vchrl.github.io/token-dd/](https://vchrl.github.io/token-dd/)**

> One command. 15+ Nansen API calls. A full token due diligence report that would take an analyst 4 hours.

**Live tool built with [Nansen CLI](https://agents.nansen.ai) for the #NansenCLI challenge.**

## What It Does

Feed it a token address. It runs a full-stack due diligence pipeline using the Nansen CLI and produces a professional-grade investment research report.

The kind of analysis a $200/hr Fractional Head of Data would deliver. Automated.

### The Pipeline (15+ API calls per report)

```
Token Address
    │
    ├── 1. Token Screener ──────────── Market overview, price, volume, liquidity
    ├── 2. Smart Money Netflow ─────── SM accumulation/distribution across timeframes
    ├── 3. SM Holdings ─────────────── What SM wallets are holding chain-wide
    ├── 4. SM DEX Trades ───────────── Recent SM trading activity
    ├── 5. Token Info ──────────────── Basic token metadata
    ├── 6. Flow Intelligence ───────── Breakdown by label: whales, exchanges, fresh wallets
    ├── 7. Who Bought/Sold ─────────── Top buyers and sellers with volumes
    ├── 8. Nansen Score ────────────── Risk/reward indicators
    ├── 9. Holder Analysis ─────────── Top holders and concentration
    ├── 10. PnL Leaderboard ────────── Who's making money on this token
    ├── 11. DEX Trades ─────────────── Recent DEX activity
    ├── 12. Token Flows ────────────── Flow metrics
    ├── 13. OHLCV ──────────────────── Price candles
    ├── 14. Profiler: Balance ──────── Deep dive on top buyer's portfolio
    └── 15. Profiler: Counterparties ─ Who the top buyer is transacting with
         │
         ▼
    Interactive HTML Due Diligence Report
```

### The Report

Not a data dump. A structured analysis with:

- **Executive Summary** - Price, market cap, volume, liquidity, token age
- **Smart Money Conviction Score** - Scored 0-100 across 4 timeframes
- **Flow Intelligence** - Who's moving tokens: whales, smart traders, exchanges, fresh wallets
- **Top Buyers & Sellers** - Named entities with volumes
- **Risk Assessment** - Automated red flags (age, liquidity, dilution, SM count)
- **Holder Analysis** - Concentration and whale exposure
- **PnL Leaderboard** - Who's winning and losing
- **Wallet Forensics** - Deep dive on the #1 buyer's full portfolio
- **Cross-Chain Context** - What SM is holding across the chain
- **Verdict** - Bullish / Neutral / Bearish with reasoning

## Quick Start

```bash
# Install Nansen CLI
npm install -g nansen-cli

# Authenticate
nansen login --api-key YOUR_KEY

# Run due diligence on a token
python3 due_diligence.py <token_address> --chain <chain>

# Examples
python3 due_diligence.py So11111111111111111111111111111111111111112 --chain solana
python3 due_diligence.py 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 --chain ethereum
```

### Scan Mode: Cross-Chain Discovery

Don't know what to research? Scan mode discovers opportunities for you.

```bash
# Scan 5 chains, run DD on top 3 signals
python3 due_diligence.py --scan --top 3

# Scan specific chains
python3 due_diligence.py --scan --chains ethereum,solana,base,arbitrum
```

Scan mode:
1. Pulls Smart Money netflows across multiple chains
2. Cross-references with token screener data
3. Scores each token on a **Convergence Index** (SM accumulation + price divergence)
4. Runs full Due Diligence on the top-ranked signals

## x402 Micropayments

No API credits? No problem. This tool works with [x402](https://x402.org) micropayments:

```bash
# Create a wallet
nansen wallet create

# Fund with USDC on Base (as little as $2)
# Send to the EVM address shown

# API calls are paid per-request ($0.01-$0.05 each)
# Full report costs ~$0.30
```

This is how the future of API access works. No subscriptions. No credit packs. Pay exactly for what you use.

## Supported Chains

All 18 chains supported by Nansen CLI:

`ethereum` `solana` `base` `bnb` `arbitrum` `polygon` `optimism` `avalanche` `linea` `scroll` `mantle` `ronin` `sei` `plasma` `sonic` `monad` `hyperevm` `iotaevm`

## Architecture

```
┌─────────────────────────────────────────────┐
│          Token Due Diligence Engine       │
├─────────────────────────────────────────────┤
│                                             │
│  CLI Arguments                              │
│       │                                     │
│       ▼                                     │
│  ┌─────────────┐    ┌──────────────────┐   │
│  │ Scan Mode   │    │ Single Token DD  │   │
│  │             │    │                  │   │
│  │ • Screener  │    │ • 15+ endpoints  │   │
│  │ • SM Flows  │    │ • 4 phases       │   │
│  │ • Scoring   │    │ • Auto-scoring   │   │
│  │ • Ranking   │    │ • Risk flags     │   │
│  └──────┬──────┘    └────────┬─────────┘   │
│         │                    │              │
│         ▼                    ▼              │
│  ┌──────────────────────────────────────┐   │
│  │         Nansen CLI (nansen-cli)      │   │
│  │  • Structured JSON output            │   │
│  │  • x402 micropayments               │   │
│  │  • 18 chains supported              │   │
│  └──────────────────────────────────────┘   │
│         │                                   │
│         ▼                                   │
│  ┌──────────────────────────────────────┐   │
│  │      HTML Report Generator            │   │
│  │  • Professional DD format            │   │
│  │  • Automated risk scoring            │   │
│  │  • SM conviction analysis            │   │
│  │  • Saved to reports/                 │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## Sample Output

See the `reports/` directory for real analysis outputs.

## The Cost

| Item | Cost |
|------|------|
| This tool | **Free** (open source) |
| Nansen CLI | **Free** to install |
| Single DD report | **~$0.30** via x402 |
| Full cross-chain scan | **~$1.50** via x402 |
| Python 3.9+ | **Free** |

No subscriptions. No lock-in. Pay per insight.

## Who Built This

Built by **[Vincent Charles](https://linkedin.com/in/vincentcfr/)** - Fractional Head of Data for Web3 projects. Previously Senior BI/Data Lead at Binance and Morpho Labs.

## Why This Exists

At Binance, this type of due diligence report took a team of analysts 4+ hours per token. It involved pulling data from multiple sources, cross-referencing wallet labels, checking smart money flows, and synthesizing everything into actionable insights.

Now it takes one command and 30 seconds.

Nansen CLI + x402 micropayments make this possible. No API key management. No credit packs. Just pay for what you use and get institutional-grade research.

This is what the future of onchain analytics looks like.

---

*Built for the [#NansenCLI](https://twitter.com/search?q=%23NansenCLI) challenge | [@nansen_ai](https://twitter.com/nansen_ai)*

*Not financial advice. For educational and research purposes only.*
