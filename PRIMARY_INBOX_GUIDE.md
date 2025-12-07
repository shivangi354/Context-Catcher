# Primary Inbox Only - Quick Guide

## ✅ Feature Added!

ContextCatcher can now filter to **only your primary inbox**, excluding:
- 📢 Promotions
- 👥 Social
- 📰 Updates  
- 💬 Forums

---

## 🚀 How to Enable

Edit your `config.json`:

```json
{
  "fetch": {
    "lookback_minutes": 5,
    "primary_only": true    // ← Set this to true!
  }
}
```

Save the file and the backend will auto-reload!

---

## 📊 What You'll See

**In the UI Config Section:**
```
Email: shi***@gmail.com
Lookback: 5 minutes
Filter: Primary inbox only ✓
```

**When Fetching:**
- Backend logs will show: "Filtering for primary inbox only"
- Only emails from your primary tab will be fetched
- Promotions, social, etc. will be skipped

---

## 🎯 Use Cases

### 1. Focus Mode
```json
{
  "lookback_minutes": 15,
  "primary_only": true
}
```
Only see important emails from the last 15 minutes.

### 2. Quick Check
```json
{
  "lookback_minutes": 5,
  "primary_only": true
}
```
Check just the last 5 minutes of primary emails.

### 3. All Emails (Default)
```json
{
  "lookback_hours": 24,
  "primary_only": false
}
```
Get everything from the last 24 hours.

---

## 🔍 How It Works

### For Gmail Users:
Uses Gmail's `X-GM-LABELS` to exclude:
- `\\Promotions`
- `\\Social`
- `\\Updates`
- `\\Forums`

### For Other Email Providers:
Just fetches from INBOX (no category filtering available).

---

## ⚡ Quick Test

1. **Edit config.json:**
   ```json
   "primary_only": true
   ```

2. **Refresh UI** (backend auto-reloads)

3. **Click "Fetch Now"**

4. **Check results** - only primary emails!

---

## 💡 Pro Tips

- **Combine with minutes:** `"lookback_minutes": 5, "primary_only": true` for real-time primary email monitoring
- **Better summaries:** AI focuses on important communications
- **Faster fetching:** Fewer emails = faster processing
- **Less noise:** Skip promotional clutter

---

## 🔄 To Disable

Set back to false:
```json
"primary_only": false
```

---

**Status:** ✅ Feature is live and ready to use!
