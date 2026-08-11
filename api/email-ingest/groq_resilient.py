"""
groq_resilient.py
Resilient Groq API wrapper with:
  • Exponential backoff on 429
  • Key rotation (primary / secondary)
  • Automatic fallback to Ollama Cloud on persistent failure
  • Chunked transcription for files above Groq upload limits

This isolates all Groq-specific resilience logic so the rest of the pipeline
doesn't need to think about rate limits.
"""
import os
import re
import glob
import time
import logging
import subprocess
import tempfile
import uuid
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


MAX_GROQ_BYTES = 24 * 1024 * 1024
CHUNK_SECONDS = 600


def _audio_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mp3":
        return "audio/mpeg"
    if ext == ".m4a":
        return "audio/mp4"
    return "audio/wav"


def _probe_duration(path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _compress_for_groq(audio_path: str) -> str:
    """Create a compact mono MP3 suitable for Groq uploads."""
    out_path = os.path.join(
        tempfile.gettempdir(),
        f"groq-compress-{uuid.uuid4().hex[:8]}.mp3",
    )
    cmd = [
        "ffmpeg",
        "-i",
        audio_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        "-y",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    return out_path


def _split_audio_chunks(audio_path: str, chunk_seconds: int = CHUNK_SECONDS) -> list[tuple[str, float]]:
    """Split audio into chunk files; return (path, offset_seconds)."""
    duration = _probe_duration(audio_path)
    if duration <= 0:
        return [(audio_path, 0.0)]

    chunk_dir = tempfile.mkdtemp(prefix="groq-chunks-")
    pattern = os.path.join(chunk_dir, "chunk_%03d.mp3")
    cmd = [
        "ffmpeg",
        "-i",
        audio_path,
        "-f",
        "segment",
        "-segment_time",
        str(chunk_seconds),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        "-reset_timestamps",
        "1",
        "-y",
        pattern,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=900)

    chunks = sorted(glob.glob(os.path.join(chunk_dir, "chunk_*.mp3")))
    if not chunks:
        return [(audio_path, 0.0)]

    return [(path, idx * chunk_seconds) for idx, path in enumerate(chunks)]


def _groq_transcribe_single(audio_path: str, timeout: int = 300) -> Optional[dict]:
    if not GROQ_KEYS:
        logger.warning("No Groq keys — cannot transcribe via Whisper")
        return None

    data_payload = {
        "model": "whisper-large-v3",
        "temperature": "0.0",
        "language": "en",
        "response_format": "verbose_json",
    }
    mime = _audio_mime(audio_path)

    key_idx = 0
    for attempt in range(MAX_RETRIES):
        key = GROQ_KEYS[key_idx]
        headers = {"Authorization": f"Bearer {key}"}

        try:
            with open(audio_path, "rb") as audio_file:
                files_payload = {
                    "file": (os.path.basename(audio_path), audio_file, mime),
                }
                resp = requests.post(
                    GROQ_AUDIO_URL,
                    headers=headers,
                    files=files_payload,
                    data=data_payload,
                    timeout=timeout,
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

        if resp.status_code == 413:
            logger.warning("Groq Whisper payload too large for single upload.")
            return None

        if resp.status_code in (500, 502, 503, 504):
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(
                f"Groq Whisper returned {resp.status_code} — retry in {delay}s"
            )
            time.sleep(delay)
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
                "text": seg.get("text", "").strip(),
            })
        full_text = data.get("text", "")
        if not segments and full_text:
            segments = [{
                "start_time": 0.0,
                "end_time": 0.0,
                "speaker": "Speaker 1",
                "text": full_text,
            }]

        return {
            "full_text": full_text,
            "segments": segments,
            "source": "groq_whisper",
            "model": "whisper-large-v3",
        }

    logger.error("Groq Whisper exhausted all keys/retries. No fallback for audio.")
    return None


def groq_transcribe(
    audio_path: str,
    timeout: int = 300,
    original_path: str | None = None,
) -> Optional[dict]:
    """
    Resilient Groq Whisper transcription with key rotation and chunking.
    Returns dict with keys: full_text, segments, source, model.
    """
    if not GROQ_KEYS:
        logger.warning("No Groq keys — cannot transcribe via Whisper")
        return None

    candidate_paths = [audio_path]
    if original_path and os.path.exists(original_path):
        candidate_paths.insert(0, original_path)

    upload_path = min(candidate_paths, key=lambda p: os.path.getsize(p))
    temp_paths: list[str] = []

    try:
        if os.path.getsize(upload_path) > MAX_GROQ_BYTES:
            compressed = _compress_for_groq(upload_path)
            temp_paths.append(compressed)
            upload_path = compressed

        if os.path.getsize(upload_path) > MAX_GROQ_BYTES:
            logger.info(
                "Groq upload still too large (%d bytes) — chunking audio",
                os.path.getsize(upload_path),
            )
            chunks = _split_audio_chunks(upload_path)
            temp_paths.extend(path for path, _ in chunks)

            merged_segments = []
            merged_text_parts = []
            for chunk_path, offset in chunks:
                chunk_result = _groq_transcribe_single(chunk_path, timeout=timeout)
                if not chunk_result:
                    logger.error(f"Groq chunk failed: {chunk_path}")
                    return None
                for seg in chunk_result["segments"]:
                    merged_segments.append({
                        "start_time": seg["start_time"] + offset,
                        "end_time": seg["end_time"] + offset,
                        "speaker": seg["speaker"],
                        "text": seg["text"],
                    })
                if chunk_result["full_text"]:
                    merged_text_parts.append(chunk_result["full_text"].strip())

            return {
                "full_text": " ".join(merged_text_parts),
                "segments": merged_segments,
                "source": "groq_whisper_chunked",
                "model": "whisper-large-v3",
            }

        return _groq_transcribe_single(upload_path, timeout=timeout)
    finally:
        for path in temp_paths:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass


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
    Rotates through both Ollama Cloud subscriptions (badders80 → badders808).
    """
    # Load all Ollama Cloud keys from ~/.hermes/.env (primary + backup)
    import re as _re
    ollama_keys = []
    hermes_env = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(hermes_env):
        for line in open(hermes_env):
            line = line.strip()
            # Active key (uncommented)
            if line.startswith("OLLAMA_API_KEY=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip()
                if val and not val.startswith("ssh-"):
                    ollama_keys.append(val)
            # Backup key (commented line with "backup" label)
            if line.startswith("#") and "backup" in line.lower():
                m = _re.search(r'([0-9a-f]{32}\.[A-Za-z0-9_\-]+)', line)
                if m:
                    ollama_keys.append(m.group(1))
    # Also check shell env
    env_key = os.getenv("OLLAMA_API_KEY", "")
    if env_key and not env_key.startswith("ssh-") and env_key not in ollama_keys:
        ollama_keys.insert(0, env_key)

    if ollama_keys:
        ollama_host = os.getenv("OLLAMA_CLOUD_HOST", "https://ollama.com/v1")
    else:
        ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    models = [
        os.getenv("OLLAMA_MODEL", "glm-5.2"),
        os.getenv("OLLAMA_FALLBACK_MODEL", "deepseek-v4-flash"),
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
            "temperature": temperature,
        }
        if format_json:
            payload["response_format"] = {"type": "json_object"}

        # Try each API key (subscription rotation)
        for api_key in ollama_keys:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            try:
                resp = requests.post(
                    f"{ollama_host}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                if resp.status_code == 401:
                    logger.warning(f"Ollama key {api_key[:8]}... unauthorized, trying next")
                    continue
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data["choices"][0]["message"]["content"]
                    if raw.startswith("```json"):
                        raw = raw.split("```json", 1)[1]
                    if raw.endswith("```"):
                        raw = raw.rsplit("```", 1)[0]
                    logger.info(f"Ollama fallback succeeded with {model} (key {api_key[:8]}...)")
                    return raw.strip()
            except Exception as e:
                logger.warning(f"Ollama fallback {model} key {api_key[:8]}... failed: {e}")
                continue

    raise RuntimeError("All inference backends exhausted (Groq + Ollama).")
