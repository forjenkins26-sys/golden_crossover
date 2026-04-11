# Railway Deployment Checklist

## ✅ Pre-Deployment Status

All code and configuration is ready for Railway deployment!

### Completed Tasks:
- ✅ Google Sheets integration implemented in rsi_hybrid_bot.py
- ✅ Real-time trade logging (Trade_Log tab)
- ✅ Daily summary automation (Daily_Summary tab at midnight)
- ✅ 6-hourly heartbeat messages to Telegram
- ✅ All credentials moved to environment variables
- ✅ requirements.txt updated with Google libraries
- ✅ .gitignore configured to exclude credentials
- ✅ Code pushed to GitHub (no secrets committed)
- ✅ google_credentials.json kept locally (NOT in git)
- ✅ RAILWAY_ENV_VARIABLES.md guide created

**GitHub Repo:** https://github.com/forjenkins26-sys/golden_crossover

---

## 🚀 Railway Deployment Steps (Ready Now)

### Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub account (use your existing account)
3. Grant permission to access your repositories

### Step 2: Create New Project from GitHub
1. Click **"New Project"** button
2. Select **"Deploy from GitHub repo"**
3. Find and select: **forjenkins26-sys/golden_crossover**
4. Click **"Deploy"**
5. Railway will auto-detect Python and read `Procfile`
6. Deployment starts automatically (takes ~2 minutes)

### Step 3: Add Environment Variables
1. In Railway Dashboard, click your **golden_crossover** project
2. Click the **deployed service** (should say "Deployed")
3. Click **"Variables"** tab
4. Add these 8 variables (copy from RAILWAY_ENV_VARIABLES.md):

| Variable | Value | Source |
|----------|-------|--------|
| `DEMO_API_KEY` | Your testnet API key | testnet.delta.exchange |
| `DEMO_API_SECRET` | Your testnet API secret | testnet.delta.exchange |
| `GOOGLE_SHEET_ID` | 19wsprhcwixtlGkZNxan5_bwzr0QQfHFoCTietqrp0bQ | Your Google Sheet URL |
| `TELEGRAM_BOT_TOKEN` | Your token | @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID | @BotFather |
| `CAPITAL` | 200 | Account capital in USD |
| `RISK_PERCENT` | 0.10 | Risk per trade (0.10 = 10%) |
| `LEVERAGE` | 10 | Leverage multiplier |

**To add a variable:**
1. Click "+ New Variable"
2. Enter **Key** (upper part) = variable name
3. Enter **Value** (lower part) = your actual value
4. Click checkmark to save
5. Repeat for all 8 variables

### Step 4: Upload Google Credentials
Since `google_credentials.json` contains sensitive data, upload it securely:

**Option A: As Railway Secret (Recommended)**
1. Click **"Secrets"** tab (next to Variables)
2. Click **"New Secret"**
3. Key: `GOOGLE_CREDENTIALS`
4. Value: Copy entire contents of your `google_credentials.json` file
5. Paste as plain text
6. Click checkmark to save

**Option B: As File in Railway Editor**
1. Click **"Editor"** tab in Railway
2. Create new file: `google_credentials.json`
3. Paste entire contents from your local file
4. Set `GOOGLE_CREDENTIALS_PATH=google_credentials.json` in Variables

**⚠️ Important:** After adding variables/secrets, Railway will **automatically redeploy** your bot.

---

## ✅ Verification After Deployment

### Check 1: Bot Started Successfully
1. In Railway Dashboard, click your project
2. Click the service, then **"Logs"** tab
3. Look for these messages:
   ```
   [BOT] RSI Hybrid Bot Started
   [MARKET DATA] BTC Price: $XX,XXX
   [ACCOUNT] Available Balance: $XXX
   [SIGNAL] Checking for new signals...
   ```
   ✅ If you see these → Bot is running!

### Check 2: Telegram Notifications
1. Open Telegram and find your chat with the bot
2. You should receive:
   - ✅ **Startup message** (immediately): "Bot connected to Delta Exchange"
   - ✅ **6-hourly alive message** (within 6 hours): "[ALIVE] Bot is running... BTC: $XX,XXX"

### Check 3: Google Sheets Logging
1. Open your Google Sheet: `RSI_Hybrid_Journal`
2. Click **"Trade_Log"** tab
3. Check if columns are populated:
   - Date, Time, Direction, Entry Price, Exit Price, Result, Gross PnL, Fees, Net PnL, Cumulative PnL, Notes
4. **When a trade closes**, a new row appears here automatically
5. At midnight (UTC), check **"Daily_Summary"** tab for that day's stats

---

## 🧪 Testing Before Full Deployment

**Want to test locally first?**

1. Create `.env` file in d:\golden_crossover:
   ```
   DEMO_API_KEY=your_key_here
   DEMO_API_SECRET=your_secret_here
   GOOGLE_SHEET_ID=19wsprhcwixtlGkZNxan5_bwzr0QQfHFoCTietqrp0bQ
   GOOGLE_CREDENTIALS_PATH=google_credentials.json
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   CAPITAL=200
   RISK_PERCENT=0.10
   LEVERAGE=10
   ```

2. Ensure `google_credentials.json` exists in d:\golden_crossover

3. Run locally:
   ```powershell
   cd d:\golden_crossover
   python rsi_hybrid_bot.py
   ```

4. Check console output and Telegram messages

5. If local test works → Deploy to Railway with same values

---

## 🔒 Security Reminders

✅ **What's protected in this setup:**
- ✅ `google_credentials.json` NOT in git (in .gitignore)
- ✅ `.env` NOT in git (in .gitignore)  
- ✅ All credentials stored in Railway Variables/Secrets (encrypted)
- ✅ GitHub repo has no secrets exposed

⚠️ **What you should do:**
- ✅ Keep `google_credentials.json` locally (don't upload to GitHub)
- ✅ Never share your `.env` file
- ✅ Use strong passwords for Railway account
- ✅ Don't commit credentials even by accident

---

## 🆘 Troubleshooting

### Bot doesn't start (Logs show errors)
**Check:**
- [ ] Are all 8 environment variables set in Railway?
- [ ] Is bot token correct?
- [ ] Is API key/secret correct?
- [ ] Is GOOGLE_SHEET_ID correct?
- [ ] Are credentials uploaded? (`GOOGLE_CREDENTIALS`)

### Trades not appearing in Google Sheets
**Check:**
- [ ] Is GOOGLE_SHEET_ID correct in Variables?
- [ ] Is google_credentials.json uploaded/readable?
- [ ] Is service account email shared with the sheet?
- [ ] Run test locally first to verify

### Telegram messages not arriving
**Check:**
- [ ] Is TELEGRAM_BOT_TOKEN correct?
- [ ] Is TELEGRAM_CHAT_ID correct?
- [ ] Test bot locally with `python rsi_hybrid_bot.py`
- [ ] Send message to @YourBotName to wake up the bot

### "Insufficient Balance" errors
**Fix:**
- [ ] Increase `CAPITAL` to 500+ in Variables
- [ ] Decrease `LEVERAGE` from 10 to 5
- [ ] Check actual balance in testnet.delta.exchange

### Need full Railway documentation?
Visit: https://docs.railway.app

---

## 📊 What Happens When Bot Runs?

**Every Hour (at :00 minute):**
- Check RSI and EMA values
- If signal detected → Place 3 orders (entry + TP + SL)
- Monitor position for close

**When Position Closes (TP or SL hit):**
- Calculate profit/loss
- Append row to Google Sheets "Trade_Log" tab
- Update cumulative PnL
- Send Telegram notification
- Continue trading

**Every 6 Hours:**
- Send "Bot is alive" message to Telegram with:
  - Current BTC price
  - Bot status
  - Timestamp

**Every Day at Midnight (UTC+0):**
- Calculate daily stats: total trades, wins, losses, win rate, daily PnL
- Write summary to Google Sheets "Daily_Summary" tab
- Reset daily counter for next day
- If no trades that day, write "No Trade Today"

**All Data:**
- Visible in Google Sheets in real-time
- Accessible from any device via Google Sheets app
- Automatically backed up by Google

---

## 🎯 Next Actions

1. **Go to Railway.app** and deploy from GitHub
2. **Add all 8 environment variables** in Railway Dashboard
3. **Upload google_credentials.json** as secret
4. **Wait for deployment** (~2-3 minutes)
5. **Check logs** for startup messages
6. **Check Telegram** for "Bot connected" message
7. **Open Google Sheets** and monitor Trade_Log tab
8. **Verify trades** appear within 1 hour as they happen

**Status:** 🟢 Ready for 24/7 automated trading! 🚀

---

## 📞 Support

If you encounter issues:

1. **Check Railway Logs:** First stop for debugging
2. **Test Locally:** Run `python rsi_hybrid_bot.py` before Railway
3. **Review This Checklist:** Most issues covered in Troubleshooting section
4. **Check RAILWAY_ENV_VARIABLES.md:** Detailed variable guide
5. **Review config.py:** Shows how variables are read

**Good luck! Your bot is ready to trade 24/7.** 🎯
