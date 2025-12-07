"""Data models for ContextCatcher."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime


@dataclass
class AttachmentMetadata:
    """Metadata for email attachments."""
    filename: str
    content_type: str
    size_bytes: int


@dataclass
class MessageMetadata:
    """Metadata about message processing."""
    fetched_at: str  # ISO8601
    source: str  # "imap"
    normalized_at: str  # ISO8601


@dataclass
class NormalizedMessage:
    """Normalized email message format."""
    id: str  # Message-ID from headers
    thread_id: str  # Derived from In-Reply-To/References
    subject: str
    from_addr: str
    to_addrs: List[str]
    date: str  # ISO8601 format
    cc_addrs: List[str] = field(default_factory=list)
    body_text: str = ""
    body_html: Optional[str] = None
    attachments: List[AttachmentMetadata] = field(default_factory=list)
    raw_headers: dict = field(default_factory=dict)
    metadata: Optional[MessageMetadata] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "from_addr": self.from_addr,
            "to_addrs": self.to_addrs,
            "cc_addrs": self.cc_addrs,
            "date": self.date,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "attachments": [
                {"filename": a.filename, "content_type": a.content_type, "size_bytes": a.size_bytes}
                for a in self.attachments
            ],
            "raw_headers": self.raw_headers,
            "metadata": {
                "fetched_at": self.metadata.fetched_at,
                "source": self.metadata.source,
                "normalized_at": self.metadata.normalized_at
            } if self.metadata else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NormalizedMessage":
        """Create from dictionary."""
        attachments = [
            AttachmentMetadata(**a) for a in data.get("attachments", [])
        ]
        metadata = None
        if data.get("metadata"):
            metadata = MessageMetadata(**data["metadata"])
        
        return cls(
            id=data["id"],
            thread_id=data["thread_id"],
            subject=data["subject"],
            from_addr=data["from_addr"],
            to_addrs=data["to_addrs"],
            cc_addrs=data.get("cc_addrs", []),
            date=data["date"],
            body_text=data.get("body_text", ""),
            body_html=data.get("body_html"),
            attachments=attachments,
            raw_headers=data.get("raw_headers", {}),
            metadata=metadata
        )


@dataclass
class ThreadView:
    """View of an email thread."""
    thread_id: str
    subject: str  # From first message
    message_count: int
    messages: List[NormalizedMessage]
    participants: List[str]  # Unique email addresses
    date_range: Tuple[str, str]  # (earliest, latest)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "thread_id": self.thread_id,
            "subject": self.subject,
            "message_count": self.message_count,
            "messages": [m.to_dict() for m in self.messages],
            "participants": self.participants,
            "date_range": list(self.date_range)
        }


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    fetched_count: int
    duplicate_count: int
    error_count: int
    errors: List[str]
    timestamp: str  # ISO8601


@dataclass
class ActionItem:
    """Extracted action item from messages."""
    action: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    evidence_snippet: str = ""


@dataclass
class Summary:
    """Summary of messages with action items."""
    digest: str  # 10-line summary
    action_items: List[ActionItem]
    confidence: float  # 0.0 to 1.0
    message_count: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "digest": self.digest,
            "action_items": [
                {
                    "action": a.action,
                    "owner": a.owner,
                    "deadline": a.deadline,
                    "evidence_snippet": a.evidence_snippet
                }
                for a in self.action_items
            ],
            "confidence": self.confidence,
            "message_count": self.message_count
        }


@dataclass
class StorageStats:
    """Storage statistics."""
    message_count: int
    thread_count: int
    oldest_message: Optional[str] = None
    newest_message: Optional[str] = None
