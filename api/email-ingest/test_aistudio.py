#!/usr/bin/env python3
"""
test_aistudio.py
Quick validation script for AI Studio free-tier API.
Run this after setting AI_STUDIO_API_KEY in ~/.env to confirm
your personal account (baddeley0@gmail.com) has active free quota.

Usage:
    cd api/email-ingest
    python test_aistudio.py
"""
import os
import sys
import json
import time
import base64
import requests
from pathlib import Path

def _load_env():
    from dotenv import load_dotenv
    load_dotenv("/home/evo/.env", override=True)

    key = os.getenv("AI_STUDIO_API_KEY", "").strip()
    if not key:
        print("❌ AI_STUDIO_API_KEY not found in /home/evo/.env")
        print("   Go to https://aistudio.google.com/apikey → Create API Key")
        print("   Paste it into ~/.env as: AI_STUDIO_API_KEY=your_key")
        sys.exit(1)
    return key

def _test_chat(key: str) -> bool:
    print("\n🧪 TEST 1: Chat (gemini-flash-latest)")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Say 'AI Studio chat is working' and nothing else."}]}],
        "generationConfig": {"temperature": 0.0},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"   ❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"   ✅ Response: {text[:80]}")
        return True
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def _test_image(key: str) -> bool:
    print("\n🧪 TEST 2: Image generation (gemini-3.1-flash-image)")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "A simple red circle on a white background, minimalist."}]}],
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            print(f"   ❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                img_bytes = base64.b64decode(part["inlineData"]["data"])
                out = Path("/tmp/aistudio_test_image.png")
                out.write_bytes(img_bytes)
                print(f"   ✅ Image saved: {out} ({len(img_bytes)} bytes)")
                return True
        print("   ⚠️  No image data in response (model may have returned text only)")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def _test_transcribe(key: str) -> bool:
    print("\n🧪 TEST 3: Audio-in-prompt transcription (gemini-flash-latest)")
    # Create a tiny synthetic WAV (1 sec silence) to test the pipeline without needing a real video
    wav_path = Path("/tmp/aistudio_test_silence.wav")
    if not wav_path.exists():
        import wave, struct
        with wave.open(str(wav_path), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00" * 16000)  # 1 second of silence

    audio_b64 = base64.b64encode(wav_path.read_bytes()).decode("utf-8")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [
            {"text": "Transcribe this audio. Return only JSON with keys: full_text, segments (list of {start_time, end_time, speaker, text})."},
            {"inlineData": {"mimeType": "audio/wav", "data": audio_b64}}
        ]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            print(f"   ❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
        print(f"   ✅ Transcript: {result.get('full_text', '')[:80]}")
        return True
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def main():
    print("=" * 60)
    print("AI Studio Free-Tier Validation")
    print("=" * 60)
    key = _load_env()
    print(f"   Key prefix: {key[:8]}...")

    results = {
        "chat": _test_chat(key),
        "image": _test_image(key),
        "transcribe": _test_transcribe(key),
    }

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for name, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"   {name:<15} {status}")

    if all(results.values()):
        print("\n🎉 All AI Studio endpoints working. You can route free-tier calls here.")
        sys.exit(0)
    else:
        print("\n⚠️  Some endpoints failed. Check key permissions / quota at")
        print("   https://aistudio.google.com/app/apikey")
        sys.exit(1)

if __name__ == "__main__":
    main()
