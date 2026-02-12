FROM python:3.10-slim

WORKDIR /app

# Install curl
RUN apt-get update && apt-get install -y curl && apt-get clean

# Install dependencies (Added prometheus-fastapi-instrumentator)
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary redis celery boto3 yt-dlp prometheus-fastapi-instrumentator

# Copy code
COPY main.py .

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
