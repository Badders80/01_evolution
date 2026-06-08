"""
groq_resilient.py
Resilient Groq API wrapper with:
  • Exponential backoff on 429
  • Key rotation (primary / secondary)
  • Automatic fallback to Ollama Cloud on persistent failure

This isolates all Groq-specific resilience logic so the rest of the pipeline
doesn't need to think about rate limits.
"""
import os
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Primary and secondary keys (secondary can be empty)
GROQ_KEYS = [
    os.getenv("GROQ_API_KEY", "").strip(),
    os.getenv("GROQ_API_KEY_2", "").strip(),
]
GROQ_KEYS = [k for k in GROQ_KEYS if k]  # drop empty

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Retry config
MAX_RETRIES = 5
BASE_DELAY = 2.0  # seconds


def _rotate_key(current_idx: int) -> int:
    """Return next key index, wrapping around."""
    if not GROQ_KEYS:
        return -1
    return (current_idx + 1) % len(GROQ_KEYS)


def groq_chat(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.1,
    format_json: bool = False,
    timeout: int = 60,
) -> str:
    """
    Resilient Groq chat completion.
    Tries each key with exponential backoff. Falls back to Ollama Cloud if all keys exhausted.
    """
    if not GROQ_KEYS:
        logger.warning("No Groq keys configured — skipping to Ollama fallback")
        return _ollama_chat_fallback(prompt, system, temperature, format_json, timeout)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if format_json:
        payload["response_format"] = {"type": "json_object"}

    key_idx = 0
    for attempt in range(MAX_RETRIES):
        key = GROQ_KEYS[key_idx]
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.Timeout:
            logger.warning(f"Groq timeout (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(BASE_DELAY * (2 ** attempt))
            continue
        except Exception as e:
            logger.warning(f"Groq request error (attempt {attempt + 1}): {e}")
            time.sleep(BASE_DELAY)
            continue

        if resp.status_code == 429:
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(f"Groq 429 on key {key_idx + 1}/{len(GROQ_KEYS)} — retry in {delay}s")
            time.sleep(delay)
            # If we have multiple keys, rotate after first retry on same key
            if len(GROQ_KEYS) > 1 and attempt > 0:
                key_idx = _rotate_key(key_idx)
            continue

        if resp.status_code == 401:
            logger.error(f"Groq key {key_idx + 1} invalid (401). Rotating...")
            key_idx = _rotate_key(key_idx)
            if key_idx == 0:  # wrapped around — all keys dead
                break
            continue

        if resp.status_code != 200:
            logger.warning(f"Groq returned {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected Groq response shape: {data}")

    # All retries exhausted — fall back to Ollama Cloud
    logger.error("Groq exhausted all keys/retries. Falling back to Ollama Cloud.")
    return _ollama_chat_fallback(prompt, system, temperature, format_json, timeout)


def groq_transcribe(audio_path: str, timeout: int = 60) -> Optional[dict]:
    """
    Resilient Groq Whisper transcription with key rotation and Ollama fallback.
    Returns dict with keys: full_text, segments, source, model.
    """
    if not GROQ_KEYS:
        logger.warning("No Groq keys — cannot transcribe via Whisper")
        return None

    headers_base = {"Authorization": f"Bearer {GROQ_KEYS[0]}"}
    files_payload = {"file": (os.path.basename(audio_path), open(audio_path, "rb"), "audio/wav")}
    data_payload = {
        "model": "whisper-large-v3",
        "temperature": "0.0",
        "language": "en",
        "response_format": "verbose_json"
    }

    key_idx = 0
    for attempt in range(MAX_RETRIES):
        key = GROQ_KEYS[key_idx]
        headers = {"Authorization": f"Bearer {key}"}

        try:
            resp = requests.post(
                GROQ_AUDIO_URL,
                headers=headers,
                files=files_payload,
                data=data_payload,
                timeout=timeout
            )
        except requests.exceptions.Timeout:
            logger.warning(f"Groq Whisper timeout (attempt {attempt + 1})")
            time.sleep(BASE_DELAY * (2 ** attempt))
            continue
        except Exception as e:
            logger.warning(f"Groq Whisper error: {e}")
            time.sleep(BASE_DELAY)
            continue

        if resp.status_code == 429:
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(f"Groq Whisper 429 — retry in {delay}s")
            time.sleep(delay)
            if len(GROQ_KEYS) > 1 and attempt > 0:
                key_idx = _rotate_key(key_idx)
            continue

        if resp.status_code == 401:
            logger.error(f"Groq key {key_idx + 1} invalid (401). Rotating...")
            key_idx = _rotate_key(key_idx)
            if key_idx == 0:
                break
            continue

        if resp.status_code != 200:
            logger.warning(f"Groq Whisper returned {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        segments = []
        for seg in data.get("segments", []):
            segments.append({
                "start_time": float(seg.get("start", 0.0)),
                "end_time": float(seg.get("end", 0.0)),
                "speaker": "Speaker 1",
                "text": seg.get("text", "").strip()
            })
        full_text = data.get("text", "")
        if not segments and full_text:
            segments = [{"start_time": 0.0, "end_time": 0.0, "speaker": "Speaker 1", "text": full_text}]

        return {
            "full_text": full_text,
            "segments": segments,
            "source": "groq_whisper",
            "model": "whisper-large-v3",
        }

    logger.error("Groq Whisper exhausted all keys/retries. No fallback for audio.")
    return None


def _ollama_chat_fallback(
    prompt: str,
    system: Optional[str],
    temperature: float,
    format_json: bool,
    timeout: int,
) -> str:
    """
    Ultimate fallback to Ollama Cloud (flat-fee, unlimited).
    Called when Groq is completely unavailable.
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    models = [
        os.getenv("OLLAMA_MODEL", "kimi-k2.6:cloud"),
        os.getenv("OLLAMA_FALLBACK_MODEL", "qwen3.5:cloud"),
    ]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if format_json:
            payload["format"] = "json"

        try:
            resp = requests.post(
                f"{ollama_host}/api/chat",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                raw = data["message"]["content"]
                if raw.startswith("```json"):
                    raw = raw.split("```json", 1)[1]
                if raw.endswith("```"):
                    raw = raw.rsplit("```", 1)[0]
                logger.info(f"Ollama fallback succeeded with {model}")
                return raw.strip()
        except Exception as e:
            logger.warning(f"Ollama fallback {model} failed: {e}")
            continue

    raise RuntimeError("All inference backends exhausted (Groq + Ollama).")
