import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.drafting import generate_draft_reply

def test_drafting():
    print("Testing LLM Drafting...")
    
    mock_knowledge = """
    --- Document: Store_Policies.txt ---
    Our return policy allows returns within 30 days of purchase for a full refund.
    We do not offer international shipping at this time.
    Our support hours are Monday to Friday, 9 AM to 5 PM EST.
    """
    
    # Test Case 1: Answer is in the documents
    subject_1 = "Can I return my item?"
    body_1 = "Hi, I bought a shirt 10 days ago but it doesn't fit. Can I return it?"
    
    print("\nTest 1 - Query CAN be answered by knowledge base:")
    print(f"Subject: {subject_1}")
    draft_1 = generate_draft_reply(mock_knowledge, subject_1, body_1)
    print("\n--- Draft Output ---")
    print(draft_1)
    print("--------------------")
    if draft_1 != "KNOWLEDGE_GAP":
        print("SUCCESS: Draft generated successfully.")
    else:
        print("FAILED: Expected a draft, got KNOWLEDGE_GAP.")

    # Test Case 2: Answer is NOT in the documents
    subject_2 = "Do you ship to Canada?"
    body_2 = "Hello, I live in Toronto and want to buy your products. Do you ship here and how much does it cost?"
    
    print("\nTest 2 - Query CANNOT be answered fully (or at all) by knowledge base:")
    print(f"Subject: {subject_2}")
    # Note: Even though the doc says "We do not offer international shipping", let's ask something specific like "how much does it cost" 
    # Actually, the LLM might just say "we don't offer international shipping". Let's test a true gap:
    subject_3 = "Who is the CEO?"
    body_3 = "I am doing a school project. Who is the CEO of your company?"
    
    print(f"Subject: {subject_3}")
    draft_2 = generate_draft_reply(mock_knowledge, subject_3, body_3)
    print("\n--- Draft Output ---")
    print(draft_2)
    print("--------------------")
    if draft_2 == "KNOWLEDGE_GAP":
        print("SUCCESS: Correctly identified KNOWLEDGE_GAP.")
    else:
        print("FAILED: Expected KNOWLEDGE_GAP but got a drafted reply.")

if __name__ == "__main__":
    test_drafting()
