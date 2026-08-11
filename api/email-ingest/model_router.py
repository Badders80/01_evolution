"""
model_router.py
Account-aware, quota-gated model router for Evolution.
Enforces: Ollama Cloud default / Google only with explicit quota / FAL for media.
"""

import os
import json
import time
import logging
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Hard Policy ───────────────────────────────────────────────
# Ollama Cloud is the sole default for all text inference.
# Google Cloud (Vertex/Gemini) is ONLY for infrastructure and
# explicit, quota-tracked AI calls.  Never use it as a silent
# fallback.
# ─────────────────────────────────────────────────────────────

# Ollama Cloud (OpenAI-compatible endpoint)
# Two subscriptions: badders80 (primary) and badders808 (backup).
# Keys live in ~/.hermes/.env. The shell env OLLAMA_API_KEY may be polluted
# (e.g. SSH key from .bashrc), so we validate format and fall back to ~/.hermes/.env.
_OLLAMA_CLOUD_HOST = "https://ollama.com/v1"

def _load_ollama_keys():
    """Load both Ollama Cloud API keys from ~/.hermes/.env.
    
    Returns list of valid keys (hex-dot format), primary first.
    Handles two formats:
      - OLLAMA_API_KEY=<key>  (active, uncommented)
      - # <label> - <key>     (backup, commented with account label)
    """
    keys = []
    hermes_env = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(hermes_env):
        for line in open(hermes_env):
            line = line.strip()
            # Active key (uncommented OLLAMA_API_KEY=...)
            if line.startswith("OLLAMA_API_KEY=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip()
                if val and not val.startswith("ssh-"):
                    keys.append(val)
            # Backup key (commented line with key in hex-dot format)
            # Format: "# badders808 (backup) - 39b393e5b4264862bcc2de256b7a9c44.YlbuobD..."
            if line.startswith("#") and "backup" in line.lower():
                # Extract the hex-dot key from the comment
                import re
                m = re.search(r'([0-9a-f]{32}\.[A-Za-z0-9_\-]+)', line)
                if m:
                    keys.append(m.group(1))
    
    # Also check shell env (but validate format)
    env_key = os.getenv("OLLAMA_API_KEY", "")
    if env_key and not env_key.startswith("ssh-") and env_key not in keys:
        keys.insert(0, env_key)
    
    return keys

_OLLAMA_KEYS = _load_ollama_keys()
OLLAMA_API_KEY = _OLLAMA_KEYS[0] if _OLLAMA_KEYS else ""
OLLAMA_API_KEYS = _OLLAMA_KEYS  # All keys for rotation

# If we have an API key, always use Ollama Cloud (OpenAI-compatible /v1 endpoint).
# The OLLAMA_HOST env var (often set to 127.0.0.1:11434 in .bashrc for local Ollama)
# is for the native API, not the Cloud OpenAI-compatible endpoint.
if OLLAMA_API_KEY:
    OLLAMA_HOST = os.getenv("OLLAMA_CLOUD_HOST", _OLLAMA_CLOUD_HOST)
else:
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "glm-5.2")
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "deepseek-v4-flash")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# AI Studio — free-tier API (aistudio.google.com), NOT Vertex. Separate key.
AI_STUDIO_API_KEY = os.getenv("AI_STUDIO_API_KEY", "")
AI_STUDIO_ALLOWED = os.getenv("AI_STUDIO_ALLOW", "true").lower() == "true"

# Legacy Gemini/Vertex — gated behind explicit env flag + quota check
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_ALLOWED = os.getenv("GEMINI_ALLOW_TRANSCRIPTION", "false").lower() == "true"

# Quota tracker file (kept next to this module)
QUOTA_FILE = Path(__file__).with_name(".quota_state.json")

# Per-account quota definitions (free-tier / budget caps)
QUOTA_RULES = {
    "google_stt_work": {
        "description": "Google Cloud Speech-to-Text free tier (work account)",
        "limit_seconds": 3600,          # ~60 min/mo free
        "resets_every": "month",
        "account": "work",               # alex@evolutionstables.nz
    },
    "google_stt_personal": {
        "description": "Google Cloud Speech-to-Text free tier (personal account)",
        "limit_seconds": 3600,          # ~60 min/mo free
        "resets_every": "month",
        "account": "personal",           # baddeley0@gmail.com
    },
    # Legacy alias — treat as work quota
    "google_stt_free": {
        "description": "Google Cloud Speech-to-Text free tier (legacy alias)",
        "limit_seconds": 3600,
        "resets_every": "month",
        "account": "work",
    },
    "veo_3_1_work": {
        "description": "Veo 3.1 video generation",
        "limit_count": 2,                # 2 videos/day on work account
        "resets_every": "day",
        "account": "work",
    },
    "ai_studio_chat": {
        "description": "AI Studio chat (free tier)",
        "limit_count": 1500,             # ~1500 requests/day free tier
        "resets_every": "day",
        "account": "personal",           # baddeley0@gmail.com
    },
    "ai_studio_image": {
        "description": "AI Studio image generation",
        "limit_count": 1500,
        "resets_every": "day",
        "account": "personal",
    },
    "ai_studio_stt": {
        "description": "AI Studio speech-to-text (audio in prompt)",
        "limit_seconds": 3600,           # ~60 min/day via free tier
        "resets_every": "day",
        "account": "personal",
    },
}


class QuotaTracker:
    """Simple JSON-backed quota counter."""

    def __init__(self, path: Path = QUOTA_FILE):
        self.path = path
        self._state = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning(f"Quota save failed: {e}")

    def _key(self, rule_id: str) -> str:
        period = QUOTA_RULES[rule_id]["resets_every"]
        if period == "day":
            bucket = time.strftime("%Y-%m-%d")
        elif period == "month":
            bucket = time.strftime("%Y-%m")
        else:
            bucket = "all"
        return f"{rule_id}:{bucket}"

    def consume(self, rule_id: str, amount: int = 1) -> bool:
        """Try to consume quota. Returns True if allowed, False if exhausted."""
        if rule_id not in QUOTA_RULES:
            logger.warning(f"Unknown quota rule: {rule_id}")
            return False
        rule = QUOTA_RULES[rule_id]
        key = self._key(rule_id)
        used = self._state.get(key, 0)
        limit = rule.get("limit_count") or rule.get("limit_seconds") or 0
        if used + amount > limit:
            logger.warning(f"Quota exhausted for {rule_id} ({used}/{limit})")
            return False
        self._state[key] = used + amount
        self._save()
        logger.info(f"Quota consumed {rule_id}: {used + amount}/{limit}")
        return True

    def remaining(self, rule_id: str) -> int:
        if rule_id not in QUOTA_RULES:
            return 0
        key = self._key(rule_id)
        used = self._state.get(key, 0)
        limit = QUOTA_RULES[rule_id].get("limit_count") or QUOTA_RULES[rule_id].get("limit_seconds") or 0
        return max(0, limit - used)

    def check(self, rule_id: str, amount: int = 1) -> bool:
        """Probe quota without consuming. Returns True if enough headroom."""
        if rule_id not in QUOTA_RULES:
            return False
        rule = QUOTA_RULES[rule_id]
        key = self._key(rule_id)
        used = self._state.get(key, 0)
        limit = rule.get("limit_count") or rule.get("limit_seconds") or 0
        return used + amount <= limit


# Global tracker singleton
_tracker: Optional[QuotaTracker] = None

def get_tracker() -> QuotaTracker:
    global _tracker
    if _tracker is None:
        _tracker = QuotaTracker()
    return _tracker


class ModelRouter:
    """
    Central router for ALL LLM / inference calls in Evolution.

    Usage:
        router = ModelRouter()
        text = router.chat("Summarise this transcript...")
        # Always hits Ollama Cloud first.  Never silently bills Vertex.
    """

    def __init__(self):
        self.ollama_host = OLLAMA_HOST
        self.ollama_api_keys = OLLAMA_API_KEYS
        self.ollama_models = [OLLAMA_DEFAULT_MODEL, OLLAMA_FALLBACK_MODEL]
        self.groq_key = GROQ_API_KEY
        self.groq_model = GROQ_MODEL

    # ── Public API ────────────────────────────────────────────

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False,
        timeout: int = 60,
    ) -> str:
        """
        Send a chat completion.  Tries Ollama Cloud → Groq.
        NEVER silently falls back to Gemini/Vertex.
        """
        # 1. Ollama Cloud (primary — unlimited flat-fee)
        for model in self.ollama_models:
            try:
                return self._ollama_chat(model, prompt, system, temperature, format_json, timeout)
            except Exception as e:
                logger.warning(f"Ollama {model} failed: {e}")
                continue

        # 2. Groq (fallback — rate-limited but cheap)
        if self.groq_key:
            try:
                return self._groq_chat(prompt, system, temperature, format_json, timeout)
            except Exception as e:
                logger.warning(f"Groq fallback failed: {e}")

        raise RuntimeError("All text inference backends exhausted. Check Ollama Cloud connectivity.")

    def email_task(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False,
        timeout: int = 60,
    ) -> str:
        """
        Email-specific inference: Groq first (burns free tier), Ollama fallback.
        Perfect for weekly batch jobs where Groq's 1k-2k daily free calls cover
        the load without touching flat-fee Ollama capacity.
        """
        # 1. Groq (primary for email — free tier, fast per-request)
        if self.groq_key:
            try:
                return self._groq_chat(prompt, system, temperature, format_json, timeout)
            except Exception as e:
                logger.warning(f"Groq email task failed: {e}")

        # 2. Ollama Cloud (fallback — flat-fee unlimited)
        for model in self.ollama_models:
            try:
                return self._ollama_chat(model, prompt, system, temperature, format_json, timeout)
            except Exception as e:
                logger.warning(f"Ollama {model} failed: {e}")
                continue

        raise RuntimeError("All email inference backends exhausted.")

    def generate_image(self, prompt: str) -> bytes:
        """Images: try AI Studio free tier first, then FAL.ai second."""
        # 1. Try AI Studio (free tier, personal account)
        if AI_STUDIO_ALLOWED and AI_STUDIO_API_KEY and get_tracker().check("ai_studio_image"):
            try:
                return self._aistudio_image(prompt)
            except Exception as e:
                logger.warning(f"AI Studio image failed: {e}")

        # 2. Try FAL.ai
        fal_key = os.getenv("FAL_API_KEY", "")
        if fal_key:
            try:
                return self._fal_image(prompt, fal_key)
            except Exception as e:
                logger.warning(f"FAL image failed: {e}")

        raise RuntimeError("All image backends exhausted (AI Studio, FAL).")

    def generate_video(self, prompt: str) -> bytes:
        """Videos: try FAL.ai only (exclusive provider)."""
        fal_key = os.getenv("FAL_API_KEY", "")
        if fal_key:
            try:
                return self._fal_video(prompt, fal_key)
            except Exception as e:
                logger.warning(f"FAL video failed: {e}")
        raise RuntimeError("FAL.ai video unavailable. Check FAL_API_KEY.")

    # ── AI Studio (free tier via aistudio.google.com API) ───────

    def aistudio_chat(self, prompt: str, system: Optional[str] = None, temperature: float = 0.1) -> str:
        """
        AI Studio free-tier chat completion. Does NOT bill GCP.
        Uses gemini-2.5-flash-exp via aistudio.google.com.
        """
        if not AI_STUDIO_ALLOWED:
            raise RuntimeError("AI Studio is disabled. Set AI_STUDIO_ALLOW=true.")
        if not AI_STUDIO_API_KEY:
            raise ValueError("AI_STUDIO_API_KEY not configured.")
        if not get_tracker().consume("ai_studio_chat"):
            raise RuntimeError("AI Studio daily chat quota exhausted.")

        headers = {"x-goog-api-key": AI_STUDIO_API_KEY, "Content-Type": "application/json"}
        contents = []
        if system:
            contents.append({"role": "system", "parts": [{"text": system}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"AI Studio returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected AI Studio response: {data}")

    def aistudio_transcribe(
        self,
        audio_path: str,
        subject: str,
        speaker_names: list[str] | None = None,
    ) -> dict:
        """
        AI Studio free-tier transcription (audio file in prompt).
        Does NOT bill GCP.
        """
        if not AI_STUDIO_ALLOWED:
            raise RuntimeError("AI Studio is disabled.")
        if not AI_STUDIO_API_KEY:
            raise ValueError("AI_STUDIO_API_KEY not configured.")

        # Estimate duration and consume quota
        duration = self._estimate_audio_duration(audio_path)
        if not get_tracker().consume("ai_studio_stt", amount=int(duration)):
            raise RuntimeError("AI Studio daily STT quota exhausted.")

        # Upload file to AI Studio (inline via base64 for < 10MB, else use files API)
        from base64 import b64encode
        import pathlib
        path = pathlib.Path(audio_path)
        if path.stat().st_size > 10 * 1024 * 1024:
            # Large files: use AI Studio files.upload endpoint
            audio_data = open(audio_path, "rb").read()
        else:
            audio_data = open(audio_path, "rb").read()

        audio_b64 = b64encode(audio_data).decode("utf-8")
        mime = "audio/wav"
        if path.suffix == ".mp3":
            mime = "audio/mp3"
        elif path.suffix == ".m4a":
            mime = "audio/mp4"

        if not speaker_names:
            speaker_names = ["Andrew Scott", "Lance O'Sullivan"]
        prompt = f"""Transcribe this audio recording about '{subject}'.
Expected speakers: {', '.join(speaker_names)}.
Return ONLY valid JSON matching:
{{"full_text": "...", "segments": [{{"start_time": 0.0, "end_time": 5.2, "speaker": "...", "text": "..."}}]}}
"""
        headers = {"x-goog-api-key": AI_STUDIO_API_KEY, "Content-Type": "application/json"}
        payload = {
            "contents": [
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": mime, "data": audio_b64}}
                ]}
            ],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
            headers=headers,
            json=payload,
            timeout=max(300, int(duration * 0.5) + 120),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"AI Studio returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
        result["source"] = "aistudio_flash"
        result["model"] = "gemini-flash-latest"
        result["speakers"] = [{"name": name, "label": f"spk{i}"} for i, name in enumerate(speaker_names)]
        return result

    @staticmethod
    def _estimate_audio_duration(audio_path: str) -> float:
        """Rough estimate: WAV files ~ 1 sec = 32KB at 16kHz mono 16-bit."""
        import os, wave
        try:
            with wave.open(audio_path, "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate()
                return frames / float(rate)
        except Exception:
            return max(60.0, os.path.getsize(audio_path) / 32000.0)

    def _aistudio_image(self, prompt: str) -> bytes:
        """Generate image via AI Studio free tier (imagen-3 or flash image generation)."""
        if not AI_STUDIO_ALLOWED or not AI_STUDIO_API_KEY:
            raise RuntimeError("AI Studio not configured.")
        if not get_tracker().consume("ai_studio_image"):
            raise RuntimeError("AI Studio daily image quota exhausted.")
        headers = {"x-goog-api-key": AI_STUDIO_API_KEY, "Content-Type": "application/json"}
        payload = {
            "contents": [
                {"role": "user", "parts": [
                    {"text": f"Generate an image: {prompt}"}
                ]}
            ],
            "generationConfig": {},
        }
        # Try flash image gen first (free tier)
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"AI Studio image returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                from base64 import b64decode
                return b64decode(part["inlineData"]["data"])
        raise RuntimeError("AI Studio response contained no image data.")

    # ── FAL.ai (exclusive image/video provider) ──────────────────

    def _fal_image(self, prompt: str, fal_key: str) -> bytes:
        """Generate image via FAL.ai."""
        headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "image_size": "landscape_4_3",
        }
        # Submit
        resp = requests.post(
            "https://queue.fal.run/fal-ai/flux/dev",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"FAL submit returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        request_id = data.get("request_id")
        if not request_id:
            raise RuntimeError("FAL did not return request_id")
        # Poll status
        status_url = f"https://queue.fal.run/fal-ai/flux/dev/requests/{request_id}/status"
        for _ in range(30):
            st = requests.get(status_url, headers=headers, timeout=30)
            st_data = st.json()
            if st_data.get("status") == "COMPLETED":
                result_url = f"https://queue.fal.run/fal-ai/flux/dev/requests/{request_id}"
                result = requests.get(result_url, headers=headers, timeout=30)
                result_data = result.json()
                image_url = result_data.get("images", [{}])[0].get("url")
                if not image_url:
                    raise RuntimeError("FAL completed but no image URL")
                img = requests.get(image_url, timeout=60)
                return img.content
            elif st_data.get("status") == "FAILED":
                raise RuntimeError(f"FAL generation failed: {st_data}")
            time.sleep(2)
        raise RuntimeError("FAL image generation timed out")

    def _fal_video(self, prompt: str, fal_key: str) -> bytes:
        """Generate video via FAL.ai."""
        headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "duration": "5", "aspect_ratio": "16:9"}
        resp = requests.post(
            "https://queue.fal.run/fal-ai/kling/video/v1/standard",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"FAL submit returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        request_id = data.get("request_id")
        if not request_id:
            raise RuntimeError("FAL did not return request_id")
        status_url = f"https://queue.fal.run/fal-ai/kling/video/v1/standard/requests/{request_id}/status"
        for _ in range(60):
            st = requests.get(status_url, headers=headers, timeout=30)
            st_data = st.json()
            if st_data.get("status") == "COMPLETED":
                result_url = f"https://queue.fal.run/fal-ai/kling/video/v1/standard/requests/{request_id}"
                result = requests.get(result_url, headers=headers, timeout=30)
                result_data = result.json()
                video_url = result_data.get("video", {}).get("url")
                if not video_url:
                    raise RuntimeError("FAL completed but no video URL")
                vid = requests.get(video_url, timeout=120)
                return vid.content
            elif st_data.get("status") == "FAILED":
                raise RuntimeError(f"FAL generation failed: {st_data}")
            time.sleep(3)
        raise RuntimeError("FAL video generation timed out")

    # ── Gemini/Vertex (last resort, gated) ──────────────────────

    def gemini_transcribe(
        self,
        video_path: str,
        subject: str,
        speaker_names: list[str] | None = None,
    ) -> dict:
        """
        Gated Gemini video transcription.  ONLY runs if:
          1. GEMINI_ALLOW_TRANSCRIPTION=true
          2. Quota tracker allows (implicit — currently no per-call STT quota)
          3. GEMINI_API_KEY is present
        Returns raw dict for Transcriber to wrap.
        """
        if not GEMINI_ALLOWED:
            raise RuntimeError("Gemini transcription is disabled. Set GEMINI_ALLOW_TRANSCRIPTION=true.")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured.")

        # Defer import so we don't blow up on missing google-genai unless actually used
        from google import genai
        from google.genai import types

        logger.info("Uploading video file to Gemini (explicit gated call)...")
        client = genai.Client(vertexai=False, api_key=GEMINI_API_KEY)
        uploaded_file = client.files.upload(file=video_path)

        try:
            while uploaded_file.state.name == "PROCESSING":
                logger.info("Waiting for Gemini video processing...")
                time.sleep(5)
                uploaded_file = client.files.get(name=uploaded_file.name)

            if uploaded_file.state.name == "FAILED":
                raise RuntimeError(f"Gemini file processing failed: {uploaded_file.error.message}")

            if not speaker_names:
                speaker_names = ["Andrew Scott", "Lance O'Sullivan"]
            prompt = f"""
You are an expert audio transcription assistant.
We have an audio recording about '{subject}'.
Expected speakers: {', '.join(speaker_names)}.
Please transcribe the audio of this video with speaker diarization.
Return ONLY a valid JSON object matching the schema below. Do not wrap in markdown block, do not include any explanatory text.

Schema:
{{
  "full_text": "the entire concatenated transcript text",
  "segments": [
    {{
      "start_time": 0.0,
      "end_time": 5.2,
      "speaker": "speaker name (must be one of: {', '.join(speaker_names)})",
      "text": "transcribed segment text"
    }}
  ]
}}

Format segments chronologically. Split segments whenever the speaker changes, or if there is a pause (keep segments under 15s). Make sure the transcription is highly accurate.
"""
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            result_json = json.loads(response.text)
            result_json["source"] = "gemini_2_5_flash"
            result_json["model"] = "gemini-2.5-flash"
            result_json["speakers"] = [
                {"name": name, "label": f"spk{i}"}
                for i, name in enumerate(speaker_names)
            ]
            return result_json
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as e:
                logger.debug(f"Gemini file deletion cleanup failed: {e}")

    # ── Private backends ──────────────────────────────────────

    def _ollama_chat(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        temperature: float,
        format_json: bool,
        timeout: int,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Ollama Cloud uses OpenAI-compatible /v1/chat/completions endpoint
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }
        if format_json:
            payload["response_format"] = {"type": "json_object"}

        # Try each API key (subscription rotation: badders80 → badders808)
        for api_key in self.ollama_api_keys:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            try:
                resp = requests.post(
                    f"{self.ollama_host}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                if resp.status_code == 401:
                    logger.warning(f"Ollama Cloud key {api_key[:8]}... unauthorized for {model}, trying next key")
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama Cloud {model} returned {resp.status_code}: {resp.text[:200]}")

                data = resp.json()
                raw = data["choices"][0]["message"]["content"]

                # Strip markdown fences if model misbehaves
                if raw.startswith("```json"):
                    raw = raw.split("```json", 1)[1]
                if raw.endswith("```"):
                    raw = raw.rsplit("```", 1)[0]
                return raw.strip()
            except RuntimeError:
                raise  # Re-raise non-auth errors immediately
            except Exception as e:
                logger.warning(f"Ollama Cloud {model} with key {api_key[:8]}... failed: {e}")
                continue

        raise RuntimeError(f"Ollama Cloud {model} failed with all {len(self.ollama_api_keys)} API keys")

    def _groq_chat(
        self,
        prompt: str,
        system: Optional[str],
        temperature: float,
        format_json: bool,
        timeout: int,
    ) -> str:
        """Delegate to resilient Groq wrapper with key rotation + Ollama fallback."""
        from groq_resilient import groq_chat
        return groq_chat(
            prompt=prompt,
            system=system,
            temperature=temperature,
            format_json=format_json,
            timeout=timeout,
        )


# Convenience singleton
_router: Optional[ModelRouter] = None

def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
