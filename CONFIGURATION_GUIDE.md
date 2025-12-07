# ContextCatcher Configuration Guide

## Lookback Period Configuration

You can now configure the lookback period in either **hours** or **minutes**!

### Option 1: Use Hours (Default)

```json
{
  "fetch": {
    "lookback_hours": 24,
    "lookback_minutes": null
  }
}
```

This will fetch emails from the last 24 hours.

### Option 2: Use Minutes (More Precise)

```json
{
  "fetch": {
    "lookback_hours": 24,
    "lookback_minutes": 30
  }
}
```

This will fetch emails from the last **30 minutes** (lookback_minutes takes priority).

### Examples

**Last 5 minutes:**
```json
"lookback_minutes": 5
```

**Last 15 minutes:**
```json
"lookback_minutes": 15
```

**Last 1 hour:**
```json
"lookback_minutes": 60
```

**Last 2 hours:**
```json
"lookback_hours": 2,
"lookback_minutes": null
```

**Last 7 days:**
```json
"lookback_hours": 168,
"lookback_minutes": null
```

## How It Works

- If `lookback_minutes` is set (not null), it will be used instead of `lookback_hours`
- If `lookback_minutes` is null, `lookback_hours` will be used
- The system converts minutes to hours internally (e.g., 30 minutes = 0.5 hours)

## Quick Test

To test with just the last 5 minutes of emails:

1. Edit `config.json`:
```json
{
  "fetch": {
    "lookback_hours": 24,
    "lookback_minutes": 5,
    ...
  }
}
```

2. Restart the backend (it will auto-reload)

3. Click "Fetch Now" in the UI

4. You'll only see emails from the last 5 minutes!

## Tips

- **For testing:** Use minutes (5, 10, 15) to quickly test with recent emails
- **For production:** Use hours (24, 48, 168) for broader coverage
- **For real-time monitoring:** Use 5-15 minutes and fetch frequently
- **For initial setup:** Use 168 hours (7 days) to get a good sample

## Environment Variable Support

You can also set this via environment variables:

```bash
export LOOKBACK_HOURS=24
export LOOKBACK_MINUTES=30
```

The environment variable will override the config file value.


---

## Primary Inbox Only (Gmail)

You can now configure ContextCatcher to **only fetch emails from your primary inbox**, excluding:
- Promotions
- Social
- Updates
- Forums

### Configuration

```json
{
  "fetch": {
    "primary_only": true
  }
}
```

### How It Works

When `primary_only` is set to `true`:
- **Gmail users:** Excludes emails in Promotions, Social, Updates, and Forums tabs
- **Other email providers:** Fetches from INBOX (no filtering)

### Examples

**Primary inbox only:**
```json
{
  "fetch": {
    "lookback_minutes": 5,
    "primary_only": true
  }
}
```

**All emails (default):**
```json
{
  "fetch": {
    "lookback_minutes": 5,
    "primary_only": false
  }
}
```

### Use Cases

- **Focus on important emails:** Skip promotional and social emails
- **Reduce noise:** Only see emails that matter
- **Faster fetching:** Fewer emails to process
- **Better summaries:** AI focuses on primary communications

### Note

This feature uses Gmail's X-GM-LABELS extension. If you're using a non-Gmail IMAP server, setting `primary_only: true` will still work but won't filter categories (it will just fetch from INBOX).


---

## Arrival Date vs Sent Date

### The Problem

By default, IMAP's `SINCE` command uses the **sent date** (when the email was sent), not the **arrival date** (when it arrived in your inbox). This means:

- An email sent 2 days ago but arriving today won't show up with `lookback_minutes: 5`
- You might get old emails that were just sent recently

### The Solution: Use Arrival Date

```json
{
  "fetch": {
    "lookback_minutes": 5,
    "use_arrival_date": true    // ← Use when email arrived, not when sent!
  }
}
```

### Comparison

**Sent Date (use_arrival_date: false):**
- Filters by when the email was **sent**
- Faster (uses IMAP SINCE command)
- May include old emails that were sent recently
- May miss recent emails that were sent earlier

**Arrival Date (use_arrival_date: true - RECOMMENDED):**
- Filters by when the email **arrived in your inbox**
- More accurate for "recent emails"
- Slightly slower (checks each message's INTERNALDATE)
- Shows exactly what you see in your inbox

### Recommended Settings

**For real-time monitoring:**
```json
{
  "lookback_minutes": 5,
  "primary_only": true,
  "use_arrival_date": true
}
```

This gives you emails that:
- Arrived in the last 5 minutes ✓
- Are in your primary inbox ✓
- Match what you see in Gmail ✓

### Performance Note

- `use_arrival_date: true` is slightly slower because it checks each message individually
- For large mailboxes, consider using `primary_only: true` to reduce the number of messages to check
- The performance difference is negligible for recent time windows (< 1 hour)


---

## LLM-Powered Summaries

ContextCatcher can use AI (OpenAI GPT) to generate intelligent summaries and extract action items from your emails.

### Configuration

```json
{
  "llm": {
    "enabled": true,
    "provider": "openai",
    "api_key": "sk-your-api-key-here",
    "model": "gpt-3.5-turbo"
  }
}
```

### Getting an OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add it to your `config.json`

### Models

**Recommended models:**
- `gpt-3.5-turbo` - Fast and affordable ($0.002 per 1K tokens)
- `gpt-4` - More accurate but slower and more expensive ($0.03 per 1K tokens)
- `gpt-4-turbo` - Good balance of speed and quality

### What You Get with LLM

**Better Summaries:**
- Organized by topics and themes
- Clear, concise language
- Highlights important information
- Identifies urgent matters

**Better Task Extraction:**
- Finds explicit requests ("please do X")
- Identifies implicit tasks ("we need to", "should")
- Extracts deadlines and time-sensitive items
- Identifies questions that need answers
- Shows evidence snippets from emails

### Example Output

**Without LLM (Heuristic):**
```
Summary of 5 messages:
Date range: 2024-12-05 to 2024-12-05
Participants: 3 unique senders

Top topics:
  - Meeting (mentioned 4 times)
  - Report (mentioned 3 times)
```

**With LLM:**
```
Key Topics:
• Team meeting scheduled for Friday at 2pm
• Q4 report needs review by end of week
• New project proposal requires feedback

Action Items:
1. Review Q4 report (Due: Friday)
   Evidence: "Please review the attached Q4 report by EOD Friday"
2. Provide feedback on project proposal
   Evidence: "We need your input on the new initiative"
```

### Fallback Behavior

If LLM is enabled but fails (API error, rate limit, etc.), the system automatically falls back to the heuristic summarizer.

### Cost Estimation

For typical usage:
- 10 emails with 500 chars each ≈ 2,000 tokens
- Using gpt-3.5-turbo: ~$0.004 per summary
- 100 summaries per day: ~$0.40/day or $12/month

### Recommended Settings

**For best results:**
```json
{
  "fetch": {
    "lookback_minutes": 5,
    "primary_only": true,
    "use_arrival_date": true
  },
  "llm": {
    "enabled": true,
    "provider": "openai",
    "api_key": "sk-your-key-here",
    "model": "gpt-3.5-turbo"
  }
}
```

### Without LLM

If you don't want to use LLM:
```json
{
  "llm": {
    "enabled": false
  }
}
```

The heuristic summarizer will still extract tasks using pattern matching for common phrases like "please", "need to", "must", "should", etc.
