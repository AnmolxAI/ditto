"""
Command parser for extracting structured fields from spoken commands.
Keyword-based parsing with no semantic inference.
"""

import re
from typing import Dict, List, Optional
from datetime import datetime


class CommandParser:
    """Parses structured commands from transcript text."""
    
    def __init__(self, trigger_phrase: str, field_keywords: Dict[str, any]):
        self.trigger_phrase = trigger_phrase.lower()
        self.field_keywords = field_keywords
        # Build keyword patterns
        self.keyword_patterns = {}
        for field, keywords in field_keywords.items():
            if isinstance(keywords, list):
                # Multiple keywords for same field (e.g., "label" and "labels")
                patterns = [re.escape(kw.lower()) for kw in keywords]
                self.keyword_patterns[field] = re.compile(
                    r'\b(' + '|'.join(patterns) + r')\b',
                    re.IGNORECASE
                )
            else:
                self.keyword_patterns[field] = re.compile(
                    r'\b' + re.escape(keywords.lower()) + r'\b',
                    re.IGNORECASE
                )
    
    def is_triggered(self, text: str) -> bool:
        """Check if text contains the trigger phrase."""
        return self.trigger_phrase in text.lower()
    
    def extract_fields(self, transcript_segments: List[str]) -> Dict[str, any]:
        """
        Extract fields from transcript segments.
        Fields may span multiple segments.
        Last occurrence of a field wins.
        """
        # Combine all segments
        full_text = " ".join(transcript_segments)
        full_text_lower = full_text.lower()
        
        # Find trigger position
        trigger_pos = full_text_lower.find(self.trigger_phrase)
        if trigger_pos == -1:
            return {}
        
        # Extract text after trigger
        text_after_trigger = full_text[trigger_pos + len(self.trigger_phrase):].strip()
        
        # Find all keyword positions
        keyword_positions = []
        for field, pattern in self.keyword_patterns.items():
            for match in pattern.finditer(text_after_trigger):
                keyword_positions.append({
                    "field": field,
                    "start": match.start(),
                    "end": match.end(),
                    "keyword": match.group()
                })
        
        # Sort by position
        keyword_positions.sort(key=lambda x: x["start"])
        
        # Extract values
        extracted_fields = {}
        
        for i, kw_pos in enumerate(keyword_positions):
            field = kw_pos["field"]
            start = kw_pos["end"]
            
            # Find end of value (next keyword or end of text)
            if i + 1 < len(keyword_positions):
                end = keyword_positions[i + 1]["start"]
            else:
                end = len(text_after_trigger)
            
            # Extract value
            value = text_after_trigger[start:end].strip()
            
            # Remove trailing punctuation that might be sentence endings
            value = re.sub(r'[.,;:!?]+$', '', value).strip()
            
            if value:
                # Handle labels specially (can have multiple)
                if field == "label":
                    if "label" not in extracted_fields:
                        extracted_fields["label"] = []
                    extracted_fields["label"].append(value)
                else:
                    # Last occurrence wins
                    extracted_fields[field] = value
        
        # Extract title if not explicitly provided
        if "title" not in extracted_fields:
            # Use text immediately after trigger until first keyword
            if keyword_positions:
                first_kw_start = keyword_positions[0]["start"]
                title_candidate = text_after_trigger[:first_kw_start].strip()
                # Remove trailing punctuation
                title_candidate = re.sub(r'[.,;:!?]+$', '', title_candidate).strip()
                if title_candidate:
                    extracted_fields["title"] = title_candidate
        
        return extracted_fields
    
    def get_transcript_excerpt(
        self,
        transcript_segments: List[str],
        current_time: datetime,
        window_seconds: int = 10
    ) -> str:
        """Get transcript excerpt around current time (±window_seconds)."""
        # For simplicity, return last N segments
        # In a real implementation, segments would have timestamps
        return " ".join(transcript_segments[-5:]) if transcript_segments else ""

