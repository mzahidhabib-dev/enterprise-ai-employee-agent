from src.db.database import SessionLocal
from src.db.models import EmailLog, Contact, CostLog

def verify():
    print("\n--- CONNECTING TO SUPABASE POSTGRES ---")
    try:
        with SessionLocal() as db:
            emails = db.query(EmailLog).count()
            contacts = db.query(Contact).count()
            costs = db.query(CostLog).count()
            print("\n--- SUCCESS! TABLES EXIST. ---")
            print(f"Emails Processed: {emails}")
            print(f"Contacts Found: {contacts}")
            print(f"Cost Logs: {costs}")
            print("--------------------------------------\n")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    verify()
