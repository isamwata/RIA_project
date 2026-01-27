"""
Google Drive API Service for RIA Project

This service provides integration with Google Drive API for:
- Listing files in Drive folders
- Extracting text from PDFs (no local download)
- Processing PDFs directly from Drive to text
- Getting file metadata

Usage:
    from backend.drive_service import DriveService
    
    service = DriveService(api_key=os.getenv("GOOGLE_API_KEY"))
    files = service.list_pdf_files(folder_id="1kDuE7YBK1WWFCbQpq3N1XBp3jJ7Nug_L")
    
    # Extract text from PDFs without downloading
    for file in files:
        text = service.extract_text_from_pdf(file["id"])
        print(f"Extracted {len(text)} characters from {file['name']}")
"""

import os
from typing import List, Dict, Optional, Any
from pathlib import Path
import io

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    import pickle
    DRIVE_API_AVAILABLE = True
except ImportError:
    DRIVE_API_AVAILABLE = False
    print("Warning: google-api-python-client not installed. Install with: pip install google-api-python-client")
    print("For OAuth support, also install: pip install google-auth-oauthlib")

# Try to import PDF extraction services
try:
    from .document_ai_service import DocumentAIService
    DOCUMENT_AI_AVAILABLE = True
except ImportError:
    DOCUMENT_AI_AVAILABLE = False

try:
    from .pdf_extractor import PDFExtractor
    PDF_EXTRACTOR_AVAILABLE = True
except ImportError:
    PDF_EXTRACTOR_AVAILABLE = False


class DriveService:
    """
    Service for interacting with Google Drive API.
    
    Provides:
    - List files in folders
    - Extract text from PDFs (no local download)
    - Get file metadata
    - Filter by file type
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        use_document_ai: bool = True,
        document_ai_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Drive service.
        
        Args:
            api_key: Google API key (for public files only, can also be set via GOOGLE_API_KEY env var)
            credentials_path: Path to OAuth2 credentials JSON file (for private folders)
            token_path: Path to store OAuth2 token (default: token.pickle)
            use_document_ai: Whether to use Document AI for text extraction (default: True)
            document_ai_config: Optional Document AI configuration dict
        """
        if not DRIVE_API_AVAILABLE:
            raise RuntimeError(
                "google-api-python-client not installed. "
                "Install with: pip install google-api-python-client"
            )
        
        # Try OAuth first (for private folders), fallback to API key (for public files)
        self.credentials = None
        self.api_key = None
        
        if credentials_path and os.path.exists(credentials_path):
            # Use OAuth2 for private folders
            self.credentials = self._get_oauth_credentials(credentials_path, token_path)
            self.service = build('drive', 'v3', credentials=self.credentials)
            print("✅ Using OAuth2 authentication (for private folders)")
        else:
            # Use API key for public files
            self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                if credentials_path:
                    raise FileNotFoundError(
                        f"OAuth credentials file not found: {credentials_path}\n"
                        "Download from: https://console.cloud.google.com/apis/credentials\n"
                        "Or use API key for public folders by setting GOOGLE_API_KEY"
                    )
                raise ValueError(
                    "Either Google API key (for public files) or OAuth credentials (for private folders) required. "
                    "Set GOOGLE_API_KEY environment variable or pass credentials_path parameter."
                )
            self.service = build('drive', 'v3', developerKey=self.api_key)
            print("✅ Using API key authentication (for public files)")
        
        # Initialize PDF extraction service
        self.use_document_ai = use_document_ai and DOCUMENT_AI_AVAILABLE
        self.document_ai_service = None
        
        if self.use_document_ai:
            if document_ai_config:
                try:
                    self.document_ai_service = DocumentAIService(**document_ai_config)
                    print("✅ Using Document AI for PDF text extraction")
                except Exception as e:
                    print(f"⚠️  Document AI initialization failed: {e}")
                    print("   Falling back to basic PDF extraction")
                    self.use_document_ai = False
            else:
                # Try to create from environment
                try:
                    from .document_ai_service import create_service_from_env
                    self.document_ai_service = create_service_from_env()
                    print("✅ Using Document AI for PDF text extraction (from environment)")
                except Exception as e:
                    print(f"⚠️  Document AI not available from environment: {e}")
                    print("   Falling back to basic PDF extraction")
                    self.use_document_ai = False
        
        if not self.use_document_ai and PDF_EXTRACTOR_AVAILABLE:
            self.pdf_extractor = PDFExtractor()
            print("✅ Using PDFExtractor for text extraction")
        elif not self.use_document_ai:
            print("⚠️  No PDF extraction service available - will only get metadata")
        
        print("✅ Google Drive API service initialized")
    
    def _get_oauth_credentials(
        self,
        credentials_path: str,
        token_path: Optional[str] = None
    ) -> Credentials:
        """
        Get OAuth2 credentials for accessing private Drive folders.
        
        Args:
            credentials_path: Path to OAuth2 client credentials JSON file
            token_path: Path to store/load OAuth2 token (default: token.pickle)
        
        Returns:
            OAuth2 credentials
        """
        if token_path is None:
            token_path = "token.pickle"
        
        SCOPES = ['https://www.googleapis.com/auth/drive']  # Full access (read + write)
        creds = None
        
        # Load existing token
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        f"OAuth credentials file not found: {credentials_path}\n"
                        "Download from: https://console.cloud.google.com/apis/credentials"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token for next time
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def list_files_in_folder(
        self,
        folder_id: str,
        file_types: Optional[List[str]] = None,
        include_subfolders: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            file_types: Optional list of MIME types to filter (e.g., ['application/pdf'])
            include_subfolders: Whether to include files in subfolders
        
        Returns:
            List of file metadata dictionaries with keys: id, name, mimeType, etc.
        """
        try:
            files = []
            page_token = None
            
            # Build query
            query = f"'{folder_id}' in parents and trashed=false"
            
            # Filter by file type if specified
            if file_types:
                mime_type_filters = " or ".join([f"mimeType='{mime}'" for mime in file_types])
                query += f" and ({mime_type_filters})"
            
            while True:
                # List files (support Shared Drives)
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size)",
                    pageToken=page_token,
                    pageSize=100,
                    supportsAllDrives=True,  # Required for Shared Drives
                    includeItemsFromAllDrives=True  # Required for Shared Drives
                ).execute()
                
                items = results.get('files', [])
                files.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            print(f"✅ Found {len(files)} files in folder {folder_id}")
            return files
            
        except HttpError as error:
            print(f"❌ Error listing files: {error}")
            raise
    
    def search_files(
        self,
        query: str,
        folder_id: Optional[str] = None,
        file_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for files in Drive by name or content.
        
        Args:
            query: Search query (searches in file names and content)
            folder_id: Optional folder ID to limit search
            file_types: Optional list of MIME types to filter
        
        Returns:
            List of matching file metadata
        """
        try:
            files = []
            page_token = None
            
            # Build query
            search_query = f"name contains '{query}' or fullText contains '{query}'"
            
            # Limit to folder if specified
            if folder_id:
                search_query += f" and '{folder_id}' in parents"
            
            # Filter by file type if specified
            if file_types:
                mime_type_filters = " or ".join([f"mimeType='{mime}'" for mime in file_types])
                search_query += f" and ({mime_type_filters})"
            
            # Add trashed filter
            search_query += " and trashed=false"
            
            while True:
                results = self.service.files().list(
                    q=search_query,
                    fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size)",
                    pageToken=page_token,
                    pageSize=100,
                    supportsAllDrives=True,  # Required for Shared Drives
                    includeItemsFromAllDrives=True  # Required for Shared Drives
                ).execute()
                
                items = results.get('files', [])
                files.extend(items)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            print(f"✅ Found {len(files)} files matching '{query}'")
            return files
            
        except HttpError as error:
            print(f"❌ Error searching files: {error}")
            raise
    
    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Get metadata for a file.
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            File metadata dictionary
        """
        try:
            metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime, size, parents",
                supportsAllDrives=True  # Required for Shared Drives
            ).execute()
            return metadata
        except HttpError as error:
            print(f"❌ Error getting file metadata: {error}")
            raise
    
    def list_pdf_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Convenience method to list only PDF files in a folder.
        
        Args:
            folder_id: Google Drive folder ID
        
        Returns:
            List of PDF file metadata
        """
        return self.list_files_in_folder(
            folder_id,
            file_types=['application/pdf']
        )
    
    def extract_text_from_pdf(self, file_id: str) -> str:
        """
        Extract text from a PDF file in Google Drive (no local download).
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            Extracted text as string
        """
        try:
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                supportsAllDrives=True  # Required for Shared Drives
            ).execute()
            file_name = file_metadata.get('name', 'unknown')
            mime_type = file_metadata.get('mimeType', '')
            
            print(f"📄 Extracting text from: {file_name}")
            
            # Download file content to memory (not to disk)
            if 'google-apps' in mime_type:
                # Export Google Docs/Sheets as PDF first
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/pdf'
                )
            else:
                # Download regular PDF files
                request = self.service.files().get_media(fileId=file_id)
            
            # Download to memory buffer
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            pdf_bytes = file_content.getvalue()
            
            # Extract text using available service
            # Note: Both Document AI and PDFExtractor need a file path, so we use temp file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_path = tmp_file.name
            
            try:
                if self.use_document_ai and self.document_ai_service:
                    # Use Document AI for high-quality extraction
                    result = self.document_ai_service.process_document(tmp_path)
                    text = result.get("text", "")
                elif PDF_EXTRACTOR_AVAILABLE:
                    # Use PDFExtractor
                    text = self.pdf_extractor.extract_text(tmp_path)
                else:
                    raise RuntimeError(
                        "No PDF extraction service available. "
                        "Install google-cloud-documentai or ensure PDFExtractor is available."
                    )
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
            
            print(f"✅ Extracted {len(text)} characters from {file_name}")
            return text
            
        except HttpError as error:
            print(f"❌ Error extracting text from file {file_id}: {error}")
            raise
        except Exception as e:
            print(f"❌ Error during text extraction: {e}")
            raise
    
    def process_folder_pdfs_to_text(
        self,
        folder_id: str,
        max_files: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Process all PDFs in a folder and extract text.
        
        Args:
            folder_id: Google Drive folder ID
            max_files: Optional limit on number of files to process
        
        Returns:
            List of dicts with keys: file_id, name, text, metadata
        """
        pdf_files = self.list_pdf_files(folder_id)
        
        if max_files:
            pdf_files = pdf_files[:max_files]
        
        results = []
        for i, file_info in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Processing: {file_info['name']}")
            try:
                text = self.extract_text_from_pdf(file_info['id'])
                results.append({
                    'file_id': file_info['id'],
                    'name': file_info['name'],
                    'text': text,
                    'metadata': file_info,
                    'text_length': len(text)
                })
            except Exception as e:
                print(f"❌ Failed to process {file_info['name']}: {e}")
                results.append({
                    'file_id': file_info['id'],
                    'name': file_info['name'],
                    'text': '',
                    'error': str(e),
                    'metadata': file_info
                })
        
        print(f"\n✅ Processed {len(results)} PDFs")
        return results
    
    def upload_text_file(
        self,
        text_content: str,
        file_name: str,
        folder_id: str,
        mime_type: str = "text/plain"
    ) -> Dict[str, Any]:
        """
        Upload a text file to Google Drive.
        
        Args:
            text_content: Text content to upload
            file_name: Name for the file (e.g., "document.txt")
            folder_id: Google Drive folder ID to upload to
            mime_type: MIME type (default: text/plain)
        
        Returns:
            File metadata dictionary
        """
        try:
            from googleapiclient.http import MediaIoBaseUpload
            
            # Create file metadata
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            # Create media upload
            file_content = io.BytesIO(text_content.encode('utf-8'))
            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, parents',
                supportsAllDrives=True  # Required for Shared Drives
            ).execute()
            
            print(f"✅ Uploaded {file_name} to Drive (ID: {file.get('id')})")
            return file
            
        except HttpError as error:
            print(f"❌ Error uploading file {file_name}: {error}")
            raise