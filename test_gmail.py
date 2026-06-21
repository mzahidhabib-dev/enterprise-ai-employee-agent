from src.tools.gmail_tools import fetch_unread_emails

print("Attempting to connect to Gmail...")
try:
    # Try to fetch up to 5 unread emails
    emails = fetch_unread_emails.invoke({"max_results": 5})
    print(f"SUCCESS! Found {len(emails)} unread emails.")
except Exception as e:
    print(f"FAILED to connect to Gmail. Error: {e}")
