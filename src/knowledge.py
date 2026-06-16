import io
import pdfplumber
import docx
from googleapiclient.http import MediaIoBaseDownload
from src.config import GOOGLE_DRIVE_FOLDER_ID

MAX_KNOWLEDGE_CHARS = 100000  # Roughly 25k-30k tokens, leaves plenty of room for 70b-versatile context window

def list_drive_files(service, folder_id):
    """List PDF and DOCX files in the specified Google Drive folder."""
    query = f"'{folder_id}' in parents and trashed = false and (mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')"
    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType)'
        ).execute()
        return results.get('files', [])
    except Exception as e:
        print(f"Error listing files from Drive folder {folder_id}: {e}")
        return []

def download_drive_file(service, file_id):
    """Download file content from Google Drive as bytes."""
    try:
        request = service.files().get_media(fileId=file_id)
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return file_io.getvalue()
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return None

def extract_text_from_pdf(file_bytes):
    """Extract plain text from a PDF, ignoring images."""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def extract_text_from_docx(file_bytes):
    """Extract plain text from a DOCX file."""
    text = ""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
    return text

def build_knowledge_context(service, folder_id=GOOGLE_DRIVE_FOLDER_ID):
    """
    Downloads and extracts text from all valid files in the folder.
    Concatenates them into a single string, truncating if necessary.
    """
    if not folder_id:
        print("Warning: GOOGLE_DRIVE_FOLDER_ID is not set.")
        return ""

    files = list_drive_files(service, folder_id)
    if not files:
        print(f"No valid knowledge files found in folder: {folder_id}")
        return ""

    context_parts = []
    
    for file in files:
        file_name = file['name']
        mime_type = file['mimeType']
        
        file_bytes = download_drive_file(service, file['id'])
        if not file_bytes:
            continue
            
        text = ""
        if mime_type == 'application/pdf':
            text = extract_text_from_pdf(file_bytes)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = extract_text_from_docx(file_bytes)
            
        if text.strip():
            context_parts.append(f"--- Document: {file_name} ---\n{text.strip()}\n")

    full_context = "\n".join(context_parts)
    
    # Truncate to avoid exceeding LLM context windows (rough character limit)
    if len(full_context) > MAX_KNOWLEDGE_CHARS:
        print(f"Warning: Knowledge context truncated from {len(full_context)} to {MAX_KNOWLEDGE_CHARS} characters.")
        full_context = full_context[:MAX_KNOWLEDGE_CHARS] + "\n...[CONTENT TRUNCATED]..."

    return full_context
