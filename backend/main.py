"""FastAPI backend for ContextCatcher."""
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import Config
from backend.models import FetchResult
from backend.services.imap_fetcher import IMAPFetcher
from backend.services.normalizer import MessageNormalizer
from backend.services.summarizer import create_summarizer
from backend.storage.adapter import JSONStorageAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config = Config.load()

# Initialize services
imap_fetcher = IMAPFetcher(config.email, config.fetch)
normalizer = MessageNormalizer(strip_quotes=config.fetch.strip_quotes)
storage = JSONStorageAdapter(config.storage.dir, config.storage.index_file)
summarizer = create_summarizer(config.llm)

# Track last fetch time
last_fetch_time: Optional[str] = None

# Create FastAPI app
app = FastAPI(
    title="ContextCatcher API",
    description="Email ingestion and analysis API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Streamlit origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class FetchRequest(BaseModel):
    """Request body for fetch endpoint."""
    since_hours: Optional[int] = None


class FetchResponse(BaseModel):
    """Response for fetch endpoint."""
    fetched: int
    duplicates: int
    errors: List[str]
    timestamp: str


class MessagesResponse(BaseModel):
    """Response for messages endpoint."""
    messages: List[dict]
    total: int


class ThreadResponse(BaseModel):
    """Response for thread endpoint."""
    thread_id: str
    messages: List[dict]
    count: int
    subject: str
    participants: List[str]
    date_range: List[str]


class SummaryResponse(BaseModel):
    """Response for summary endpoint."""
    digest: str
    action_items: List[dict]
    confidence: float
    message_count: int


class StatusResponse(BaseModel):
    """Response for status endpoint."""
    last_fetch: Optional[str]
    message_count: int
    thread_count: int
    health: str


# Endpoints

@app.post("/fetch", response_model=FetchResponse)
async def fetch_emails(request: Optional[FetchRequest] = None):
    """
    Trigger IMAP fetch operation.
    
    Args:
        request: Optional request with since_hours parameter
        
    Returns:
        Fetch result with counts and errors
    """
    global last_fetch_time
    
    try:
        since_hours = request.since_hours if request else None
        
        logger.info(f"Starting fetch operation (since_hours={since_hours})")
        
        # Fetch messages
        raw_messages, errors = imap_fetcher.fetch_messages(since_hours)
        
        # Normalize and store
        fetched_count = 0
        duplicate_count = 0
        
        for raw_msg in raw_messages:
            try:
                # Normalize
                normalized = normalizer.normalize(raw_msg)
                
                # Save (returns False if duplicate)
                is_new = storage.save_message(normalized)
                
                if is_new:
                    fetched_count += 1
                else:
                    duplicate_count += 1
                    
            except Exception as e:
                error_msg = f"Failed to process message: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Update last fetch time
        last_fetch_time = datetime.now().isoformat()
        
        logger.info(f"Fetch complete: {fetched_count} new, {duplicate_count} duplicates, {len(errors)} errors")
        
        return FetchResponse(
            fetched=fetched_count,
            duplicates=duplicate_count,
            errors=errors,
            timestamp=last_fetch_time
        )
        
    except Exception as e:
        logger.error(f"Fetch operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/messages", response_model=MessagesResponse)
async def get_messages(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    """
    Get recent normalized messages.
    
    Args:
        limit: Maximum number of messages (1-200)
        offset: Number of messages to skip
        
    Returns:
        List of messages and total count
    """
    try:
        messages = storage.get_messages(limit=limit, offset=offset)
        stats = storage.get_stats()
        
        return MessagesResponse(
            messages=[msg.to_dict() for msg in messages],
            total=stats.message_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str):
    """
    Get all messages in a thread.
    
    Args:
        thread_id: Thread identifier
        
    Returns:
        Thread with all constituent messages
    """
    try:
        thread = storage.get_thread(thread_id)
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return ThreadResponse(
            thread_id=thread.thread_id,
            messages=[msg.to_dict() for msg in thread.messages],
            count=thread.message_count,
            subject=thread.subject,
            participants=thread.participants,
            date_range=list(thread.date_range)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary", response_model=SummaryResponse)
async def get_summary(limit: int = Query(default=5, ge=1, le=50)):
    """
    Generate summary with action items.
    
    Args:
        limit: Number of recent messages to analyze
        
    Returns:
        Summary with digest and action items
    """
    try:
        # Get recent messages
        messages = storage.get_messages(limit=limit)
        
        if not messages:
            return SummaryResponse(
                digest="No messages available to summarize.",
                action_items=[],
                confidence=0.0,
                message_count=0
            )
        
        # Generate summary
        summary = summarizer.generate_summary(messages)
        
        return SummaryResponse(
            digest=summary.digest,
            action_items=[
                {
                    "action": item.action,
                    "owner": item.owner,
                    "deadline": item.deadline,
                    "evidence_snippet": item.evidence_snippet
                }
                for item in summary.action_items
            ],
            confidence=summary.confidence,
            message_count=summary.message_count
        )
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get system health and statistics.
    
    Returns:
        Status with last fetch time and message counts
    """
    try:
        stats = storage.get_stats()
        
        return StatusResponse(
            last_fetch=last_fetch_time,
            message_count=stats.message_count,
            thread_count=stats.thread_count,
            health="healthy"
        )
        
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        return StatusResponse(
            last_fetch=last_fetch_time,
            message_count=0,
            thread_count=0,
            health=f"unhealthy: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ContextCatcher API",
        "version": "1.0.0",
        "endpoints": [
            "POST /fetch",
            "GET /messages",
            "GET /threads/{thread_id}",
            "GET /summary",
            "GET /status"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
