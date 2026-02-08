from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
import psycopg2
import os
import yt_dlp

app = FastAPI()

# --- Config ---
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

def update_job_status(job_id, status, title=None, duration=None):
    conn = get_db_connection()
    cur = conn.cursor()
    if title:
        cur.execute(
            "UPDATE videos SET status = %s, title = %s, duration = %s WHERE id = %s",
            (status, title, duration, job_id)
        )
    else:
        cur.execute("UPDATE videos SET status = %s WHERE id = %s", (status, job_id))
    conn.commit()
    cur.close()
    conn.close()

# --- The Real Worker Logic ---
@celery_app.task
def process_video_task(job_id, url):
    print(f"Starting job {job_id} for {url}")
    update_job_status(job_id, "processing")
    
    try:
        # Use yt-dlp to get metadata (don't download video yet)
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
        print(f"Found video: {title} ({duration}s)")
        
        # Update DB with real data
        update_job_status(job_id, "completed", title, duration)
        return f"Finished {job_id}: {title}"
        
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        update_job_status(job_id, "failed")
        return f"Failed {job_id}"

# --- API ---
@app.get("/")
def read_root():
    return {"status": "Media Engine Online", "version": "v5-real-code"}

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
        process_video_task.delay(job_id, video.url)
        return {"job_id": job_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
