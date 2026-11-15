
# Cloudflare R2 Upload

`upload_to_r2.py` uploads the latest batch (raw input, curated Parquet, and all JSON reports) to an R2 bucket under:

- `raw/<batch_id>/`
- `curated/<batch_id>/`
- `reports/<batch_id>/`

Each object carries its SHA-256 hash as metadata and is verified after upload.

## One-Time Setup

1. Go to **Cloudflare Dashboard → R2** and create a bucket.
2. Navigate to **R2 → Manage API Tokens**.
3. Create an API token with **Object Read & Write** permissions for that bucket.
4. Set the following environment variables. Never commit these credentials to GitHub.

**PowerShell (Windows):**

```powershell
$env:R2_ACCOUNT_ID="..."
$env:R2_ACCESS_KEY_ID="..."
$env:R2_SECRET_ACCESS_KEY="..."
$env:R2_BUCKET="..."
```

## Run

Install the required dependencies:

```bash
pip install -r deployment/cloud/requirements-cloud.txt
```

Run the data pipeline:

```bash
python run_pipeline.py
```

Upload the latest batch to Cloudflare R2:

```bash
python deployment/cloud/upload_to_r2.py
```

Run in dry-run mode:

```bash
python deployment/cloud/upload_to_r2.py --dry-run
```

**Note:** Without the required environment variables, the upload script only lists the files it would upload.
