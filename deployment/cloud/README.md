
Cloudflare R2 upload
`upload_to_r2.py` uploads the latest batch (raw input, curated Parquet, all JSON reports) to an R2 bucket
under `raw/<batch_id>/`, `curated/<batch_id>/` and `reports/<batch_id>/`. Each object carries its SHA-256 as
metadata and is verified after upload.
One-time setup
Cloudflare dashboard > R2 > create a bucket.
R2 > Manage API tokens > create a token with Object Read & Write on that bucket.
Set the variables (never commit them):
$env:R2_ACCOUNT_ID="..."; $env:R2_ACCESS_KEY_ID="..."; $env:R2_SECRET_ACCESS_KEY="..."; $env:R2_BUCKET="..."

Run
    pip install -r deployment/cloud/requirements-cloud.txt
    python run_pipeline.py
    python deployment/cloud/upload_to_r2.py            # without the variables it only lists what it would upload
    python deployment/cloud/upload_to_r2.py --dry-run