def scan_needs_human_threads(service, label_needs_human_id):
    """
    Fetches all threads that currently have the Needs-Human label.
    """
    threads = []
    page_token = None

    while True:
        results = service.users().threads().list(
            userId='me',
            labelIds=[label_needs_human_id],
            pageToken=page_token
        ).execute()

        if 'threads' in results:
            threads.extend(results['threads'])

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return threads

def get_message_sender(message_payload):
    """Helper to extract the sender (From header) of a message."""
    headers = message_payload.get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'from':
            return header.get('value', '')
    return ""

def is_human_reply(latest_message, my_email):
    """
    Determines if the latest message is a human reply.
    It is considered a human reply if:
    1. It was sent by the authenticated user.
    2. It is NOT a draft.
    """
    # Check if it's a draft
    if 'DRAFT' in latest_message.get('labelIds', []):
        return False
        
    sender = get_message_sender(latest_message.get('payload', {}))
    # Basic string match to see if the user's email is in the From header
    if my_email.lower() in sender.lower():
        return True
        
    return False

def perform_auto_cleanup(service, label_needs_human_id, label_agent_processed_id):
    """
    Scans all Needs-Human threads. If the human has replied to the thread,
    it removes the Needs-Human label and applies Agent-Processed.
    """
    # Get the authenticated user's email
    profile = service.users().getProfile(userId='me').execute()
    my_email = profile.get('emailAddress')
    
    if not my_email:
        print("Error: Could not retrieve authenticated user email.")
        return 0
        
    needs_human_threads = scan_needs_human_threads(service, label_needs_human_id)
    cleanup_count = 0
    
    for thread_info in needs_human_threads:
        thread_id = thread_info['id']
        # Fetch full thread details to inspect messages
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        messages = thread.get('messages', [])
        
        if not messages:
            continue
            
        # The last message is the most recent one in the thread
        latest_message = messages[-1]
        
        if is_human_reply(latest_message, my_email):
            print(f"Human reply detected in thread {thread_id}. Cleaning up labels...")
            try:
                # Remove Needs-Human, Add Agent-Processed
                body = {
                    'addLabelIds': [label_agent_processed_id],
                    'removeLabelIds': [label_needs_human_id]
                }
                service.users().threads().modify(userId='me', id=thread_id, body=body).execute()
                cleanup_count += 1
            except Exception as e:
                print(f"Error updating labels for thread {thread_id}: {e}")
                
    return cleanup_count
