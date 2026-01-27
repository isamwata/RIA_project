# Vector Store Setup Guide

## Overview

The vector store contains embeddings and indexes for semantic search. It's **NOT committed to git** due to size (~32MB).

## Current Location

```
/Users/isaiah/Documents/RIA-Project/vector_store/
```

**Files:**
- `dense_vectors.npy` (20MB) - Embedding vectors
- `entries.json` (10MB) - Chunk content and metadata
- `bm25_index.pkl` (2.5MB) - BM25 search index
- `metadata.json` (171B) - Store metadata

## Options for Git Deployment

### Option 1: Cloud Storage (Recommended for Production)

**AWS S3:**
```python
# Add to backend/vector_store.py
import boto3

def load_from_s3(bucket_name: str, prefix: str = "vector_store/"):
    s3 = boto3.client('s3')
    # Download files from S3
    # Load into VectorStore
```

**Google Cloud Storage:**
```python
from google.cloud import storage

def load_from_gcs(bucket_name: str, prefix: str = "vector_store/"):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    # Download and load
```

**Azure Blob Storage:**
```python
from azure.storage.blob import BlobServiceClient

def load_from_azure(container_name: str, prefix: str = "vector_store/"):
    # Download and load
```

### Option 2: Build Scripts (Recommended for Development)

**Rebuild from source documents:**

1. **Scripts available:**
   - `build_vector_store.py` - Main build script
   - `process_all_eu_txt.py` - Process EU documents
   - `process_all_ria_txt.py` - Process RIA documents
   - `process_drive_txt_to_vector_store.py` - Process Google Drive files

2. **Setup instructions:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Build vector store from source documents
   python build_vector_store.py
   ```

3. **Add to README.md:**
   ```markdown
   ## Setup Vector Store
   
   After cloning, rebuild the vector store:
   ```bash
   python build_vector_store.py
   ```
   ```

### Option 3: Git LFS (If Version Control Needed)

**If you need version control for vectors:**

```bash
# Install Git LFS
git lfs install

# Track vector store files
git lfs track "vector_store/*.npy"
git lfs track "vector_store/*.pkl"
git lfs track "vector_store/entries.json"

# Add to git
git add .gitattributes
git add vector_store/
```

**Note:** Git LFS requires a hosting service that supports it (GitHub, GitLab, etc.)

### Option 4: Docker Volume (For Containerized Deployments)

**docker-compose.yml:**
```yaml
services:
  backend:
    volumes:
      - vector_store_data:/app/vector_store
      
volumes:
  vector_store_data:
    driver: local
```

**Initialize on first run:**
```bash
docker-compose run backend python build_vector_store.py
```

## Recommended Approach

**For Development:**
- Use build scripts (Option 2)
- Document source document locations
- Add setup instructions to README

**For Production:**
- Use cloud storage (Option 1)
- Download on container startup or mount as volume
- Cache locally after first download

**For Team Collaboration:**
- Use cloud storage with shared bucket
- Or Git LFS if version control is needed
- Document access credentials securely

## Environment Variable Configuration

Add to `.env`:
```bash
# Vector Store Configuration
VECTOR_STORE_PATH=vector_store
VECTOR_STORE_SOURCE=s3://your-bucket/vector_store  # Optional: cloud source
VECTOR_STORE_REBUILD=false  # Set to true to rebuild from source
```

## Migration Checklist

- [ ] Add `vector_store/` to `.gitignore`
- [ ] Document source document locations
- [ ] Create build script documentation
- [ ] Set up cloud storage (if using)
- [ ] Update deployment scripts
- [ ] Test rebuild process
- [ ] Update README with setup instructions
