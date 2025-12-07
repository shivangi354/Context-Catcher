#!/usr/bin/env python3
"""Test IMAP connection with current credentials."""
import imaplib
import json

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

email = config['email']['username']
password = config['email']['password']
host = config['email']['host']
port = config['email']['port']

print(f"Testing IMAP connection...")
print(f"Host: {host}:{port}")
print(f"Email: {email}")
print(f"Password: {'*' * len(password)} ({len(password)} characters)")
print()

try:
    print("Connecting...")
    conn = imaplib.IMAP4_SSL(host, port)
    print("✓ SSL connection established")
    
    print("Logging in...")
    conn.login(email, password)
    print("✓ Login successful!")
    
    print("Selecting INBOX...")
    conn.select('INBOX')
    print("✓ INBOX selected")
    
    print("\n🎉 SUCCESS! IMAP connection works!")
    
    conn.logout()
    
except Exception as e:
    print(f"\n❌ FAILED: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Verify the app password is correct")
    print("2. Check IMAP is enabled in Gmail settings")
    print("3. Make sure 2-Step Verification is enabled")
    print("4. Try creating a new app password")
