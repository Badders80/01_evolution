# Evolution Stables — Update Builder v2

Structured editor for creating production-quality investor updates. Outputs two HTML versions:
- **v2:** Full dark editorial (website hosting)
- **v3:** Gmail teaser (email)

## Quick Start

```bash
npm install
npm run dev
```

Opens at http://localhost:3051

## Features

- **Structured content entry** — No parsing, just fill in the fields
- **Live preview** — See v2 HTML update as you type
- **Copy-to-clipboard** — One-click copy for both v2 and v3 HTML
- **Email-safe templates** — Table-based, inline styles, tested in Gmail
- **Brand-compliant** — Uses Evolution Stables colors (#d4a964, #121212) and typography (Playfair Display + Inter)

## Content Structure

| Field | Required | Description |
|-------|----------|-------------|
| Preheader | Yes | Hidden email preview text |
| Slug | Yes | URL-safe filename (e.g. `Prudentia-Update-20May2026`) |
| Heading | Yes | Headline, 8-12 words |
| Subheader Label | Yes | e.g. "FEATURED RUNNER" |
| Subheader Bullets | Yes | 2-5 bullet points |
| Body | Yes | 1-3 paragraphs |
| Quote | Yes | Quote text + attribution |
| Link | No | CTA URL + label |
| Hero Image | No | Image URL + caption |
| Sign-off | Yes | Name + title |

## Template Sources

- **v2:** Based on `Prudentia-Update-12May2026.html` (dark editorial, table-based)
- **v3:** Based on `v3-gmail.html` (light Gmail teaser)

## Next Steps

1. Test with existing updates (recreate Prudentia-TeRapa-17Apr2026, etc.)
2. Wire save/publish APIs (POST /updates, POST /updates/upload-html)
3. Port to Next.js in 02_website/ for production use
