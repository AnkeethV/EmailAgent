import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.triage import evaluate_customer_query

def test_triage():
    print("Testing LLM Triage (Filtering Noise)...")
    
    # Test Case 1: Genuine Customer Query
    query_subject = "Help with my recent order"
    query_body = "Hi, I ordered a package last week but I haven't received a tracking number yet. Can you please check on this for me? Order #12345."
    
    print(f"\nTest 1 - Genuine Query:")
    print(f"Subject: {query_subject}")
    print("Evaluating...")
    result1 = evaluate_customer_query(query_subject, query_body)
    print(f"Result: is_customer_query = {result1}")
    if result1 is True:
        print("SUCCESS: Correctly identified as a customer query.")
    else:
        print("FAILED: Incorrectly identified.")

    # Test Case 2: Newsletter / Noise
    noise_subject = "Your Weekly Tech Newsletter!"
    noise_body = "Here are the top 10 tech stories of the week. Don't forget to upgrade to our premium plan to get these daily."
    
    print(f"\nTest 2 - Newsletter / Noise:")
    print(f"Subject: {noise_subject}")
    print("Evaluating...")
    result2 = evaluate_customer_query(noise_subject, noise_body)
    print(f"Result: is_customer_query = {result2}")
    if result2 is False:
        print("SUCCESS: Correctly identified as noise.")
    else:
        print("FAILED: Incorrectly identified as a customer query.")

if __name__ == "__main__":
    test_triage()
