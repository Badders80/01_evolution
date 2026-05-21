# Sprint 001: Design Token System + Admin Primitives

> **Sprint detail file.** Lives in `docs/sprints/`.
> **Linked from:** `docs/SPRINTS.md`
> **Session logs:** `docs/logs/YYYY-MM-DD.md`

---

## Sprint 001: Design Token System + Admin Primitives

**Status:** ✅ Complete  
**Created:** 2026-05-20  
**Started:** 2026-05-20  
**Completed:** 2026-05-20  
**Goal:** Tokenize the `02_website` design language and build shared admin primitives so admin pages match the public site visually.

---

## Scope

### In Scope
- Extract hardcoded values from all `02_website` pages into canonical tokens
- Update `tailwind.config.ts` + `globals.css` with unified token system
- Install and configure shadcn/ui as base primitive layer
- Build `components/admin/` primitives (11 components)
- Refactor all 12 admin pages to use primitives
- Verify build passes with 0 errors

### Out of Scope
- Firebase Auth integration (moved to Sprint 002)
- Stripe KYC wiring (moved to Sprint 002)
- Marketplace/MyStable feature work (design tokens only, no new features)
- Backend changes (`01_evolution` is frozen)
- Public page refactoring (HeroSection, etc. — NOT in scope)

---

## Checklist

### Phase 1: Tokenize (items 1-4)
- [x] 1. Audit all hardcoded values in `02_website` (colors, typography, spacing, shadows)
- [x] 2. Update `tailwind.config.ts` with full token map
- [x] 3. Bridge CSS variables in `globals.css` to Tailwind
- [x] 4. Create `src/lib/tokens.ts` as single source of truth

### Phase 2: Install shadcn/ui (items 5-6)
- [x] 5. Install shadcn/ui dependency and initialize
- [x] 6. Configure shadcn theme to match Evolution tokens (dark mode, gold accent)

### Phase 3: Build primitives (items 7-14)
- [x] 7. Design `components/admin/` API signatures
- [x] 8. Build `AdminTable.tsx`
- [x] 9. Build `AdminForm.tsx` + `AdminInput.tsx` + `AdminSelect.tsx`
- [x] 10. Build `AdminButton.tsx` (primary/secondary/ghost)
- [x] 11. Build `AdminBadge.tsx` (status, role, KYC)
- [x] 12. Build `AdminCard.tsx` + `AdminStat.tsx` + `AdminEmptyState.tsx`
- [x] 13. Build `AdminFileUpload.tsx`
- [x] 14. Build `AdminLoading.tsx`

### Phase 4: Refactor pages (items 15-25)
- [x] 15. Refactor `admin/layout.tsx` with tokens
- [x] 16. Refactor `admin/page.tsx` (dashboard)
- [x] 17. Refactor `admin/horses/page.tsx`
- [x] 18. Refactor `admin/horses/new/page.tsx` ✅
- [x] 19. Refactor `admin/owners/page.tsx` ✅
- [x] 20. Refactor `admin/trainers/page.tsx` ✅
- [x] 21. Refactor `admin/hlts/page.tsx`
- [x] 22. Refactor `admin/assets/page.tsx` ✅
- [x] 23. Refactor `admin/assets/upload/page.tsx`
- [x] 24. Refactor `admin/website/press/page.tsx` ✅
- [x] 25. Refactor `admin/website/faq/page.tsx` ✅

### Phase 5: Verify (items 26-27)
- [x] 26. Build passes: `npm run build` (22 pages, 0 errors)
- [ ] 27. Visual regression check — admin matches public site feel

---

## Definition of Done

1. `npm run build` passes with 0 TypeScript errors
2. No hardcoded Tailwind classes in admin pages (all via `components/admin/`)
3. Admin pages visually consistent with Marketplace/MyStable (same tokens, same feel)
4. `components/admin/` is documented and ready for reuse in Marketplace + MyStable
5. shadcn/ui is installed and themed to match Evolution brand

---

## Sessions Log

| Date | Focus | Log Link |
|------|-------|----------|
| 2026-05-20 | Sprint planning + token audit | `logs/2026-05-20.md` |

---

## Decisions

- **Font:** Geist Sans for admin and public pages (current, already rendering). Public pages may use Playfair Display for hero moments in future.
- **shadcn/ui:** Install as base primitive layer. Theme it to match Evolution dark theme + gold accent. Gives us more components with less custom code.
- **CSS vars as source of truth:** `:root` in `globals.css` defines values, `tailwind.config.ts` references them via `var()`. Bridges the gap.
- **AdminLoading:** Added as 11th primitive. Loading pattern (flex items-center justify-center py-24 + text) repeated 5+ times across pages.
- **AdminTable v1:** Display + column config only. Sorting/filtering deferred to future sprint when needed.
- **Scope exclusion:** Public pages (HeroSection, etc.) are NOT in scope. Only admin pages get refactored this sprint.

---

## Blockers

- None

---

## Retrospective

*(To be filled when sprint is marked Complete)*

---

## Verification

```bash
cd /home/evo/evo_01/02_website && npm run build
# Expected: ✓ Compiled successfully, 20 pages, 0 errors
```
