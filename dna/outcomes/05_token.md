# Extraction Report: Evolution_Token

**Source:** `/home/evo/workspace/projects/Evolution_Token`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Next.js production build | Syndication platform (marketplace + MyStable + admin) | Cloud Run or Firebase Hosting |
| HorseLeaseToken.sol (compiled) | ERC-20 smart contract with KYC-gated transfers | Base Sepolia testnet → Base mainnet |
| Contract deployment artifacts | ABI + address JSON for frontend integration | Hardhat artifacts directory |
| Stripe checkout sessions | Payment processing for syndicate shares | Stripe API → Cloud Functions |
| Stripe Identity KYC sessions | Identity verification for investors | Stripe API → Cloud Functions |
| SQLite database | User, investment, and holdings data | Must migrate to Firestore |
| Openfort embedded wallets | Wallet creation for Stage 2 on-chain | Openfort API |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Next.js 16 | Web framework | App Router |
| React 19 | UI library | |
| Hardhat | Solidity compilation + deployment | Smart contract toolchain |
| viem + wagmi | Ethereum interaction | Chain-configurable |
| better-sqlite3 | Local database | Must migrate to Firestore |
| Stripe (`stripe`, `@stripe/stripe-js`, `@stripe/react-stripe-js`) | Payments + KYC | Cloud Functions for webhooks |
| Openfort (`@openfort/openfort-js`) | Embedded wallet creation | Stage 2 feature |
| Zod | Schema validation | API input validation |
| Framer Motion | Animations | UI polish |
| Winston | Structured logging | Production logging |
| rate-limiter-flexible | Rate limiting | API protection |
| @excalidraw/excalidraw | Diagram rendering | Architecture diagrams in admin |
| Tailwind CSS 4 | Styling | |
| OpenZeppelin Contracts | ERC-20 base | Smart contract library |

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe client-side key | Yes |
| `STRIPE_SECRET_KEY` | Stripe server-side key | Yes |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | Yes |
| `NEXTAUTH_SECRET` | NextAuth encryption key | Yes |
| `NEXTAUTH_URL` | NextAuth base URL | Yes |
| `DATABASE_PATH` | SQLite database file path | Yes (local) |
| `NEXT_PUBLIC_STAGE_1_MODE` | Toggle Stage 1 (digital) vs Stage 2 (on-chain) | Yes |
| `NEXT_PUBLIC_ALCHEMY_API_KEY` | Ethereum node provider | Yes (for viem) |
| `NEXT_PUBLIC_OPENFORT_API_KEY` | Embedded wallet creation | Stage 2 |
| `NEXT_PUBLIC_CONTRACT_ADDRESS` | Deployed contract address | Post-deployment |
| `PRIVATE_KEY` | Contract deployer wallet key | Deployment only |
| `ETHERSCAN_API_KEY` | Contract verification | Deployment only |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `just check` | TypeScript type-check + Hardhat contract compilation |
| `npm run build` | Full Next.js production build |
| `npm run test` | Integration tests (`tests/integration.test.ts`) |
| `npm run test:unit` | Unit tests (`test-runner.ts`) |
| `npm run test:contract` | Hardhat contract tests |
| `npm run lint` | ESLint |
| `npm run ci` | Full CI: check + test:unit + build |
| `just deploy` | Deploy contract to Ethereum Sepolia testnet |
| `just verify` | Verify contract on Etherscan |

**This project has the second-best test coverage** (integration + unit + contract tests).

---

## Key Business Logic / Pipeline Milestones

1. **Browse Marketplace** — Investor browses syndicate listings with real horse data
2. **Register Interest** — Investor creates account (wallet-based in Stage 1)
3. **KYC Verification** — Stripe Identity session for identity verification
4. **Document Acknowledgement** — Investor acknowledges PDS + SA before payment
5. **Stripe Payment** — NZD payment via Stripe checkout
6. **Share Confirmation** — Digital share confirmation in MyStable dashboard
7. **Admin Cap Table** — Real-time view of investors, shares sold, and holdings
8. **Stage 2 (Future)** — Digital shares become on-chain ERC-20 tokens on Base

### Critical Business Rules

- KYC verification is mandatory before any investment
- Stripe payments in NZD only
- Real-time cap table in admin dashboard
- Document acknowledgement (PDS + SA) recorded before payment
- Stage 1 bypass must be toggleable via `NEXT_PUBLIC_STAGE_1_MODE`
- Smart contract: `HorseLeaseToken.sol` (ERC-20 with KYC-gated transfers)
- Contract deployed via Hardhat to Base Sepolia (testnet) → Base mainnet (production)

### Data Flow (Unidirectional)

```
SSOT_Build → Evolution_Token (HLT data: horse identity, terms, pricing)
Evolution_Platform → Evolution_Token (listing data, investor sign-ups)
Evolution_Token → Evolution_CRM (investor data, KYC status, holdings)
Evolution_Token → Evolution_Ops (financial data for GST/reconciliation)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| SQLite as production database | No concurrency, no cloud access, no multi-user | Migrate to Firestore for user/investor data; consider Cloud SQL for relational data |
| Wallet-only auth (no email) | Limits user base, no recovery mechanism | Add Firebase Auth for email/password + social login with wallet linking |
| Separate repo from Evolution_Platform | Merge hell, duplicate deps, fragile manual promotion | Consider single Next.js app with RBAC (defer monorepo) |
| No automated deployment | Manual `git push` and `hardhat deploy` | Add Cloud Build CI/CD pipeline |
| Hardcoded contract addresses | Fragile on redeployment | Use environment variables for contract addresses |
| Openfort dependency for Stage 2 | Unproven at scale | Validate Openfort integration before Stage 2 commitment |
| No Firestore security rules | Data exposure risk | Define and deploy Firestore security rules before any production data |