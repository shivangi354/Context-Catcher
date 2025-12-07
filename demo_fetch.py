#!/usr/bin/env python3
"""Demo script for ContextCatcher - Fetch and display messages with summary."""
import sys
from backend.config import Config
from backend.services.imap_fetcher import IMAPFetcher
from backend.services.normalizer import MessageNormalizer
from backend.services.summarizer import create_summarizer
from backend.storage.adapter import JSONStorageAdapter


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def print_message(msg, index):
    """Print a formatted message."""
    print(f"Message {index}:")
    print(f"  ID: {msg.id}")
    print(f"  From: {msg.from_addr}")
    print(f"  To: {', '.join(msg.to_addrs)}")
    print(f"  Subject: {msg.subject}")
    print(f"  Date: {msg.date}")
    print(f"  Body Preview: {msg.body_text[:200]}...")
    if msg.attachments:
        print(f"  Attachments: {len(msg.attachments)}")
        for att in msg.attachments:
            print(f"    - {att.filename} ({att.size_bytes} bytes)")
    print()


def print_summary(summary):
    """Print a formatted summary."""
    print("SUMMARY")
    print("-" * 80)
    print(summary.digest)
    print()
    
    print(f"Confidence: {summary.confidence:.0%}")
    print(f"Messages Analyzed: {summary.message_count}")
    print()
    
    if summary.action_items:
        print("ACTION ITEMS")
        print("-" * 80)
        for i, item in enumerate(summary.action_items, 1):
            print(f"{i}. {item.action}")
            if item.owner:
                print(f"   Owner: {item.owner}")
            if item.deadline:
                print(f"   Deadline: {item.deadline}")
            if item.evidence_snippet:
                print(f"   Evidence: {item.evidence_snippet[:100]}...")
            print()
    else:
        print("No action items extracted.")


def main():
    """Run the demo."""
    print_separator()
    print("ContextCatcher Demo - Email Fetch and Analysis")
    print_separator()
    
    try:
        # Load configuration
        print("Loading configuration...")
        config = Config.load()
        print(f"✓ Config loaded")
        print(f"  Email: {config.email.username}")
        print(f"  Lookback: {config.fetch.lookback_hours} hours")
        print(f"  LLM Enabled: {config.llm.enabled}")
        
        # Initialize components
        print("\nInitializing components...")
        imap_fetcher = IMAPFetcher(config.email, config.fetch)
        normalizer = MessageNormalizer(strip_quotes=config.fetch.strip_quotes)
        storage = JSONStorageAdapter(config.storage.dir, config.storage.index_file)
        summarizer = create_summarizer(config.llm)
        print("✓ Components initialized")
        
        # Fetch messages
        print_separator()
        print(f"Fetching emails from last {config.fetch.lookback_hours} hours...")
        raw_messages, errors = imap_fetcher.fetch_messages()
        
        if errors:
            print(f"\n⚠️  Encountered {len(errors)} errors:")
            for error in errors:
                print(f"  - {error}")
        
        if not raw_messages:
            print("\n❌ No messages fetched. Check your configuration and try again.")
            return 1
        
        print(f"✓ Fetched {len(raw_messages)} messages")
        
        # Normalize and store
        print("\nNormalizing and storing messages...")
        normalized_messages = []
        new_count = 0
        duplicate_count = 0
        
        for raw_msg in raw_messages:
            try:
                normalized = normalizer.normalize(raw_msg)
                normalized_messages.append(normalized)
                
                is_new = storage.save_message(normalized)
                if is_new:
                    new_count += 1
                else:
                    duplicate_count += 1
            except Exception as e:
                print(f"  ⚠️  Failed to process message: {str(e)}")
        
        print(f"✓ Processed {len(normalized_messages)} messages")
        print(f"  New: {new_count}")
        print(f"  Duplicates: {duplicate_count}")
        
        # Display latest 3 messages
        print_separator()
        print("LATEST 3 NORMALIZED MESSAGES")
        print_separator()
        
        latest_messages = normalized_messages[:3]
        for i, msg in enumerate(latest_messages, 1):
            print_message(msg, i)
        
        # Generate summary
        print_separator()
        print("Generating summary...")
        summary = summarizer.generate_summary(normalized_messages[:5])
        print("✓ Summary generated")
        
        print_separator()
        print_summary(summary)
        
        # Show storage stats
        print_separator()
        stats = storage.get_stats()
        print("STORAGE STATISTICS")
        print("-" * 80)
        print(f"Total Messages: {stats.message_count}")
        print(f"Total Threads: {stats.thread_count}")
        if stats.oldest_message:
            print(f"Oldest Message: {stats.oldest_message}")
        if stats.newest_message:
            print(f"Newest Message: {stats.newest_message}")
        
        print_separator()
        print("✅ Demo completed successfully!")
        print("\nNext steps:")
        print("  1. Start the backend: python backend/main.py")
        print("  2. Start the UI: streamlit run ui/app.py")
        print("  3. Open http://localhost:8501 in your browser")
        print_separator()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
