# ContextCatcher MVP - Deployment Checklist

Use this checklist to deploy ContextCatcher MVP successfully.

## ✅ Pre-Deployment Checklist

### 1. Email Configuration

- [ ] Have Gmail account (or other IMAP email)
- [ ] Created app-specific password for Gmail
  - Go to: https://myaccount.google.com/security
  - Enable 2-Step Verification
  - Generate App Password
- [ ] Verified IMAP is enabled in email settings
- [ ] Tested IMAP credentials manually (optional)

### 2. System Requirements

- [ ] Python 3.10 or higher installed
- [ ] pip/pip3 available
- [ ] (Optional) Docker and Docker Compose installed
- [ ] (Optional) OpenAI API key for AI summaries

### 3. Project Setup

- [ ] Cloned/downloaded the repository
- [ ] Reviewed README.md
- [ ] Checked all files are present

## 🚀 Deployment Options

Choose one of the following deployment methods:

### Option A: Local Development (Recommended for First Time)

#### Step 1: Configuration
```bash
# Copy example config
cp config.example.json config.json

# Edit with your credentials
nano config.json  # or use your preferred editor
```

**Required fields to update:**
- `email.username` - Your email address
- `email.password` - Your app-specific password

**Optional fields:**
- `fetch.lookback_hours` - How far back to fetch (default: 24)
- `llm.enabled` - Enable AI summaries (default: false)
- `llm.api_key` - Your OpenAI API key (if enabled)

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Test Configuration
```bash
# Run demo script to test
python demo_fetch.py
```

#### Step 4: Start Services
```bash
# Option 1: Use quick start script
./start.sh

# Option 2: Manual start
# Terminal 1:
python backend/main.py

# Terminal 2:
streamlit run ui/app.py
```

#### Step 5: Verify
- [ ] Backend running at http://localhost:8000
- [ ] UI running at http://localhost:8501
- [ ] Can access API docs at http://localhost:8000/docs
- [ ] Can click "Fetch Now" in UI
- [ ] Messages appear in UI

### Option B: Docker Deployment

#### Step 1: Configuration
```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required fields:**
- `EMAIL_USERNAME`
- `EMAIL_PASSWORD`

#### Step 2: Build and Run
```bash
docker-compose up --build
```

#### Step 3: Verify
- [ ] Container started successfully
- [ ] Backend accessible at http://localhost:8000
- [ ] UI accessible at http://localhost:8501
- [ ] Can fetch emails

### Option C: Production Deployment

#### Additional Steps for Production:

1. **Security**
   - [ ] Use environment variables instead of config.json
   - [ ] Set up HTTPS reverse proxy (nginx/traefik)
   - [ ] Restrict CORS origins in backend/main.py
   - [ ] Enable firewall rules
   - [ ] Use secrets management (e.g., HashiCorp Vault)

2. **Persistence**
   - [ ] Mount storage volume
   - [ ] Set up backup for storage directory
   - [ ] Configure log rotation

3. **Monitoring**
   - [ ] Set up health check monitoring
   - [ ] Configure alerting
   - [ ] Set up log aggregation

4. **Performance**
   - [ ] Configure appropriate resource limits
   - [ ] Set up load balancing (if needed)
   - [ ] Optimize fetch intervals

## 🧪 Testing Checklist

### Basic Functionality
- [ ] Configuration loads successfully
- [ ] IMAP connection succeeds
- [ ] Messages are fetched
- [ ] Messages are normalized correctly
- [ ] Messages are stored in storage/
- [ ] Deduplication works (fetch twice, no duplicates)
- [ ] API endpoints respond correctly
- [ ] UI displays messages
- [ ] Summary generation works

### API Testing
```bash
# Test status endpoint
curl http://localhost:8000/status

# Test fetch endpoint
curl -X POST http://localhost:8000/fetch

# Test messages endpoint
curl http://localhost:8000/messages?limit=5

# Test summary endpoint
curl http://localhost:8000/summary
```

- [ ] All endpoints return valid JSON
- [ ] No 500 errors
- [ ] Appropriate error messages for invalid requests

### UI Testing
- [ ] Config viewer shows masked email
- [ ] Fetch button works
- [ ] Progress indicator appears during fetch
- [ ] Messages list populates
- [ ] Can click message to view details
- [ ] Summary displays correctly
- [ ] Action items show up
- [ ] Statistics sidebar updates

### Security Testing
- [ ] Password not visible in UI
- [ ] Password not in logs
- [ ] Password not in API responses
- [ ] Config file not accessible via web

## 🔧 Troubleshooting

### Issue: IMAP Connection Fails

**Check:**
- [ ] Email and password are correct
- [ ] Using app-specific password (for Gmail)
- [ ] IMAP is enabled in email settings
- [ ] Network allows IMAP connections (port 993)
- [ ] No firewall blocking

**Solution:**
```bash
# Test IMAP manually
python3 -c "
import imaplib
conn = imaplib.IMAP4_SSL('imap.gmail.com', 993)
conn.login('your-email@gmail.com', 'your-app-password')
print('✅ IMAP connection successful!')
conn.logout()
"
```

### Issue: No Messages Fetched

**Check:**
- [ ] Have emails in inbox within lookback period
- [ ] Lookback hours is appropriate
- [ ] IMAP folder is correct (INBOX)

**Solution:**
Increase lookback_hours in config:
```json
{
  "fetch": {
    "lookback_hours": 168  // 7 days
  }
}
```

### Issue: Dependencies Won't Install

**Check:**
- [ ] Python version is 3.10+
- [ ] pip is up to date

**Solution:**
```bash
# Update pip
python3 -m pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v
```

### Issue: Port Already in Use

**Check:**
- [ ] Port 8000 available (backend)
- [ ] Port 8501 available (UI)

**Solution:**
```bash
# Find process using port
lsof -i :8000
lsof -i :8501

# Kill process or change port
# For backend: uvicorn backend.main:app --port 8001
# For UI: streamlit run ui/app.py --server.port 8502
```

## 📊 Post-Deployment Verification

### Day 1
- [ ] Fetch emails successfully
- [ ] Review normalized messages
- [ ] Check storage directory has files
- [ ] Verify summary generation
- [ ] Monitor logs for errors

### Week 1
- [ ] Check storage size growth
- [ ] Verify deduplication working
- [ ] Review action items accuracy
- [ ] Adjust lookback_hours if needed
- [ ] Consider enabling LLM if using heuristic

### Month 1
- [ ] Review overall system performance
- [ ] Check for any recurring errors
- [ ] Optimize fetch frequency
- [ ] Consider backup strategy
- [ ] Plan for Phase 2 features

## 🎯 Success Criteria

Your deployment is successful when:

- ✅ Backend starts without errors
- ✅ UI loads and displays correctly
- ✅ Can fetch emails on demand
- ✅ Messages display in UI
- ✅ Summaries generate correctly
- ✅ No passwords visible anywhere
- ✅ Storage persists between restarts
- ✅ System runs stably for 24+ hours

## 📞 Getting Help

If you encounter issues:

1. Check logs:
   - Backend: Console output or logs/
   - UI: Streamlit console output

2. Review documentation:
   - README.md
   - API_EXAMPLES.md
   - PROJECT_SUMMARY.md

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

4. Try demo script:
   ```bash
   python demo_fetch.py
   ```

5. Check GitHub issues (if applicable)

## 🎉 Deployment Complete!

Once all checkboxes are marked, your ContextCatcher MVP is fully deployed and operational!

**Next Steps:**
- Start using the system daily
- Provide feedback on summaries
- Consider enabling AI summaries
- Plan for additional integrations (WhatsApp, Slack)

---

**Version:** 1.0.0  
**Last Updated:** December 2024
