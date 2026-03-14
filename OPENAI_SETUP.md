# OpenAI Setup

This document explains how to configure OpenAI to improve the chatbot's natural language understanding.

## 🔑 How to Get an OpenAI Token

### Step 1: Create an OpenAI Account

1. Go to [https://platform.openai.com/](https://platform.openai.com/)
2. Click **"Sign up"**
3. Complete registration with your email or Google/Microsoft account

### Step 2: Add a Payment Method

1. Once registered, go to **"Settings"** → **"Billing"**
2. Add a payment method (credit card)
3. OpenAI requires a payment method to use the API (even though there are initial free credits)

### Step 3: Generate an API Key

1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **"Create new secret key"**
3. Give it a descriptive name (e.g., "ContaBot")
4. **IMPORTANT**: Copy the key immediately; it is shown only once
5. Save the key securely

### Step 4: Configure It in the Bot

You have two options:

#### Option A: Environment Variable (Recommended)

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"

# Windows CMD
set OPENAI_API_KEY=your-api-key-here

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
```

#### Option B: config_secret.py File

Add the key to your `config_secret.py` file:

```python
TOKEN = "your_telegram_token"
ADMIN_USER_IDS = [123456789]

# OpenAI Configuration
OPENAI_API_KEY = "sk-proj-..."  # Your API key here
```

And update `core/config.py` to read it:

```python
# It is already in config_secret.py; you only need to add it there
```

## 💰 OpenAI Costs

- **Model used**: `gpt-4o-mini` (the most economical)
- **Approximate cost**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **Typical usage**: Each user message consumes ~200-500 tokens
- **Estimate**: ~2000-5000 messages per $1 USD

### Free Credits

OpenAI usually offers initial free credits ($5-18 USD) for new users, enough to test the system.

## ✅ Verify It Works

1. Start the bot: `python bot.py`
2. You should see in logs: `"🤖 OpenAI enabled - Using advanced AI..."`
3. Test by writing: "Hello, how much money is in the cash boxes?"
4. The bot should respond correctly

## 🔄 Automatic Fallback

If OpenAI is not configured or fails, the system automatically uses the **basic rule-based parser**, which also works well for most cases.

## 🛡️ Security

- **NEVER** share your API key
- **NEVER** upload it to public repositories
- Use environment variables or `.gitignore`-protected files
- If a key is compromised, revoke it immediately in OpenAI

## 📊 Usage Monitoring

You can monitor usage at:
- [https://platform.openai.com/usage](https://platform.openai.com/usage)

There you can see how many tokens you have used and how much you have spent.

## 🚨 Limits and Rate Limits

OpenAI has rate limits (request speed). If the bot receives many simultaneous messages, delays may occur. The system handles this automatically with the rules fallback.

## 💡 Tips

- The `gpt-4o-mini` model is fast and cost-effective, perfect for this use case
- If you need higher accuracy, you can switch to `gpt-4o` in `ai/openai_service.py`
- Costs are very low for normal usage (cents per day)

