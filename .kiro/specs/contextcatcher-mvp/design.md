# Design Document

## Overview

ContextCatcher MVP is a Python-based email ingestion and analysis system consisting of two main components: a FastAPI backend that handles IMAP connections, message normalization, and REST API endpoints, and a Streamlit UI for user interaction. The system uses local JSON file storage, supports optional LLM-based summarization via OpenAI, and follows a pluggable architecture for future extensibility.

The architecture prioritizes security (no credential logging), simplicity (local JSON storage), and modularity (pluggable storage and LLM adapters). The system is designed to run locally or in Docker containers for development and demo purposes.

## Architecture

### High-Level Architecture

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
│  │              API Endpoints Layer                      │   │
│  │  /fetch  /messages  /threads  /summary  /status      │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────┴─────────────────────────────────────────┐   │
│  │              Business Logic Layer                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │   │
│  │  │ IMAP Fetcher │  │  Normalizer  │  │Summarizer │  │   │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────┴─────────────────────────────────────────┐   │
│  │              Storage Layer                            │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │  Storage Adapter (JSON File Implementation)  │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │  IMAP Server    │
                    │  (Gmail, etc.)  │
                    └─────────────────┘
```

### Component Responsibilities

**API Endpoints Layer**: Handles HTTP requests, validates input, orchestrates business logic, and formats responses.

**IMAP Fetcher**: Manages IMAP connections, implements retry logic, fetches messages within time windows, and handles authentication.

**Normalizer**: Converts raw email messages to standardized JSON format, strips quoted replies/signatures, extracts metadata, and handles character encoding.

**Summarizer**: Generates digests and extracts action items using either LLM (OpenAI) or heuristic-based approaches.

**Storage Adapter**: Provides pluggable interface for persisting and retrieving normalized messages, with JSON file implementation as default.

## Components and Interfaces

### Configuration Module

**File**: `backend/config.py`

**Purpose**: Load and validate configuration from file or environment variables.

```python
class Config:
    email: EmailConfig
    fetch: FetchConfig
    llm: LLMConfig
    storage: StorageConfig
    
class EmailConfig:
    host: str
    port: int
    username: str
    password: str  # Never logged
    use_ssl: bool
    
class FetchConfig:
    lookback_hours: int
    strip_quotes: bool
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    
class LLMConfig:
    enabled: bool
    provider: str = "openai"
    api_key: str
    model: str = "gpt-3.5-turbo"
    
class StorageConfig:
    dir: str
    index_file: str = "index.json"
```

### IMAP Fetcher

**File**: `backend/services/imap_fetcher.py`

**Interface**:
```python
class IMAPFetcher:
    def __init__(self, config: EmailConfig, fetch_config: FetchConfig)
    
    def fetch_messages(self, since_hours: int) -> FetchResult:
        """
        Fetch messages from IMAP server with retry logic.
        Returns: FetchResult with raw messages and errors
        """
        
    def _connect_with_retry(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP with exponential backoff"""
        
    def _fetch_message_ids(self, since_date: datetime) -> List[str]:
        """Search for message IDs since given date"""
        
    def _fetch_raw_message(self, msg_id: str) -> email.message.Message:
        """Fetch raw email message by ID"""
```

**Key Behaviors**:
- Implements exponential backoff: delay = base^attempt (2^0, 2^1, 2^2 seconds)
- Uses IMAP SEARCH with SINCE criterion for date filtering
- Handles SSL/TLS connections
- Never logs password values
- Closes connections properly in finally blocks

### Message Normalizer

**File**: `backend/services/normalizer.py`

**Interface**:
```python
class MessageNormalizer:
    def __init__(self, strip_quotes: bool = True)
    
    def normalize(self, raw_message: email.message.Message) -> NormalizedMessage:
        """Convert raw email to normalized format"""
        
    def _extract_thread_id(self, raw_message) -> str:
        """Extract or generate thread ID from headers"""
        
    def _extract_body(self, raw_message) -> Tuple[str, str]:
        """Extract plain text and HTML body"""
        
    def _strip_quotes_and_signatures(self, text: str) -> str:
        """Remove quoted replies and email signatures"""
        
    def _extract_attachments(self, raw_message) -> List[AttachmentMetadata]:
        """Extract attachment metadata without content"""
```

**Key Behaviors**:
- Uses Message-ID header as unique identifier
- Generates thread_id from In-Reply-To or References headers, falls back to subject-based grouping
- Strips quotes using regex patterns (>, |, On ... wrote:)
- Detects signatures by common markers (--,  Sent from, Best regards)
- Converts dates to ISO8601 format
- Handles multipart messages and character encoding

### Storage Adapter

**File**: `backend/storage/adapter.py`

**Interface**:
```python
class StorageAdapter(ABC):
    @abstractmethod
    def save_message(self, message: NormalizedMessage) -> bool:
        """Save normalized message, return True if new"""
        
    @abstractmethod
    def get_messages(self, limit: int, offset: int = 0) -> List[NormalizedMessage]:
        """Retrieve messages ordered by date desc"""
        
    @abstractmethod
    def get_thread(self, thread_id: str) -> ThreadView:
        """Get all messages in a thread"""
        
    @abstractmethod
    def message_exists(self, message_id: str) -> bool:
        """Check if message already stored"""
        
    @abstractmethod
    def get_stats(self) -> StorageStats:
        """Get message counts and statistics"""

class JSONStorageAdapter(StorageAdapter):
    """Implementation using local JSON files"""
    def __init__(self, storage_dir: str, index_file: str)
```

**JSON Storage Structure**:
```
storage_dir/
├── index.json          # {message_id: filename, thread_id, date, ...}
├── messages/
│   ├── msg_001.json
│   ├── msg_002.json
│   └── ...
```

**Key Behaviors**:
- Index file enables fast lookups without reading all message files
- Each message stored in separate file for easy inspection
- Atomic writes using temp file + rename pattern
- Index updated after successful message write
- Thread queries use index to find related messages

### Summarizer

**File**: `backend/services/summarizer.py`

**Interface**:
```python
class Summarizer(ABC):
    @abstractmethod
    def generate_summary(self, messages: List[NormalizedMessage]) -> Summary:
        """Generate digest and extract action items"""

class LLMSummarizer(Summarizer):
    def __init__(self, llm_config: LLMConfig)
    
class HeuristicSummarizer(Summarizer):
    """Fallback summarizer using keyword extraction"""
```

**Summary Output**:
```python
class ActionItem:
    action: str
    owner: Optional[str]
    deadline: Optional[str]
    evidence_snippet: str
    
class Summary:
    digest: str  # 10-line summary
    action_items: List[ActionItem]
    confidence: float  # 0.0 to 1.0
    message_count: int
```

**LLM Prompt Strategy**:
```
System: You are an email analysis assistant. Generate concise summaries and extract action items.

User: Analyze these {N} emails and provide:
1. A 10-line digest of key topics and information
2. Extracted action items in JSON format with: action, owner, deadline, evidence_snippet

Messages:
[message summaries with subject, from, date, body excerpt]

Format response as JSON: {digest: str, action_items: [...], confidence: float}
```

**Heuristic Strategy**:
- Extract frequent keywords and phrases
- Identify imperative sentences as potential actions
- Look for date patterns for deadlines
- Confidence always 0.5 for heuristic approach

### FastAPI Application

**File**: `backend/main.py`

**Endpoints**:

```python
@app.post("/fetch")
async def fetch_emails(request: FetchRequest = None) -> FetchResponse:
    """
    Trigger IMAP fetch operation
    Request: {since_hours?: int}
    Response: {fetched: int, duplicates: int, errors: List[str], timestamp: str}
    """

@app.get("/messages")
async def get_messages(limit: int = 50, offset: int = 0) -> MessagesResponse:
    """
    Get recent normalized messages
    Response: {messages: List[NormalizedMessage], total: int}
    """

@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str) -> ThreadResponse:
    """
    Get thread with all constituent messages
    Response: {thread_id: str, messages: List[NormalizedMessage], count: int}
    """

@app.get("/summary")
async def get_summary(limit: int = 5) -> SummaryResponse:
    """
    Generate summary with action items
    Response: Summary object
    """

@app.get("/status")
async def get_status() -> StatusResponse:
    """
    Get system health and statistics
    Response: {last_fetch: str, message_count: int, health: str}
    """
```

**Middleware**:
- CORS enabled for Streamlit UI
- Request logging (excluding sensitive data)
- Error handling with structured responses

### Streamlit UI

**File**: `ui/app.py`

**Layout**:
```python
# Top: Config Section
st.header("Configuration")
col1, col2 = st.columns([3, 1])
with col1:
    st.text(f"Email: {mask_email(config.email.username)}")
    st.text(f"Lookback: {config.fetch.lookback_hours} hours")
with col2:
    if st.button("Edit Config"):
        open_config_file()

# Middle: Fetch Controls
st.header("Fetch Controls")
col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    if st.button("Fetch Now"):
        trigger_fetch()
with col2:
    st.metric("Last Fetch", last_fetch_time)
with col3:
    if fetching:
        st.progress(fetch_progress)

# Main Content: Two Columns
col_left, col_right = st.columns([1, 1])

with col_left:
    st.header("Recent Messages")
    messages = fetch_messages_from_api()
    for msg in messages:
        if st.button(f"{msg.subject} - {msg.from_}", key=msg.id):
            st.session_state.selected_message = msg.id
    
    if st.session_state.selected_message:
        display_message_detail(st.session_state.selected_message)

with col_right:
    st.header("Summary & Action Items")
    summary = fetch_summary_from_api()
    st.text_area("Digest", summary.digest, height=200)
    st.subheader("Action Items")
    for item in summary.action_items:
        st.markdown(f"**{item.action}**")
        if item.owner:
            st.text(f"Owner: {item.owner}")
        if item.deadline:
            st.text(f"Deadline: {item.deadline}")
        st.caption(item.evidence_snippet)
    st.metric("Confidence", f"{summary.confidence:.0%}")

# Footer
st.markdown("---")
st.info("WhatsApp, Slack integration — Coming soon")
```

**State Management**:
- Use `st.session_state` for selected message
- Cache API responses with `@st.cache_data(ttl=60)`
- Auto-refresh summary every 5 minutes

## Data Models

### NormalizedMessage

```python
@dataclass
class NormalizedMessage:
    id: str  # Message-ID from headers
    thread_id: str  # Derived from In-Reply-To/References
    subject: str
    from_addr: str
    to_addrs: List[str]
    cc_addrs: List[str]
    date: str  # ISO8601 format
    body_text: str
    body_html: Optional[str]
    attachments: List[AttachmentMetadata]
    raw_headers: Dict[str, str]
    metadata: MessageMetadata

@dataclass
class AttachmentMetadata:
    filename: str
    content_type: str
    size_bytes: int

@dataclass
class MessageMetadata:
    fetched_at: str  # ISO8601
    source: str  # "imap"
    normalized_at: str  # ISO8601
```

### ThreadView

```python
@dataclass
class ThreadView:
    thread_id: str
    subject: str  # From first message
    message_count: int
    messages: List[NormalizedMessage]  # Ordered by date
    participants: List[str]  # Unique email addresses
    date_range: Tuple[str, str]  # (earliest, latest)
```

### FetchResult

```python
@dataclass
class FetchResult:
    fetched_count: int
    duplicate_count: int
    error_count: int
    errors: List[str]
    timestamp: str  # ISO8601
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Core Properties

Property 1: Configuration values are applied correctly
*For any* valid configuration file with specified email credentials, lookback_hours, LLM settings, and storage directory, when the Backend starts, all configuration values should be correctly loaded and used by their respective components.
**Validates: Requirements 1.1, 1.3, 1.4, 1.5**

Property 2: Passwords never appear in logs
*For any* operation that generates log output, the log content should never contain the configured password string.
**Validates: Requirements 1.2**

Property 3: IMAP retry with exponential backoff
*For any* IMAP connection that fails, the system should retry up to 3 times with exponentially increasing delays (2^0, 2^1, 2^2 seconds).
**Validates: Requirements 2.2**

Property 4: Fetch time window respects parameters
*For any* fetch request with a since_hours parameter, the IMAP search should use that time window; when omitted, it should use the configured lookback_hours.
**Validates: Requirements 2.4, 2.5, 6.3**

Property 5: Message normalization completeness
*For any* raw email message, the normalized output should contain all required fields: id, thread_id, subject, from_addr, to_addrs, date, body_text, raw_headers, and metadata.
**Validates: Requirements 3.1**

Property 6: Date normalization to ISO8601
*For any* email message with a date header, the normalized date field should be a valid ISO8601 formatted string.
**Validates: Requirements 3.2**

Property 7: Quote and signature stripping
*For any* email message body containing quoted replies (lines starting with >, |, or "On ... wrote:") or signatures (following --, Sent from, Best regards), when strip_quotes is enabled, the normalized body_text should not contain these patterns.
**Validates: Requirements 3.3**

Property 8: Quote stripping respects configuration
*For any* email message, when strip_quotes is disabled in configuration, the normalized body_text should be identical to the original body.
**Validates: Requirements 3.4**

Property 9: Attachment metadata extraction
*For any* email message with attachments, the normalized message should contain attachment metadata (filename, content_type, size_bytes) but should not contain the actual attachment content.
**Validates: Requirements 3.5**

Property 10: Message deduplication by Message-ID
*For any* message with a given Message-ID, if that message is processed twice, only one copy should exist in storage and the duplicate_count should increment.
**Validates: Requirements 4.1, 4.2, 4.3**

Property 11: Storage persistence round-trip
*For any* normalized message that is saved to storage, retrieving messages from storage should return an equivalent message with all fields preserved.
**Validates: Requirements 5.1, 5.2**

Property 12: Storage directory creation
*For any* storage directory path that does not exist, when the Storage Adapter attempts to save a message, the directory should be created automatically.
**Validates: Requirements 5.3**

Property 13: Index-based retrieval
*For any* message retrieval operation, the system should read from index.json rather than opening individual message files for lookup.
**Validates: Requirements 5.4**

Property 14: Fetch endpoint triggers IMAP operation
*For any* POST request to /fetch, the system should initiate an IMAP connection and fetch operation.
**Validates: Requirements 6.1**

Property 15: Fetch response includes errors
*For any* fetch operation that encounters errors, the response errors array should contain descriptions of those errors.
**Validates: Requirements 6.4**

Property 16: Fetch updates timestamp
*For any* completed fetch operation, the last fetch timestamp should be updated to the completion time.
**Validates: Requirements 6.5**

Property 17: Messages endpoint respects limit
*For any* GET request to /messages with a limit parameter, the response should contain at most that many messages.
**Validates: Requirements 7.2**

Property 18: Messages ordered by date descending
*For any* GET request to /messages, the returned messages should be ordered with the most recent date first.
**Validates: Requirements 7.4**

Property 19: Thread filtering by thread_id
*For any* GET request to /threads/{thread_id}, all returned messages should have a matching thread_id value.
**Validates: Requirements 8.1**

Property 20: Thread response structure
*For any* valid thread_id, the response should include a ThreadView with thread_id, message_count, messages list, participants, and date_range.
**Validates: Requirements 8.2**

Property 21: LLM summarizer selection
*For any* summary request, when llm.enabled is true, the system should use LLMSummarizer; when false, it should use HeuristicSummarizer.
**Validates: Requirements 9.2, 9.3**

Property 22: Action item structure
*For any* generated summary, each action item should contain the fields: action, owner (optional), deadline (optional), and evidence_snippet.
**Validates: Requirements 9.4**

Property 23: Summary respects message limit
*For any* GET request to /summary with a limit parameter, the system should analyze at most that many messages.
**Validates: Requirements 9.5**

Property 24: Summary includes confidence score
*For any* generated summary, the response should include a confidence score between 0.0 and 1.0.
**Validates: Requirements 9.7**

Property 25: Status endpoint completeness
*For any* GET request to /status, the response should include last_fetch timestamp, message_count, and health indicator.
**Validates: Requirements 10.1, 10.2, 10.3**

Property 26: UI masks password in config display
*For any* configuration with a password, when the UI displays the email configuration, the password should be masked (e.g., "***") and not shown in plain text.
**Validates: Requirements 11.1**

Property 27: UI fetch button triggers API call
*For any* click on the Fetch Now button, the UI should make a POST request to the /fetch endpoint.
**Validates: Requirements 12.2**

Property 28: UI shows progress during fetch
*For any* fetch operation in progress, the UI should display a progress indicator until the operation completes.
**Validates: Requirements 12.3**

Property 29: UI updates after fetch completion
*For any* completed fetch operation, the UI should update the last fetch info display with the new timestamp.
**Validates: Requirements 12.4**

Property 30: Message list displays required fields
*For any* message in the UI message list, the display should include subject, from, and date fields.
**Validates: Requirements 13.1**

Property 31: Message click shows detail
*For any* message clicked in the UI list, the system should display the full message body and headers.
**Validates: Requirements 13.2**

Property 32: UI retrieves messages from API
*For any* message list display, the UI should retrieve data by calling the GET /messages endpoint.
**Validates: Requirements 13.3**

Property 33: Summary area shows evidence snippets when LLM enabled
*For any* action item displayed in the UI, when LLM is enabled, the evidence_snippet should be visible.
**Validates: Requirements 14.3**

Property 34: UI retrieves summary from API
*For any* summary display, the UI should retrieve data by calling the GET /summary endpoint.
**Validates: Requirements 14.5**

Property 35: Container environment variable configuration
*For any* Docker container started with environment variables for configuration, the Backend should use those values instead of the config file.
**Validates: Requirements 19.3**

## Error Handling

### Error Categories

**Connection Errors**:
- IMAP connection failures (network, authentication, timeout)
- Retry with exponential backoff (3 attempts max)
- Return structured error: `{error: "connection_failed", message: str, retry_count: int}`

**Validation Errors**:
- Invalid configuration (missing required fields, invalid formats)
- Invalid API request parameters (negative limits, invalid thread_id format)
- Return HTTP 400 with structured error: `{error: "validation_error", field: str, message: str}`

**Storage Errors**:
- Disk full, permission denied, corrupted index
- Attempt recovery (rebuild index from message files)
- Return HTTP 500 with structured error: `{error: "storage_error", message: str}`

**LLM Errors**:
- API key invalid, rate limit exceeded, timeout
- Fallback to HeuristicSummarizer automatically
- Log warning but continue operation
- Return summary with confidence=0.5 and note in metadata

**Message Processing Errors**:
- Malformed email headers, encoding issues
- Skip problematic message, log error, continue processing
- Include in fetch response errors array

### Error Response Format

All API errors follow this structure:
```json
{
  "error": "error_type",
  "message": "Human-readable description",
  "details": {
    "field": "optional field name",
    "retry_count": "optional retry info"
  },
  "timestamp": "ISO8601"
}
```

### Logging Strategy

- Use Python `logging` module with structured logging
- Log levels:
  - DEBUG: IMAP commands, message processing details
  - INFO: Fetch operations, API requests, summary generation
  - WARNING: Fallback to heuristic summarizer, skipped messages
  - ERROR: Connection failures, storage errors, validation errors
- Never log passwords or sensitive email content
- Mask email addresses in logs (show first 3 chars + domain)

## Testing Strategy

### Unit Testing

**Framework**: pytest with pytest-asyncio for async tests

**Coverage Areas**:
- Configuration loading and validation
- Message normalization with various email formats
- Storage adapter operations (save, retrieve, deduplication)
- API endpoint request/response handling
- Error handling and retry logic

**Key Test Cases**:
- Config loading from file and environment variables
- Password masking in logs and UI
- Date parsing from various email date formats
- Quote and signature stripping with different patterns
- Attachment metadata extraction
- Deduplication with same Message-ID
- IMAP retry logic with mocked failures
- Thread grouping by In-Reply-To and References headers
- API parameter validation (negative limits, missing required fields)
- Storage directory creation
- Index file corruption recovery

**Mocking Strategy**:
- Mock IMAP server responses using `unittest.mock`
- Mock LLM API calls to avoid external dependencies
- Use temporary directories for storage tests
- Mock time for testing retry backoff timing

### Property-Based Testing

**Framework**: Hypothesis for Python

**Configuration**:
- Minimum 100 iterations per property test
- Use `@given` decorator with appropriate strategies
- Tag each test with format: `# Feature: contextcatcher-mvp, Property {N}: {description}`

**Property Tests**:

1. **Property 2: Password never in logs** - Generate random operations, capture all log output, verify password string never appears
2. **Property 6: Date normalization** - Generate random email date formats, verify output is valid ISO8601
3. **Property 7: Quote stripping** - Generate messages with various quote patterns, verify they are removed
4. **Property 8: Quote stripping disabled** - Generate messages, verify body unchanged when strip_quotes=false
5. **Property 9: Attachment metadata only** - Generate messages with attachments, verify content not in normalized message
6. **Property 10: Deduplication** - Generate messages with duplicate Message-IDs, verify only one stored
7. **Property 11: Storage round-trip** - Generate random normalized messages, save and retrieve, verify equivalence
8. **Property 17: Messages limit** - Generate random limit values, verify response count ≤ limit
9. **Property 18: Date ordering** - Generate messages with random dates, verify descending order
10. **Property 19: Thread filtering** - Generate messages with various thread_ids, verify filtering correctness

**Hypothesis Strategies**:
```python
from hypothesis import strategies as st

# Email address strategy
email_addresses = st.emails()

# Date strategy (various formats)
email_dates = st.one_of(
    st.datetimes(),
    st.text(regex=r'\w{3}, \d{1,2} \w{3} \d{4} \d{2}:\d{2}:\d{2}')
)

# Message body with quotes
bodies_with_quotes = st.text().flatmap(
    lambda text: st.just(f"> Quoted text\n{text}\n--\nSignature")
)

# Message-ID strategy
message_ids = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
    min_size=10, max_size=50
).map(lambda s: f"<{s}@example.com>")
```

### Integration Testing

**Scope**: End-to-end flows with real components (no mocks except external services)

**Test Scenarios**:
1. Full fetch flow: API call → IMAP fetch (mocked) → normalize → store → retrieve
2. Summary generation: Fetch messages → generate summary → verify action items
3. UI interaction: Trigger fetch → display messages → show summary
4. Error recovery: IMAP failure → retry → fallback → error response
5. Configuration changes: Update config → restart → verify new settings applied

**Test Environment**:
- Use Docker Compose for integration tests
- Temporary storage directory cleaned between tests
- Mock IMAP server using `aiosmtpd` or similar
- Mock LLM API using `responses` library

### Test Organization

```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_imap_fetcher.py
│   ├── test_normalizer.py
│   ├── test_storage.py
│   ├── test_summarizer.py
│   └── test_api_endpoints.py
├── property/
│   ├── test_properties_normalization.py
│   ├── test_properties_storage.py
│   ├── test_properties_api.py
│   └── strategies.py  # Hypothesis strategies
├── integration/
│   ├── test_fetch_flow.py
│   ├── test_summary_flow.py
│   └── test_ui_integration.py
└── conftest.py  # Shared fixtures
```

### CI/CD Testing

- Run all tests on every commit
- Fail build if any test fails or coverage drops below 80%
- Run property tests with 200 iterations in CI (more thorough)
- Generate coverage report and upload to codecov

## Deployment and Operations

### Local Development

**Prerequisites**:
- Python 3.10+
- pip or poetry for dependency management

**Setup**:
```bash
# Clone repository
git clone https://github.com/user/contextcatcher-mvp.git
cd contextcatcher-mvp

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp config.example.json config.json

# Edit config with your IMAP credentials
nano config.json

# Run backend
cd backend
uvicorn main:app --reload --port 8000

# Run UI (separate terminal)
cd ui
streamlit run app.py
```

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY ui/ ./ui/
COPY config.example.json ./config.json

# Expose ports
EXPOSE 8000 8501

# Start both services
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0"]
```

**Docker Compose**:
```yaml
version: '3.8'
services:
  contextcatcher:
    build: .
    ports:
      - "8000:8000"
      - "8501:8501"
    environment:
      - EMAIL_HOST=${EMAIL_HOST}
      - EMAIL_USERNAME=${EMAIL_USERNAME}
      - EMAIL_PASSWORD=${EMAIL_PASSWORD}
      - LOOKBACK_HOURS=${LOOKBACK_HOURS:-24}
      - LLM_ENABLED=${LLM_ENABLED:-false}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./storage:/app/storage
      - ./config.json:/app/config.json
```

### Configuration Management

**Priority Order** (highest to lowest):
1. Environment variables
2. config.json file
3. Default values

**Environment Variable Mapping**:
- `EMAIL_HOST` → `email.host`
- `EMAIL_PORT` → `email.port`
- `EMAIL_USERNAME` → `email.username`
- `EMAIL_PASSWORD` → `email.password`
- `LOOKBACK_HOURS` → `fetch.lookback_hours`
- `LLM_ENABLED` → `llm.enabled`
- `OPENAI_API_KEY` → `llm.api_key`
- `STORAGE_DIR` → `storage.dir`

### Monitoring and Observability

**Health Checks**:
- `/status` endpoint returns health status
- Check IMAP connectivity
- Check storage accessibility
- Check LLM API availability (if enabled)

**Metrics** (future enhancement):
- Fetch operation count and duration
- Message processing rate
- Storage size and message count
- API request rate and latency
- LLM API call count and cost

**Logging**:
- Structured JSON logs for production
- Log rotation (max 100MB per file, keep 10 files)
- Separate log files for backend and UI
- Centralized logging to stdout in Docker

## Security Considerations

### Credential Protection

- Never log passwords or API keys
- Mask credentials in UI displays
- Use environment variables in production
- Support credential rotation without code changes
- Consider using secret management tools (e.g., HashiCorp Vault) for production

### Email Security

- Use SSL/TLS for IMAP connections (port 993)
- Validate SSL certificates
- Support app-specific passwords (recommended for Gmail)
- Never store email content in logs
- Implement rate limiting to prevent abuse

### API Security

- Add authentication middleware (future enhancement)
- Implement rate limiting per IP
- Validate all input parameters
- Sanitize error messages (no stack traces in production)
- CORS configuration for UI origin only

### Data Privacy

- Store messages locally (no cloud storage by default)
- Provide data deletion endpoint (future enhancement)
- Mask email addresses in logs
- Support data encryption at rest (future enhancement)

## Future Enhancements

### Phase 2: WhatsApp Integration

- WhatsApp Business API integration
- Message normalization for WhatsApp format
- Media attachment handling
- Group chat support

### Phase 3: Slack Integration

- Slack API integration
- Channel and DM message fetching
- Thread support
- Reaction and emoji handling

### Phase 4: Advanced Features

- Real-time message streaming (WebSocket)
- Advanced search and filtering
- Custom action item extraction rules
- Multi-user support with authentication
- Database backend option (PostgreSQL)
- Message archival and retention policies
- Export functionality (CSV, PDF)
- Email sending capabilities
- Calendar integration for action item deadlines
- Notification system for urgent action items

## Appendix

### Technology Stack Summary

**Backend**:
- Python 3.10+
- FastAPI 0.104+
- Uvicorn (ASGI server)
- imaplib (stdlib, IMAP client)
- email (stdlib, email parsing)
- Pydantic (data validation)
- OpenAI Python SDK (optional)

**UI**:
- Streamlit 1.28+
- Requests (HTTP client)

**Testing**:
- pytest 7.4+
- pytest-asyncio
- Hypothesis 6.88+
- unittest.mock

**Development**:
- Docker & Docker Compose
- Black (code formatting)
- Ruff (linting)
- mypy (type checking)

### API Endpoint Reference

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| POST | /fetch | `{since_hours?: int}` | `{fetched: int, duplicates: int, errors: str[], timestamp: str}` |
| GET | /messages | `?limit=50&offset=0` | `{messages: NormalizedMessage[], total: int}` |
| GET | /threads/{id} | - | `{thread_id: str, messages: NormalizedMessage[], count: int}` |
| GET | /summary | `?limit=5` | `{digest: str, action_items: ActionItem[], confidence: float}` |
| GET | /status | - | `{last_fetch: str, message_count: int, health: str}` |

### Configuration File Schema

```json
{
  "email": {
    "host": "imap.gmail.com",
    "port": 993,
    "username": "user@gmail.com",
    "password": "app-specific-password",
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
