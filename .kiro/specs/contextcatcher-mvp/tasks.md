# Implementation Plan

- [x] 1. Set up project structure and configuration
  - Create directory structure: backend/, ui/, tests/, storage/
  - Create requirements.txt with FastAPI, Streamlit, pytest, Hypothesis, OpenAI dependencies
  - Create config.example.json with all required fields
  - Implement Config class with Pydantic models for validation
  - Support loading from both config file and environment variables
  - _Requirements: 1.1, 1.3, 1.4, 1.5, 16.5_

- [ ]* 1.1 Write property test for configuration loading
  - **Property 1: Configuration values are applied correctly**
  - **Validates: Requirements 1.1, 1.3, 1.4, 1.5**

- [x] 2. Implement IMAP fetcher with retry logic
  - Create IMAPFetcher class with connection management
  - Implement exponential backoff retry logic (3 attempts, 2^n seconds delay)
  - Implement fetch_messages method with since_hours parameter
  - Handle SSL/TLS connections to IMAP server
  - Ensure password is never logged or printed
  - Return FetchResult with counts and errors
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 2.1 Write property test for IMAP retry logic
  - **Property 3: IMAP retry with exponential backoff**
  - **Validates: Requirements 2.2**

- [ ]* 2.2 Write property test for fetch time window
  - **Property 4: Fetch time window respects parameters**
  - **Validates: Requirements 2.4, 2.5, 6.3**

- [ ]* 2.3 Write property test for password logging
  - **Property 2: Passwords never appear in logs**
  - **Validates: Requirements 1.2**

- [x] 3. Implement message normalizer
  - Create MessageNormalizer class
  - Implement normalize method to extract all required fields
  - Convert dates to ISO8601 format
  - Extract thread_id from In-Reply-To/References headers
  - Implement quote and signature stripping with configurable toggle
  - Extract attachment metadata without content
  - Handle multipart messages and character encoding
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ]* 3.1 Write property test for message normalization completeness
  - **Property 5: Message normalization completeness**
  - **Validates: Requirements 3.1**

- [ ]* 3.2 Write property test for date normalization
  - **Property 6: Date normalization to ISO8601**
  - **Validates: Requirements 3.2**

- [ ]* 3.3 Write property test for quote stripping
  - **Property 7: Quote and signature stripping**
  - **Validates: Requirements 3.3**

- [ ]* 3.4 Write property test for quote stripping configuration
  - **Property 8: Quote stripping respects configuration**
  - **Validates: Requirements 3.4**

- [ ]* 3.5 Write property test for attachment metadata
  - **Property 9: Attachment metadata extraction**
  - **Validates: Requirements 3.5**

- [x] 4. Implement storage adapter with JSON backend
  - Create StorageAdapter abstract base class
  - Implement JSONStorageAdapter with local file storage
  - Implement save_message with deduplication by Message-ID
  - Implement get_messages with limit and offset
  - Implement get_thread for thread_id filtering
  - Maintain index.json for efficient lookups
  - Ensure storage directory creation
  - Track duplicate counts
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4_

- [ ]* 4.1 Write property test for deduplication
  - **Property 10: Message deduplication by Message-ID**
  - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ]* 4.2 Write property test for storage round-trip
  - **Property 11: Storage persistence round-trip**
  - **Validates: Requirements 5.1, 5.2**

- [ ]* 4.3 Write property test for storage directory creation
  - **Property 12: Storage directory creation**
  - **Validates: Requirements 5.3**

- [ ]* 4.4 Write property test for index-based retrieval
  - **Property 13: Index-based retrieval**
  - **Validates: Requirements 5.4**

- [x] 5. Implement summarizer with LLM and heuristic options
  - Create Summarizer abstract base class
  - Implement LLMSummarizer using OpenAI API
  - Implement HeuristicSummarizer as fallback
  - Generate 10-line digest from messages
  - Extract action items with action, owner, deadline, evidence_snippet
  - Return confidence score
  - Handle LLM errors by falling back to heuristic
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.7_

- [ ]* 5.1 Write property test for summarizer selection
  - **Property 21: LLM summarizer selection**
  - **Validates: Requirements 9.2, 9.3**

- [ ]* 5.2 Write property test for action item structure
  - **Property 22: Action item structure**
  - **Validates: Requirements 9.4**

- [x] 6. Implement FastAPI backend with all endpoints
  - Create FastAPI application with CORS middleware
  - Implement POST /fetch endpoint with since_hours parameter
  - Implement GET /messages endpoint with limit and offset
  - Implement GET /threads/{thread_id} endpoint
  - Implement GET /summary endpoint with limit parameter
  - Implement GET /status endpoint
  - Add structured error handling for all endpoints
  - Add request logging (excluding sensitive data)
  - Wire up all services (IMAPFetcher, Normalizer, Storage, Summarizer)
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 9.1, 9.5, 9.6, 10.1, 10.2, 10.3_

- [ ]* 6.1 Write property test for fetch endpoint behavior
  - **Property 14: Fetch endpoint triggers IMAP operation**
  - **Validates: Requirements 6.1**

- [ ]* 6.2 Write property test for fetch error reporting
  - **Property 15: Fetch response includes errors**
  - **Validates: Requirements 6.4**

- [ ]* 6.3 Write property test for fetch timestamp update
  - **Property 16: Fetch updates timestamp**
  - **Validates: Requirements 6.5**

- [ ]* 6.4 Write property test for messages limit
  - **Property 17: Messages endpoint respects limit**
  - **Validates: Requirements 7.2**

- [ ]* 6.5 Write property test for message ordering
  - **Property 18: Messages ordered by date descending**
  - **Validates: Requirements 7.4**

- [ ]* 6.6 Write property test for thread filtering
  - **Property 19: Thread filtering by thread_id**
  - **Validates: Requirements 8.1**

- [ ]* 6.7 Write property test for thread response structure
  - **Property 20: Thread response structure**
  - **Validates: Requirements 8.2**

- [ ]* 6.8 Write property test for summary message limit
  - **Property 23: Summary respects message limit**
  - **Validates: Requirements 9.5**

- [ ]* 6.9 Write property test for summary confidence score
  - **Property 24: Summary includes confidence score**
  - **Validates: Requirements 9.7**

- [ ]* 6.10 Write property test for status endpoint completeness
  - **Property 25: Status endpoint completeness**
  - **Validates: Requirements 10.1, 10.2, 10.3**

- [x] 7. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Streamlit UI with config viewer
  - Create Streamlit app.py with single-page layout
  - Implement config viewer section showing masked email and lookback_hours
  - Add Edit Config button to open config file
  - _Requirements: 11.1, 11.2, 11.3_

- [ ]* 8.1 Write property test for password masking in UI
  - **Property 26: UI masks password in config display**
  - **Validates: Requirements 11.1**

- [x] 9. Implement UI fetch controls
  - Add Fetch Now button that calls POST /fetch endpoint
  - Display progress indicator during fetch
  - Show last fetch timestamp and info
  - Update display after fetch completes
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ]* 9.1 Write property test for fetch button API call
  - **Property 27: UI fetch button triggers API call**
  - **Validates: Requirements 12.2**

- [ ]* 9.2 Write property test for progress indicator
  - **Property 28: UI shows progress during fetch**
  - **Validates: Requirements 12.3**

- [ ]* 9.3 Write property test for UI update after fetch
  - **Property 29: UI updates after fetch completion**
  - **Validates: Requirements 12.4**

- [x] 10. Implement UI message list and detail view
  - Create left pane with recent messages list
  - Display subject, from, and date for each message
  - Implement click handler to show message detail
  - Display full message body and headers in detail view
  - Call GET /messages endpoint to retrieve data
  - _Requirements: 13.1, 13.2, 13.3_

- [ ]* 10.1 Write property test for message list display
  - **Property 30: Message list displays required fields**
  - **Validates: Requirements 13.1**

- [ ]* 10.2 Write property test for message detail view
  - **Property 31: Message click shows detail**
  - **Validates: Requirements 13.2**

- [ ]* 10.3 Write property test for messages API call
  - **Property 32: UI retrieves messages from API**
  - **Validates: Requirements 13.3**

- [x] 11. Implement UI summary and action items view
  - Create right pane for summary display
  - Show 10-line digest in text area
  - Display action items with action, owner, deadline
  - Show evidence snippets when LLM enabled
  - Display confidence score
  - Call GET /summary endpoint to retrieve data
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ]* 11.1 Write property test for evidence snippets display
  - **Property 33: Summary area shows evidence snippets when LLM enabled**
  - **Validates: Requirements 14.3**

- [ ]* 11.2 Write property test for summary API call
  - **Property 34: UI retrieves summary from API**
  - **Validates: Requirements 14.5**

- [x] 12. Add UI footer with integration placeholders
  - Add footer section with "WhatsApp, Slack integration — Coming soon" message
  - _Requirements: 15.1_

- [x] 13. Create comprehensive README documentation
  - Write introduction and overview
  - Document setup steps for local development
  - Explain how to create Gmail app password
  - Document how to run locally (backend + UI)
  - Document how to run with Docker
  - Explain how to enable LLM summarization
  - Add troubleshooting section
  - _Requirements: 16.1, 16.2, 16.3, 16.4_

- [x] 14. Create demo script
  - Implement demo_fetch.py script
  - Execute sample fetch operation
  - Print 3 latest normalized messages
  - Print summary with action items
  - _Requirements: 17.1, 17.2, 17.3_

- [x] 15. Create Dockerfile and Docker Compose configuration
  - Write Dockerfile with Python 3.10+ base image
  - Install all dependencies
  - Configure to start both backend and UI services
  - Support environment variable configuration
  - Create docker-compose.yml for easy deployment
  - _Requirements: 19.1, 19.2, 19.3_

- [ ]* 15.1 Write property test for container environment variables
  - **Property 35: Container environment variable configuration**
  - **Validates: Requirements 19.3**

- [x] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
