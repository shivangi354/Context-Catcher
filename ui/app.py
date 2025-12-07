"""Streamlit UI for ContextCatcher."""
import streamlit as st
import requests
import json
import os
import subprocess
from datetime import datetime
from typing import Optional, List, Dict

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")

# Page config
st.set_page_config(
    page_title="ContextCatcher",
    page_icon="📧",
    layout="wide"
)

# Initialize session state
if 'selected_message' not in st.session_state:
    st.session_state.selected_message = None
if 'fetching' not in st.session_state:
    st.session_state.fetching = False


def load_config() -> Dict:
    """Load configuration from file."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        st.error(f"Failed to load config: {str(e)}")
        return {}


def mask_email(email: str) -> str:
    """Mask email address for display."""
    if '@' in email:
        parts = email.split('@')
        if len(parts[0]) > 3:
            return f"{parts[0][:3]}***@{parts[1]}"
        else:
            return f"***@{parts[1]}"
    return email


def open_config_file():
    """Open config file in default editor."""
    try:
        if os.path.exists(CONFIG_PATH):
            if os.name == 'nt':  # Windows
                os.startfile(CONFIG_PATH)
            elif os.name == 'posix':  # macOS/Linux
                subprocess.run(['open', CONFIG_PATH])
        else:
            st.warning(f"Config file not found: {CONFIG_PATH}")
    except Exception as e:
        st.error(f"Failed to open config: {str(e)}")


def fetch_from_api(endpoint: str, method: str = "GET", data: dict = None) -> Optional[dict]:
    """Make API request."""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        # Use longer timeout for fetch operations (up to 5 minutes)
        timeout = 300 if endpoint == "/fetch" else 30
        
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            return None
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API request failed: {str(e)}")
        return None


# Main UI
st.title("📧 ContextCatcher")
st.markdown("Email ingestion and analysis platform")

# Top: Config Section
st.header("⚙️ Configuration")
config = load_config()

col1, col2 = st.columns([3, 1])
with col1:
    if config.get('email'):
        email_username = config['email'].get('username', 'Not configured')
        st.text(f"Email: {mask_email(email_username)}")
    else:
        st.text("Email: Not configured")
    
    if config.get('fetch'):
        lookback_minutes = config['fetch'].get('lookback_minutes')
        lookback_hours = config['fetch'].get('lookback_hours', 24)
        primary_only = config['fetch'].get('primary_only', False)
        
        if lookback_minutes is not None:
            st.text(f"Lookback: {lookback_minutes} minutes")
        else:
            st.text(f"Lookback: {lookback_hours} hours")
        
        if primary_only:
            st.text("Filter: Primary inbox only ✓")
        else:
            st.text("Filter: All emails")
    else:
        st.text("Lookback: Not configured")

with col2:
    if st.button("📝 Edit Config"):
        open_config_file()

st.markdown("---")

# Middle: Fetch Controls
st.header("🔄 Fetch Controls")

col1, col2, col3 = st.columns([2, 2, 3])

with col1:
    if st.button("🚀 Fetch Now", disabled=st.session_state.fetching):
        st.session_state.fetching = True
        with st.spinner("Fetching emails..."):
            result = fetch_from_api("/fetch", method="POST")
            if result:
                st.success(f"✅ Fetched {result.get('fetched', 0)} new messages")
                if result.get('duplicates', 0) > 0:
                    st.info(f"ℹ️ Skipped {result['duplicates']} duplicates")
                if result.get('errors'):
                    st.warning(f"⚠️ {len(result['errors'])} errors occurred")
        st.session_state.fetching = False
        st.rerun()

with col2:
    # Get status
    status = fetch_from_api("/status")
    if status and status.get('last_fetch'):
        try:
            last_fetch = datetime.fromisoformat(status['last_fetch'])
            st.metric("Last Fetch", last_fetch.strftime("%H:%M:%S"))
        except:
            st.metric("Last Fetch", "Never")
    else:
        st.metric("Last Fetch", "Never")

with col3:
    if st.session_state.fetching:
        st.progress(0.5, text="Fetching in progress...")

st.markdown("---")

# Main Content: Two Columns
col_left, col_right = st.columns([1, 1])

with col_left:
    st.header("📬 Recent Messages")
    
    # Fetch messages
    messages_data = fetch_from_api("/messages?limit=20")
    
    if messages_data and messages_data.get('messages'):
        messages = messages_data['messages']
        
        # Display message list
        for msg in messages:
            # Create a button for each message
            button_label = f"**{msg.get('subject', '(No Subject)')}**\n{msg.get('from_addr', 'Unknown')} • {msg.get('date', '')[:10]}"
            
            if st.button(button_label, key=msg['id'], use_container_width=True):
                st.session_state.selected_message = msg['id']
                st.rerun()
        
        # Show selected message detail
        if st.session_state.selected_message:
            selected = next((m for m in messages if m['id'] == st.session_state.selected_message), None)
            if selected:
                st.markdown("---")
                st.subheader("📄 Message Detail")
                st.markdown(f"**From:** {selected.get('from_addr', 'Unknown')}")
                st.markdown(f"**To:** {', '.join(selected.get('to_addrs', []))}")
                st.markdown(f"**Subject:** {selected.get('subject', '(No Subject)')}")
                st.markdown(f"**Date:** {selected.get('date', 'Unknown')}")
                
                st.markdown("**Body:**")
                st.text_area("", selected.get('body_text', ''), height=200, key="body_display")
                
                if selected.get('attachments'):
                    st.markdown("**Attachments:**")
                    for att in selected['attachments']:
                        st.text(f"📎 {att.get('filename', 'Unknown')} ({att.get('size_bytes', 0)} bytes)")
    else:
        st.info("No messages found. Click 'Fetch Now' to retrieve emails.")

with col_right:
    st.header("📊 Summary & Action Items")
    
    # Fetch summary
    summary_data = fetch_from_api("/summary?limit=5")
    
    if summary_data:
        # Display digest
        st.subheader("Digest")
        st.text_area("", summary_data.get('digest', 'No summary available'), height=200, key="digest_display")
        
        # Display confidence
        confidence = summary_data.get('confidence', 0.0)
        st.metric("Confidence", f"{confidence:.0%}")
        
        # Display action items
        st.subheader("🎯 Action Items")
        action_items = summary_data.get('action_items', [])
        
        if action_items:
            for i, item in enumerate(action_items):
                with st.expander(f"Action {i+1}: {item.get('action', 'Unknown')[:50]}..."):
                    st.markdown(f"**Action:** {item.get('action', 'Unknown')}")
                    if item.get('owner'):
                        st.markdown(f"**Owner:** {item['owner']}")
                    if item.get('deadline'):
                        st.markdown(f"**Deadline:** {item['deadline']}")
                    if item.get('evidence_snippet'):
                        st.caption(f"Evidence: {item['evidence_snippet']}")
        else:
            st.info("No action items extracted")
    else:
        st.info("No summary available. Fetch some messages first.")

# Footer
st.markdown("---")
st.info("💬 WhatsApp, Slack integration — Coming soon")

# Sidebar with stats
with st.sidebar:
    st.header("📈 Statistics")
    
    status = fetch_from_api("/status")
    if status:
        st.metric("Total Messages", status.get('message_count', 0))
        st.metric("Total Threads", status.get('thread_count', 0))
        st.metric("System Health", status.get('health', 'Unknown'))
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("ContextCatcher MVP - Email ingestion and analysis")
    st.markdown("Version 1.0.0")
