#!/usr/bin/env python3
"""RELAY refiner via Gemini (B) or NVIDIA NIM (C)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import requests
from dotenv import load_dotenv

REPO_ROOT = "/home/evo/evo_01"
BRIEF_PATH = os.path.join(REPO_ROOT, "relay/inbox/refiner-brief.md")
OUT_PATH = os.path.join(REPO_ROOT, "relay/outbox/refiner-result.md")

REFINER_PROMPT = """You are the RELAY Refiner (cross-model reviewer). Review the author's work against the brief.

Rules:
- Compare implementation to refiner-brief.md requirements
- Flag security issues (path traversal, SQL injection, credential leaks)
- Flag logic bugs, missed files, false-green gates
- Do NOT rewrite code — output an issues table
- End with: VERDICT: PASS or VERDICT: FAIL

Format:
## Issues
| Severity | File | Issue | Fix |
|----------|------|-------|-----|
...

## Gate
- command run / recommended
- expected outcome

## VERDICT: PASS|FAIL
"""


def _read_brief() -> str:
    if not os.path.exists(BRIEF_PATH):
        raise FileNotFoundError(f"Missing brief: {BRIEF_PATH}")
    with open(BRIEF_PATH, encoding="utf-8") as f:
        return f.read()


def _git_diff() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--stat", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            full = subprocess.run(
                ["git", "-C", REPO_ROOT, "diff", "HEAD"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            diff = full.stdout if full.returncode == 0 else out.stdout
            return diff[:120000]
    except Exception:
        pass
    return "(no git diff available — review brief file list)"


def _call_gemini(prompt: str) -> str:
    key = os.getenv("AI_STUDIO_API_KEY", "").strip()
    if not key:
        raise RuntimeError("AI_STUDIO_API_KEY not set")
    model = os.getenv("REFINER_GEMINI_MODEL", "gemini-flash-latest")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_nim(prompt: str) -> str:
    key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("NVIDIA_API_KEY not set")
    url = os.getenv(
        "NVIDIA_API_URL",
        "https://integrate.api.nvidia.com/v1/chat/completions",
    )
    model = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": REFINER_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RELAY refiner (Gemini or NIM)")
    parser.add_argument(
        "--provider",
        choices=["gemini", "nim"],
        default="gemini",
        help="Refiner backend (default: gemini / Option B)",
    )
    args = parser.parse_args()

    load_dotenv("/home/evo/.env")
    brief = _read_brief()
    diff = _git_diff()
    user_prompt = f"{REFINER_PROMPT}\n\n# REFINER BRIEF\n{brief}\n\n# GIT DIFF\n{diff}"

    try:
        if args.provider == "gemini":
            result = _call_gemini(user_prompt)
        else:
            result = _call_nim(user_prompt)
    except Exception as exc:
        result = f"REFINER ERROR: {exc}\n\nVERDICT: FAIL"
        print(result, file=sys.stderr)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Refiner Result ({args.provider})\n\n")
        f.write(result)
        f.write("\n")

    print(result)
    return 0 if "VERDICT: PASS" in result.upper() else 1


if __name__ == "__main__":
    raise SystemExit(main())