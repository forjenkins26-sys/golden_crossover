# Railway Environment Variables Setup

## Complete List of Environment Variables for Railway Dashboard

Copy and paste these into your Railway project's **Variables** tab. Replace the placeholder values with your actual credentials.

---

## 🔐 API Credentials (Delta Exchange)

```
DEMO_API_KEY=aMpcVoWFDJNpGGb2QYJKp2ZrljalU4
```
- **Value:** Your Delta Exchange testnet API key
- **From:** testnet.delta.exchange → Settings → API Keys

```
DEMO_API_SECRET=ypj0WNDEOaQ4WNyx4fLidxde0Ba0Uo4iKI5HYes7Q46XtkPSDs1Wami1zDIH
```
- **Value:** Your Delta Exchange testnet API secret
- **From:** testnet.delta.exchange → Settings → API Keys
- **⚠️ KEEP PRIVATE:** Never share this publicly

---

## 📊 Google Sheets Configuration

```
GOOGLE_SHEET_ID=19wsprhcwixtlGkZNxan5_bwzr0QQfHFoCTietqrp0bQ
```
- **Value:** Your Google Sheet ID
- **From:** URL of your `RSI_Hybrid_Journal` sheet
  - URL format: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
  - Copy the `SHEET_ID_HERE` part

```
GOOGLE_CREDENTIALS_PATH=google_credentials.json
```
- **Value:** `google_credentials.json` (leave as is)
- **File:** Upload `google_credentials.json` to Railway as a file secret

---

## 💬 Telegram Notifications

```
TELEGRAM_BOT_TOKEN=8765740344:AAGXil8M89EMg5W1qCT5EQojspizltahkv4
```
- **Value:** Your Telegram bot token
- **From:** @BotFather on Telegram

```
TELEGRAM_CHAT_ID=757555299
```
- **Value:** Your personal Telegram chat ID
- **How to find:**
  1. Send a message to your bot
  2. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` (replace TOKEN)
  3. Look for `"chat":{"id":YOUR_ID}`

---

## 💰 Trading Parameters

```
CAPITAL=200
```
- **Value:** Your account capital in USD
- **Example:** `200` = $200 account
- **Range:** Any positive number (recommended: 100-1000)

```
RISK_PERCENT=0.10
```
- **Value:** Risk per trade as decimal (10% = 0.10)
- **Example:** `0.10` = Risk 10% of your capital per trade
- **Recommended:** `0.05` to `0.20` (5-20%)

```
LEVERAGE=10
```
- **Value:** Leverage multiplier
- **Example:** `10` = 10x leverage (buying power = capital × 10)
- **Warning:** Higher leverage = higher risk

---

## 📋 How to Add Variables in Railway Dashboard

1. **Go to Railway:** https://railway.app/dashboard
2. **Select your project:** `golden_crossover`
3. **Click the deployed service**
4. **Click "Variables" tab**
5. **Click "+ New Variable"**
6. **Enter each variable:**
   - **Key:** Variable name (e.g., `DEMO_API_KEY`)
   - **Value:** Your actual value
7. **Click checkmark** to save
8. **Repeat for all variables above**
9. **If Railway asks to redeploy:** Click "Redeploy"

---

## 🔒 Handling google_credentials.json on Railway

Since `google_credentials.json` contains sensitive credentials, you have two options:

### **Option 1: Upload as Railway File Secret (Recommended)**
1. In Railway Dashboard → Select your service
2. Click **"Secrets"** tab (not Variables)
3. Click **"New Secret"**
4. **Key:** `GOOGLE_CREDENTIALS`
5. **Value:** Paste entire contents of your `google_credentials.json` file as plain text
6. In config.py, this will be read as an environment variable

### **Option 2: Use Base64 Encoding**
1. Convert `google_credentials.json` to base64:
   ```bash
   # On Windows PowerShell:
   [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("google_credentials.json")) | Set-Clipboard
   ```
2. In Railway → Variables → Add `GOOGLE_CREDENTIALS_BASE64`
3. Paste the base64 string
4. Bot will automatically decode it

### **Option 3: Don't Upload Credentials (Not Recommended)**
- Keep `GOOGLE_CREDENTIALS_PATH=google_credentials.json`
- Upload the actual file via Railway's file system
- Risk: Credentials could be accidentally exposed

---

## ✅ Verification Checklist

Before deploying on Railway, verify:

- [ ] `DEMO_API_KEY` is set and correct
- [ ] `DEMO_API_SECRET` is set and correct (keep private!)
- [ ] `GOOGLE_SHEET_ID` matches your Google Sheet
- [ ] `GOOGLE_CREDENTIALS_PATH` or credentials uploaded
- [ ] `TELEGRAM_BOT_TOKEN` is set
- [ ] `TELEGRAM_CHAT_ID` is set
- [ ] `CAPITAL`, `RISK_PERCENT`, `LEVERAGE` are set
- [ ] All values have NO trailing spaces

---

## 🧪 Testing Environment Variables

After adding all variables, Railway will show them in **Variables** tab. 

To test if they're loaded correctly:
1. Check Railway **Logs** tab
2. Look for startup message:
   ```
   [BOT] RSI Hybrid Bot Started
   [MARKET DATA] BTC Price: $XX,XXX
   [ACCOUNT] Available Balance: $XXX
   ```
3. If you see prices → Variables are loaded correctly ✅

---

## 📌 Important Notes

1. **Never commit credentials to GitHub** - Use `.env.example` as template
2. **Environment variables override .env** - Railway variables take precedence
3. **Redeploy required** - After changing variables, Railway redeploys automatically
4. **Check logs** - If bot doesn't start, look at Railway logs for error messages
5. **Test locally first** - Copy variables to `.env` file and test with `python rsi_hybrid_bot.py`

---

## 🚀 Deployment Steps

1. **Fork/clone repository** from GitHub
2. **Deploy on Railway** from GitHub
3. **Add ALL variables above** in Railway Dashboard
4. **Upload credentials** (google_credentials.json)
5. **Verify in logs** that bot started successfully
6. **Check Telegram** for startup message
7. **Monitor trade logging** in Google Sheets

**After this, your bot runs 24/7 on Railway!** 🎯

---

## ❓ Troubleshooting

**Bot doesn't start?**
- Check Rails logs for error messages
- Verify all variables are set (no missing keys)
- Ensure API credentials are correct

**Google Sheets not logging trades?**
- Verify `GOOGLE_SHEET_ID` is correct
- Verify credentials file is uploaded
- Check that sheet is shared with service account email

**Telegram alerts not working?**
- Verify bot token is correct
- Verify chat ID is correct
- Test bot in Telegram first: send message to @YourBotName

**"Insufficient balance" error?**
- Set higher `CAPITAL` value
- Reduce `LEVERAGE` value
- Check testnet account has funds

---

**Need help?** Check Railway docs: https://docs.railway.app
