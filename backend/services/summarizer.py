"""Message summarizer with LLM and heuristic implementations."""
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import List
from collections import Counter

from backend.models import NormalizedMessage, Summary, ActionItem
from backend.config import LLMConfig

logger = logging.getLogger(__name__)


class Summarizer(ABC):
    """Abstract base class for summarizers."""
    
    @abstractmethod
    def generate_summary(self, messages: List[NormalizedMessage]) -> Summary:
        """
        Generate digest and extract action items.
        
        Args:
            messages: List of messages to summarize
            
        Returns:
            Summary with digest and action items
        """
        pass


class LLMSummarizer(Summarizer):
    """Summarizer using LLM (OpenAI)."""
    
    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config
        self._client = None
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.llm_config.api_key)
            except ImportError:
                raise Exception("OpenAI package not installed. Run: pip install openai")
        return self._client
    
    def generate_summary(self, messages: List[NormalizedMessage]) -> Summary:
        """Generate summary using LLM."""
        if not messages:
            return Summary(
                digest="No messages to summarize.",
                action_items=[],
                confidence=0.0,
                message_count=0
            )
        
        try:
            # Prepare message summaries for LLM
            message_summaries = []
            for msg in messages[:10]:  # Limit to avoid token limits
                summary = f"From: {msg.from_addr}\n"
                summary += f"Subject: {msg.subject}\n"
                summary += f"Date: {msg.date}\n"
                summary += f"Body: {msg.body_text[:500]}...\n"  # First 500 chars
                message_summaries.append(summary)
            
            # Create prompt
            prompt = f"""Analyze these {len(messages)} emails and provide a comprehensive summary with actionable tasks.

Messages:
{chr(10).join(message_summaries)}

Please provide:
1. A clear, organized digest covering:
   - Key topics and themes
   - Important information or updates
   - Decisions or announcements
   - Any urgent matters

2. Extract ALL tasks, action items, or requests including:
   - Explicit requests ("please do X", "can you Y")
   - Implicit tasks ("we need to", "should", "must")
   - Deadlines or time-sensitive items
   - Follow-ups required
   - Questions that need answers

Respond with JSON in this exact format:
{{
  "digest": "Well-organized summary with clear sections and bullet points",
  "action_items": [
    {{
      "action": "Clear description of what needs to be done",
      "owner": "person responsible or null if not specified",
      "deadline": "deadline if mentioned or null",
      "evidence_snippet": "relevant quote from the email showing this task"
    }}
  ],
  "confidence": 0.9
}}"""
            
            # Call LLM
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {"role": "system", "content": "You are an email analysis assistant. Generate concise summaries and extract action items."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            result = json.loads(content)
            
            # Create action items
            action_items = []
            for item in result.get("action_items", []):
                action_items.append(ActionItem(
                    action=item.get("action", ""),
                    owner=item.get("owner"),
                    deadline=item.get("deadline"),
                    evidence_snippet=item.get("evidence_snippet", "")
                ))
            
            return Summary(
                digest=result.get("digest", ""),
                action_items=action_items,
                confidence=result.get("confidence", 0.8),
                message_count=len(messages)
            )
            
        except Exception as e:
            logger.error(f"LLM summarization failed: {str(e)}")
            # Fallback to heuristic
            logger.info("Falling back to heuristic summarizer")
            fallback = HeuristicSummarizer()
            return fallback.generate_summary(messages)


class HeuristicSummarizer(Summarizer):
    """Fallback summarizer using keyword extraction."""
    
    def generate_summary(self, messages: List[NormalizedMessage]) -> Summary:
        """Generate summary using heuristic approach."""
        if not messages:
            return Summary(
                digest="No messages to summarize.",
                action_items=[],
                confidence=0.0,
                message_count=0
            )
        
        # Extract keywords and topics
        all_text = " ".join([msg.subject + " " + msg.body_text for msg in messages])
        words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
        
        # Get most common words (excluding common stop words)
        stop_words = {'that', 'this', 'with', 'from', 'have', 'will', 'your', 'about', 'been', 'were', 'their'}
        filtered_words = [w for w in words if w not in stop_words]
        common_words = Counter(filtered_words).most_common(10)
        
        # Build digest
        digest_lines = [
            f"Summary of {len(messages)} messages:",
            f"Date range: {messages[-1].date} to {messages[0].date}",
            f"Participants: {len(set(msg.from_addr for msg in messages))} unique senders",
            "",
            "Top topics:",
        ]
        
        for word, count in common_words[:5]:
            digest_lines.append(f"  - {word.capitalize()} (mentioned {count} times)")
        
        digest_lines.append("")
        digest_lines.append("Recent subjects:")
        for msg in messages[:3]:
            digest_lines.append(f"  - {msg.subject}")
        
        digest = "\n".join(digest_lines)
        
        # Extract potential action items (imperative sentences and task patterns)
        action_items = []
        action_patterns = [
            r'^(Please|Could you|Can you|Would you|Will you)',
            r'^(Need to|Must|Should|Have to|Got to)',
            r'^(Let\'s|We need|We should|We must)',
            r'(action required|todo|to-do|task|deadline)',
            r'(by \w+day|by \d+|due|before \d+)',
        ]
        
        for msg in messages:
            # Look for action patterns in body
            sentences = re.split(r'[.!?\n]+', msg.body_text)
            for sentence in sentences[:20]:  # Check more sentences
                sentence = sentence.strip()
                if len(sentence) < 10:  # Skip very short sentences
                    continue
                    
                # Check if sentence matches any action pattern
                for pattern in action_patterns:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        action_items.append(ActionItem(
                            action=sentence[:150],  # Slightly longer limit
                            owner=None,
                            deadline=None,
                            evidence_snippet=f"From: {msg.from_addr}, Subject: {msg.subject}"
                        ))
                        break  # Don't match same sentence multiple times
                        
                if len(action_items) >= 10:  # Increased limit
                    break
            if len(action_items) >= 10:
                break
        
        return Summary(
            digest=digest,
            action_items=action_items,
            confidence=0.5,  # Lower confidence for heuristic
            message_count=len(messages)
        )


def create_summarizer(llm_config: LLMConfig) -> Summarizer:
    """
    Factory function to create appropriate summarizer.
    
    Args:
        llm_config: LLM configuration
        
    Returns:
        LLMSummarizer if enabled, otherwise HeuristicSummarizer
    """
    if llm_config.enabled and llm_config.api_key:
        return LLMSummarizer(llm_config)
    else:
        return HeuristicSummarizer()
