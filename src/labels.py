from googleapiclient.errors import HttpError

LABEL_AGENT_PROCESSED = "Agent-Processed"
LABEL_NEEDS_HUMAN = "Needs-Human"

def get_all_labels(service):
    """List all existing labels for the authenticated user."""
    try:
        results = service.users().labels().list(userId='me').execute()
        return results.get('labels', [])
    except HttpError as error:
        print(f"An error occurred fetching labels: {error}")
        return []

def get_label_id_by_name(service, label_name):
    """Fetch the Label ID for a specific label name. Returns None if not found."""
    labels = get_all_labels(service)
    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']
    return None

def create_label(service, label_name):
    """Create a new label and return its ID."""
    try:
        label_object = {
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show',
            'name': label_name
        }
        created_label = service.users().labels().create(userId='me', body=label_object).execute()
        print(f"Created label: {label_name} with ID: {created_label['id']}")
        return created_label['id']
    except HttpError as error:
        print(f"An error occurred creating label '{label_name}': {error}")
        return None

def ensure_label_exists(service, label_name):
    """Ensure a label exists, creating it if necessary. Returns the Label ID."""
    label_id = get_label_id_by_name(service, label_name)
    if label_id:
        return label_id
    # If not found, create it
    return create_label(service, label_name)

def setup_required_labels(service):
    """Ensure both required labels exist and return their IDs."""
    agent_processed_id = ensure_label_exists(service, LABEL_AGENT_PROCESSED)
    needs_human_id = ensure_label_exists(service, LABEL_NEEDS_HUMAN)
    
    return {
        LABEL_AGENT_PROCESSED: agent_processed_id,
        LABEL_NEEDS_HUMAN: needs_human_id
    }

def add_label_to_thread(service, thread_id, label_id):
    """Add a specific label to a thread."""
    try:
        body = {'addLabelIds': [label_id]}
        service.users().threads().modify(userId='me', id=thread_id, body=body).execute()
        # print(f"Added label {label_id} to thread {thread_id}")
    except HttpError as error:
        print(f"An error occurred adding label to thread {thread_id}: {error}")

def remove_label_from_thread(service, thread_id, label_id):
    """Remove a specific label from a thread."""
    try:
        body = {'removeLabelIds': [label_id]}
        service.users().threads().modify(userId='me', id=thread_id, body=body).execute()
        # print(f"Removed label {label_id} from thread {thread_id}")
    except HttpError as error:
        print(f"An error occurred removing label from thread {thread_id}: {error}")
