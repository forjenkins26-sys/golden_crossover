# RSI Hybrid Bot - Automated Trading on Delta Exchange

A fully automated cryptocurrency trading bot using RSI + 200 EMA hybrid strategy on BTCUSD perpetual futures.

## Features

✅ **Automated Trading**
- RSI 30/70 + 200 EMA hybrid filter
- 1-hour candle analysis
- Dynamic position sizing (capital-risk based)
- 10x leverage on Delta Exchange

✅ **Risk Management**
- 4% take profit per trade
- 1.2% stop loss per trade
- Balance checks before trading
- 0.2% roundtrip commission (included)

✅ **Monitoring & Alerts**
- Telegram notifications for entries/exits/errors
- Excel daily trade logging
- Hourly signal monitoring
- 5-minute position checks

✅ **Infrastructure**
- Runs 24/7 on Railway
- Auto-restart on failure
- Environment variable configuration
- Error handling with retries

---

## Quick Start - Deploy on Railway

### 1. Fork/Clone Repository
```bash
git clone https://github.com/yourusername/golden_crossover.git
```

### 2. Deploy on Railway (One-Click)

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Connect your GitHub account
5. Select `golden_crossover` repository
6. Railway will auto-detect Python project and start deployment

### 3. Set Environment Variables on Railway

In Railway Dashboard:

1. Click on the deployed service
2. Go to **Variables** tab
3. Add these environment variables:

```
DEMO_API_KEY=your_api_key_from_delta_exchange
DEMO_API_SECRET=your_api_secret_from_delta_exchange
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
CAPITAL=200
RISK_PERCENT=0.10
LEVERAGE=10
```

### 4. Enable Persistent Logging

In Railway Dashboard > Settings > Enable "Persistent Volume" (optional, for trading logs)

### 5. Monitor Bot

In Railway Dashboard:
- View **Logs** tab to see live bot output
- View **Deployments** tab for revision history
- Set up alerts for job failures

---

## Local Development

### Prerequisites
```bash
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Fill in your credentials in `.env`
3. Run locally: `python rsi_hybrid_bot.py`

### Environment Variables

```
DEMO_API_KEY        - Delta Exchange testnet API key
DEMO_API_SECRET     - Delta Exchange testnet API secret
TELEGRAM_BOT_TOKEN  - Telegram bot token for alerts
TELEGRAM_CHAT_ID    - Your Telegram chat ID for alerts
CAPITAL             - Account capital in USD (default: 200)
RISK_PERCENT        - Risk per trade as decimal (default: 0.10)
LEVERAGE            - Leverage multiplier (default: 10)
```

---

## Strategy Details

**Entry Conditions:**
- **LONG**: RSI < 30 AND Price > 200 EMA
- **SHORT**: RSI > 70

**Exit Conditions:**
- **TP**: 4% profit (automatic limit order)
- **SL**: 1.2% loss (automatic stop market order)

**Position Sizing:**
```
position_size = (CAPITAL × RISK_PERCENT) / (SL_PERCENT × current_price)
```

With $200 capital at $72,000 BTC:
- Risk per trade: $20
- Position size: ~0.0023 BTC
- Required margin: ~$166 (at 10x leverage)

---

## Files

- `rsi_hybrid_bot.py` - Main trading bot (607 lines)
- `config.py` - Configuration & environment variables
- `Procfile` - Railway deployment config
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variable template
- `start_bot.bat` - Windows launcher (local use)

---

## Monitoring

### Telegram Alerts
Bot sends automatic alerts for:
- Startup confirmation
- Trade entries (side, price, position size)
- Trade exits (P&L, hold time, status)
- Errors (API failures, balance issues)

### Daily Excel Logs
Trading journal saved to: `~/Desktop/RSI_Hybrid_Journal/Daily_Logs/`

### Terminal Logs
View real-time bot output in Railway dashboard:
```
[BOT] RSI Hybrid Bot Started
[STRATEGY] RSI 30/70 + 200 EMA
[MONITOR] Checking signals hourly, monitoring positions every 5 minutes
[2026-04-11 12:09:13] Hour check complete. RSI=49.3 EMA=$67,908 Price=$72,706 Signal=NEUTRAL
```

---

## Backtesting Results

Strategy backtested on 2 years of hourly BTCUSD data (Apr 2024 - Apr 2026):

| Metric | Value |
|--------|-------|
| Total Trades | 357 |
| Wins | 104 (29.1%) |
| Profit Factor | 1.73 |
| Total Profit | $4,804 |
| Best Trade | +8.2% |
| Worst Trade | -2.4% |

---

## FAQ

**Q: Is this real money trading?**
A: No, currently running on Delta Exchange **testnet** with demo account. Switch to live credentials when ready.

**Q: What if the bot crashes?**
A: Railway automatically restarts the job. Check logs in dashboard for issues.

**Q: Can I modify the strategy?**
A: Yes! Edit `config.py` to change RSI periods, EMA period, leverage, capital, etc. Backtest first!

**Q: How much does Railway cost?**
A: Free tier includes 500 hours/month (enough for continuous bot). Paid plans start at $5/month.

**Q: Can I run this locally too?**
A: Yes! Run `python rsi_hybrid_bot.py` on your machine or use `start_bot.bat` on Windows.

---

## Getting Help

1. Check bot logs in Railway dashboard
2. Verify environment variables are set correctly
3. Ensure API credentials are from Delta Exchange testnet
4. Check Telegram bot token is valid

---

## License

Private trading bot - Do not redistribute without permission.

---

**Happy trading! 🚀**
