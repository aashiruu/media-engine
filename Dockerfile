FROM python:3.9-slim

WORKDIR /app

# Install dependencies (added redis and celery)
RUN pip install fastapi uvicorn psycopg2-binary redis celery

# Copy code
COPY main.py .

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
