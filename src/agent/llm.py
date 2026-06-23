# src/agent/llm.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Singleton LLM instance – swap model here to change globally
llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0,
    api_key=os.getenv("GEMINI_API_KEY"),
)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

__all__ = ["llm", "embeddings"]
