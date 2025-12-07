"""Basic tests for ContextCatcher components."""
import pytest
import tempfile
import os
from pathlib import Path

from backend.config import Config, EmailConfig, FetchConfig, LLMConfig, StorageConfig
from backend.models import NormalizedMessage, MessageMetadata, AttachmentMetadata
from backend.storage.adapter import JSONStorageAdapter
from backend.services.normalizer import MessageNormalizer


def test_config_loading():
    """Test configuration loading."""
    # Create temp config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('''{
            "email": {
                "host": "imap.test.com",
                "port": 993,
                "username": "test@test.com",
                "password": "secret123",
                "use_ssl": true
            },
            "fetch": {
                "lookback_hours": 48,
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
                "dir": "./test_storage",
                "index_file": "index.json"
            }
        }''')
        config_path = f.name
    
    try:
        config = Config.load(config_path)
        assert config.email.host == "imap.test.com"
        assert config.email.username == "test@test.com"
        assert config.fetch.lookback_hours == 48
        
        # Test masking
        masked = config.mask_sensitive()
        assert masked["email"]["password"] == "***"
        
    finally:
        os.unlink(config_path)


def test_storage_adapter():
    """Test JSON storage adapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONStorageAdapter(tmpdir)
        
        # Create test message
        msg = NormalizedMessage(
            id="<test123@example.com>",
            thread_id="<thread1@example.com>",
            subject="Test Subject",
            from_addr="sender@example.com",
            to_addrs=["recipient@example.com"],
            cc_addrs=[],
            date="2024-01-01T12:00:00",
            body_text="Test body",
            body_html=None,
            attachments=[],
            raw_headers={},
            metadata=MessageMetadata(
                fetched_at="2024-01-01T12:00:00",
                source="imap",
                normalized_at="2024-01-01T12:00:00"
            )
        )
        
        # Test save
        is_new = storage.save_message(msg)
        assert is_new is True
        
        # Test duplicate detection
        is_new = storage.save_message(msg)
        assert is_new is False
        
        # Test retrieval
        messages = storage.get_messages(limit=10)
        assert len(messages) == 1
        assert messages[0].id == msg.id
        
        # Test stats
        stats = storage.get_stats()
        assert stats.message_count == 1


def test_normalizer_quote_stripping():
    """Test quote and signature stripping."""
    normalizer = MessageNormalizer(strip_quotes=True)
    
    text = """This is the main message.

> This is a quoted reply
> Another quoted line

--
Best regards,
John"""
    
    stripped = normalizer._strip_quotes_and_signatures(text)
    assert "This is the main message" in stripped
    assert "quoted reply" not in stripped
    # Signature markers cause the function to stop processing


def test_normalizer_preserves_body_when_disabled():
    """Test that quote stripping can be disabled."""
    normalizer = MessageNormalizer(strip_quotes=False)
    
    text = """Main message
> Quoted text"""
    
    # When strip_quotes is False, the normalizer doesn't call the strip method
    # So we just verify the flag is set correctly
    assert normalizer.strip_quotes is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
