import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import get_gmail_service
from src.ingestion import fetch_recent_threads, get_thread_details, get_latest_message, get_message_subject
from src.draft_creation import create_draft_payload, create_gmail_draft
from src.labels import setup_required_labels, add_label_to_thread, LABEL_AGENT_PROCESSED

def get_message_sender(message_payload):
    """Helper to extract the sender (From header) of a message."""
    headers = message_payload.get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'from':
            return header.get('value', '')
    return ""

def get_message_id_header(message_payload):
    """Helper to extract the Message-ID header for threading."""
    headers = message_payload.get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'message-id':
            return header.get('value', '')
    return ""

def test_draft_creation():
    print("Testing Gmail Draft Creation...")
    try:
        gmail_service = get_gmail_service()
        
        # 1. Ensure labels exist so we can apply the processed label
        label_ids = setup_required_labels(gmail_service)
        processed_label_id = label_ids[LABEL_AGENT_PROCESSED]
        
        # 2. Find a thread to reply to (we'll just grab the most recent one for the test)
        print("\nFetching the most recent thread to create a test draft...")
        threads = fetch_recent_threads(gmail_service, hours=24, max_results=1)
        
        if not threads:
            print("FAILED: No recent threads found to test draft creation on.")
            return
            
        thread_id = threads[0]['id']
        thread_details = get_thread_details(gmail_service, thread_id)
        latest_message = get_latest_message(thread_details)
        
        msg_payload = latest_message.get('payload', {})
        subject = get_message_subject(msg_payload)
        sender = get_message_sender(msg_payload)
        message_id = get_message_id_header(msg_payload)
        
        print(f"\nFound Thread:")
        print(f"Subject: {subject}")
        print(f"From: {sender}")
        
        # 3. Create the payload
        draft_body = "Hi there,\n\nThis is an automated test draft created by the Agent.\n\nBest,\nAgent"
        
        print("\nGenerating Draft Payload...")
        payload = create_draft_payload(
            to_email=sender,
            subject=subject,
            body_text=draft_body,
            thread_id=thread_id,
            message_id=message_id
        )
        
        # 4. Create the draft in Gmail
        print("Sending to Gmail API...")
        draft_id = create_gmail_draft(gmail_service, payload)
        
        if draft_id:
            print("\nSUCCESS: Draft was created.")
            
            # 5. Apply the Agent-Processed label
            print(f"Applying '{LABEL_AGENT_PROCESSED}' label to thread...")
            add_label_to_thread(gmail_service, thread_id, processed_label_id)
            print("SUCCESS: Label applied.")
            
            print("\nGo check your Gmail! You should see a draft reply in the most recent thread.")
        else:
            print("\nFAILED: Draft creation failed.")
            
    except Exception as e:
        print(f"\nFAILED: Test failed with exception: {e}")

if __name__ == "__main__":
    test_draft_creation()
