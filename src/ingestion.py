import base64

def fetch_recent_threads(service, hours=2, max_results=None):
    """
    Fetch threads received within the last N hours.
    Handles pagination. If max_results is provided, stops after fetching that many.
    """
    query = f"newer_than:{hours}h"
    threads = []
    page_token = None

    while True:
        results = service.users().threads().list(
            userId='me',
            q=query,
            pageToken=page_token
        ).execute()

        if 'threads' in results:
            threads.extend(results['threads'])

        if max_results and len(threads) >= max_results:
            threads = threads[:max_results]
            break

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return threads

def get_thread_details(service, thread_id):
    """Fetch full details of a thread including all its messages."""
    return service.users().threads().get(userId='me', id=thread_id).execute()

def has_attachments(message_payload):
    """
    Recursively check if a message payload contains any non-trivial attachments.
    """
    if 'parts' in message_payload:
        for part in message_payload['parts']:
            # If the part has a filename and an attachment ID, it's an attachment
            if part.get('filename') and part.get('body', {}).get('attachmentId'):
                return True
            # Recursively check sub-parts
            if has_attachments(part):
                return True
    return False

def thread_has_draft(thread):
    """Check if any message in the thread is a draft."""
    for message in thread.get('messages', []):
        if 'DRAFT' in message.get('labelIds', []):
            return True
    return False

def get_latest_message(thread):
    """Returns the most recent message in the thread."""
    messages = thread.get('messages', [])
    if not messages:
        return None
    # Gmail API returns messages in chronological order (oldest first)
    return messages[-1]

def filter_threads_for_processing(service, threads, label_processed_id, label_needs_human_id):
    """
    Filters threads based on idempotency rules:
    1. Skip if Agent-Processed
    2. Skip if already contains a draft
    3. Skip if Needs-Human (already handled or waiting for human)
    """
    threads_to_process = []
    
    for th in threads:
        thread_id = th['id']
        thread_details = get_thread_details(service, thread_id)
        
        # Check thread-level labels (labels applied to the thread apply to its messages)
        # We can look at the latest message's labels or the thread object if it has them.
        # However, thread.get doesn't return thread-level labels directly, we must check the messages.
        
        # Collect all labels from all messages in the thread to get thread context
        all_labels = set()
        for msg in thread_details.get('messages', []):
            all_labels.update(msg.get('labelIds', []))
            
        if label_processed_id in all_labels:
            continue
            
        if label_needs_human_id in all_labels:
            continue
            
        if thread_has_draft(thread_details):
            continue
            
        threads_to_process.append(thread_details)
        
    return threads_to_process

def extract_text_from_message(message_payload):
    """Extract plain text body from a message payload."""
    body_text = ""
    
    if 'parts' in message_payload:
        for part in message_payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    body_text += base64.urlsafe_b64decode(data).decode('utf-8')
            elif 'parts' in part:
                body_text += extract_text_from_message(part)
    else:
        if message_payload.get('mimeType') == 'text/plain':
            data = message_payload.get('body', {}).get('data')
            if data:
                body_text += base64.urlsafe_b64decode(data).decode('utf-8')
                
    return body_text

def get_message_subject(message_payload):
    """Extract the subject from message headers."""
    headers = message_payload.get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'subject':
            return header.get('value', '')
    return ""
