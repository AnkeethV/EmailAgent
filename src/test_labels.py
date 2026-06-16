import sys
import os

# Add the parent directory to the sys.path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import get_gmail_service
from src.labels import (
    setup_required_labels,
    get_all_labels,
    LABEL_AGENT_PROCESSED,
    LABEL_NEEDS_HUMAN
)

def test_labels():
    print("Testing Gmail Labels State Management...")
    try:
        gmail_service = get_gmail_service()
        
        # 1. Ensure labels exist (creates them if they don't)
        print("Checking and setting up required labels...")
        label_ids = setup_required_labels(gmail_service)
        
        print("\nRequired Label IDs:")
        print(f" - {LABEL_AGENT_PROCESSED}: {label_ids[LABEL_AGENT_PROCESSED]}")
        print(f" - {LABEL_NEEDS_HUMAN}: {label_ids[LABEL_NEEDS_HUMAN]}")
        
        if not label_ids[LABEL_AGENT_PROCESSED] or not label_ids[LABEL_NEEDS_HUMAN]:
            print("\nFAILED: Failed to setup labels. Check your API permissions.")
            return

        # 2. List labels to verify they are in the account
        print("\nFetching all labels from account to verify...")
        all_labels = get_all_labels(gmail_service)
        label_names = [label['name'] for label in all_labels]
        
        if LABEL_AGENT_PROCESSED in label_names and LABEL_NEEDS_HUMAN in label_names:
            print(f"\nSUCCESS: Labels '{LABEL_AGENT_PROCESSED}' and '{LABEL_NEEDS_HUMAN}' are present in the Gmail account.")
        else:
            print(f"\nFAILED: Labels were not found in the account.")
            
    except Exception as e:
        print(f"\nFAILED: Test failed with exception: {e}")

if __name__ == "__main__":
    test_labels()
