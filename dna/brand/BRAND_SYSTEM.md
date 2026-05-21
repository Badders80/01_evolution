# Evolution Stables — Brand System

**Version:** 2.0
**Last Updated:** 2026-05-20

> **Note:** Updated to match the current `02_website` implementation. Previous v1.0 used Playfair Display + Inter and #121212 background. v2.0 reflects the actual deployed site.

---

## Color Palette

### Primary

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Evolution Gold | `#d4a964` | rgb(212, 169, 100) | Primary accent, CTAs, headings, hover states |
| Background | `#09090b` | rgb(9, 9, 11) | Page backgrounds, body |
| Surface | `#0a0a0a` | rgb(10, 10, 10) | Cards, panels, sidebar, elevated surfaces |
| Surface Alt | `#111111` | rgb(17, 17, 17) | Alternate surface, scrollbar track, subtle backgrounds |
| Foreground | `#f5f5f5` | rgb(245, 245, 245) | Primary text on dark backgrounds |
| Muted | `#a1a1aa` | rgb(161, 161, 170) | Secondary text, labels, descriptions |
| Muted Foreground | `#737373` | rgb(115, 115, 115) | Tertiary text, placeholders, disabled |
| Border | `rgba(255,255,255,0.06)` | — | Subtle borders, dividers, table rows |

### Gold Scale

| Shade | Hex | Usage |
|-------|-----|-------|
| 50 | `#fdf8ed` | Lightest background |
| 100 | `#f9edcc` | Subtle highlight |
| 200 | `#f2d894` | Hover state |
| 300 | `#e8be55` | Active state |
| 400 | `#d4a964` | **Primary** |
| 500 | `#c49a5a` | Hover darken (was #c49a3d in v1) |
| 600 | `#a67c2e` | Dark accent |
| 700 | `#8a5f25` | Text on gold |
| 800 | `#724d23` | Deep accent |
| 900 | `#5f4022` | Darkest accent |

### Status Colors (Admin)

| Status | Background | Text | Usage |
|--------|-----------|------|-------|
| Draft | `rgba(161,161,170,0.1)` | `#a1a1aa` | HLT draft |
| Reviewed | `rgba(212,169,100,0.1)` | `#d4a964` | HLT reviewed |
| Publish Ready | `rgba(34,197,94,0.1)` | `#22c55e` | HLT publish_ready |
| Published | `rgba(59,130,246,0.1)` | `#3b82f6` | HLT published |
| Admin | `rgba(212,169,100,0.1)` | `#d4a964` | Role badge |
| KYC Verified | `rgba(34,197,94,0.1)` | `#22c55e` | KYC badge |
| KYC Pending | `rgba(234,179,8,0.1)` | `#eab308` | KYC badge |
| KYC Unverified | `rgba(239,68,68,0.1)` | `#ef4444` | KYC badge |

## Typography

### Font Stack

- **Primary:** Geist Sans (variable font, weight 100-900) — all text, headings, body, UI
- **Fallback:** system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif

> **v1.0 used Playfair Display + Inter.** v2.0 uses Geist Sans exclusively for consistency and performance (single variable font file). Public pages may introduce Playfair Display for hero moments in future sprints.

### Scale

| Element | Size | Weight | Letter Spacing |
|---------|------|--------|----------------|
| H1 | 3rem (48px) | 700 | -0.02em |
| H2 | 2rem (32px) | 600 | -0.01em |
| H3 | 1.5rem (24px) | 600 | -0.01em |
| H4 | 1.25rem (20px) | 600 | 0 |
| Body | 1rem (16px) | 400 | 0 |
| Small | 0.875rem (14px) | 400 | 0 |
| Caption | 0.75rem (12px) | 500 | 0.01em |
| Label | 0.6875rem (11px) | 500 | 0.2em (uppercase) |

## Spacing

Based on 4px grid:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Tight gaps |
| sm | 8px | Inline spacing |
| md | 16px | Standard padding |
| lg | 24px | Section spacing |
| xl | 32px | Large gaps |
| 2xl | 48px | Hero spacing |
| 3xl | 64px | Page sections |

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| sm | 8px | Small elements |
| md | 12px | Cards, inputs |
| lg | 16px | Panels |
| xl | 24px | Hero cards |
| full | 9999px | Buttons, pills, badges |

## Shadows

| Token | Value | Usage |
|-------|-------|-------|
| sm | `0 1px 2px rgba(0,0,0,0.3)` | Subtle elevation |
| md | `0 4px 6px rgba(0,0,0,0.4)` | Cards |
| lg | `0 10px 15px rgba(0,0,0,0.5)` | Modals |
| gold | `0 0 20px rgba(212,169,100,0.15)` | Gold glow effect |

## Components

### Button

- **Primary:** Gold background (#d4a964), black text (#09090b), rounded-full, hover #c49a5a
- **Secondary:** Transparent with gold border, gold text, rounded-full, hover gold/10 background
- **Ghost:** Transparent, light text, hover surface-alt background
- **Danger:** Red background (#ef4444), white text, rounded-full

### Card

- Surface background (#0a0a0a), border rgba(255,255,255,0.06), rounded-2xl
- Hover: border transitions to gold/50
- Padding: 24px (lg)

### Input

- Surface background (#0a0a0a), border rgba(255,255,255,0.06), foreground text
- Focus: gold border (#d4a964), gold ring at 20% opacity
- Placeholder: muted-foreground (#737373)

### Badge

- Rounded-full, small text (caption size), colored background at 10% opacity
- See Status Colors table above for specific color mappings

### Table

- Header: muted text, uppercase label style, border-bottom
- Row: border rgba(255,255,255,0.06), hover surface-alt background
- Cell padding: 16px vertical, 24px horizontal

## Logo

The Evolution Stables wordmark uses Geist Sans in gold (#d4a964) on dark backgrounds. The wordmark is "Evolution Stables" with "Evolution" in bold (700) and "Stables" in regular weight (400).