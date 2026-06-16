import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import get_gmail_service
from src.labels import setup_required_labels, LABEL_AGENT_PROCESSED, LABEL_NEEDS_HUMAN, add_label_to_thread
from src.cleanup import scan_needs_human_threads, perform_auto_cleanup

def test_cleanup():
    print("Testing Human Handoff & Auto-Cleanup...")
    try:
        gmail_service = get_gmail_service()
        
        # 1. Setup labels
        label_ids = setup_required_labels(gmail_service)
        processed_id = label_ids[LABEL_AGENT_PROCESSED]
        human_id = label_ids[LABEL_NEEDS_HUMAN]
        
        # Note: Testing cleanup fully requires a thread that has Needs-Human and a sent reply.
        # This is hard to guarantee in a live inbox without sending a real email.
        # We will test the fetching and execution logic to ensure it doesn't crash.
        
        print("\nScanning for threads with Needs-Human label...")
        threads = scan_needs_human_threads(gmail_service, human_id)
        print(f"Found {len(threads)} threads currently waiting for human intervention.")
        
        print("\nRunning Auto-Cleanup routine...")
        cleaned_count = perform_auto_cleanup(gmail_service, human_id, processed_id)
        
        print(f"\nSUCCESS: Auto-Cleanup routine executed successfully.")
        print(f"Threads cleaned up during this run: {cleaned_count}")
        
    except Exception as e:
        print(f"\nFAILED: Test failed with exception: {e}")

if __name__ == "__main__":
    test_cleanup()
