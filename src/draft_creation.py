import base64
from email.message import EmailMessage

def create_draft_payload(to_email, subject, body_text, thread_id, message_id):
    """
    Creates a base64 encoded email payload formatted as a reply.
    Requires the original message ID to correctly thread the reply in Gmail clients.
    """
    message = EmailMessage()
    message.set_content(body_text)

    message['To'] = to_email
    
    # Prefix with 'Re: ' if not already present
    if not subject.lower().startswith('re:'):
        message['Subject'] = f"Re: {subject}"
    else:
        message['Subject'] = subject
        
    # Standard headers to ensure it threads correctly as a reply
    if message_id:
        message['In-Reply-To'] = message_id
        message['References'] = message_id

    # The Gmail API requires the raw message to be base64url encoded
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    return {
        'message': {
            'threadId': thread_id,
            'raw': encoded_message
        }
    }

def create_gmail_draft(service, draft_payload):
    """
    Creates a draft in the user's Gmail account using the provided payload.
    Returns the Draft ID on success.
    """
    try:
        draft = service.users().drafts().create(
            userId='me',
            body=draft_payload
        ).execute()
        
        print(f"Draft created successfully. Draft ID: {draft['id']}")
        return draft['id']
    except Exception as e:
        print(f"Error creating Gmail draft: {e}")
        return None
