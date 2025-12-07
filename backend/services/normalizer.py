"""Email message normalizer."""
import re
import hashlib
from datetime import datetime
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from typing import List, Tuple, Optional

from backend.models import NormalizedMessage, AttachmentMetadata, MessageMetadata


class MessageNormalizer:
    """Normalizes raw email messages to standard format."""
    
    def __init__(self, strip_quotes: bool = True):
        self.strip_quotes = strip_quotes
    
    def normalize(self, raw_message: Message) -> NormalizedMessage:
        """
        Convert raw email message to normalized format.
        
        Args:
            raw_message: Raw email.message.Message object
            
        Returns:
            NormalizedMessage with all fields populated
        """
        # Extract basic fields
        message_id = self._extract_message_id(raw_message)
        thread_id = self._extract_thread_id(raw_message)
        subject = raw_message.get('Subject', '(No Subject)')
        
        # Parse addresses
        from_name, from_addr = parseaddr(raw_message.get('From', ''))
        to_addrs = self._parse_address_list(raw_message.get('To', ''))
        cc_addrs = self._parse_address_list(raw_message.get('Cc', ''))
        
        # Parse date
        date_iso = self._parse_date(raw_message)
        
        # Extract body
        body_text, body_html = self._extract_body(raw_message)
        
        # Strip quotes if enabled
        if self.strip_quotes and body_text:
            body_text = self._strip_quotes_and_signatures(body_text)
        
        # Extract attachments
        attachments = self._extract_attachments(raw_message)
        
        # Extract raw headers
        raw_headers = dict(raw_message.items())
        
        # Create metadata
        now = datetime.now().isoformat()
        metadata = MessageMetadata(
            fetched_at=now,
            source="imap",
            normalized_at=now
        )
        
        return NormalizedMessage(
            id=message_id,
            thread_id=thread_id,
            subject=subject,
            from_addr=from_addr,
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            date=date_iso,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            raw_headers=raw_headers,
            metadata=metadata
        )
    
    def _extract_message_id(self, raw_message: Message) -> str:
        """Extract Message-ID from headers."""
        msg_id = raw_message.get('Message-ID', '')
        if not msg_id:
            # Generate fallback ID from subject and date
            subject = raw_message.get('Subject', '')
            date = raw_message.get('Date', '')
            fallback = f"{subject}{date}".encode('utf-8')
            msg_id = f"<generated-{hashlib.md5(fallback).hexdigest()}@contextcatcher>"
        return msg_id
    
    def _extract_thread_id(self, raw_message: Message) -> str:
        """
        Extract or generate thread ID from headers.
        Uses In-Reply-To or References headers, falls back to subject-based grouping.
        """
        # Try In-Reply-To first
        in_reply_to = raw_message.get('In-Reply-To', '')
        if in_reply_to:
            return in_reply_to
        
        # Try References (use first reference)
        references = raw_message.get('References', '')
        if references:
            refs = references.split()
            if refs:
                return refs[0]
        
        # Fall back to subject-based grouping
        subject = raw_message.get('Subject', '(No Subject)')
        # Remove Re:, Fwd:, etc.
        clean_subject = re.sub(r'^(Re|Fwd|Fw):\s*', '', subject, flags=re.IGNORECASE)
        # Generate thread ID from cleaned subject
        thread_id = f"<thread-{hashlib.md5(clean_subject.encode('utf-8')).hexdigest()}@contextcatcher>"
        return thread_id
    
    def _parse_address_list(self, address_string: str) -> List[str]:
        """Parse comma-separated email addresses."""
        if not address_string:
            return []
        
        addresses = []
        for addr in address_string.split(','):
            name, email_addr = parseaddr(addr.strip())
            if email_addr:
                addresses.append(email_addr)
        
        return addresses
    
    def _parse_date(self, raw_message: Message) -> str:
        """Parse date to ISO8601 format."""
        date_str = raw_message.get('Date', '')
        
        try:
            # Parse email date
            dt = parsedate_to_datetime(date_str)
            # Convert to ISO8601
            return dt.isoformat()
        except Exception:
            # Fallback to current time
            return datetime.now().isoformat()
    
    def _extract_body(self, raw_message: Message) -> Tuple[str, Optional[str]]:
        """
        Extract plain text and HTML body from message.
        
        Returns:
            Tuple of (plain_text, html_text)
        """
        body_text = ""
        body_html = None
        
        if raw_message.is_multipart():
            # Handle multipart messages
            for part in raw_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        text = payload.decode(charset, errors='ignore')
                        
                        if content_type == 'text/plain' and not body_text:
                            body_text = text
                        elif content_type == 'text/html' and not body_html:
                            body_html = text
                except Exception:
                    continue
        else:
            # Handle simple messages
            try:
                payload = raw_message.get_payload(decode=True)
                if payload:
                    charset = raw_message.get_content_charset() or 'utf-8'
                    body_text = payload.decode(charset, errors='ignore')
            except Exception:
                body_text = str(raw_message.get_payload())
        
        return body_text, body_html
    
    def _strip_quotes_and_signatures(self, text: str) -> str:
        """
        Remove quoted replies and email signatures.
        
        Args:
            text: Original message body
            
        Returns:
            Text with quotes and signatures removed
        """
        lines = text.split('\n')
        result_lines = []
        
        for line in lines:
            # Skip quoted lines (starting with >, |, or "On ... wrote:")
            if line.strip().startswith('>'):
                continue
            if line.strip().startswith('|'):
                continue
            if re.match(r'^On .+ wrote:', line.strip()):
                break  # Stop processing after "On ... wrote:"
            
            # Stop at common signature markers
            if line.strip() in ['--', '___', '---']:
                break
            if line.strip().startswith('Sent from'):
                break
            if line.strip() in ['Best regards', 'Best', 'Thanks', 'Thank you', 'Regards']:
                # Include this line but stop after
                result_lines.append(line)
                break
            
            result_lines.append(line)
        
        return '\n'.join(result_lines).strip()
    
    def _extract_attachments(self, raw_message: Message) -> List[AttachmentMetadata]:
        """
        Extract attachment metadata (without content).
        
        Returns:
            List of attachment metadata
        """
        attachments = []
        
        if raw_message.is_multipart():
            for part in raw_message.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        content_type = part.get_content_type()
                        
                        # Get size
                        payload = part.get_payload(decode=True)
                        size_bytes = len(payload) if payload else 0
                        
                        attachments.append(AttachmentMetadata(
                            filename=filename,
                            content_type=content_type,
                            size_bytes=size_bytes
                        ))
        
        return attachments
