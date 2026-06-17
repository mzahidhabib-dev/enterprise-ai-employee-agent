# src/agent/llm.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI

# Singleton LLM instance – swap model here to change globally
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    api_key=os.getenv("GEMINI_API_KEY"),
)

__all__ = ["llm"]
