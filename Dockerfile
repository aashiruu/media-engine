FROM python:3.10-slim

WORKDIR /app

# Install curl (for healthchecks)
RUN apt-get update && apt-get install -y curl && apt-get clean

# Install python dependencies
# faster-whisper is the magic library
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary redis celery boto3 yt-dlp faster-whisper

# Copy code
COPY main.py .

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
