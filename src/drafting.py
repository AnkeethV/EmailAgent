from groq import Groq
from src.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

DRAFTING_PROMPT_TEMPLATE = """You are a helpful customer support assistant. Use ONLY the information in the provided documents to answer the customer's question.

Rules:
- If the answer is not found in the documents, respond with exactly: KNOWLEDGE_GAP
- Do not make up information. Do not use outside knowledge.
- Be concise, professional, and friendly.
- If the documents partially answer the question but leave a part unanswered, respond with KNOWLEDGE_GAP. Do not provide partial answers.

Documents:
{concatenated_document_text}

Customer Email:
Subject: {subject}
Body: {body}

Your draft reply:"""

def generate_draft_reply(knowledge_context, subject, body, model="llama-3.3-70b-versatile"):
    """
    Generates a draft reply using the provided knowledge context.
    Returns 'KNOWLEDGE_GAP' if the LLM cannot confidently answer based ONLY on the documents.
    Returns the drafted reply string otherwise.
    """
    prompt = DRAFTING_PROMPT_TEMPLATE.format(
        concatenated_document_text=knowledge_context,
        subject=subject,
        body=body
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0, # Low temperature to enforce strict adherence to knowledge base
            max_tokens=1024
        )
        
        reply_text = response.choices[0].message.content.strip()
        
        # Output handling: Check if the model explicitly returned KNOWLEDGE_GAP
        if "KNOWLEDGE_GAP" in reply_text.upper():
            return "KNOWLEDGE_GAP"
            
        if not reply_text:
            return "KNOWLEDGE_GAP"
            
        return reply_text
        
    except Exception as e:
        print(f"Error during LLM drafting: {e}")
        # Fail safe: If drafting fails due to API error, treat it as a knowledge gap so a human takes over
        return "KNOWLEDGE_GAP"
