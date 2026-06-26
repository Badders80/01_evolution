#!/usr/bin/env python3
"""
kb-index.py — Index and query the Evolution Stables knowledge repository.

Walks all .md files under a root directory (default: 01_evolution/), parses
YAML frontmatter, and supports tag/type/role/entity queries via CLI.

Usage:
    python kb-index.py --list
    python kb-index.py --stats
    python kb-index.py --type horse
    python kb-index.py --tag racing
    python kb-index.py --role trainer
    python kb-index.py --horse first-gear
    python kb-index.py --person stephen-gray
    python kb-index.py --stable wexford-stables
    python kb-index.py --pedigree proisir
    python kb-index.py --tag first-gear --type press

Output: table of file path | type | slug | tags
"""

import argparse
import os
import sys
from collections import defaultdict


# ─── YAML Frontmatter Parser (stdlib only) ───────────────────────────────────

def parse_frontmatter(text):
    """Extract and parse YAML frontmatter from markdown text. Returns dict or None."""
    lines = text.splitlines()
    start = end = None
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if start is None:
                start = i
            else:
                end = i
                break
    if start is None or end is None:
        return None
    return _parse_yaml_block(lines[start + 1:end])


def _parse_yaml_block(lines):
    """Parse simple YAML key: value pairs and lists. No PyYAML dependency."""
    data = {}
    current_key = None
    current_list = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # Block list item
        if stripped.startswith('- ') and current_key is not None:
            current_list.append(_clean_scalar(stripped[2:].strip()))
            continue
        # Finalize previous block list
        if current_key is not None and current_list is not None:
            data[current_key] = current_list
            current_key = None
            current_list = None
        # key: value
        if ':' in stripped:
            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()
            if not value:
                current_key = key
                current_list = []
            elif value.startswith('[') and value.endswith(']'):
                items = [v.strip() for v in value[1:-1].split(',') if v.strip()]
                data[key] = [_clean_scalar(v) for v in items]
            else:
                data[key] = _clean_scalar(value)
    # Don't forget trailing list
    if current_key is not None and current_list is not None:
        data[current_key] = current_list
    return data


def _clean_scalar(val):
    """Convert YAML scalar string to Python value."""
    val = val.strip()
    if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
        val = val[1:-1]
    low = val.lower()
    if low in ('true', 'yes', 'on'):
        return True
    if low in ('false', 'no', 'off'):
        return False
    if low in ('null', 'none', '~'):
        return None
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return val


# ─── Index Builder ───────────────────────────────────────────────────────────

LIST_FIELDS = {'tags', 'roles', 'horses', 'people', 'stables', 'pedigrees', 'tracks', 'progeny'}
SCALAR_FIELDS = {'slug', 'type', 'name', 'trainer', 'sire', 'dam', 'stable', 'owner', 'breeder', 'lease', 'governing_body', 'source_url', 'publisher', 'date', 'author', 'microchip', 'company', 'contact', 'code', 'status', 'horse'}


def build_index(root_dir):
    """Walk root_dir, parse all .md files, return list of records."""
    index = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in sorted(filenames):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, root_dir)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError) as e:
                print(f"  WARN: Could not read {fpath}: {e}", file=sys.stderr)
                continue
            fm = parse_frontmatter(content)
            if fm is None:
                continue
            record = {'path': rel_path}
            for field in SCALAR_FIELDS:
                record[field] = str(fm.get(field, '')).lower() if fm.get(field) else ''
            for field in LIST_FIELDS:
                val = fm.get(field, [])
                if isinstance(val, list):
                    record[field] = [str(v).lower() for v in val]
                elif isinstance(val, str) and val:
                    record[field] = [val.lower()]
                else:
                    record[field] = []
            index.append(record)
    return index


# ─── Query Filters ───────────────────────────────────────────────────────────

def by_tag(index, tag):
    tag = tag.lower()
    return [r for r in index if tag in r.get('tags', [])]


def by_type(index, typ):
    typ = typ.lower()
    return [r for r in index if r.get('type', '') == typ]


def by_role(index, role):
    role = role.lower()
    return [r for r in index if role in r.get('roles', [])]


def by_horse(index, slug):
    slug = slug.lower()
    return [r for r in index if slug in r.get('horses', []) or r.get('slug', '') == slug]


def by_person(index, slug):
    slug = slug.lower()
    return [r for r in index if slug in r.get('people', []) or r.get('slug', '') == slug]


def by_stable(index, slug):
    slug = slug.lower()
    return [r for r in index if slug in r.get('stables', []) or r.get('slug', '') == slug]


def by_pedigree(index, slug):
    slug = slug.lower()
    return [r for r in index if slug in r.get('pedigrees', []) or r.get('slug', '') == slug]


def by_owner(index, slug):
    slug = slug.lower()
    return [r for r in index if r.get('owner', '') == slug or slug in r.get('people', [])]


def by_lease(index, slug):
    slug = slug.lower()
    return [r for r in index if r.get('lease', '') == slug or r.get('slug', '') == slug]


def by_hlt(index, slug):
    slug = slug.lower()
    return [r for r in index if r.get('type', '') == 'hlt' and (r.get('slug', '') == slug or r.get('horse', '') == slug)]


# ─── Output ──────────────────────────────────────────────────────────────────

def print_table(records):
    if not records:
        print("  (no results)")
        return
    # Calculate column widths
    paths = [r['path'] for r in records]
    types = [r.get('type', '') for r in records]
    slugs = [r.get('slug', '') for r in records]
    tags = [', '.join(r.get('tags', [])) for r in records]
    w1 = max(len('File'), max(len(p) for p in paths)) if paths else len('File')
    w2 = max(len('Type'), max(len(t) for t in types)) if types else len('Type')
    w3 = max(len('Slug'), max(len(s) for s in slugs)) if slugs else len('Slug')
    w4 = max(len('Tags'), max(len(t) for t in tags)) if tags else len('Tags')
    header = f"  {'File':<{w1}}  {'Type':<{w2}}  {'Slug':<{w3}}  {'Tags':<{w4}}"
    print(header)
    print(f"  {'-' * w1}  {'-' * w2}  {'-' * w3}  {'-' * w4}")
    for r in records:
        t = ', '.join(r.get('tags', []))
        print(f"  {r['path']:<{w1}}  {r.get('type', ''):<{w2}}  {r.get('slug', ''):<{w3}}  {t:<{w4}}")
    print(f"\n  {len(records)} result(s)")


def print_stats(index):
    type_counts = defaultdict(int)
    tag_counts = defaultdict(int)
    for r in index:
        type_counts[r.get('type', 'unknown')] += 1
        for t in r.get('tags', []):
            tag_counts[t] += 1
    print(f"\n  Knowledge Repository Stats")
    print(f"  {'=' * 40}")
    print(f"  Total files: {len(index)}")
    print(f"\n  By type:")
    for typ, count in sorted(type_counts.items()):
        print(f"    {typ:<20} {count}")
    print(f"\n  Top tags:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"    {tag:<20} {count}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Index and query the Evolution Stables knowledge repository.'
    )
    parser.add_argument('--root', default='01_evolution/', help='Root directory (default: 01_evolution/)')
    parser.add_argument('--list', action='store_true', help='List all files')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--tag', help='Filter by tag')
    parser.add_argument('--type', dest='filter_type', help='Filter by type (horse, person, stable, pedigree, press)')
    parser.add_argument('--role', help='Filter people by role (trainer, owner, breeder, jockey)')
    parser.add_argument('--horse', help='Find all files linked to this horse slug')
    parser.add_argument('--person', help='Find all files linked to this person slug')
    parser.add_argument('--stable', help='Find all files linked to this stable slug')
    parser.add_argument('--pedigree', help='Find all files linked to this pedigree slug')
    parser.add_argument('--owner', help='Find all files linked to this owner slug')
    parser.add_argument('--lease', help='Find all files linked to this lease ID')
    parser.add_argument('--hlt', help='Find HLT campaign files for a horse slug')
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print(f"Error: {args.root} is not a directory", file=sys.stderr)
        sys.exit(1)

    index = build_index(args.root)

    # Apply filters (can combine)
    results = index
    if args.tag:
        results = by_tag(results, args.tag)
    if args.filter_type:
        results = by_type(results, args.filter_type)
    if args.role:
        results = by_role(results, args.role)
    if args.horse:
        results = by_horse(results, args.horse)
    if args.person:
        results = by_person(results, args.person)
    if args.stable:
        results = by_stable(results, args.stable)
    if args.pedigree:
        results = by_pedigree(results, args.pedigree)
    if args.owner:
        results = by_owner(results, args.owner)
    if args.lease:
        results = by_lease(results, args.lease)
    if args.hlt:
        results = by_hlt(results, args.hlt)

    if args.stats:
        print_stats(index)
    elif args.list or not any([args.tag, args.filter_type, args.role, args.horse, args.person, args.stable, args.pedigree, args.owner, args.lease, args.hlt]):
        print_table(results)
    else:
        print_table(results)


if __name__ == '__main__':
    main()