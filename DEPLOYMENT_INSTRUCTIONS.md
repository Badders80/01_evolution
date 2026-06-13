# Deployment Instructions — 2026-06-12

## Summary

CORS configuration has been updated to include Vercel domains. The changes are committed and pushed to GitHub.

## What Was Changed

### Files Modified:
1. `api/ssot/main.py` - Added Vercel domains to `ALLOWED_ORIGINS`
2. `api/assets/main.py` - Added Vercel domains to `ALLOWED_ORIGINS`
3. `api/kyc/main.py` - Added Vercel domains to `ALLOWED_ORIGINS`
4. `api/proxy/server.js` - Added CORS middleware to all routes + Vercel domains

### Git Commit:
```
b86fe54 - feat: add Vercel domains to CORS config for ssot, assets, kyc, and proxy
```

## Manual Deployment Steps

### Step 1: Refresh gcloud Authentication

Run this command manually in your terminal:

```bash
gcloud auth login
```

Or if you prefer, refresh the application default credentials:

```bash
gcloud auth application-default login
```

### Step 2: Deploy Cloud Functions

Run these commands in order:

```bash
# Deploy SSOT function
cd /home/evo/evo_01/01_evolution
just deploy-ssot

# Deploy Assets function
just deploy-assets

# Deploy KYC function
just deploy-kyc
```

### Step 3: Deploy Cloud Run Proxy

```bash
# Build and push the proxy image
cd /home/evo/evo_01/01_evolution/api/proxy
gcloud builds submit --tag gcr.io/evolution-engine/evolution-api-proxy

# Deploy to Cloud Run
gcloud run deploy evolution-api-proxy \
  --image gcr.io/evolution-engine/evolution-api-proxy \
  --region australia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars="ALLOWED_ORIGINS=https://evolution.2.0.vercel.app,https://02website-pearl.vercel.app"
```

### Step 4: Verify CORS is Working

After deployment, test the handshake page:

1. Visit: `https://02website-pearl.vercel.app/handshake`
2. Click each endpoint button to test
3. All 7 should show **OK** with green status

---

## Current Status

| Component | Status |
|-----------|--------|
| CORS config updated | ✅ Committed & pushed |
| Cloud Functions | 🔴 Need redeployment |
| Cloud Run proxy | 🔴 Need redeployment |
| Vercel OIDC | 🔴 Enable in dashboard |

---

## Next Steps After Deployment

1. **Test handshake page** - All 7 endpoints should be green
2. **Enable Vercel OIDC** - Dashboard → Settings → Security → OpenID Connect
3. **Redeploy Vercel** - Trigger a new deployment
4. **Test end-to-end** - Apply to Own → KYC flow

---

## Troubleshooting

### If CORS still fails:
- Check Cloud Functions logs: `gcloud functions logs read --region australia-southeast1`
- Verify `ALLOWED_ORIGINS` env var is set correctly
- Check Cloud Run proxy logs: `gcloud run logs service/evolution-api-proxy --region australia-southeast1`

### If handshake shows < 7 green:
- Verify all 3 Cloud Functions are deployed and healthy
- Check Cloud Run proxy is serving
- Confirm Vercel OIDC is enabled
