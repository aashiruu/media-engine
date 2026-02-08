from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
import psycopg2
import os
import yt_dlp
import boto3

app = FastAPI()

# --- Config ---
celery_app = Celery(
    "media_engine",
    broker="redis://redis-master:6379/0",
    backend="redis://redis-master:6379/0"
)

s3_client = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="password123"
)

BUCKET_NAME = "raw-videos"

class VideoRequest(BaseModel):
    url: str

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-service"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "supersecretpassword")
    )

def update_job_status(job_id, status, title=None, duration=None, s3_url=None):
    conn = get_db_connection()
    cur = conn.cursor()
    if s3_url:
        cur.execute(
            "UPDATE videos SET status = %s, title = %s, duration = %s, s3_url = %s WHERE id = %s",
            (status, title, duration, s3_url, job_id)
        )
    elif title:
        cur.execute(
            "UPDATE videos SET status = %s, title = %s, duration = %s WHERE id = %s",
            (status, title, duration, job_id)
        )
    else:
        cur.execute("UPDATE videos SET status = %s WHERE id = %s", (status, job_id))
    conn.commit()
    cur.close()
    conn.close()

# --- The Worker Logic ---
@celery_app.task
def process_video_task(job_id, url):
    print(f"Starting job {job_id} for {url}")
    update_job_status(job_id, "processing")
    
    try:
        # 1. Download with 'Stealth' options
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'/tmp/{job_id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            # SPOOFING: Pretend to be an Android Client to bypass 403
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            filename = ydl.prepare_filename(info)

        print(f"Downloaded locally: {filename}")

        # 2. Upload to MinIO
        s3_key = f"{job_id}-{os.path.basename(filename)}"
        s3_client.upload_file(filename, BUCKET_NAME, s3_key)
        print(f"Uploaded to MinIO: {s3_key}")

        # 3. Cleanup Local File
        os.remove(filename)

        # 4. Update DB
        s3_url = f"s3://{BUCKET_NAME}/{s3_key}"
        update_job_status(job_id, "completed", title, duration, s3_url)
        
        return f"Finished {job_id}: {title}"
        
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        update_job_status(job_id, "failed")
        return f"Failed {job_id}"

# --- API ---
@app.get("/")
def read_root():
    return {"status": "Media Engine Online", "version": "v7-stealth"}

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
