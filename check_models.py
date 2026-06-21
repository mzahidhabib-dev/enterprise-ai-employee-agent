import os
import requests

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Read from .env manually
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.strip().split("=")[1]
                break

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json().get("models", [])
        for m in models:
            if "gemini" in m["name"].lower():
                print(m["name"])
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Failed: {e}")
