import os
import sys
import json
import logging
from datetime import datetime
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from googleapiclient.errors import HttpError

# Import all our project modules
from src.auth import get_gmail_service, get_drive_service
from src.labels import setup_required_labels, add_label_to_thread, LABEL_AGENT_PROCESSED, LABEL_NEEDS_HUMAN
from src.ingestion import fetch_recent_threads, filter_threads_for_processing, get_latest_message, has_attachments, get_message_subject, extract_text_from_message
from src.triage import evaluate_customer_query
from src.knowledge import build_knowledge_context
from src.drafting import generate_draft_reply
from src.draft_creation import create_draft_payload, create_gmail_draft
from src.cleanup import perform_auto_cleanup

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

# Setup structured JSON Logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage()
        }
        if hasattr(record, 'extra_data'):
            log_record.update(record.extra_data)
        return json.dumps(log_record)

logger = logging.getLogger("EmailAgent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# Retry wrappers for rate-limited API calls
@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), retry=retry_if_exception_type(HttpError))
def safe_fetch_threads(service, hours, max_results):
    return fetch_recent_threads(service, hours=hours, max_results=max_results)

@retry(wait=wait_exponential(multiplier=2, min=4, max=15), stop=stop_after_attempt(3))
def safe_evaluate_query(subject, body):
    return evaluate_customer_query(subject, body)

@retry(wait=wait_exponential(multiplier=2, min=4, max=15), stop=stop_after_attempt(3))
def safe_generate_draft(context, subject, body):
    return generate_draft_reply(context, subject, body)

def main():
    logger.info("Starting Email Agent Execution", extra={"extra_data": {"event": "run_started"}})
    
    try:
        # 1. Initialize APIs
        gmail_service = get_gmail_service()
        drive_service = get_drive_service()
        
        # 2. Setup Labels
        label_ids = setup_required_labels(gmail_service)
        if not label_ids:
            raise ValueError("Failed to retrieve or create required Gmail labels.")
        processed_id = label_ids[LABEL_AGENT_PROCESSED]
        human_id = label_ids[LABEL_NEEDS_HUMAN]
        
        # 3. Auto-Cleanup
        cleaned_count = perform_auto_cleanup(gmail_service, human_id, processed_id)
        logger.info(f"Auto-cleanup completed.", extra={"extra_data": {"event": "cleanup_completed", "threads_cleaned": cleaned_count}})
        
        # 4. Fetch and Filter Threads
        # In production we look at the last 2 hours. We cap at 15 for safety if it's the first run, 
        # but the query params can handle that. We'll stick to max_results=15 for safety bounds.
        threads = safe_fetch_threads(gmail_service, hours=2, max_results=15)
        
        if not threads:
            logger.info("No new threads found in the last 2 hours.", extra={"extra_data": {"event": "no_emails_found"}})
            return
            
        valid_threads = filter_threads_for_processing(gmail_service, threads, processed_id, human_id)
        logger.info(f"Filtered threads.", extra={"extra_data": {"event": "filtering_completed", "total_found": len(threads), "valid_for_processing": len(valid_threads)}})
        
        if not valid_threads:
            return

        # 5. Pre-fetch knowledge context once (saves API calls if there are multiple emails)
        knowledge_context = build_knowledge_context(drive_service)
        if not knowledge_context:
            logger.warning("Knowledge base is empty or unreachable.", extra={"extra_data": {"event": "knowledge_fetch_empty"}})

        # 6. Process each valid thread
        for thread in valid_threads:
            thread_id = thread['id']
            latest_message = get_latest_message(thread)
            payload = latest_message.get('payload', {})
            
            subject = get_message_subject(payload)
            body_text = extract_text_from_message(payload)
            sender = get_message_sender(payload)
            message_id = get_message_id_header(payload)
            
            # --- Check Attachments ---
            if has_attachments(payload):
                logger.info("Thread contains attachments. Flagging for human.", extra={"extra_data": {"event": "attachment_flagged", "thread_id": thread_id}})
                add_label_to_thread(gmail_service, thread_id, human_id)
                continue
                
            # --- Triage LLM ---
            is_customer = safe_evaluate_query(subject, body_text)
            if not is_customer:
                logger.info("Thread triaged as noise.", extra={"extra_data": {"event": "triaged_as_noise", "thread_id": thread_id}})
                add_label_to_thread(gmail_service, thread_id, processed_id)
                continue
                
            # --- Drafting LLM ---
            if not knowledge_context:
                 # If we have no knowledge, everything is a gap
                 draft_text = "KNOWLEDGE_GAP"
            else:
                 draft_text = safe_generate_draft(knowledge_context, subject, body_text)
                 
            if draft_text == "KNOWLEDGE_GAP":
                logger.info("Knowledge gap identified. Flagging for human.", extra={"extra_data": {"event": "knowledge_gap_flagged", "thread_id": thread_id}})
                add_label_to_thread(gmail_service, thread_id, human_id)
                continue
                
            # --- Create Draft ---
            draft_payload = create_draft_payload(sender, subject, draft_text, thread_id, message_id)
            draft_id = create_gmail_draft(gmail_service, draft_payload)
            
            if draft_id:
                logger.info("Draft created successfully.", extra={"extra_data": {"event": "draft_created", "thread_id": thread_id, "draft_id": draft_id}})
                add_label_to_thread(gmail_service, thread_id, processed_id)
            else:
                logger.error("Failed to create draft via Gmail API.", extra={"extra_data": {"event": "draft_creation_failed", "thread_id": thread_id}})
                add_label_to_thread(gmail_service, thread_id, human_id) # Fallback to human if API fails
                
        logger.info("Email Agent Execution Completed Successfully.", extra={"extra_data": {"event": "run_completed"}})

    except Exception as e:
        logger.fatal(f"Fatal error during agent execution: {e}", extra={"extra_data": {"event": "fatal_error", "error": str(e)}}, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
