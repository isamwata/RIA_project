# Document AI Setup Guide for RIA Project

This guide walks you through adding Google Cloud Document AI to your existing Google Cloud project.

## Prerequisites

- ✅ Google Cloud account (you already have this)
- ✅ Google Cloud project with billing enabled
- ✅ Google Cloud Storage already set up

## Step 1: Enable Document AI API

### Option A: Using Google Cloud Console (Web UI)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project from the project dropdown
3. Navigate to **APIs & Services** > **Library**
4. Search for "**Document AI API**"
5. Click on "**Document AI API**"
6. Click **Enable**

### Option B: Using gcloud CLI

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Enable Document AI API
gcloud services enable documentai.googleapis.com --project=$PROJECT_ID
```

## Step 2: Create a Document AI Processor

You need to create a processor to use Document AI. For RIA documents, start with the **OCR Processor**.

### Option A: Using Google Cloud Console

1. Go to [Document AI Console](https://console.cloud.google.com/ai/document-ai/processors)
2. Click **Create Processor**
3. Select **OCR Processor** (General Document OCR)
4. Choose a location:
   - **us** (United States) - Recommended for most users
   - **eu** (Europe) - If you need EU data residency
5. Enter a processor name: `ria-ocr-processor` (or your preferred name)
6. Click **Create**

**Note the Processor ID** - you'll need this later (it looks like: `1234567890abcdef`)

### Option B: Using gcloud CLI

```bash
# Create OCR processor
gcloud documentai processors create \
  --location=us \
  --display-name="RIA OCR Processor" \
  --type=OCR_PROCESSOR \
  --project=$PROJECT_ID
```

This will output the processor ID. Save it!

## Step 3: Create Service Account for Authentication

Document AI needs a service account to authenticate API calls.

### Option A: Using Google Cloud Console

1. Go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Enter details:
   - **Name**: `ria-document-ai-service`
   - **Description**: `Service account for RIA Document AI processing`
4. Click **Create and Continue**
5. Grant role: **Document AI API User** (or `roles/documentai.apiUser`)
6. Click **Continue** > **Done**

### Option B: Using gcloud CLI

```bash
# Create service account
gcloud iam service-accounts create ria-document-ai-service \
  --display-name="RIA Document AI Service" \
  --project=$PROJECT_ID

# Grant Document AI API User role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ria-document-ai-service@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/documentai.apiUser"
```

## Step 4: Create and Download Service Account Key

You need to download a JSON key file for authentication.

### Option A: Using Google Cloud Console

1. Go to **IAM & Admin** > **Service Accounts**
2. Click on your service account (`ria-document-ai-service`)
3. Go to **Keys** tab
4. Click **Add Key** > **Create New Key**
5. Select **JSON** format
6. Click **Create**
7. The JSON file will download automatically - **save it securely!**

### Option B: Using gcloud CLI

```bash
# Create and download key
gcloud iam service-accounts keys create ./credentials/document-ai-key.json \
  --iam-account=ria-document-ai-service@${PROJECT_ID}.iam.gserviceaccount.com \
  --project=$PROJECT_ID
```

**Important**: 
- Store this file securely (don't commit to git!)
- Add it to `.gitignore`
- This key gives access to your Document AI resources

## Step 5: Configure Your RIA Project

### 5.1: Install Required Library

```bash
# In your project directory
pip install google-cloud-documentai
```

Or if using `uv`:
```bash
uv pip install google-cloud-documentai
```

### 5.2: Set Environment Variables

Add to your `.env` file:

```bash
# Google Cloud Document AI Configuration
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=your-processor-id-here
GCP_CREDENTIALS_PATH=./credentials/document-ai-key.json

# Feature flags
USE_DOCUMENT_AI=true
DOCUMENT_AI_FALLBACK=true
```

**Replace**:
- `your-project-id`: Your Google Cloud project ID
- `your-processor-id-here`: The processor ID from Step 2
- `./credentials/document-ai-key.json`: Path to your service account key

### 5.3: Create Credentials Directory

```bash
# Create credentials directory (if it doesn't exist)
mkdir -p credentials

# Move your downloaded key file there
# (or if using gcloud CLI, it's already there)

# Make sure it's in .gitignore
echo "credentials/" >> .gitignore
echo "*.json" >> .gitignore  # If you want to ignore all JSON files
```

### 5.4: Update .gitignore

Make sure your `.gitignore` includes:

```gitignore
# Credentials
credentials/
*.json
!package.json  # Keep package.json if needed
!package-lock.json

# Google Cloud
.env
```

## Step 6: Test the Setup

Create a test script to verify everything works:

```python
# test_document_ai.py
import os
from pathlib import Path
from backend.document_ai_service import DocumentAIService

# Load from environment
project_id = os.getenv("GCP_PROJECT_ID")
location = os.getenv("GCP_LOCATION", "us")
processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
credentials_path = os.getenv("GCP_CREDENTIALS_PATH")

if not all([project_id, processor_id, credentials_path]):
    print("❌ Missing environment variables!")
    print("Set: GCP_PROJECT_ID, DOCUMENT_AI_PROCESSOR_ID, GCP_CREDENTIALS_PATH")
    exit(1)

# Initialize service
try:
    service = DocumentAIService(
        project_id=project_id,
        location=location,
        processor_id=processor_id,
        credentials_path=credentials_path
    )
    print("✅ Document AI service initialized successfully!")
    
    # Test with a sample PDF (if you have one)
    test_pdf = Path("EU Impact Assessments_SWD(2022)167_main_2_EN.pdf")
    if test_pdf.exists():
        print(f"\n📄 Testing with: {test_pdf}")
        result = service.process_document(str(test_pdf))
        print(f"✅ Extraction successful!")
        print(f"   - Text length: {len(result['text'])} characters")
        print(f"   - Pages: {result['metadata']['page_count']}")
        print(f"   - Tables found: {len(result['tables'])}")
    else:
        print("\n⚠️  No test PDF found. Service is ready to use!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check that Document AI API is enabled")
    print("2. Verify processor ID is correct")
    print("3. Ensure credentials file path is correct")
    print("4. Check service account has Document AI API User role")
```

Run the test:

```bash
# Load environment variables
source .env  # or use python-dotenv

# Run test
python test_document_ai.py
```

## Step 7: Verify Billing and Quotas

### Check Billing

Document AI requires billing to be enabled:

1. Go to **Billing** in Google Cloud Console
2. Ensure your project has a billing account linked
3. Check that billing is enabled

### Check Quotas

1. Go to **APIs & Services** > **Quotas**
2. Search for "Document AI"
3. Verify your quotas are sufficient:
   - **OCR Processor**: Usually 1,000 pages/day free tier, then $1.50 per 1,000 pages
   - **Form Parser**: Similar pricing

### Free Tier

Google Cloud Document AI offers:
- **First 1,000 pages/month free** (OCR Processor)
- After that: ~$1.50 per 1,000 pages

## Quick Reference: All Required Values

After setup, you should have:

1. **Project ID**: Found in Google Cloud Console (top bar)
2. **Processor ID**: Found in Document AI Console (processor details page)
3. **Location**: Usually `us` or `eu`
4. **Credentials Path**: Path to your downloaded service account JSON key

## Troubleshooting

### Error: "API not enabled"
- **Solution**: Enable Document AI API (Step 1)

### Error: "Permission denied"
- **Solution**: Ensure service account has `Document AI API User` role

### Error: "Processor not found"
- **Solution**: Verify processor ID is correct and in the right location

### Error: "Invalid credentials"
- **Solution**: Check credentials file path and ensure JSON is valid

### Error: "Billing not enabled"
- **Solution**: Link a billing account to your project

## Next Steps

Once setup is complete:

1. ✅ Test with a sample RIA document
2. ✅ Integrate with your PDF extractor (see `backend/pdf_extractor.py`)
3. ✅ Consider training a custom processor for RIA-specific documents (advanced)

## Cost Optimization Tips

1. **Use Document AI for complex documents only**
   - Simple text PDFs → Use PyMuPDF (free)
   - Complex/scanned PDFs → Use Document AI

2. **Batch processing**
   - Process multiple documents in one batch
   - More efficient than individual requests

3. **Cache results**
   - Don't reprocess the same document
   - Store extracted text in your database

4. **Monitor usage**
   - Set up billing alerts
   - Track usage in Cloud Console

## Security Best Practices

1. **Never commit credentials to git**
   - Use `.gitignore`
   - Use environment variables
   - Consider using Google Cloud Secret Manager for production

2. **Limit service account permissions**
   - Only grant `Document AI API User` role
   - Don't use overly permissive roles

3. **Rotate keys regularly**
   - Create new keys periodically
   - Revoke old keys

4. **Use different keys for different environments**
   - Development vs. Production
   - Different service accounts

## Additional Resources

- [Document AI Documentation](https://cloud.google.com/document-ai/docs)
- [Document AI Pricing](https://cloud.google.com/document-ai/pricing)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [API Quotas and Limits](https://cloud.google.com/document-ai/quotas)
