# Requirements Document

## Introduction

ContextCatcher is a minimal, secure MVP that ingests email via IMAP, normalizes messages, and provides a FastAPI backend with REST endpoints plus a Streamlit UI for viewing messages and AI-generated summaries with action items. The system focuses on email integration initially, with placeholders for future WhatsApp and Slack support.

## Glossary

- **ContextCatcher**: The complete system including backend API and UI components
- **Backend**: The FastAPI server that handles IMAP connections, message processing, and API endpoints
- **UI**: The Streamlit single-page application for user interaction
- **IMAP**: Internet Message Access Protocol for retrieving email messages
- **Normalized Message**: A standardized JSON representation of an email message
- **Thread**: A collection of related email messages grouped by thread_id
- **Summarizer**: The component that generates digest summaries and extracts action items from messages
- **LLM**: Large Language Model (e.g., OpenAI) used for intelligent summarization
- **Storage Adapter**: The pluggable interface for persisting normalized messages
- **Message-ID**: The unique identifier for an email message from email headers
- **Lookback Hours**: The time window (in hours) for fetching historical messages

## Requirements

### Requirement 1

**User Story:** As a user, I want to configure IMAP credentials and fetch parameters in a local config file, so that I can securely connect to my email account without hardcoding sensitive information.

#### Acceptance Criteria

1. WHEN the Backend starts THEN the system SHALL read IMAP credentials from a local configuration file or environment variables
2. WHEN the configuration file contains credentials THEN the system SHALL never log or print password values
3. WHEN the configuration specifies lookback_hours THEN the system SHALL use this value as the default time window for message fetching
4. WHERE the configuration includes LLM settings THEN the system SHALL enable or disable the Summarizer based on the llm.enabled flag
5. WHEN the configuration specifies a storage directory THEN the system SHALL persist all normalized messages to that location

### Requirement 2

**User Story:** As a user, I want to fetch emails via IMAP with automatic retry logic, so that temporary network issues do not prevent message retrieval.

#### Acceptance Criteria

1. WHEN the Backend receives a fetch request THEN the system SHALL connect to the IMAP server using configured credentials
2. WHEN the IMAP connection fails THEN the system SHALL retry with exponential backoff up to 3 attempts
3. WHEN the IMAP connection fails after all retries THEN the system SHALL return a clear error message to the caller
4. WHEN a fetch request includes since_hours parameter THEN the system SHALL fetch messages from that time window instead of the configured default
5. WHEN a fetch request omits since_hours parameter THEN the system SHALL use the configured lookback_hours value

### Requirement 3

**User Story:** As a user, I want emails to be normalized into a consistent JSON format, so that I can process messages uniformly regardless of their original format.

#### Acceptance Criteria

1. WHEN the Backend fetches an email message THEN the system SHALL extract and normalize fields including id, thread_id, subject, from, to, date, body_text, body_html, attachments, raw_headers, and metadata
2. WHEN normalizing the date field THEN the system SHALL convert it to ISO8601 format
3. WHEN normalizing the body THEN the system SHALL strip quoted replies and signatures by default
4. WHEN the configuration disables quote stripping THEN the system SHALL preserve the full message body
5. WHEN normalizing attachments THEN the system SHALL extract metadata without storing the full attachment content

### Requirement 4

**User Story:** As a user, I want messages to be deduplicated by Message-ID, so that I do not see duplicate entries when fetching overlapping time windows.

#### Acceptance Criteria

1. WHEN the Backend processes a fetched message THEN the system SHALL check if a message with the same Message-ID already exists in storage
2. WHEN a duplicate Message-ID is detected THEN the system SHALL skip persisting that message
3. WHEN deduplication occurs THEN the system SHALL maintain a count of skipped duplicates in the fetch response

### Requirement 5

**User Story:** As a user, I want to persist normalized messages as JSON files with an index, so that I can access message data without requiring a database.

#### Acceptance Criteria

1. WHEN the Backend normalizes a message THEN the system SHALL save it as a JSON file in the configured storage directory
2. WHEN saving messages THEN the system SHALL maintain an index.json file that tracks all stored messages
3. WHEN the Storage Adapter writes files THEN the system SHALL ensure the storage directory exists
4. WHEN retrieving messages THEN the system SHALL read from the index.json file for efficient lookup

### Requirement 6

**User Story:** As a developer, I want a POST /fetch endpoint, so that I can trigger email fetching programmatically or via the UI.

#### Acceptance Criteria

1. WHEN the Backend receives a POST request to /fetch THEN the system SHALL initiate an IMAP fetch operation
2. WHEN the fetch completes successfully THEN the system SHALL return a JSON response with fetched count and errors array
3. WHEN the fetch request includes a since_hours parameter THEN the system SHALL use that value for the time window
4. WHEN the fetch encounters errors THEN the system SHALL include error details in the response errors array
5. WHEN the fetch completes THEN the system SHALL update the last fetch timestamp

### Requirement 7

**User Story:** As a developer, I want a GET /messages endpoint, so that I can retrieve recent normalized messages for display or processing.

#### Acceptance Criteria

1. WHEN the Backend receives a GET request to /messages THEN the system SHALL return normalized messages in JSON format
2. WHEN the request includes a limit parameter THEN the system SHALL return at most that many messages
3. WHEN the request omits a limit parameter THEN the system SHALL default to returning 50 messages
4. WHEN returning messages THEN the system SHALL order them by date in descending order

### Requirement 8

**User Story:** As a developer, I want a GET /threads/{thread_id} endpoint, so that I can retrieve all messages in a conversation thread.

#### Acceptance Criteria

1. WHEN the Backend receives a GET request to /threads/{thread_id} THEN the system SHALL return all messages with matching thread_id
2. WHEN returning thread messages THEN the system SHALL include a flattened thread document with constituent messages
3. WHEN the thread_id does not exist THEN the system SHALL return an appropriate error response

### Requirement 9

**User Story:** As a user, I want a GET /summary endpoint that generates intelligent summaries with action items, so that I can quickly understand key information from my messages.

#### Acceptance Criteria

1. WHEN the Backend receives a GET request to /summary THEN the system SHALL analyze recent messages or top topics
2. WHERE the LLM is enabled THEN the system SHALL use the configured LLM to generate a 10-line digest
3. WHERE the LLM is disabled THEN the system SHALL use heuristic-based summarization
4. WHEN generating summaries THEN the system SHALL extract action items as JSON with action, owner, deadline, and evidence_snippet fields
5. WHEN the request includes a limit parameter THEN the system SHALL analyze at most that many messages
6. WHEN the request omits a limit parameter THEN the system SHALL default to analyzing 5 messages
7. WHEN returning summaries THEN the system SHALL include a confidence score

### Requirement 10

**User Story:** As a developer, I want a GET /status endpoint, so that I can monitor system health and fetch statistics.

#### Acceptance Criteria

1. WHEN the Backend receives a GET request to /status THEN the system SHALL return the last fetch timestamp
2. WHEN returning status THEN the system SHALL include message counts from storage
3. WHEN returning status THEN the system SHALL include a health indicator

### Requirement 11

**User Story:** As a user, I want a Streamlit UI with a config viewer, so that I can see my current settings without exposing sensitive credentials.

#### Acceptance Criteria

1. WHEN the UI loads THEN the system SHALL display the configured email address with password masked
2. WHEN the UI displays config THEN the system SHALL show the lookback_hours value
3. WHEN the user clicks Edit Config THEN the system SHALL open the local configuration file

### Requirement 12

**User Story:** As a user, I want UI controls to trigger fetches and view progress, so that I can manually refresh my messages and see fetch status.

#### Acceptance Criteria

1. WHEN the UI displays controls THEN the system SHALL show a Fetch Now button
2. WHEN the user clicks Fetch Now THEN the system SHALL call the POST /fetch endpoint
3. WHILE a fetch is in progress THEN the system SHALL display a progress indicator
4. WHEN a fetch completes THEN the system SHALL update the last fetch info display

### Requirement 13

**User Story:** As a user, I want to browse recent messages in the UI, so that I can select and view individual message details.

#### Acceptance Criteria

1. WHEN the UI displays the message list THEN the system SHALL show subject, from, and date for each message
2. WHEN the user clicks a message THEN the system SHALL display the full message body and headers
3. WHEN displaying messages THEN the system SHALL retrieve them from the GET /messages endpoint

### Requirement 14

**User Story:** As a user, I want to view AI-generated summaries and action items in the UI, so that I can quickly understand key information without reading all messages.

#### Acceptance Criteria

1. WHEN the UI displays the summary area THEN the system SHALL show a 10-line digest
2. WHEN the summary is generated THEN the system SHALL display extracted action items
3. WHERE the LLM is enabled THEN the system SHALL show evidence snippets for each action item
4. WHEN displaying summaries THEN the system SHALL show a confidence score
5. WHEN the summary area loads THEN the system SHALL retrieve data from the GET /summary endpoint

### Requirement 15

**User Story:** As a user, I want to see placeholder notices for future integrations, so that I understand the roadmap for WhatsApp and Slack support.

#### Acceptance Criteria

1. WHEN the UI displays the footer THEN the system SHALL show a "WhatsApp, Slack integration — Coming soon" message

### Requirement 16

**User Story:** As a developer, I want comprehensive documentation, so that I can set up and run ContextCatcher easily.

#### Acceptance Criteria

1. WHEN the repository is cloned THEN the system SHALL include a README.md with setup instructions
2. WHEN the README is read THEN the system SHALL explain how to create a Gmail app password
3. WHEN the README is read THEN the system SHALL document how to run the system locally and with Docker
4. WHEN the README is read THEN the system SHALL explain how to enable LLM summarization
5. WHEN the repository is cloned THEN the system SHALL include a config.example.json file

### Requirement 17

**User Story:** As a developer, I want a demo script, so that I can quickly test the fetch and summarization functionality.

#### Acceptance Criteria

1. WHEN the demo script runs THEN the system SHALL execute a sample fetch operation
2. WHEN the demo completes THEN the system SHALL print the 3 latest normalized messages
3. WHEN the demo completes THEN the system SHALL print a summary with action items

### Requirement 18

**User Story:** As a developer, I want unit tests for core functionality, so that I can verify IMAP fetch and normalization logic works correctly.

#### Acceptance Criteria

1. WHEN tests are executed THEN the system SHALL include tests for IMAP fetch operations using mocked IMAP responses
2. WHEN tests are executed THEN the system SHALL include tests for message normalization
3. WHEN tests are executed THEN the system SHALL include tests for deduplication logic

### Requirement 19

**User Story:** As a developer, I want a Dockerfile, so that I can run ContextCatcher in a containerized environment for development or demo purposes.

#### Acceptance Criteria

1. WHEN the Dockerfile is built THEN the system SHALL create a container with all required dependencies
2. WHEN the container runs THEN the system SHALL start both the Backend and UI services
3. WHEN the container is configured THEN the system SHALL support environment variable configuration
