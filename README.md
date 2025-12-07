# ContextCatcher MVP

ContextCatcher is a lightweight AI-powered context-summarization tool that automatically fetches your messages from different communication channels and converts them into clear, actionable daily digests. The goal is to unify email, WhatsApp, Slack, and other chat platforms into one intelligent “catch-up” dashboard powered by generative AI.
At the moment, the MVP includes email ingestion via IMAP with summarization and action extraction.
WhatsApp and Slack integrations are coming soon.
## Features

- 📧 **IMAP Email Ingestion** - Fetch emails from Gmail and other IMAP servers
- 🔄 **Message Normalization** - Convert emails to consistent JSON format
- 🧠 **AI Summarization** - Generate digests and extract action items (OpenAI optional)
- 🗄️ **Local Storage** - Store messages as JSON files with efficient indexing
- 🌐 **REST API** - FastAPI backend with 5 core endpoints
- 🎨 **Streamlit UI** - Simple, intuitive web interface
- 🔒 **Security First** - Credentials never logged, app-specific passwords supported
- 🐳 **Docker Ready** - Easy deployment with Docker Compose

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Streamlit UI                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Config View  │  │ Message List │  │ Summary View │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP REST API
┌────────────────────────────┴────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /fetch  /messages  /threads  /summary  /status      │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────┴─────────────────────────────────────────┐   │
│  │  IMAP Fetcher → Normalizer → Storage → Summarizer    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Gmail account with app-specific password (or other IMAP email)
- (Optional) OpenAI API key for AI summarization

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/contextcatcher-mvp.git
cd contextcatcher-mvp
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure your email**
```bash
cp config.example.json config.json
# Edit config.json with your credentials
```

4. **Run the backend**
```bash
python backend/main.py
# Or: uvicorn backend.main:app --reload
```

5. **Run the UI** (in a separate terminal)
```bash
streamlit run ui/app.py
```

6. **Access the application**
- UI: http://localhost:8501
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Configuration

### Creating a Gmail App Password

For Gmail users, you need to create an app-specific password:

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Scroll down to **App passwords**
4. Select **Mail** and **Other (Custom name)**
5. Enter "ContextCatcher" as the name
6. Click **Generate**
7. Copy the 16-character password (no spaces)
8. Use this password in your `config.json`

### Configuration File

Edit `config.json` with your settings:

```json
{
  "email": {
    "host": "imap.gmail.com",
    "port": 993,
    "username": "your-email@gmail.com",
    "password": "your-app-specific-password",
    "use_ssl": true
  },
  "fetch": {
    "lookback_hours": 24,
    "strip_quotes": true,
    "max_retries": 3,
    "retry_backoff_base": 2.0
  },
  "llm": {
    "enabled": false,
    "provider": "openai",
    "api_key": "",
    "model": "gpt-3.5-turbo"
  },
  "storage": {
    "dir": "./storage",
    "index_file": "index.json"
  }
}
```

### Enabling LLM Summarization

To enable AI-powered summaries:

1. Get an OpenAI API key from https://platform.openai.com/api-keys
2. Update `config.json`:
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

**Note:** When LLM is disabled, the system uses a heuristic-based summarizer as fallback.

### Environment Variables

You can also configure via environment variables (takes precedence over config file):

```bash
export EMAIL_HOST=imap.gmail.com
export EMAIL_USERNAME=your-email@gmail.com
export EMAIL_PASSWORD=your-app-password
export LOOKBACK_HOURS=24
export LLM_ENABLED=true
export OPENAI_API_KEY=sk-your-key
export STORAGE_DIR=./storage
```

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Create `.env` file**
```bash
EMAIL_HOST=imap.gmail.com
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
LOOKBACK_HOURS=24
LLM_ENABLED=false
OPENAI_API_KEY=
```

2. **Build and run**
```bash
docker-compose up --build
```

3. **Access**
- UI: http://localhost:8501
- API: http://localhost:8000

### Using Dockerfile

```bash
# Build
docker build -t contextcatcher .

# Run
docker run -p 8000:8000 -p 8501:8501 \
  -e EMAIL_HOST=imap.gmail.com \
  -e EMAIL_USERNAME=your-email@gmail.com \
  -e EMAIL_PASSWORD=your-app-password \
  -v $(pwd)/storage:/app/storage \
  contextcatcher
```

## API Endpoints

### POST /fetch
Trigger email fetch operation.

**Request:**
```json
{
  "since_hours": 24  // Optional, overrides config
}
```

**Response:**
```json
{
  "fetched": 10,
  "duplicates": 2,
  "errors": [],
  "timestamp": "2024-01-01T12:00:00"
}
```

### GET /messages
Retrieve recent normalized messages.

**Parameters:**
- `limit` (default: 50, max: 200)
- `offset` (default: 0)

**Response:**
```json
{
  "messages": [...],
  "total": 100
}
```

### GET /threads/{thread_id}
Get all messages in a thread.

**Response:**
```json
{
  "thread_id": "...",
  "subject": "...",
  "messages": [...],
  "count": 5,
  "participants": ["email1@example.com", "email2@example.com"],
  "date_range": ["2024-01-01T10:00:00", "2024-01-01T15:00:00"]
}
```

### GET /summary
Generate summary with action items.

**Parameters:**
- `limit` (default: 5, max: 50) - Number of messages to analyze

**Response:**
```json
{
  "digest": "10-line summary...",
  "action_items": [
    {
      "action": "Review the proposal",
      "owner": "John Doe",
      "deadline": "2024-01-15",
      "evidence_snippet": "From: boss@company.com..."
    }
  ],
  "confidence": 0.85,
  "message_count": 5
}
```

### GET /status
Get system health and statistics.

**Response:**
```json
{
  "last_fetch": "2024-01-01T12:00:00",
  "message_count": 150,
  "thread_count": 45,
  "health": "healthy"
}
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_basic.py -v
```

## Demo Script

Run the demo to test fetch and summarization:

```bash
python demo_fetch.py
```

This will:
1. Fetch recent emails
2. Display the 3 latest normalized messages
3. Generate and display a summary with action items

## Project Structure

```
contextcatcher-mvp/
├── backend/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── models.py           # Data models
│   ├── main.py             # FastAPI application
│   ├── services/
│   │   ├── imap_fetcher.py # IMAP email fetching
│   │   ├── normalizer.py   # Message normalization
│   │   └── summarizer.py   # AI/heuristic summarization
│   └── storage/
│       └── adapter.py      # Storage interface & JSON impl
├── ui/
│   └── app.py              # Streamlit UI
├── tests/
│   └── test_basic.py       # Unit tests
├── storage/                # Message storage (created at runtime)
│   ├── index.json
│   └── messages/
├── config.example.json     # Example configuration
├── config.json             # Your configuration (gitignored)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── demo_fetch.py           # Demo script
└── README.md               # This file
```

## Troubleshooting

### IMAP Connection Fails

**Problem:** "Failed to connect after 3 attempts"

**Solutions:**
- Verify your email and password are correct
- For Gmail, ensure you're using an app-specific password, not your regular password
- Check if IMAP is enabled in your email settings
- Verify firewall/network allows IMAP connections (port 993)

### No Messages Fetched

**Problem:** Fetch succeeds but returns 0 messages

**Solutions:**
- Check the `lookback_hours` setting - increase if needed
- Verify you have emails in your inbox within the lookback period
- Check the IMAP folder being accessed (default is INBOX)

### LLM Summarization Fails

**Problem:** Summary shows low confidence or errors

**Solutions:**
- Verify your OpenAI API key is valid
- Check your OpenAI account has available credits
- System automatically falls back to heuristic summarizer on LLM errors
- Check logs for specific error messages

### Storage Errors

**Problem:** "Permission denied" or "Failed to save message"

**Solutions:**
- Ensure the storage directory is writable
- Check disk space availability
- Verify the path in `config.json` is correct

## Security Best Practices

1. **Never commit `config.json`** - It's in `.gitignore` by default
2. **Use app-specific passwords** - Don't use your main email password
3. **Rotate credentials regularly** - Update passwords periodically
4. **Limit API access** - Use environment variables in production
5. **Review logs** - Passwords are never logged, but review for sensitive data
6. **Use HTTPS** - In production, deploy behind HTTPS proxy

## Roadmap

### Phase 2: WhatsApp Integration
- WhatsApp Business API integration
- Message normalization for WhatsApp format
- Media attachment handling

### Phase 3: Slack Integration
- Slack API integration
- Channel and DM message fetching
- Thread support

### Phase 4: Advanced Features
- Real-time message streaming
- Advanced search and filtering
- Multi-user support with authentication
- Database backend option (PostgreSQL)
- Export functionality (CSV, PDF)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/contextcatcher-mvp/issues
- Documentation: See this README and API docs at `/docs`

## Acknowledgments

Built with:
- FastAPI - Modern Python web framework
- Streamlit - Rapid UI development
- OpenAI - AI-powered summarization
- Python standard library - IMAP and email handling
