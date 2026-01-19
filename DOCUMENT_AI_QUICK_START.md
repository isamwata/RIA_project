# Document AI Quick Start

Since you already have Google Cloud Storage set up, here's the fastest way to add Document AI:

## 5-Minute Setup

### 1. Enable Document AI API

**In Google Cloud Console:**
- Go to: [APIs & Services > Library](https://console.cloud.google.com/apis/library)
- Search: "Document AI API"
- Click: **Enable**

**Or via CLI:**
```bash
gcloud services enable documentai.googleapis.com --project=YOUR_PROJECT_ID
```

### 2. Create OCR Processor

**In Google Cloud Console:**
- Go to: [Document AI > Processors](https://console.cloud.google.com/ai/document-ai/processors)
- Click: **Create Processor**
- Select: **OCR Processor**
- Location: **us** (or **eu** if needed)
- Name: `ria-ocr-processor`
- Click: **Create**
- **Copy the Processor ID** (you'll need it)

**Or via CLI:**
```bash
gcloud documentai processors create \
  --location=us \
  --display-name="RIA OCR Processor" \
  --type=OCR_PROCESSOR \
  --project=YOUR_PROJECT_ID
```

### 3. Create Service Account

**In Google Cloud Console:**
- Go to: [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
- Click: **Create Service Account**
- Name: `ria-document-ai-service`
- Grant role: **Document AI API User**
- Click: **Create Key** > **JSON**
- **Download the JSON file** → Save as `credentials/document-ai-key.json`

**Or via CLI:**
```bash
# Create service account
gcloud iam service-accounts create ria-document-ai-service \
  --display-name="RIA Document AI Service" \
  --project=YOUR_PROJECT_ID

# Grant role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:ria-document-ai-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/documentai.apiUser"

# Create key
gcloud iam service-accounts keys create ./credentials/document-ai-key.json \
  --iam-account=ria-document-ai-service@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 4. Install Library

```bash
pip install google-cloud-documentai
# or
uv pip install google-cloud-documentai
```

### 5. Configure Environment

Add to your `.env` file:

```bash
# Document AI Configuration
GCP_PROJECT_ID=your-actual-project-id
GCP_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=your-actual-processor-id
GCP_CREDENTIALS_PATH=./credentials/document-ai-key.json

# Feature flags
USE_DOCUMENT_AI=true
DOCUMENT_AI_FALLBACK=true
```

### 6. Test It

```bash
python test_document_ai.py
```

Or test with a specific PDF:
```bash
python test_document_ai.py "path/to/your/document.pdf"
```

## What You Need

After setup, you'll have:
- ✅ **Project ID**: Your Google Cloud project ID (you already have this)
- ✅ **Processor ID**: From step 2 (looks like: `1234567890abcdef`)
- ✅ **Credentials**: JSON file at `credentials/document-ai-key.json`
- ✅ **Location**: Usually `us` or `eu`

## Quick Test in Python

```python
from backend.pdf_extractor import extract_pdf

# Extract with Document AI (auto-falls back to PyMuPDF if needed)
result = extract_pdf("path/to/document.pdf")

print(result["text"])  # Full text
print(result["tables"])  # Extracted tables
print(result["entities"])  # Extracted entities
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| "API not enabled" | Enable Document AI API (Step 1) |
| "Permission denied" | Grant `Document AI API User` role to service account |
| "Processor not found" | Check processor ID and location match |
| "Billing not enabled" | Link billing account to project |

## Cost

- **First 1,000 pages/month**: FREE
- **After that**: ~$1.50 per 1,000 pages

## Next Steps

1. ✅ Test with a sample RIA document
2. ✅ Integrate into your workflow (see `backend/pdf_extractor.py`)
3. 📚 Read full guide: `DOCUMENT_AI_SETUP.md`

---

**Need help?** Check `DOCUMENT_AI_SETUP.md` for detailed instructions.
