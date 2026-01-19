# Document AI Configuration Status

## ✅ Completed Steps

1. **Document AI API**: ✅ Enabled
2. **Service Account**: ✅ Created (`ria-document-ai-service`)
3. **IAM Role**: ✅ Granted (`Document AI API User`)
4. **Credentials**: ✅ Downloaded to `credentials/document-ai-key.json`
5. **Project**: ✅ Set to `pocdocaiuhasselt`

## ⏳ Next Step Required

### Create Document AI Processor

You need to create a processor in Google Cloud Console:

1. **Go to**: https://console.cloud.google.com/ai/document-ai/processors?project=pocdocaiuhasselt

2. **Click**: "Create Processor"

3. **Select**: "OCR Processor" (General Document OCR)

4. **Location**: `us` (or `eu` if you prefer)

5. **Name**: `ria-ocr-processor` (or any name you prefer)

6. **Click**: "Create"

7. **Copy the Processor ID** (it will look like: `1234567890abcdef`)

8. **Update `.env` file** with the processor ID:
   ```bash
   DOCUMENT_AI_PROCESSOR_ID=your-actual-processor-id-here
   ```

## 📝 Environment Configuration

Create a `.env` file in the project root with:

```bash
# Google Cloud Document AI Configuration
GCP_PROJECT_ID=pocdocaiuhasselt
GCP_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=<paste-your-processor-id-here>
GCP_CREDENTIALS_PATH=./credentials/document-ai-key.json

# Feature flags
USE_DOCUMENT_AI=true
DOCUMENT_AI_FALLBACK=true
```

## 🧪 Test Configuration

After adding the processor ID to `.env`, test with:

```bash
python test_document_ai.py
```

Or process a PDF:

```bash
python process_pdf_with_document_ai.py 140110.0-2014A03330.002FR.pdf
```

## 📦 Install Required Library

If not already installed:

```bash
pip install google-cloud-documentai
```

Or with `uv`:

```bash
uv pip install google-cloud-documentai
```

## 🔍 Verify Setup

Check that credentials file exists:
```bash
ls -la credentials/document-ai-key.json
```

Check service account:
```bash
gcloud iam service-accounts describe ria-document-ai-service@pocdocaiuhasselt.iam.gserviceaccount.com --project=pocdocaiuhasselt
```
