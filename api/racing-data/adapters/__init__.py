"""
Racing Data — Adapters

Source-specific parsers. Each adapter knows how to turn raw HTML
from one site into structured racing data.

Adapters:
  loveracing.py — loveracing.nz Breeding page + race history
"""

from . import loveracing

__all__ = ["loveracing"]
