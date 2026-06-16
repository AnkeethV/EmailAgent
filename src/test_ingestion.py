import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import get_gmail_service
from src.labels import setup_required_labels, LABEL_AGENT_PROCESSED, LABEL_NEEDS_HUMAN
from src.ingestion import (
    fetch_recent_threads,
    filter_threads_for_processing,
    get_latest_message,
    has_attachments,
    get_message_subject
)

def test_ingestion():
    print("Testing Gmail Ingestion & Filtering...")
    try:
        gmail_service = get_gmail_service()
        
        # Get our label IDs
        print("Fetching label IDs...")
        label_ids = setup_required_labels(gmail_service)
        processed_id = label_ids[LABEL_AGENT_PROCESSED]
        human_id = label_ids[LABEL_NEEDS_HUMAN]
        
        # 1. Fetch recent threads (Let's test with max_results=5 to avoid long execution during test)
        print("\nFetching up to 5 recent threads from the last 24 hours (for testing)...")
        # We use 24 hours for testing just to ensure we find *something*, but the PRD requires 2 hours for production
        threads = fetch_recent_threads(gmail_service, hours=24, max_results=5)
        print(f"Found {len(threads)} threads.")
        
        if not threads:
            print("No threads found in the last 24 hours to test with.")
            return
            
        # 2. Filter threads
        print("\nFiltering threads based on idempotency rules...")
        valid_threads = filter_threads_for_processing(gmail_service, threads, processed_id, human_id)
        print(f"{len(valid_threads)} threads passed the filters and need processing.")
        
        # 3. Inspect a valid thread
        if valid_threads:
            thread = valid_threads[0]
            latest_message = get_latest_message(thread)
            payload = latest_message.get('payload', {})
            
            subject = get_message_subject(payload)
            attachments_present = has_attachments(payload)
            
            print("\n--- Details of first valid thread ---")
            print(f"Thread ID: {thread['id']}")
            print(f"Subject: {subject}")
            print(f"Has Attachments: {attachments_present}")
            
        print("\nSUCCESS: Ingestion & Filtering test completed.")
        
    except Exception as e:
        print(f"\nFAILED: Test failed with exception: {e}")

if __name__ == "__main__":
    test_ingestion()
