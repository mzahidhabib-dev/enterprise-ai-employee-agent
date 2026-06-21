import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import time

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.strip().split("=")[1]
                break

models_to_test = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash",
    "gemini-flash-latest"
]

for m in models_to_test:
    print(f"Testing model: {m}...")
    try:
        llm = ChatGoogleGenerativeAI(model=m, api_key=api_key, temperature=0)
        res = llm.invoke([HumanMessage(content="Hello")])
        print(f"✅ SUCCESS: {m} works! Response: {res.content}")
        break # If we find a working one, we can stop
    except Exception as e:
        print(f"❌ FAILED: {m} -> {e}")
    time.sleep(2)
