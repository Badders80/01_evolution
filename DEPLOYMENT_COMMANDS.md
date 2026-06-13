# Deployment Commands — Run Manually

## Step 1: Refresh gcloud Authentication

Run this command in your terminal:

```bash
gcloud auth login
```

Then paste the verification code from your browser.

---

## Step 2: Deploy Cloud Functions

After authentication succeeds, run these commands:

```bash
# Deploy SSOT function
cd /home/evo/evo_01/01_evolution
just deploy-ssot

# Deploy Assets function
just deploy-assets

# Deploy KYC function
just deploy-kyc
```

---

## Step 3: Deploy Cloud Run Proxy

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

---

## Step 4: Verify Deployment

After deployment completes, test the handshake page:

1. Visit: `https://02website-pearl.vercel.app/handshake`
2. Click each endpoint button
3. All 7 should show **OK** with green status

---

## Alternative: Use gcloud auth activate-service-account

If you have a service account key file, you can use:

```bash
gcloud auth activate-service-account --key-file=PATH_TO_KEY_FILE.json
```

But the `website-api-key.json` file appears to be empty, so you'll need to use `gcloud auth login`.
