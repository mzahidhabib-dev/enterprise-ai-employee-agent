FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required for packages like psycopg2 and spacy
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Download the spacy model required by presidio-analyzer
RUN python -m spacy download en_core_web_lg

COPY . .

EXPOSE 8000

# Start the uvicorn server
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
