FROM python:3.10-slim

WORKDIR /app

# SKIP ffmpeg to save time. We only install curl.
RUN apt-get update && apt-get install -y curl

# Install python dependencies (force upgrade yt-dlp)
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary redis celery boto3
RUN pip install --no-cache-dir --upgrade yt-dlp

# Copy code
COPY main.py .

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
