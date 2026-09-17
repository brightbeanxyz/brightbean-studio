# BrightBean Asset Ingestion - Run Locally on Your Mac

## Prerequisites

You need the R2 credentials from the API token you just created in Cloudflare:

```bash
# From Cloudflare Dashboard → R2 → Manage R2 API tokens → your token
export S3_ENDPOINT_URL="https://<YOUR_ACCOUNT_ID>.r2.cloudflarestorage.com"
export S3_ACCESS_KEY_ID="<YOUR_ACCESS_KEY_ID>"
export S3_SECRET_ACCESS_KEY="<YOUR_SECRET_ACCESS_KEY>"
export S3_BUCKET_NAME="brightbean-assets"
export S3_REGION_NAME="auto"
```

Find your **Account ID** at: https://dash.cloudflare.com/ (top right, copy the 32-char ID)

---

## Run the Ingestion

```bash
cd /Users/mfdoom/conductor/workspaces/brightbean-studio/brazzaville

# 1. Install boto3 (one-time)
pip3 install boto3

# 2. Preview what will be uploaded (dry run)
python3 scripts/ingest_assets_standalone.py --dry-run

# 3. Actual upload to R2
python3 scripts/ingest_assets_standalone.py
```

---

## What Happens

1. **Scans 4 source directories** (from `.context/brightbean-social-readiness.md`)
2. **Deduplicates by SHA-256** (skips identical files)
3. **Uploads to R2** at `assets/<project>/<sha256-prefix>/<filename>`
4. **Creates `asset_manifest.json`** with all metadata for later MediaAsset creation

---

## After Upload: Create MediaAsset Records

The upload puts files in R2. To make them usable in BrightBean:

### Option A: BrightBean API (once social accounts connected)
```bash
# Get API key from BrightBean UI → Organization → API Keys
export BB_API_KEY="bb_studio_..."
export BB_URL="https://brightbean-pnc.fly.dev"

# Use the manifest to create records
python3 -c "
import json, requests
manifest = json.load(open('asset_manifest.json'))
for asset in manifest:
    r = requests.post(f'{BB_URL}/api/v1/media', headers={'Authorization': f'Bearer {BB_API_KEY}'}, json={
        'title': asset['title'],
        'file': asset['r2_key'],
        'sha256': asset['sha256'],
        'file_size': asset['file_size'],
        'mime_type': asset['mime_type'],
        'project': asset['project'],
        'tags': [asset['project']],
        'alt_text': asset['title'],
    })
    print(asset['filename'], r.status_code)
"
```

### Option B: Django Admin (immediate)
1. Go to https://brightbean-pnc.fly.dev/admin/
2. Login with superuser
3. Media Library → Media Assets → Add
4. Fill in from `asset_manifest.json`

### Option C: BrightBean UI
1. Go to Media Library in BrightBean
2. Click "Add" → the files are already in R2, just need records

---

## Expected Results

| Category | Files |
|----------|-------|
| Social-ready set | 26 PNGs |
| Content pool | ~152 unique (deduped from 259) |
| Originals (PAC) | 2 PNGs |
| Reels | 2 MP4s |
| **Total unique** | **~182 assets** |

---

## Troubleshooting

**"Source directory not found"** — The paths in `SOURCE_DIRS` are from your `.context/brightbean-social-readiness.md`. If files moved, update the script.

**"Missing R2 credentials"** — Re-export the 5 environment variables above.

**"Access Denied"** — R2 token needs "Object Read & Write" permissions on the bucket.

**"Bucket not found"** — Create bucket `brightbean-assets` in R2 first, or update `S3_BUCKET_NAME`.