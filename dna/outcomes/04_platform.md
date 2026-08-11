# Extraction Report: Evolution_Platform (Legacy Old Build)

**Note:** Evolution_Platform and SSOT_Build refer to the pre-evo_01 / workspace/projects/ structure. This is historical migration documentation only. Current surfaces and code are in evo_01/ per SURFACES.md.

**Source:** `/home/evo/workspace/projects/Evolution_Platform` (legacy)
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Next.js production build | Public website + marketplace + investor portal | Cloud Run or Firebase Hosting |
| Marketplace listing pages | Dynamic horse syndicate listings with real data | `/marketplace` route |
| MyStable dashboard | Auth-gated investor portfolio | `/mystable` route |
| Admin dashboard | RBAC-protected syndicator operations | `/admin` route |
| Investor Update HTML pages | Generated update pages served publicly | `/public/updates/` |
| SEO-optimized pages | Dynamic OG images, sitemaps, structured data | All public routes |
| Stripe checkout sessions | Payment processing for syndicate shares | Stripe API → Cloud Functions |
| Stripe Identity KYC sessions | Identity verification for investors | Stripe API → Cloud Functions |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Next.js 16 | Web framework (App Router) | Production build via `next build` |
| React 19 | UI library | Server Components for SEO |
| Tailwind CSS 4 | Styling | With `@tailwindcss/typography` |
| shadcn/ui | Component library | Via `class-variance-authority` + `tailwind-merge` |
| better-sqlite3 | Local database | Must migrate to Firestore |
| Stripe (`stripe`, `@stripe/stripe-js`, `@stripe/react-stripe-js`) | Payments + KYC | Cloud Functions for webhooks |
| viem + wagmi | Ethereum interaction | For wallet connection (Stage 2) |
| next-auth | Authentication | v4 — consider v5 or Firebase Auth |
| Resend | Email delivery | For investor communications |
| Zod | Schema validation | API input validation |
| Framer Motion | Animations | UI polish |
| GSAP | Advanced animations | Hero sections, transitions |
| Playwright | E2E testing | Test suite exists |
| Vitest | Unit testing | Test suite exists |
| Husky + lint-staged | Git hooks | Pre-commit linting |

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| `NEXTAUTH_SECRET` | NextAuth encryption key | Yes |
| `NEXTAUTH_URL` | NextAuth base URL | Yes |
| `STRIPE_SECRET_KEY` | Stripe server-side key | Yes |
| `STRIPE_PUBLISHABLE_KEY` | Stripe client-side key | Yes |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | Yes |
| `DATABASE_PATH` | SQLite database file path | Yes (local) |
| `RESEND_API_KEY` | Email delivery | Yes |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Client-side Stripe key | Yes |
| `NEXT_PUBLIC_STAGE_1_MODE` | Toggle Stage 1 (digital) vs Stage 2 (on-chain) | Yes |
| `NODE_OPTIONS` | Memory limit (`--max-old-space-size=4096`) | Dev only |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `just check` | TypeScript type-check (`tsc --noEmit`) + production build |
| `npm run build` | Full Next.js production build |
| `npm run lint` | ESLint with Next.js + security plugins |
| `npm test` | Vitest unit tests |
| `npm run test:e2e` | Playwright end-to-end tests |
| `npm run generate:simple` | Generate investor update HTML |
| Husky pre-commit | Lint-staged (ESLint + Prettier) |

**This project has the best test coverage in the ecosystem.** Vitest + Playwright + lint-staged.

---

## Key Business Logic / Pipeline Milestones

1. **Public Marketing Pages** — Home, about, press (SEO-first, Server Components)
2. **Marketplace Listings** — Dynamic horse listings driven by SSOT_Build data
3. **Investor Onboarding** — Browse → Register → KYC → Invest flow
4. **MyStable Dashboard** — Auth-gated portfolio showing holdings, documents, updates
5. **Admin Dashboard** — RBAC-protected syndicator operations (cap table, investor list)
6. **SSOT Sync** — Receive HLT payloads from SSOT_Build via POST `/api/marketplace/sync`
7. **Investor Update Delivery** — Serve generated HTML updates to investors

### Critical Business Rules

- SEO-first architecture (Server Components, dynamic OG images, sitemaps, structured data)
- Live marketplace listings driven by SSOT_Build data (not stale copies)
- Auth-gated `/mystable` and `/admin` routes
- RBAC on admin (role-based middleware)
- SSOT sync must work (auto + manual trigger)
- Stage 1 bypass must be toggleable via `NEXT_PUBLIC_STAGE_1_MODE`
- KYC verification is mandatory before any investment
- Stripe payments in NZD
- Real-time cap table in admin dashboard
- Document acknowledgement (PDS + SA) recorded before payment

### Data Flow (Unidirectional)

```
SSOT_Build → Evolution_Platform (HLT payloads → marketplace listings)
Evolution_Token → Evolution_Platform (holdings data → MyStable dashboard)
Evolution_Content → Evolution_Platform (public content: tips, results, news)
Evolution_Studio → Evolution_Platform (delivery copies: videos, HTML updates)
Evolution_Platform → Evolution_CRM (lead capture from public site)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| SQLite as production database | No concurrency, no cloud access | Migrate to Firestore for listings, Cloud SQL for auth/session |
| NextAuth v4 | Outdated auth library | Migrate to NextAuth v5 or Firebase Auth + custom claims |
| 108MB `public/` directory | Unoptimized static assets | Move to Cloud Storage + CDN, optimize images |
| Manual `git push` for content deployment | Error-prone, not auditable | Replace with Pub/Sub → Cloud Build trigger |
| File watcher for SSOT sync | Fragile, local-only | Replace with Firestore triggers or Cloud Functions |
| Wallet-only auth (no email) | Limits user base | Add Firebase Auth for email/password + social login |
| Separate repo from Evolution_Token | Merge hell, duplicate deps | Consider single Next.js app with RBAC (defer monorepo) |