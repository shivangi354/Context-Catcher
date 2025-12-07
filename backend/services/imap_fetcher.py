"""IMAP email fetcher with retry logic."""
import imaplib
import email
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from email.message import Message

from backend.config import EmailConfig, FetchConfig
from backend.models import FetchResult

# Configure logging to never show passwords
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IMAPFetcher:
    """Fetches emails from IMAP server with retry logic."""
    
    def __init__(self, email_config: EmailConfig, fetch_config: FetchConfig):
        self.email_config = email_config
        self.fetch_config = fetch_config
        self._connection = None
    
    def fetch_messages(self, since_hours: int = None) -> Tuple[List[Message], List[str]]:
        """
        Fetch messages from IMAP server.
        
        Args:
            since_hours: Hours to look back (overrides config if provided)
            
        Returns:
            Tuple of (list of raw email messages, list of errors)
        """
        errors = []
        messages = []
        
        # Determine lookback period
        if since_hours is not None:
            lookback = since_hours
        else:
            lookback = self.fetch_config.get_lookback_hours()
        # Use timezone-aware datetime for proper comparison with INTERNALDATE
        since_date = datetime.now(timezone.utc) - timedelta(hours=lookback)
        
        try:
            # Connect with retry
            connection = self._connect_with_retry()
            
            # Fetch message IDs
            message_ids = self._fetch_message_ids(connection, since_date)
            logger.info(f"Found {len(message_ids)} messages since {since_date.isoformat()}")
            
            # Fetch each message
            for msg_id in message_ids:
                try:
                    raw_message = self._fetch_raw_message(connection, msg_id)
                    messages.append(raw_message)
                except Exception as e:
                    error_msg = f"Failed to fetch message {msg_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Logout
            connection.logout()
            
        except Exception as e:
            error_msg = f"IMAP fetch failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return messages, errors
    
    def _connect_with_retry(self) -> imaplib.IMAP4_SSL:
        """
        Connect to IMAP server with exponential backoff retry.
        
        Returns:
            Connected IMAP connection
            
        Raises:
            Exception if all retries fail
        """
        last_error = None
        
        for attempt in range(self.fetch_config.max_retries):
            try:
                # Log connection attempt (without password)
                logger.info(f"Connecting to IMAP server {self.email_config.host}:{self.email_config.port} "
                           f"as {self.email_config.username} (attempt {attempt + 1}/{self.fetch_config.max_retries})")
                
                # Create connection
                if self.email_config.use_ssl:
                    connection = imaplib.IMAP4_SSL(
                        self.email_config.host,
                        self.email_config.port
                    )
                else:
                    connection = imaplib.IMAP4(
                        self.email_config.host,
                        self.email_config.port
                    )
                
                # Login (password never logged)
                connection.login(self.email_config.username, self.email_config.password)
                
                # Select inbox
                connection.select('INBOX')
                
                logger.info("Successfully connected to IMAP server")
                return connection
                
            except Exception as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                
                # Don't sleep after last attempt
                if attempt < self.fetch_config.max_retries - 1:
                    delay = self.fetch_config.retry_backoff_base ** attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries failed
        raise Exception(f"Failed to connect after {self.fetch_config.max_retries} attempts: {str(last_error)}")
    
    def _fetch_message_ids(self, connection: imaplib.IMAP4_SSL, since_date: datetime) -> List[bytes]:
        """
        Search for message IDs since given date.
        
        Args:
            connection: Active IMAP connection
            since_date: Fetch messages since this date
            
        Returns:
            List of message IDs
        """
        if self.fetch_config.use_arrival_date:
            # Use arrival date - fetch all messages and filter by INTERNALDATE
            logger.info("Using arrival date for filtering (more accurate for recent emails)")
            return self._fetch_by_arrival_date(connection, since_date)
        else:
            # Use sent date (SINCE command)
            logger.info("Using sent date for filtering")
            return self._fetch_by_sent_date(connection, since_date)
    
    def _fetch_by_sent_date(self, connection: imaplib.IMAP4_SSL, since_date: datetime) -> List[bytes]:
        """Fetch messages by sent date (original SINCE behavior)."""
        # Format date for IMAP SINCE search (DD-Mon-YYYY)
        date_str = since_date.strftime("%d-%b-%Y")
        
        # Build search criteria
        if self.fetch_config.primary_only:
            # Gmail-specific: exclude promotions, social, updates, forums
            search_criteria = f'(SINCE {date_str} NOT X-GM-LABELS "\\\\Promotions" NOT X-GM-LABELS "\\\\Social" NOT X-GM-LABELS "\\\\Updates" NOT X-GM-LABELS "\\\\Forums")'
            logger.info("Filtering for primary inbox only (excluding promotions, social, updates, forums)")
        else:
            search_criteria = f'SINCE {date_str}'
        
        # Search for messages
        status, data = connection.search(None, search_criteria)
        
        if status != 'OK':
            raise Exception(f"IMAP search failed with status: {status}")
        
        return data[0].split()
    
    def _fetch_by_arrival_date(self, connection: imaplib.IMAP4_SSL, since_date: datetime) -> List[bytes]:
        """Fetch messages by arrival date (when they arrived in your inbox)."""
        import email.utils
        import re
        
        # For arrival date, we need to check INTERNALDATE
        # Strategy: Get recent message IDs (last 100) and filter by INTERNALDATE
        # This is much faster than checking all messages
        
        # Build search criteria to get recent messages
        if self.fetch_config.primary_only:
            # Gmail-specific: exclude promotions, social, updates, forums
            search_criteria = f'(NOT X-GM-LABELS "\\\\Promotions" NOT X-GM-LABELS "\\\\Social" NOT X-GM-LABELS "\\\\Updates" NOT X-GM-LABELS "\\\\Forums")'
            logger.info("Filtering for primary inbox only (excluding promotions, social, updates, forums)")
        else:
            search_criteria = 'ALL'
        
        # Search for messages
        status, data = connection.search(None, search_criteria)
        
        if status != 'OK':
            raise Exception(f"IMAP search failed with status: {status}")
        
        all_message_ids = data[0].split()
        
        # Only check the most recent N messages (sorted in reverse to get newest first)
        # For a 2-minute lookback, checking last 50 messages should be more than enough
        max_to_check = 50
        recent_ids = all_message_ids[-max_to_check:] if len(all_message_ids) > max_to_check else all_message_ids
        
        logger.info(f"Checking INTERNALDATE for {len(recent_ids)} most recent messages (out of {len(all_message_ids)} total)")
        
        # Now filter by INTERNALDATE (arrival date)
        filtered_ids = []
        for msg_id in recent_ids:
            try:
                # Fetch INTERNALDATE for this message
                status, data = connection.fetch(msg_id, '(INTERNALDATE)')
                if status == 'OK' and data and data[0]:
                    response = data[0].decode('utf-8') if isinstance(data[0], bytes) else str(data[0])
                    # Extract date from response like: '1 (INTERNALDATE "05-Dec-2024 10:30:00 +0000")'
                    date_match = re.search(r'INTERNALDATE "([^"]+)"', response)
                    if date_match:
                        date_str_internal = date_match.group(1)
                        # Parse the date
                        internal_date = email.utils.parsedate_to_datetime(date_str_internal)
                        
                        # Check if it's within our lookback period
                        if internal_date >= since_date:
                            filtered_ids.append(msg_id)
            except Exception as e:
                logger.warning(f"Failed to check INTERNALDATE for message {msg_id}: {str(e)}")
                # Skip messages we can't check
                continue
        
        logger.info(f"Found {len(filtered_ids)} messages by arrival date from {len(recent_ids)} checked")
        return filtered_ids
    
    def _fetch_raw_message(self, connection: imaplib.IMAP4_SSL, msg_id: bytes) -> Message:
        """
        Fetch raw email message by ID.
        
        Args:
            connection: Active IMAP connection
            msg_id: Message ID to fetch
            
        Returns:
            Parsed email message
        """
        # Fetch message
        status, data = connection.fetch(msg_id, '(RFC822)')
        
        if status != 'OK':
            raise Exception(f"Failed to fetch message {msg_id}")
        
        # Parse email
        raw_email = data[0][1]
        message = email.message_from_bytes(raw_email)
        
        return message
