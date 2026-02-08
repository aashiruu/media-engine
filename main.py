from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
import psycopg2
import os
import time

app = FastAPI()

# --- Configuration ---
# Celery acts as the "Client" for the API and the "Server" for the Worker
celery_app = Celery(
    "media_engine",
    broker="redis://redis-master:6379/0",
    backend="redis://redis-master:6379/0"
)

class VideoRequest(BaseModel):
    url: str

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-service"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "supersecretpassword")
    )

def update_job_status(job_id, status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE videos SET status = %s WHERE id = %s", (status, job_id))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Job {job_id} updated to {status}")

# --- The Worker Logic ---
@celery_app.task
def process_video_task(job_id, url):
    print(f"Starting job {job_id} for {url}")
    
    # 1. Update DB to 'processing'
    update_job_status(job_id, "processing")
    
    # 2. Simulate heavy AI work (downloading, processing)
    time.sleep(10) 
    
    # 3. Update DB to 'completed'
    update_job_status(job_id, "completed")
    return f"Finished {job_id}"

# --- The API Logic ---
@app.post("/videos")
def create_video_job(video: VideoRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO videos (url, status) VALUES (%s, %s) RETURNING id, status",
            (video.url, "pending")
        )
        new_job = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        job_id = new_job[0]
        # Send to Redis
        process_video_task.delay(job_id, video.url)
        
        return {"job_id": job_id, "status": "queued", "message": "Job sent to background worker"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
