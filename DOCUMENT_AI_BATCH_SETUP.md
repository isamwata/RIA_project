# Document AI Batch Processing Setup

For large documents (>30 pages), Document AI requires batch processing which uses Google Cloud Storage.

## Quick Setup

### 1. Create GCS Bucket (if you don't have one)

```bash
# Using gcloud CLI
gsutil mb -p pocdocaiuhasselt -l us gs://pocdocaiuhasselt-document-ai-temp

# Or in Console:
# Go to: https://console.cloud.google.com/storage
# Click "Create Bucket"
# Name: pocdocaiuhasselt-document-ai-temp (or your preferred name)
# Location: us (same as Document AI processor)
```

### 2. Grant Service Account Access

```bash
# Grant storage access to Document AI service account
gsutil iam ch serviceAccount:ria-document-ai-service@pocdocaiuhasselt.iam.gserviceaccount.com:roles/storage.objectAdmin gs://pocdocaiuhasselt-document-ai-temp
```

### 3. Add to .env File

```bash
GCS_BUCKET_NAME=pocdocaiuhasselt-document-ai-temp
```

### 4. Install Google Cloud Storage Library

```bash
pip install google-cloud-storage
```

## How It Works

- **Documents ≤ 30 pages**: Processed directly (synchronous)
- **Documents > 30 pages**: Automatically use batch processing via GCS
  - Uploads PDF to GCS
  - Processes via batch API (supports up to 200 pages)
  - Downloads results
  - Cleans up temporary files

## Batch Processing Limits

- **OCR Processor**: Up to 200 pages in batch mode
- **Layout Parser**: Up to 500 pages in batch mode
- **File size**: Up to 1 GB in batch mode

## Cost

- GCS storage: Minimal (temporary files, cleaned up after processing)
- Document AI: Same pricing (~$1.50 per 1,000 pages)
