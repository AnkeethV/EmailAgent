import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import get_drive_service
from src.knowledge import list_drive_files, build_knowledge_context
from src.config import GOOGLE_DRIVE_FOLDER_ID

def test_knowledge():
    print("Testing Knowledge Retrieval & Document Processing...")
    
    try:
        if not GOOGLE_DRIVE_FOLDER_ID:
            print("FAILED: GOOGLE_DRIVE_FOLDER_ID is missing from .env")
            return
            
        print(f"Target Drive Folder ID: {GOOGLE_DRIVE_FOLDER_ID}")
        drive_service = get_drive_service()
        
        # 1. List files
        print("\nListing files in Drive Folder...")
        files = list_drive_files(drive_service, GOOGLE_DRIVE_FOLDER_ID)
        print(f"Found {len(files)} files.")
        for f in files:
            print(f" - {f['name']} ({f['mimeType']})")
            
        if not files:
            print("\nWARNING: No PDF or DOCX files found. Ensure the folder has supported documents to test extraction.")
            # We don't fail here, because the folder might just be empty, but extraction won't be fully tested
            return
            
        # 2. Build full context
        print("\nExtracting text and building knowledge context...")
        context = build_knowledge_context(drive_service, GOOGLE_DRIVE_FOLDER_ID)
        
        context_length = len(context)
        print(f"\nExtracted a total of {context_length} characters of context.")
        
        if context_length > 0:
            print("\n--- Context Preview (First 500 chars) ---")
            print(context[:500])
            print("-----------------------------------------")
            print("\nSUCCESS: Knowledge retrieval and processing complete.")
        else:
            print("\nFAILED: Files were found but no text could be extracted.")
            
    except Exception as e:
        print(f"\nFAILED: Test failed with exception: {e}")

if __name__ == "__main__":
    test_knowledge()
