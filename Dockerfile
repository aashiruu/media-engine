FROM python:3.9-slim

WORKDIR /app

# Removed heavy ffmpeg install for now
# RUN apt-get update && apt-get install -y ffmpeg

# Install python dependencies
RUN pip install fastapi uvicorn psycopg2-binary redis celery yt-dlp

# Copy code
COPY main.py .

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
