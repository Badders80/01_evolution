# Sprint 004: Investor Update Editor

> **Sprint detail file.** Lives in `docs/sprints/`.
> **Linked from:** `docs/SPRINTS.md`
> **Session logs:** `docs/logs/YYYY-MM-DD.md`

---

## Sprint 004: Investor Update Editor

**Status:** 🟡 Planned  
**Created:** 2026-05-20  
**Started:** —  
**Completed:** —  
**Goal:** Build an investor update editor where structured content is entered and instantly renders production-quality HTML outputs (v2 full editorial + v3 Gmail teaser).

---

## Scope

### In Scope
- Investor update editor page (`/admin/updates/new`) with structured content entry
- Live preview of v2 full editorial HTML as content is entered
- Two template outputs: v2 (website page) and v3 (Gmail teaser)
- Copy-to-clipboard workflow for both v2 and v3 HTML
- Save update metadata to Firestore via SSOT API
- Upload rendered HTML to GCS via Assets API
- List view of all updates (`/admin/updates`)
- Public route for viewing updates (`/updates/[slug]`)
- Index page listing all published updates (`/updates`)

### Out of Scope
- LLM content generation (user provides all content)
- Automated Gmail sending (manual copy-paste workflow)
- Template variant switching (single canonical v2 template)
- Multi-section updates (single topic per update for MVP)
- Image upload within editor (use existing Assets API separately)
- Recipient list management (deferred to Gmail workflow phase)
- Telegram notification integration (legacy from old pipeline)

---

## Checklist

### Phase 1: Editor Page (items 1-8)
- [ ] 1. Create `/admin/updates/new` page with two-panel layout (form + preview)
- [ ] 2. Build structured form with fields for all content blocks (Preheader, Slug, Heading, Subheader, Body, Quote, Link, Hero Image, Sign-off)
- [ ] 3. Port v2 template to React component (based on `Prudentia-Update-12May2026.html`)
- [ ] 4. Port v3 template to React component (Gmail teaser)
- [ ] 5. Implement live preview in iframe, updating as content is typed
- [ ] 6. Add "Copy v2 HTML" button — generates standalone HTML, copies to clipboard
- [ ] 7. Add "Copy v3 HTML" button — generates standalone HTML, copies to clipboard
- [ ] 8. Add form validation (required fields, slug format, URL validation)

### Phase 2: Save & Publish (items 9-13)
- [ ] 9. Add `POST /updates` endpoint to SSOT API — saves metadata to Firestore `updates` collection
- [ ] 10. Add `POST /updates/upload-html` endpoint to Assets API — uploads v2 HTML to GCS `updates/{slug}.html`
- [ ] 11. Wire "Save" button in editor to call both APIs
- [ ] 12. Add success/error feedback (toasts, loading states)
- [ ] 13. Add "Publish" action to set status to `published`

### Phase 3: List & Public Routes (items 14-18)
- [ ] 14. Create `/admin/updates` list page — shows all updates with slug, title, date, status
- [ ] 15. Add filter by status (draft, published)
- [ ] 16. Create `/updates/[slug]` dynamic route — fetches and renders v2 HTML from GCS or Firestore
- [ ] 17. Create `/updates` index page — lists all published updates with links
- [ ] 18. Add SEO metadata (title, description, robots noindex for draft)

### Phase 4: Polish & Verification (items 19-24)
- [ ] 19. Add loading skeletons for preview panel
- [ ] 20. Add empty state for `/admin/updates` list
- [ ] 21. Add mobile responsiveness check (editor, list, public pages)
- [ ] 22. Verify all 5 existing example updates can be reproduced in the editor
- [ ] 23. Test copy-paste workflow: v2 → browser, v3 → Gmail preview
- [ ] 24. Verify build passes: `npm run build`

---

## Acceptance Criteria

1. **Editor loads** at `/admin/updates/new` with all content block fields visible
2. **Live preview** updates in real-time as content is typed (no manual refresh needed)
3. **Copy buttons work** — v2 HTML renders correctly when pasted into browser, v3 HTML renders correctly in Gmail
4. **Save works** — update metadata saved to Firestore, HTML uploaded to GCS, URL returned
5. **List page shows updates** — `/admin/updates` displays all saved updates with correct metadata
6. **Public route works** — `/updates/{slug}` renders the v2 HTML correctly
7. **Index page lists updates** — `/updates` shows all published updates with links
8. **All example updates reproducible** — Prudentia-TeRapa-17Apr2026, Prudentia-Pukekohe-01Apr2026, First-Gear-Update-22Dec2025, etc. can be recreated in the editor

---

## Dependencies

- **Blocks on:** None (greenfield feature)
- **Blocked by:** None
- **Related:** Sprint 002 (Horse Registration + Content Upload) — uses same Assets API for HTML upload
- **Follows:** Existing admin UI patterns from Sprint 002

---

## Notes

- **Template source:** `Evolution_Platform/public/updates/Prudentia-Update-12May2026.html` is the canonical v2 reference
- **Writing guide:** `Evolution_Studio/.../WRITING_STYLE_GUIDE.md` for voice/tone rules
- **Content schema:** `Evolution_Studio/.../CONTENT_BACK_GUIDE.md` for tag/block structure
- **Brand system:** `01_evolution/dna/brand/BRAND_SYSTEM.md` for colors (#d4a964, #121212) and typography (Playfair Display + Inter)
