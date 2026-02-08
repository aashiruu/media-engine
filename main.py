from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI()

# --- Data Model ---
class VideoRequest(BaseModel):
    url: str

# --- Database Connection ---
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-service"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "supersecretpassword")
    )

@app.get("/")
def read_root():
    return {"status": "Media Engine Online", "version": "v2"}

# --- The Ingest Endpoint ---
@app.post("/videos")
def create_video_job(video: VideoRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert the URL into the DB
        cur.execute(
            "INSERT INTO videos (url, status) VALUES (%s, %s) RETURNING id, status",
            (video.url, "pending")
        )
        new_job = cur.fetchone()
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"job_id": new_job[0], "status": new_job[1], "message": "Ingest started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
