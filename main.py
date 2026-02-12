from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery
from prometheus_fastapi_instrumentator import Instrumentator # NEW
import psycopg2
import os
import yt_dlp
import boto3
import time

app = FastAPI()

# --- OBSERVABILITY SETUP (NEW) ---
# This automatically tracks requests, errors, and latency
Instrumentator().instrument(app).expose(app)

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

# --- MOCK AI MODEL ---
print("Loading AI Model (MOCK)...")
time.sleep(1)
print("AI Model Loaded.")

class VideoRequest(BaseModel):
    url: str

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-service"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "supersecretpassword")
    )

def update_job_status(job_id, status, title=None, duration=None, s3_url=None, audio_url=None, transcript=None):
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = "UPDATE videos SET status = %s"
    params = [status]
    
    if title:
        query += ", title = %s"
        params.append(title)
    if duration:
        query += ", duration = %s"
        params.append(duration)
    if s3_url:
        query += ", s3_url = %s"
        params.append(s3_url)
    if audio_url:
        query += ", audio_s3_url = %s"
        params.append(audio_url)
    if transcript:
        query += ", transcript_text = %s"
        params.append(transcript)
        
    query += " WHERE id = %s"
    params.append(job_id)
    
    cur.execute(query, tuple(params))
    conn.commit()
    cur.close()
    conn.close()

@celery_app.task
def process_video_task(job_id, url):
    print(f"Starting job {job_id} for {url}")
    update_job_status(job_id, "processing")
    
    try:
        # --- 1. Download RAW Audio & Video ---
        audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'/tmp/{job_id}-audio.%(ext)s',
            'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
        }
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            audio_filename = ydl.prepare_filename(info)
        print(f"Audio downloaded: {audio_filename}")

        video_opts = {
            'format': 'worstvideo[ext=mp4]/worst[ext=mp4]/worst', 
            'outtmpl': f'/tmp/{job_id}-video.mp4',
            'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
        }
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            ydl.download([url])
            video_filename = f'/tmp/{job_id}-video.mp4'

        # --- 2. Transcribe Audio (SIMULATED) ---
        print("Starting Mock Transcription...")
        time.sleep(3) # Simulate work
        transcript_text = "We're no strangers to love. You know the rules and so do I. A full commitment's what I'm thinking of. You wouldn't get this from any other guy."
        print(f"Transcription complete: {len(transcript_text)} chars")

        # 3. Upload & Cleanup
        audio_ext = os.path.splitext(audio_filename)[1]
        audio_key = f"{job_id}-audio{audio_ext}"
        video_key = f"{job_id}-video.mp4"
        
        s3_client.upload_file(audio_filename, BUCKET_NAME, audio_key)
        s3_client.upload_file(video_filename, BUCKET_NAME, video_key)

        if os.path.exists(video_filename): os.remove(video_filename)
        if os.path.exists(audio_filename): os.remove(audio_filename)

        # 4. Update DB
        video_s3 = f"s3://{BUCKET_NAME}/{video_key}"
        audio_s3 = f"s3://{BUCKET_NAME}/{audio_key}"
        
        update_job_status(job_id, "completed", title, duration, video_s3, audio_s3, transcript_text)
        return f"Finished {job_id}: {title}"
        
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        update_job_status(job_id, "failed")
        return f"Failed {job_id}"

# --- API ---
@app.get("/")
def read_root():
    return {"status": "Media Engine Online", "version": "v15-metrics"}

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
