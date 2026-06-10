# Sprint Zero: Foundation & Security

**Status:** 🟡 IN PROGRESS  
**Date Created:** 2026-06-10  
**Priority:** 🔴 CRITICAL (P0)  
**Estimated Effort:** 8-10 hours  

---

##  Executive Summary

**Trigger:** Comprehensive backend audit revealed critical technical debt blocking confident iteration.

**Goal:** Establish zero-debt foundation with unified models, working tests, and production security.

**Success Criteria:**
- ✅ Single canonical model source (`api/core/models.py`)
- ✅ All tests passing (7/7 test files)
- ✅ Admin API secured with Firebase Auth
- ✅ CORS restricted to known domains
- ✅ Mission Control UI fully functional

---

## 🔍 Audit Summary (2026-06-10)

**Overall Score:** 6.1/10 — 🟡 NEEDS ATTENTION

| Dimension | Score | Status |
|-----------|-------|--------|
| Architecture & Design | 9/10 | 🟢 Excellent |
| **Model Consistency** | **4/10** | 🔴 **Critical** |
| API Contract Compliance | 7/10 | 🟡 Needs Work |
| **Test Infrastructure** | **2/10** | 🔴 **Broken** |
| **Security & Data Integrity** | **6/10** | 🔴 **Gaps Exist** |
| Performance & Scalability | 7/10 | 🟡 Good Foundation |
| Deployment & Ops | 8/10 | 🟢 Production-Ready |

### 🔴 Top 3 Critical Issues Identified

1. **Model Fragmentation** — 3+ conflicting model definitions (`api/models`, `api/ssot/models`, `api/admin/models`, `api/admin/db.py`)
2. **Broken Tests** — 4/7 test files fail at import time (missing Flask, models)
3. **Admin Auth Bypass** — Zero authentication on admin API endpoints

---

## ✅ Completed Work

### Phase 1: Model Consolidation (✅ DONE — 2026-06-10)

**Goal:** Single source of truth for all Pydantic models

**Actions:**
- ✅ Created `api/core/models.py` as canonical model layer
  - Contains: Horse, Owner, Trainer, HLT, Lease, Asset, Content, DocumentRecord, Holding, GoverningBody
  - All pricing engines, validators, and helper functions included
- ✅ Deleted duplicate model layers:
  - ❌ `api/models/__init__.py`
  - ❌ `api/ssot/models/__init__.py`
  - ❌ `api/admin/models.py`
- ✅ Updated 20+ files to import from `core.models`:
  - SSOT routes: `horses.py`, `owners.py`, `trainers.py`, `hlts.py`, `leases.py`, `docs.py`, `holdings.py`, `content.py`, `governing_bodies.py`
  - Tests: All test files updated
  - Admin server: `admin_server.py`
  - Scripts: `seed_canonical_entities.py`
- ✅ Fixed test infrastructure:
  - Added `Flask`, `Flask-CORS`, `beautifulsoup4`, `requests`, `pytest`, `pytest-flask` to `api/requirements.txt`
  - Installed all dependencies

**Validation:**
```bash
✅ python -c "from core.models import *"  # All models import successfully
✅ curl http://localhost:5000/api/horses  # Returns data correctly
✅ curl http://localhost:5000/api/health  # Health endpoint works
✅ pytest api/ssot/tests/ -v  # 128/128 tests pass
```

**Status:** Backend models are now **locked in** with zero drift.

---

### Phase 2: Frontend Cache Fix (✅ DONE — 2026-06-10)

**Goal:** Mission Control UI displays data correctly

**Actions:**
- ✅ Added `type="module"` to script tags in `api/admin/static/index.html`
  - Changed: `<script src="app.js"></script>` → `<script type="module" src="app.js"></script>`
- ✅ Verified server serves files with correct MIME types

**Status:** UI ready for validation (pending browser cache clear).

---

### Phase 3: Test Suite Verification (✅ DONE — 2026-06-10)

**Goal:** All test files pass

**Results:**
```
======================= 128 passed, 4 warnings in 1.01s ========================
```

**Test Coverage:**
- ✅ `test_docs.py` — 24 tests (was broken, now passes)
- ✅ `test_extract_endpoint.py` — 11 tests (was broken, now passes)
- ✅ `test_governing_bodies.py` — 13 tests (was broken, now passes)
- ✅ `test_hlt.py` — All tests pass
- ✅ `test_horses.py` — All tests pass
- ✅ `test_leases.py` — All tests pass (was broken, now passes)
- ✅ `test_owners.py` — All tests pass
- ✅ `test_trainers.py` — All tests pass

**Status:** ✅ **Model consolidation is 100% verified!**

---

### Phase 4: Admin Authentication (✅ DONE — 2026-06-10)

**Goal:** Secure admin API with Firebase Auth

**Actions:**
- ✅ Created `api/admin/auth.py` — Firebase Auth middleware
  - `@require_auth` decorator for protecting endpoints
  - Verifies Firebase ID tokens
  - Returns 401 Unauthorized without valid token
- ✅ Protected all `/api/*` endpoints in `admin_server.py`:
  - `/api/horses/*` — All CRUD operations
  - `/api/owners/*` — All CRUD operations
  - `/api/trainers/*` — All CRUD operations
  - `/api/leases/*` — All CRUD operations
  - `/api/hlts/*` — List and workflow
  - `/api/governing-bodies/*` — CRUD operations
  - `/api/stats` — Dashboard stats
- ✅ Excluded from auth:
  - `/api/health` — Public health check
  - Static files (`/`, `/*.js`, `/*.html`) — UI assets

**Validation:**
```bash
✅ curl http://localhost:5000/api/health
   → {"status": "ok"}  (works without auth)

✅ curl http://localhost:5000/api/horses
   → {"error": "Missing or invalid Authorization header"}  (401 Unauthorized)
```

**Files Created/Modified:**
- ✅ Created: `api/admin/auth.py`
- ✅ Modified: `api/admin_server.py` (added `@require_auth` to 20+ endpoints)
- ✅ Dependency: `firebase-admin` (already installed)

**Status:** ✅ **Admin API is now secured!**

**Next Step:** Update frontend to attach Firebase auth headers (Phase 4b).

---

## 🔴 In Progress

### Phase 3: Test Suite Verification (⏳ PENDING — 30 min)

**Goal:** All 7 test files pass

**Commands:**
```bash
cd /home/evo/evo_01/01_evolution/api
source .venv/bin/activate
pytest ssot/tests/ -v
```

**Expected Results:**
- ✅ `test_horses.py` — 19 tests pass
- ✅ `test_owners.py` — Pass
- ✅ `test_trainers.py` — Pass
- ✅ `test_leases.py` — Pass (was broken, model now exists)
- ✅ `test_governing_bodies.py` — Pass (was broken, model now exists)
- ✅ `test_hlt.py` — Pass
- ✅ `test_docs.py` — Pass (was broken, model now exists)
- ✅ `test_extract_endpoint.py` — Pass (Flask now installed)

**Status:** Ready to execute.

---

## 🚨 Critical Security Fixes (TODO)

### Phase 4: Admin Authentication (⏳ TODO — 3-4 hrs)

**Risk:** Anyone can access admin API — create/delete horses, owners, HLTs without authentication

**Current State:**
```python
# api/admin_server.py — NO AUTH CHECKS
@app.route("/api/horses", methods=["GET", "POST"])
@app.route("/api/owners", methods=["GET", "POST", "PATCH", "DELETE"])
# ... all endpoints completely open
```

**Implementation Plan:**

1. **Create `api/admin/auth.py`** — Firebase Auth middleware
   ```python
   from firebase_admin import auth
   
   def require_auth(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
           try:
               decoded_token = auth.verify_id_token(id_token)
               request.user = decoded_token
               return f(*args, **kwargs)
           except Exception:
               return jsonify({"error": "Unauthorized"}), 401
       return decorated_function
   ```

2. **Protect all endpoints** in `api/admin_server.py`
   ```python
   from admin.auth import require_auth
   
   @app.route("/api/horses", methods=["GET", "POST"])
   @require_auth
   def list_horses():
       # ... existing code
   ```

3. **Frontend: Add auth to `api/admin/static/app.js`**
   - Get Firebase ID token on app load
   - Attach to all API requests: `Authorization: Bearer <token>`

4. **Test:**
   - Without token → 401 Unauthorized
   - With valid token → 200 OK
   - Admin role check (optional for now)

**Files to Create/Modify:**
- ✏️ Create: `api/admin/auth.py`
- ✏️ Modify: `api/admin_server.py` (add `@require_auth` to all routes)
- ✏️ Modify: `api/admin/static/app.js` (attach auth header)
- ✏️ Add dependency: `firebase-admin` to `api/requirements.txt`

**Definition of Done:**
- ✅ All admin endpoints return 401 without auth token
- ✅ Frontend successfully authenticates and displays data
- ✅ Test suite includes auth tests

---

### Phase 5: CORS Restriction (⏳ TODO — 1 hr)

**Risk:** Any website can make requests to your API (CSRF-style attacks)

**Current State:**
```python
# api/ssot/main.py, api/assets/main.py, api/kyc/main.py
response.headers.add("Access-Control-Allow-Origin", "*")  # WILDCARD!
```

**Implementation Plan:**

1. **Define allowed origins** in environment variables
   ```python
   ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://evolutionstables.nz").split(",")
   ```

2. **Replace wildcard with dynamic origin check**
   ```python
   @app.after_request
   def add_cors_headers(response):
       origin = request.headers.get('Origin')
       if origin in ALLOWED_ORIGINS:
           response.headers.add('Access-Control-Allow-Origin', origin)
           response.headers.add('Access-Control-Allow-Credentials', 'true')
       return response
   ```

3. **Update all 3 Cloud Functions:**
   - `api/ssot/main.py`
   - `api/assets/main.py`
   - `api/kyc/main.py`

**Files to Modify:**
- ✏️ `api/ssot/main.py`
- ✏️ `api/assets/main.py`
- ✏️ `api/kyc/main.py`

**Definition of Done:**
- ✅ `*` replaced with allowlist
- ✅ Frontend domains configured in `.env`
- ✅ Requests from unknown origins blocked

---

## 🟡 Performance Improvements (TODO)

### Phase 6: Fix Admin UI N+1 Problem (⏳ TODO — 3-4 hrs)

**Risk:** Admin UI loads ALL entities on every page load — will be slow with 1000+ horses

**Current State:**
```javascript
// app.js:345-347 — renderCreateHlt()
const [horses, owners, trainers, governing_bodies, leases] = await Promise.all([
  loadHorses(), loadOwners(), loadTrainers(), loadGoverningBodies(), loadHlts()
]);
```

**Implementation Plan:**

1. **Add pagination to API endpoints**
   - `GET /api/horses?limit=50&offset=0`
   - `GET /api/horses?search=Prudentia`

2. **Lazy-load entities in UI**
   - Load horses only when "Select Horse" dropdown opens
   - Add search/filter before loading

3. **Add server-side filtering**
   - `GET /api/horses?sex=mare&status=active`

**Files to Modify:**
- ✏️ `api/admin_server.py` (add pagination params)
- ✏️ `api/admin/static/app.js` (lazy loading)

**Definition of Done:**
- ✅ Initial page load < 500ms
- ✅ Dropdowns load on-demand
- ✅ Search works efficiently

---

## 📅 Timeline

| Phase | Task | Effort | Status |
|-------|------|--------|--------|
| **Phase 1** | Model Consolidation | 1 hr | ✅ DONE |
| **Phase 2** | Frontend Cache Fix | 5 min | ✅ DONE |
| **Phase 3** | Test Suite Verification | 30 min | ⏳ READY |
| **Phase 4** | Admin Authentication | 3-4 hrs | 🔴 TODO |
| **Phase 5** | CORS Restriction | 1 hr | 🔴 TODO |
| **Phase 6** | N+1 Performance Fix | 3-4 hrs | 🟡 TODO |

**Total Estimated Time:** 8-10 hours

---

## 🎯 Mission Control UI Status

### Current State: ✅ **READY FOR VALIDATION**

**What Works:**
- ✅ Backend API serves data correctly
- ✅ All models consolidated
- ✅ Script modules configured correctly
- ✅ Server running on port 5000

**What's Needed:**
1. **Browser cache clear** — Force reload JavaScript files
2. **Test Suite Verification** — Run `pytest` to confirm backend works
3. **Admin Auth** — Once added, UI will authenticate properly

### When Will It Be Fully Functional?

**Timeline:**
- **Today (after Phase 3):** UI displays data correctly (no auth yet)
- **Today (after Phase 4):** UI fully secured with Firebase Auth
- **Tomorrow (after Phase 5-6):** Production-ready with performance optimizations

**Verification Steps (Do Now):**
1. Open browser DevTools → Network tab
2. Navigate to http://localhost:5000/#/
3. Check if `app.js` and `hlt-engine.js` load with status 200
4. Check if API calls are made (`/api/horses`, `/api/stats`, etc.)
5. Verify Dashboard shows stats cards

If still blank:
- Hard refresh: `Ctrl+Shift+R` (Linux/Windows) or `Cmd+Shift+R` (Mac)
- Clear cache: `Ctrl+Shift+Delete` → Clear cached images
- Check browser console for errors

---

## 📝 Related Documents

- **Main Plan:** [`GAME_PLAN.md`](GAME_PLAN.md) — 9 checkpoints
- **Blockers:** [`BLOCKERS.md`](BLOCKERS.md) — Resolved issues
- **Audit Report:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Full audit findings
- **Progress:** [`docs/PROGRESS.md`](docs/PROGRESS.md) — Live build tracker
- **Architecture:** [`AGENTS.md`](AGENTS.md) — Core laws

---

## 🚀 Next Actions

**Immediate (Next 30 min):**
1. Run `pytest api/ssot/tests/ -v` to verify all tests pass
2. Fix any remaining test failures
3. Validate Mission Control UI displays data

**Today (Remaining 6-8 hrs):**
4. Implement Firebase Auth on admin server
5. Restrict CORS to known domains
6. Test end-to-end flow with auth enabled

**Result:** Production-ready, secure foundation with zero technical debt.
