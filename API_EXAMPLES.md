# ContextCatcher API Examples

This document provides curl examples for all API endpoints.

## Prerequisites

Ensure the backend is running:
```bash
python backend/main.py
# Or: uvicorn backend.main:app --reload
```

## Endpoints

### 1. Root Endpoint

Get API information:
```bash
curl http://localhost:8000/
```

### 2. Fetch Emails

Trigger email fetch with default lookback hours:
```bash
curl -X POST http://localhost:8000/fetch \
  -H "Content-Type: application/json"
```

Fetch with custom lookback period:
```bash
curl -X POST http://localhost:8000/fetch \
  -H "Content-Type: application/json" \
  -d '{"since_hours": 48}'
```

### 3. Get Messages

Get recent messages (default limit 50):
```bash
curl http://localhost:8000/messages
```

Get messages with custom limit:
```bash
curl "http://localhost:8000/messages?limit=10"
```

Get messages with pagination:
```bash
curl "http://localhost:8000/messages?limit=10&offset=20"
```

Pretty print JSON response:
```bash
curl http://localhost:8000/messages | python -m json.tool
```

### 4. Get Thread

Get all messages in a specific thread:
```bash
curl http://localhost:8000/threads/<thread-id>
```

Example with actual thread ID:
```bash
# First, get a thread_id from messages
THREAD_ID=$(curl -s http://localhost:8000/messages?limit=1 | python -c "import sys, json; print(json.load(sys.stdin)['messages'][0]['thread_id'])")

# Then fetch the thread
curl "http://localhost:8000/threads/${THREAD_ID}" | python -m json.tool
```

### 5. Get Summary

Get summary of recent messages (default 5):
```bash
curl http://localhost:8000/summary
```

Get summary with custom message limit:
```bash
curl "http://localhost:8000/summary?limit=10"
```

Pretty print summary:
```bash
curl http://localhost:8000/summary | python -m json.tool
```

### 6. Get Status

Get system health and statistics:
```bash
curl http://localhost:8000/status
```

Pretty print status:
```bash
curl http://localhost:8000/status | python -m json.tool
```

## Complete Workflow Example

Here's a complete workflow using curl:

```bash
#!/bin/bash

echo "=== ContextCatcher API Workflow ==="
echo

# 1. Check status
echo "1. Checking system status..."
curl -s http://localhost:8000/status | python -m json.tool
echo

# 2. Fetch emails
echo "2. Fetching emails..."
curl -s -X POST http://localhost:8000/fetch \
  -H "Content-Type: application/json" \
  -d '{"since_hours": 24}' | python -m json.tool
echo

# 3. Get recent messages
echo "3. Getting recent messages..."
curl -s "http://localhost:8000/messages?limit=5" | python -m json.tool
echo

# 4. Generate summary
echo "4. Generating summary..."
curl -s "http://localhost:8000/summary?limit=5" | python -m json.tool
echo

# 5. Check status again
echo "5. Checking updated status..."
curl -s http://localhost:8000/status | python -m json.tool
echo

echo "=== Workflow Complete ==="
```

Save this as `test_api.sh`, make it executable, and run:
```bash
chmod +x test_api.sh
./test_api.sh
```

## Error Handling

### Invalid Thread ID
```bash
curl http://localhost:8000/threads/invalid-thread-id
# Returns: {"detail": "Thread not found"}
```

### Invalid Parameters
```bash
curl "http://localhost:8000/messages?limit=-1"
# Returns: 422 Unprocessable Entity with validation error
```

### Server Error
If the backend encounters an error, you'll receive a 500 response:
```json
{
  "detail": "Error message here"
}
```

## Using jq for Better JSON Parsing

If you have `jq` installed, you can parse responses more elegantly:

```bash
# Get just the message count
curl -s http://localhost:8000/status | jq '.message_count'

# Get subjects of all messages
curl -s http://localhost:8000/messages | jq '.messages[].subject'

# Get action items from summary
curl -s http://localhost:8000/summary | jq '.action_items[].action'

# Get digest with confidence
curl -s http://localhost:8000/summary | jq '{digest: .digest, confidence: .confidence}'
```

## Testing with Different Content-Types

The API accepts JSON for POST requests:

```bash
# Correct
curl -X POST http://localhost:8000/fetch \
  -H "Content-Type: application/json" \
  -d '{"since_hours": 24}'

# Also works (empty body)
curl -X POST http://localhost:8000/fetch \
  -H "Content-Type: application/json"
```

## Monitoring and Debugging

### Watch for new messages
```bash
watch -n 10 'curl -s http://localhost:8000/status | python -m json.tool'
```

### Continuous fetch and display
```bash
while true; do
  echo "Fetching..."
  curl -s -X POST http://localhost:8000/fetch | python -m json.tool
  echo "Waiting 5 minutes..."
  sleep 300
done
```

### Check API health
```bash
curl -f http://localhost:8000/status && echo "API is healthy" || echo "API is down"
```
