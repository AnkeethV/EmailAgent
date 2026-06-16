from src.auth import get_gmail_service, get_drive_service

def test_authentication():
    print("Testing Google API Authentication...")
    
    try:
        # Test Gmail API
        print("Initializing Gmail Service...")
        gmail_service = get_gmail_service()
        # Fetch the authenticated user's email profile to verify connection
        profile = gmail_service.users().getProfile(userId='me').execute()
        print(f"SUCCESS: Gmail API successful! Authenticated as: {profile.get('emailAddress')}")

        # Test Drive API
        print("Initializing Drive Service...")
        drive_service = get_drive_service()
        # Fetch basic info about the user from Drive
        about = drive_service.about().get(fields="user").execute()
        print(f"SUCCESS: Drive API successful! Authenticated as: {about.get('user', {}).get('emailAddress')}")

    except Exception as e:
        print(f"FAILED: Authentication test failed: {e}")

if __name__ == "__main__":
    test_authentication()
