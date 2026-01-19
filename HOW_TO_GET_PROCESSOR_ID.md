# How to Get Document AI Processor ID

## Step-by-Step Guide

### 1. Go to Document AI Processors Page

**Direct Link**: https://console.cloud.google.com/ai/document-ai/processors?project=pocdocaiuhasselt

Or navigate manually:
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Select project: **pocdocaiuhasselt**
- In the left menu, go to: **AI & Machine Learning** > **Document AI** > **Processors**

### 2. Create a Processor (if you haven't already)

1. Click **"Create Processor"** button (top of the page)
2. Select **"OCR Processor"** (General Document OCR)
3. Choose **Location**: `us` (or `eu`)
4. Enter **Display Name**: `ria-ocr-processor` (or any name)
5. Click **"Create"**

### 3. Find the Processor ID

After creating the processor, you'll see the processor in the list. The Processor ID is shown in **two places**:

#### Option A: From the Processors List

1. Look at the processor list table
2. Find your processor (`ria-ocr-processor`)
3. The **Processor ID** is in the **"ID"** column
   - It looks like: `1234567890abcdef` or `a1b2c3d4e5f6g7h8`

#### Option B: From the Processor Details Page

1. Click on your processor name to open details
2. The Processor ID is displayed at the top of the page
3. It's labeled as **"Processor ID"** or shown in the URL

#### Option C: From the URL

When you click on a processor, the URL will look like:
```
https://console.cloud.google.com/ai/document-ai/processors/1234567890abcdef?project=pocdocaiuhasselt
```

The Processor ID is the long string in the URL: `1234567890abcdef`

### 4. Copy the Processor ID

- Click on the Processor ID to select it
- Copy it (Cmd+C on Mac, Ctrl+C on Windows)
- It should be a long alphanumeric string (usually 16+ characters)

### 5. Add to .env File

Add the Processor ID to your `.env` file:

```bash
DOCUMENT_AI_PROCESSOR_ID=1234567890abcdef
```

Replace `1234567890abcdef` with your actual processor ID.

## Visual Guide

```
┌─────────────────────────────────────────────────────────┐
│  Document AI > Processors                               │
├─────────────────────────────────────────────────────────┤
│  [Create Processor]                                      │
│                                                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Display Name      │ Type      │ ID                 │ │
│  ├───────────────────────────────────────────────────┤ │
│  │ ria-ocr-processor │ OCR       │ 1234567890abcdef  │ │ ← Copy this ID
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Alternative: Using gcloud CLI

If you prefer using the command line, you can list processors (though the gcloud CLI doesn't have direct Document AI commands, you can use the REST API):

```bash
# This requires the processor to be created first via Console
# Then you can find it in the Console
```

**Note**: Document AI processors are typically created and managed via the Console UI, not gcloud CLI.

## Troubleshooting

### "I don't see any processors"
- Make sure you've created a processor first
- Check that you're in the correct project (`pocdocaiuhasselt`)
- Verify you're looking at the correct location (`us` or `eu`)

### "I can't find the Processor ID"
- Click on the processor name to open the details page
- The Processor ID is always shown in the processor details
- Check the URL - the ID is in the path

### "The Processor ID looks wrong"
- Processor IDs are long alphanumeric strings (16+ characters)
- They don't have spaces or special characters
- They're case-sensitive, so copy exactly as shown

## Quick Reference

1. **Console URL**: https://console.cloud.google.com/ai/document-ai/processors?project=pocdocaiuhasselt
2. **Look for**: The "ID" column in the processors table
3. **Or**: Click processor → See ID in details page or URL
4. **Copy**: The long alphanumeric string
5. **Paste**: Into `.env` file as `DOCUMENT_AI_PROCESSOR_ID=...`
