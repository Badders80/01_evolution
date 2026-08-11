"""
reconciler.py
Handles multi-engine ASR transcript consensus reconciliation using Ollama (local/cloud)
and a domain-specific knowledge base.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

KB_FILE = os.path.join(os.path.dirname(__file__), "knowledge-base.json")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

class TranscriptReconciler:
    def __init__(self):
        self.kb_data = {}
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load domain-specific entities (horses, venues, people, racing terms) from JSON."""
        if not os.path.exists(KB_FILE):
            logger.warning(f"Knowledge base not found at {KB_FILE}")
            return
        
        try:
            with open(KB_FILE, "r") as f:
                self.kb_data = json.load(f)
                logger.info("Loaded domain knowledge base for reconciliation.")
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")

    def _build_knowledge_base_context(self) -> str:
        """Construct a readable text summary of the knowledge base for LLM context."""
        context_parts = []
        
        # Horses
        for name, data in self.kb_data.get("horses", {}).items():
            aliases_str = ", ".join(data.get("aliases", []))
            context_parts.append(f"Horse: {name} (stable: {data.get('stable')}, type: {data.get('type')}, aliases: [{aliases_str}])")
            
        # Venues
        for name, data in self.kb_data.get("venues", {}).items():
            aliases_str = ", ".join(data.get("aliases", []))
            context_parts.append(f"Venue: {name} (location: {data.get('location')}, aliases: [{aliases_str}])")
            
        # People
        for name, data in self.kb_data.get("people", {}).items():
            aliases_str = ", ".join(data.get("aliases", []))
            context_parts.append(f"Person: {name} (role: {data.get('role')}, aliases: [{aliases_str}])")
            
        # Racing Terms
        for term, data in self.kb_data.get("racingTerms", {}).items():
            aliases_str = ", ".join(data.get("aliases", []))
            context_parts.append(f"Term: {term} (meaning: {data.get('meaning')}, aliases: [{aliases_str}])")
            
        return "\n".join(context_parts)

    def reconcile(self, transcripts_dict: dict[str, str], meta: dict = None) -> dict:
        """
        Reconcile multiple engine transcripts using Ollama.
        
        Args:
            transcripts_dict: Dict mapping engine_name -> transcript_text.
                              E.g. {"google_speech_v1": "some text...", "nvidia_canary": "some text"}
            meta: Dict with metadata like {"horse": "Prudentia", "venue": "Te Rapa", "content_type": "update"}
            
        Returns:
            Dict matching the schema:
            {
              "finalText": "reconciled text",
              "confidence": "high|medium|low",
              "changes": [{"original": "...", "corrected": "...", "reason": "..."}],
              "needsHumanReview": False,
              "reviewReason": "",
              "reconciliation_model": "..."
            }
        """
        if not transcripts_dict:
            return {}

        meta = meta or {}
        
        # Deduplicate candidate transcripts to save input length/tokens
        filtered_transcripts = {}
        seen_texts = set()
        for engine, text in transcripts_dict.items():
            if not text:
                continue
            normalized = "".join(c.lower() for c in text if c.isalnum())
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                filtered_transcripts[engine] = text

        # If we have nothing to reconcile, return empty
        if not filtered_transcripts:
            return {}

        # Build prompt
        kb_context = self._build_knowledge_base_context()
        transcripts_section = "\n\n".join(
            f"--- {engine.upper()} ---\n{text}"
            for engine, text in filtered_transcripts.items()
        )

        content_type = meta.get("content_type", "unknown")
        speakers = meta.get("speakers") or []
        is_interview = content_type == "interview"

        if is_interview:
            domain_section = (
                "DOMAIN CONTEXT:\n"
                f"- This is an academic research interview.\n"
                f"- Expected speakers: {', '.join(speakers) if speakers else 'unknown'}\n"
                f"- Preserve speaker attribution and quoted wording faithfully.\n"
            )
            kb_section = ""
            reconcile_guidance = (
                "2. Resolve ambiguous or misheard words using context and proper nouns from the transcripts.\n"
                "3. For disagreements, prefer the version that is grammatically correct and contextually plausible.\n"
                "4. Do not paraphrase — keep the speakers' original meaning and phrasing.\n"
                "5. Flag any remaining uncertain words for human review."
            )
        else:
            domain_section = (
                "KNOWLEDGE BASE (correct names, terms, and aliases):\n"
                f"{kb_context}\n"
            )
            kb_section = ""
            reconcile_guidance = (
                '2. Use the knowledge base to resolve ambiguous or misheard words (e.g., "mere" → "mare", "Ninja" → "Prudentia", "run the truck" → "run the trip", "healthy meat" → "healthy mare", "weak white week" → "quiet week", "twelve hundred teams" → "twelve hundred meters").\n'
                "3. For words where models disagree or there is an acoustic error, choose the version that best matches the knowledge base and stable context.\n"
                "4. Flag any remaining uncertain words for human review."
            )

        prompt = f"""You are a transcript reconciliation expert. You have {len(filtered_transcripts)} different ASR (automatic speech recognition) transcripts of the same audio. Your job is to produce the most accurate final transcript.

{domain_section}
METADATA:
- Subject: {meta.get('horse', meta.get('subject', 'unknown'))}
- Title: {meta.get('title', 'unknown')}
- Venue: {meta.get('venue', 'unknown')}
- Content type: {content_type}

TRANSCRIPTS TO RECONCILE:
{transcripts_section}

TASK:
1. Compare all transcripts word-by-word (or read the single transcript if only one is provided).
{reconcile_guidance}

Return ONLY a JSON object with this exact structure:
{{
  "finalText": "the reconciled transcript text",
  "confidence": "high|medium|low",
  "changes": [
    {{ "original": "mere", "corrected": "mare", "reason": "horse name from knowledge base" }}
  ],
  "needsHumanReview": false,
  "reviewReason": ""
}}

Rules:
- If confidence is "low" or any word is highly uncertain, set needsHumanReview: true
- The finalText should be natural, readable English
- Do NOT include markdown code blocks, only raw JSON
"""

        from model_router import get_router
        router = get_router()

        for model in [os.getenv("OLLAMA_MODEL", "glm-5.2"), os.getenv("OLLAMA_FALLBACK_MODEL", "deepseek-v4-flash")]:
            try:
                logger.info(f"Reconciling transcripts using Ollama model {model}...")
                raw_content = router.chat(
                    prompt=prompt,
                    system=None,
                    temperature=0.1,
                    format_json=True,
                    timeout=45,
                )
                
                # Sanitize content if model enclosed it in markdown code blocks
                if raw_content.startswith("```json"):
                    raw_content = raw_content.split("```json", 1)[1]
                if raw_content.endswith("```"):
                    raw_content = raw_content.rsplit("```", 1)[0]
                raw_content = raw_content.strip()
                
                result = json.loads(raw_content)
                result["reconciliation_model"] = model
                return result
                
            except Exception as e:
                logger.warning(f"Ollama reconciliation with {model} failed: {e}")
                continue

        logger.error("All Ollama reconciliation models failed.")
        return {}
