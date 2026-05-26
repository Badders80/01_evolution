"""
corrections.py
Applies domain-specific regular expression mapping to transcripts (e.g. 'weak white week' -> 'quiet week').
"""

import os
import re
import json
import logging

logger = logging.getLogger(__name__)

CORRECTIONS_FILE = os.path.join(os.path.dirname(__file__), "transcript-corrections.json")

class CorrectionsApplier:
    def __init__(self):
        self.rules = []
        self._load_rules()

    def _load_rules(self):
        if not os.path.exists(CORRECTIONS_FILE):
            logger.warning(f"Transcript corrections dictionary not found at {CORRECTIONS_FILE}")
            return
        
        try:
            with open(CORRECTIONS_FILE, "r") as f:
                data = json.load(f)
                self.rules = data.get("applyRules", [])
                logger.info(f"Loaded {len(self.rules)} transcription correction rules.")
        except Exception as e:
            logger.error(f"Failed to load transcription corrections: {e}")

    def apply(self, text: str) -> str:
        """Apply all corrections rules to a given string of text."""
        if not text or not self.rules:
            return text
        
        modified = text
        for rule in self.rules:
            pattern_str = rule.get("pattern")
            replacement = rule.get("replacement")
            if pattern_str and replacement is not None:
                try:
                    # Ignore case for robust matching
                    modified = re.sub(pattern_str, replacement, modified, flags=re.IGNORECASE)
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
        
        return modified

    def apply_to_transcript_result(self, transcript_result):
        """
        Apply rules to a TranscriptResult Pydantic model (or a dict of equivalent structure).
        Modifies segments in-place and updates the full concatenated text.
        """
        if not transcript_result:
            return transcript_result

        # Detect if Pydantic model or dict
        is_pydantic = hasattr(transcript_result, "segments") and hasattr(transcript_result, "full_text")

        segments = transcript_result.segments if is_pydantic else transcript_result.get("segments", [])
        
        # Apply to each individual segment
        for segment in segments:
            if is_pydantic:
                segment.text = self.apply(segment.text)
            else:
                segment["text"] = self.apply(segment.get("text", ""))

        # Re-build full_text based on corrected segments
        if is_pydantic:
            transcript_result.full_text = " ".join(s.text for s in segments)
        else:
            transcript_result["full_text"] = " ".join(s.get("text", "") for s in segments)

        return transcript_result
