"""
Single-Command Launcher for Online Job Portal Full-Stack Application
Starts FastAPI REST Backend and serves the Frontend at http://localhost:8000
"""

import os
import sqlite3
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "job_portal.db")

def main():
    print("=" * 80)
    print("ONLINE JOB PORTAL MANAGEMENT SYSTEM (WITH RECRUITER PREMIUM SUBSCRIPTION)")
    print("=" * 80)

    # 1. Check or initialize database
    if not os.path.exists(DB_PATH):
        print("[INFO] Database file not found. Running automatic initialization...")
        import setup_database
        setup_database.init_database()
    else:
        print(f"[OK] Database verified at: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        job_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    finally:
        conn.close()

    if job_count < 500:
        print(f"[INFO] Found {job_count} jobs; adding the demo job inventory...")
        from populate_300_jobs import populate
        job_count = populate(DB_PATH)

    if job_count < 500:
        raise RuntimeError(f"Job inventory initialization failed: found only {job_count} jobs.")
    print(f"[OK] Job inventory verified: {job_count} jobs available.")

    print("\nStarting FastAPI Application Server...")
    print("--> Web Application URL: http://localhost:8000")
    print("--> Interactive API Docs (Swagger): http://localhost:8000/docs")
    print("\nPre-configured Demo Accounts:")
    print("  * Job Seeker:  kamal.sen@email.com     | Password: any")
    print("  * Recruiter:   rajesh.varma@infosys.com | Password: any (Premium Plan)")
    print("  * Recruiter:   sneha@cloudscale.io     | Password: any (Free Plan)")
    print("  * Admin:       admin@jobportal.com     | Password: any")
    print("=" * 80)
    print("Press Ctrl+C to terminate the server.\n")

    # Start uvicorn server
    uvicorn.run("backend_app:app", host="127.0.0.1", port=8000, log_level="info", reload=False)

if __name__ == "__main__":
    main()
