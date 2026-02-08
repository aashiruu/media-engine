from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-service"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "supersecretpassword")
    )
    return conn

@app.get("/")
def read_root():
    return {"status": "Media Engine is Online"}

@app.get("/db-test")
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        cur.close()
        conn.close()
        return {"database_status": "Connected", "version": db_version[0]}
    except Exception as e:
        return {"database_status": "Failed", "error": str(e)}
