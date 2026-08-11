"""Horse identity registry for email ingest — slugs, microchips, and source metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class HorseEntry:
    slug: str
    display_name: str
    microchip: str
    stable: str
    trainer: str
    speakers: list[str]


@dataclass(frozen=True)
class IngestSource:
    name: str
    imap_query: str
    subject_patterns: list[str]
    default_speakers: list[str]


HORSE_ENTRIES: dict[str, HorseEntry] = {
    "prudentia": HorseEntry(
        slug="prudentia",
        display_name="Prudentia",
        microchip="985125000126462",
        stable="Wexford Stables",
        trainer="Lance O'Sullivan & Andrew Scott",
        speakers=["Andrew Scott", "Lance O'Sullivan"],
    ),
    "turn-me-loose-x-yearn": HorseEntry(
        slug="turn-me-loose-x-yearn",
        display_name="Turn Me Loose x Yearn",
        microchip="985125000128426",
        stable="Stephen Gray Racing",
        trainer="Stephen Gray",
        speakers=["Stephen Gray"],
    ),
    "first-gear": HorseEntry(
        slug="first-gear",
        display_name="First Gear",
        microchip="985125000126713",
        stable="Stephen Gray Racing",
        trainer="Stephen Gray",
        speakers=["Stephen Gray"],
    ),
}

# Lowercase alias → slug
HORSE_ALIASES: dict[str, str] = {
    "prudentia": "prudentia",
    "prudentia (nz)": "prudentia",
    "audio update: prudentia": "prudentia",
    "turn me loose x yearn": "turn-me-loose-x-yearn",
    "turn me loose - yearn": "turn-me-loose-x-yearn",
    "turn me loose - yearn 23f": "turn-me-loose-x-yearn",
    "turn me loose - yearn 23f horse report": "turn-me-loose-x-yearn",
    "tml x yearn": "turn-me-loose-x-yearn",
    "tlm x yearn": "turn-me-loose-x-yearn",  # legacy typo alias
    "first gear": "first-gear",
    "first gear horse report": "first-gear",
}

INGEST_SOURCES: dict[str, IngestSource] = {
    "wexford": IngestSource(
        name="wexford",
        imap_query='(OR FROM "info@wexfordstables.co.nz" TEXT "Prudentia")',
        subject_patterns=[
            r"Video Update.*Prudentia",
            r"Audio Update.*Prudentia",
            r"Race Acceptance.*Prudentia",
            r"Race Result.*Prudentia",
        ],
        default_speakers=["Andrew Scott"],
    ),
    "stephen-gray": IngestSource(
        name="stephen-gray",
        imap_query='(FROM "contact+2jn7p623lkog@m.mistable.com")',
        subject_patterns=[
            r"Horse Report",
            r"Turn Me Loose.*Yearn",
        ],
        default_speakers=["Stephen Gray"],
    ),
}


def _slugify(name: str) -> str:
    slug = name.lower().strip().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9_-]", "", slug)
    if not slug or ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError(f"Invalid horse slug from name: {name!r}")
    return slug


def normalize_horse_slug(name: str) -> str:
    """Normalize a horse display name to canonical filesystem slug."""
    key = name.lower().strip()
    if ".." in key or "/" in key or "\\" in key:
        raise ValueError(f"Invalid horse slug from name: {name!r}")
    if key in HORSE_ALIASES:
        return HORSE_ALIASES[key]
    slug = _slugify(name)
    if slug in HORSE_ENTRIES:
        return slug
    return slug


def resolve_horse_entry(horse_name: str) -> HorseEntry:
    """Resolve horse display name to registry entry."""
    slug = normalize_horse_slug(horse_name)
    if slug in HORSE_ENTRIES:
        return HORSE_ENTRIES[slug]

    lowered = horse_name.lower()
    for alias, alias_slug in HORSE_ALIASES.items():
        if alias in lowered or lowered in alias:
            return HORSE_ENTRIES[alias_slug]

    raise ValueError(f"Horse '{horse_name}' not registered in ingest registry")


def resolve_horse_microchip(horse_name: str) -> str:
    return resolve_horse_entry(horse_name).microchip


def infer_source(from_address: str) -> str:
    lower = (from_address or "").lower()
    if "2jn7p623lkog@m.mistable.com" in lower or "stephen gray" in lower:
        return "stephen-gray"
    if "wexfordstables" in lower:
        return "wexford"
    return "wexford"