import json
from groq import Groq
from src.config import GROQ_API_KEY

# Initialize the Groq client
client = Groq(api_key=GROQ_API_KEY)

TRIAGE_PROMPT_TEMPLATE = """You are an email classifier. Read the email below and decide if it is a genuine customer query that requires a response from a business.

Rules:
- Ignore newsletters, promotional emails, receipts, invoices, automated notifications, and internal emails.
- Focus on the body content, not the sender or headers.
- A customer query asks a question, requests help, or seeks information about products/services.

Respond with ONLY a JSON object: {{"is_customer_query": true/false}}

Email Subject: {subject}
Email Body: {body}"""

def evaluate_customer_query(subject, body, model="llama-3.1-8b-instant"):
    """
    Evaluates whether an email is a genuine customer query using the Groq LLM.
    Returns True if it is a customer query, False otherwise.
    """
    prompt = TRIAGE_PROMPT_TEMPLATE.format(subject=subject, body=body)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        response_text = response.choices[0].message.content
        parsed_json = json.loads(response_text)
        
        # Extract the boolean value, default to False if missing
        is_query = parsed_json.get("is_customer_query", False)
        
        # Ensure it's a boolean
        if isinstance(is_query, bool):
            return is_query
        elif isinstance(is_query, str):
            return is_query.lower() == "true"
        return False
        
    except Exception as e:
        print(f"Error during LLM triage: {e}")
        # Fail safe: If triage fails, we assume it's NOT a customer query to avoid wasting tokens or doing bad things
        # Alternatively, we could raise the error to trigger a Needs-Human fallback.
        # But for now, we'll return False and log.
        return False
