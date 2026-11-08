"""
FastAPI Backend Application for Online Job Portal Management System
Implements REST API for all 12 modules with SQLite/MySQL database integration.
"""

import sqlite3
import os
import json
import re
import tempfile
import threading
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ON_VERCEL = os.environ.get("VERCEL") == "1"
DB_PATH = os.path.join(
    tempfile.gettempdir() if ON_VERCEL else BASE_DIR,
    "job_portal.db"
)
_db_initialization_lock = threading.Lock()

app = FastAPI(
    title="Online Job Portal API",
    description="REST API for Online Job Portal with Recruiter Premium Subscription (12 Core Modules)",
    version="2.0.0"
)

# High Performance Compression & CORS
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    if ON_VERCEL:
        with _db_initialization_lock:
            if not os.path.exists(DB_PATH):
                import setup_database

                setup_database.DB_PATH = DB_PATH
                setup_database.init_database()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    try:
        yield conn
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# HIGH PERFORMANCE IN-MEMORY DATA CACHING
# -----------------------------------------------------------------------------
JOBS_CACHE = {
    "base_jobs": None,
    "job_skills_map": None
}

def invalidate_jobs_cache():
    JOBS_CACHE["base_jobs"] = None
    JOBS_CACHE["job_skills_map"] = None

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    phone: Optional[str] = ""
    role: str  # 'job_seeker' or 'recruiter'
    qualification: Optional[str] = "B.Tech"
    experience_years: Optional[float] = 0.0
    current_location: Optional[str] = "Bengaluru"
    expected_salary: Optional[float] = 600000.0
    company_name: Optional[str] = None
    designation: Optional[str] = "Talent Acquisition Specialist"

class PostJobRequest(BaseModel):
    recruiter_id: int
    company_id: int
    job_title: str
    job_type: str = "Full-time"
    experience_level: str = "Mid"
    location: str
    salary_min: float
    salary_max: float
    description: str
    requirements: Optional[str] = ""
    open_vacancies: int = 1
    is_featured: bool = False
    deadline: str
    skill_ids: List[int] = []

class ApplyJobRequest(BaseModel):
    seeker_id: int
    resume_id: int
    cover_letter: Optional[str] = ""

class UpdateStatusRequest(BaseModel):
    status: str
    remarks: Optional[str] = ""
    changed_by_user_id: Optional[int] = None
    offered_ctc: Optional[float] = None
    joining_date: Optional[str] = None

class AcceptApplicationRequest(BaseModel):
    remarks: Optional[str] = "Congratulations! Your application has been accepted and an offer has been extended."
    offered_ctc: Optional[float] = None
    joining_date: Optional[str] = None
    changed_by_user_id: Optional[int] = None

class RejectApplicationRequest(BaseModel):
    reason: Optional[str] = "Vacancy requirements criteria"
    remarks: Optional[str] = "Thank you for applying. We encourage you to apply for future positions."
    changed_by_user_id: Optional[int] = None

class PurchaseSubscriptionRequest(BaseModel):
    recruiter_id: int
    plan_id: int
    payment_method: str = "Razorpay UPI"
    transaction_id: Optional[str] = None

class ResumeUploadRequest(BaseModel):
    seeker_id: int
    file_name: str
    file_size_kb: int = 250

# -----------------------------------------------------------------------------
# 1. AUTHENTICATION MODULE
# -----------------------------------------------------------------------------

@app.post("/api/auth/login")
def login(req: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    user = cursor.execute(
        "SELECT * FROM users WHERE email = ? AND is_active = 1", (req.email.strip(),)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or inactive account")

    # In demonstration mode, accept the password or sample password
    user_dict = dict(user)
    # Remove password hash from response
    user_dict.pop("password_hash", None)

    # Attach role specific profile details
    if user["role"] == "job_seeker":
        seeker = cursor.execute(
            "SELECT * FROM job_seekers WHERE user_id = ?", (user["user_id"],)
        ).fetchone()
        if seeker:
            user_dict["seeker_id"] = seeker["seeker_id"]
            user_dict["headline"] = seeker["headline"]
            user_dict["qualification"] = seeker["qualification"]
            user_dict["experience_years"] = seeker["experience_years"]
            user_dict["current_location"] = seeker["current_location"]
            user_dict["expected_salary"] = seeker["expected_salary"]
    elif user["role"] == "recruiter":
        recruiter = cursor.execute(
            """SELECT r.*, c.company_name, c.is_verified AS is_company_verified 
               FROM recruiters r 
               JOIN companies c ON r.company_id = c.company_id 
               WHERE r.user_id = ?""", (user["user_id"],)
        ).fetchone()
        if recruiter:
            user_dict["recruiter_id"] = recruiter["recruiter_id"]
            user_dict["company_id"] = recruiter["company_id"]
            user_dict["company_name"] = recruiter["company_name"]
            user_dict["designation"] = recruiter["designation"]
            user_dict["is_company_verified"] = bool(recruiter["is_company_verified"])

            # Check active subscription
            sub = cursor.execute(
                """SELECT rs.*, sp.plan_name, sp.job_posting_limit, sp.candidate_search_limit, sp.featured_jobs_allowed
                   FROM recruiter_subscriptions rs
                   JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
                   WHERE rs.recruiter_id = ? AND rs.status = 'active'
                   ORDER BY rs.subscription_id DESC LIMIT 1""",
                (recruiter["recruiter_id"],)
            ).fetchone()
            if sub:
                user_dict["subscription"] = dict(sub)
            else:
                user_dict["subscription"] = {
                    "plan_name": "Free Starter",
                    "job_posting_limit": 2,
                    "status": "active"
                }

    return {"message": "Login successful", "user": user_dict}

@app.post("/api/auth/register")
def register(req: RegisterRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    # Check existing email
    existing = cursor.execute("SELECT user_id FROM users WHERE email = ?", (req.email.strip(),)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    try:
        # Insert user
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)",
            (req.full_name, req.email.strip(), "$2b$12$HashedPwdDemo", req.phone, req.role)
        )
        user_id = cursor.lastrowid

        if req.role == "job_seeker":
            cursor.execute(
                """INSERT INTO job_seekers (user_id, headline, qualification, experience_years, current_location, expected_salary)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, f"{req.qualification} Professional", req.qualification, req.experience_years, req.current_location, req.expected_salary)
            )
            seeker_id = cursor.lastrowid
            # Create default primary resume
            cursor.execute(
                "INSERT INTO resumes (seeker_id, file_name, file_path, file_size_kb, is_primary) VALUES (?, ?, ?, ?, 1)",
                (seeker_id, f"{req.full_name.replace(' ', '_')}_Resume.pdf", f"/media/resumes/{user_id}_cv.pdf", 210)
            )
        elif req.role == "recruiter":
            # Check or create company
            company_name = req.company_name or "Enterprise Hiring Co."
            company = cursor.execute("SELECT company_id FROM companies WHERE company_name = ?", (company_name,)).fetchone()
            if company:
                company_id = company["company_id"]
            else:
                cursor.execute(
                    "INSERT INTO companies (company_name, industry, location, is_verified) VALUES (?, ?, ?, 1)",
                    (company_name, "Technology", "Bengaluru", 1)
                )
                company_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO recruiters (user_id, company_id, designation, is_verified) VALUES (?, ?, ?, 1)",
                (user_id, company_id, req.designation)
            )
            recruiter_id = cursor.lastrowid

            # Default Free Plan Subscription
            today = date.today()
            end_date = today + timedelta(days=30)
            cursor.execute(
                "INSERT INTO recruiter_subscriptions (recruiter_id, plan_id, start_date, end_date, status) VALUES (?, 1, ?, ?, 'active')",
                (recruiter_id, str(today), str(end_date))
            )

        db.commit()
        return {"message": "Account created successfully. You can now log in.", "user_id": user_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during registration: {str(e)}")

# -----------------------------------------------------------------------------
# 2. JOBS & SEARCH MODULE (WITH CANDIDATE SKILL MATCHING % & HIGH-SPEED CACHING)
# -----------------------------------------------------------------------------

def load_base_jobs(db: sqlite3.Connection):
    cursor = db.cursor()
    query = """
        SELECT 
            j.*,
            c.company_name,
            c.industry,
            c.logo_url,
            c.is_verified AS is_company_verified,
            u.full_name AS recruiter_name,
            (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS applicants_count
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        JOIN recruiters r ON j.recruiter_id = r.recruiter_id
        JOIN users u ON r.user_id = u.user_id
        WHERE j.status = 'open'
        ORDER BY j.is_featured DESC, j.created_at DESC
    """
    jobs = [dict(row) for row in cursor.execute(query).fetchall()]

    job_skills_map = {}
    all_job_skills = cursor.execute("""
        SELECT js.job_id, s.skill_id, s.skill_name, s.category, js.is_required
        FROM job_skills js
        JOIN skills s ON js.skill_id = s.skill_id
    """).fetchall()
    for row in all_job_skills:
        job_skills_map.setdefault(row["job_id"], []).append({
            "skill_id": row["skill_id"],
            "skill_name": row["skill_name"],
            "category": row["category"],
            "is_required": bool(row["is_required"])
        })

    for j in jobs:
        j["required_skills"] = job_skills_map.get(j["job_id"], [])

    return jobs, job_skills_map

@app.get("/api/jobs")
def get_jobs(
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    job_type: Optional[str] = None,
    seeker_id: Optional[int] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    global JOBS_CACHE
    if JOBS_CACHE["base_jobs"] is None:
        JOBS_CACHE["base_jobs"], JOBS_CACHE["job_skills_map"] = load_base_jobs(db)

    base_jobs = JOBS_CACHE["base_jobs"]

    has_filter = bool(keyword or location or (job_type and job_type != "All"))
    if has_filter:
        kw = keyword.lower().strip() if keyword else None
        loc = location.lower().strip() if location else None
        jt = job_type.strip() if (job_type and job_type != "All") else None

        filtered = []
        for j in base_jobs:
            if kw and not (kw in j["job_title"].lower() or kw in j["description"].lower() or kw in j["company_name"].lower()):
                continue
            if loc and not (loc in j["location"].lower()):
                continue
            if jt and j["job_type"] != jt:
                continue
            filtered.append(j)
        jobs = [dict(j) for j in filtered]
    else:
        jobs = [dict(j) for j in base_jobs]

    cand_skill_set = set()
    applied_map = {}
    saved_set = set()

    if seeker_id:
        cursor = db.cursor()
        c_skills = cursor.execute("SELECT skill_id FROM seeker_skills WHERE seeker_id = ?", (seeker_id,)).fetchall()
        cand_skill_set = set(cs["skill_id"] for cs in c_skills)

        c_apps = cursor.execute("SELECT job_id, current_status FROM applications WHERE seeker_id = ?", (seeker_id,)).fetchall()
        applied_map = {ca["job_id"]: ca["current_status"] for ca in c_apps}

        c_saved = cursor.execute("SELECT job_id FROM saved_jobs WHERE seeker_id = ?", (seeker_id,)).fetchall()
        saved_set = set(cs["job_id"] for cs in c_saved)

    for j in jobs:
        req_skills = j.get("required_skills", [])

        if seeker_id:
            req_skill_set = set(s["skill_id"] for s in req_skills)
            if req_skill_set:
                matched = len(cand_skill_set.intersection(req_skill_set))
                pct = round((matched / len(req_skill_set)) * 100, 1)
                j["match_percentage"] = pct
                j["matched_skills_count"] = matched
                j["total_skills_count"] = len(req_skill_set)
            else:
                j["match_percentage"] = 100.0

            jid = j["job_id"]
            j["already_applied"] = jid in applied_map
            j["application_status"] = applied_map.get(jid)
            j["is_saved"] = jid in saved_set
        else:
            j["match_percentage"] = None
            j["already_applied"] = False
            j["is_saved"] = False

    return {"jobs": jobs, "total": len(jobs)}

@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: int, seeker_id: Optional[int] = None, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    row = cursor.execute(
        """SELECT j.*, c.company_name, c.industry, c.website, c.description AS company_desc, 
                  c.location AS company_hq, c.is_verified AS is_company_verified,
                  u.full_name AS recruiter_name, u.email AS recruiter_email
           FROM jobs j
           JOIN companies c ON j.company_id = c.company_id
           JOIN recruiters r ON j.recruiter_id = r.recruiter_id
           JOIN users u ON r.user_id = u.user_id
           WHERE j.job_id = ?""",
        (job_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    job = dict(row)
    # Skills
    skills = cursor.execute(
        """SELECT s.skill_id, s.skill_name, s.category, js.is_required 
           FROM job_skills js JOIN skills s ON js.skill_id = s.skill_id WHERE js.job_id = ?""",
        (job_id,)
    ).fetchall()
    job["required_skills"] = [dict(s) for s in skills]

    if seeker_id:
        applied = cursor.execute(
            "SELECT application_id, current_status FROM applications WHERE job_id = ? AND seeker_id = ?",
            (job_id, seeker_id)
        ).fetchone()
        job["already_applied"] = bool(applied)
        job["application_status"] = applied["current_status"] if applied else None

    return job

# -----------------------------------------------------------------------------
# 3. ONLINE APPLICATIONS & APPLICATION TRACKING MODULE
# -----------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/apply")
def apply_job(job_id: int, req: ApplyJobRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    # Check duplicate application
    existing = cursor.execute(
        "SELECT application_id FROM applications WHERE job_id = ? AND seeker_id = ?",
        (job_id, req.seeker_id)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="You have already submitted an application for this vacancy.")

    try:
        # Insert application
        cursor.execute(
            "INSERT INTO applications (job_id, seeker_id, resume_id, cover_letter, current_status) VALUES (?, ?, ?, ?, 'applied')",
            (job_id, req.seeker_id, req.resume_id, req.cover_letter)
        )
        app_id = cursor.lastrowid

        # Insert tracking milestone
        seeker = cursor.execute("SELECT user_id FROM job_seekers WHERE seeker_id = ?", (req.seeker_id,)).fetchone()
        user_id = seeker["user_id"] if seeker else None
        cursor.execute(
            "INSERT INTO application_tracking (application_id, status, remarks, changed_by_user_id) VALUES (?, 'applied', 'Application successfully submitted by applicant.', ?)",
            (app_id, user_id)
        )

        # Notify Recruiter
        job_info = cursor.execute(
            "SELECT j.job_title, r.user_id AS recruiter_user_id FROM jobs j JOIN recruiters r ON j.recruiter_id = r.recruiter_id WHERE j.job_id = ?",
            (job_id,)
        ).fetchone()
        if job_info:
            cursor.execute(
                "INSERT INTO notifications (user_id, title, message, notification_type) VALUES (?, 'New Job Application', ?, 'application')",
                (job_info["recruiter_user_id"], f"A new candidate applied for: {job_info['job_title']}")
            )

        db.commit()
        invalidate_jobs_cache()
        return {"message": "Application submitted successfully!", "application_id": app_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit application: {str(e)}")

@app.get("/api/seeker/{seeker_id}/applications")
def get_seeker_applications(seeker_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    apps = cursor.execute(
        """SELECT a.*, j.job_title, j.location, j.salary_min, j.salary_max, j.job_type,
                  c.company_name, c.is_verified AS is_company_verified, r.file_name AS resume_file
           FROM applications a
           JOIN jobs j ON a.job_id = j.job_id
           JOIN companies c ON j.company_id = c.company_id
           JOIN resumes r ON a.resume_id = r.resume_id
           WHERE a.seeker_id = ?
           ORDER BY a.applied_at DESC""",
        (seeker_id,)
    ).fetchall()

    result = []
    for a in apps:
        app_dict = dict(a)
        # Fetch tracking milestones history
        timeline = cursor.execute(
            """SELECT at.*, u.full_name AS changed_by_name 
               FROM application_tracking at 
               LEFT JOIN users u ON at.changed_by_user_id = u.user_id 
               WHERE at.application_id = ? 
               ORDER BY at.changed_at ASC""",
            (a["application_id"],)
        ).fetchall()
        app_dict["timeline"] = [dict(t) for t in timeline]
        result.append(app_dict)

    return {"applications": result, "count": len(result)}

# -----------------------------------------------------------------------------
# 4. RECRUITER MODULE & VACANCY MANAGEMENT (WITH PLAN LIMIT ENFORCEMENT)
# -----------------------------------------------------------------------------

@app.get("/api/recruiter/{recruiter_id}/dashboard")
def get_recruiter_dashboard(recruiter_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    # Check plan quota
    sub = cursor.execute(
        """SELECT rs.*, sp.plan_name, sp.job_posting_limit, sp.candidate_search_limit, sp.featured_jobs_allowed
           FROM recruiter_subscriptions rs
           JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
           WHERE rs.recruiter_id = ? AND rs.status = 'active'
           ORDER BY rs.subscription_id DESC LIMIT 1""",
        (recruiter_id,)
    ).fetchone()

    plan_limit = sub["job_posting_limit"] if sub else 2
    plan_name = sub["plan_name"] if sub else "Free Starter"
    is_featured_allowed = bool(sub["featured_jobs_allowed"]) if sub else False

    # Jobs count
    jobs = cursor.execute(
        """SELECT j.*, COUNT(a.application_id) AS applicants_count 
           FROM jobs j 
           LEFT JOIN applications a ON j.job_id = a.job_id 
           WHERE j.recruiter_id = ? 
           GROUP BY j.job_id 
           ORDER BY j.created_at DESC""",
        (recruiter_id,)
    ).fetchall()

    total_posted = len(jobs)
    active_jobs = sum(1 for j in jobs if j["status"] == "open")

    # Applicants count
    total_applicants = cursor.execute(
        """SELECT COUNT(a.application_id) 
           FROM applications a 
           JOIN jobs j ON a.job_id = j.job_id 
           WHERE j.recruiter_id = ?""",
        (recruiter_id,)
    ).fetchone()[0]

    return {
        "recruiter_id": recruiter_id,
        "subscription": {
            "plan_name": plan_name,
            "job_posting_limit": plan_limit,
            "jobs_posted": active_jobs,
            "jobs_remaining": max(0, plan_limit - active_jobs),
            "is_quota_exhausted": active_jobs >= plan_limit,
            "featured_jobs_allowed": is_featured_allowed,
            "end_date": sub["end_date"] if sub else None
        },
        "stats": {
            "total_jobs_posted": total_posted,
            "active_jobs": active_jobs,
            "total_applicants": total_applicants
        },
        "jobs": [dict(j) for j in jobs]
    }

@app.post("/api/recruiter/post-job")
def post_job(req: PostJobRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    # Check plan quota
    sub = cursor.execute(
        """SELECT sp.job_posting_limit, sp.featured_jobs_allowed 
           FROM recruiter_subscriptions rs
           JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
           WHERE rs.recruiter_id = ? AND rs.status = 'active'
           ORDER BY rs.subscription_id DESC LIMIT 1""",
        (req.recruiter_id,)
    ).fetchone()

    plan_limit = sub["job_posting_limit"] if sub else 2
    featured_allowed = bool(sub["featured_jobs_allowed"]) if sub else False

    active_count = cursor.execute(
        "SELECT COUNT(*) FROM jobs WHERE recruiter_id = ? AND status = 'open'",
        (req.recruiter_id,)
    ).fetchone()[0]

    if active_count >= plan_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Subscription posting quota exhausted! Your active plan allows maximum {plan_limit} active jobs. Please upgrade to Recruiter Premium or Enterprise."
        )

    try:
        # Check if user selected featured but not allowed
        is_featured = req.is_featured and featured_allowed

        cursor.execute(
            """INSERT INTO jobs (recruiter_id, company_id, job_title, job_type, experience_level, location, salary_min, salary_max, description, requirements, open_vacancies, is_featured, deadline, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
            (req.recruiter_id, req.company_id, req.job_title, req.job_type, req.experience_level, req.location, req.salary_min, req.salary_max, req.description, req.requirements, req.open_vacancies, int(is_featured), req.deadline)
        )
        job_id = cursor.lastrowid

        # Insert skill mappings
        for sid in req.skill_ids:
            cursor.execute("INSERT OR IGNORE INTO job_skills (job_id, skill_id, is_required) VALUES (?, ?, 1)", (job_id, sid))

        db.commit()
        invalidate_jobs_cache()
        return {"message": "Job vacancy published successfully!", "job_id": job_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to post job: {str(e)}")

@app.get("/api/recruiter/jobs/{job_id}/applicants")
def get_job_applicants(job_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    applicants = cursor.execute(
        """SELECT a.*, u.full_name, u.email, u.phone, 
                  js.qualification, js.experience_years, js.current_location, js.expected_salary,
                  r.file_name AS resume_file, r.file_path AS resume_path
           FROM applications a
           JOIN job_seekers js ON a.seeker_id = js.seeker_id
           JOIN users u ON js.user_id = u.user_id
           JOIN resumes r ON a.resume_id = r.resume_id
           WHERE a.job_id = ?
           ORDER BY a.applied_at DESC""",
        (job_id,)
    ).fetchall()

    return {"applicants": [dict(ap) for ap in applicants], "count": len(applicants)}

@app.post("/api/recruiter/applications/{application_id}/accept")
def accept_application(application_id: int, req: AcceptApplicationRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    app_record = cursor.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application record not found")

    try:
        cursor.execute(
            "UPDATE applications SET current_status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE application_id = ?",
            (application_id,)
        )

        details = []
        if req.offered_ctc:
            details.append(f"Offered CTC: ₹{req.offered_ctc:,.2f}")
        if req.joining_date:
            details.append(f"Joining Date: {req.joining_date}")

        detail_text = f" [{', '.join(details)}]" if details else ""
        remarks = f"🎉 Application Accepted & Offer Released: {req.remarks or 'Candidate selected for the position.'}{detail_text}"

        cursor.execute(
            "INSERT INTO application_tracking (application_id, status, remarks, changed_by_user_id) VALUES (?, 'accepted', ?, ?)",
            (application_id, remarks, req.changed_by_user_id)
        )

        seeker = cursor.execute(
            """SELECT js.user_id, j.job_title, c.company_name 
               FROM applications a 
               JOIN job_seekers js ON a.seeker_id = js.seeker_id 
               JOIN jobs j ON a.job_id = j.job_id 
               JOIN companies c ON j.company_id = c.company_id 
               WHERE a.application_id = ?""",
            (application_id,)
        ).fetchone()

        if seeker:
            notif_msg = f"🎉 Congratulations! Your application for '{seeker['job_title']}' at {seeker['company_name']} has been ACCEPTED. Official job offer extended!"
            cursor.execute(
                "INSERT INTO notifications (user_id, title, message, notification_type) VALUES (?, '🎉 Job Application Accepted!', ?, 'application')",
                (seeker["user_id"], notif_msg)
            )

        db.commit()
        invalidate_jobs_cache()
        return {
            "message": "Candidate application accepted and employment offer extended!",
            "application_id": application_id,
            "status": "accepted",
            "remarks": remarks
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to accept application: {str(e)}")

@app.post("/api/recruiter/applications/{application_id}/reject")
def reject_application(application_id: int, req: RejectApplicationRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    app_record = cursor.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application record not found")

    try:
        cursor.execute(
            "UPDATE applications SET current_status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE application_id = ?",
            (application_id,)
        )

        remarks = f"Application Rejected ({req.reason}): {req.remarks or 'Thank you for your interest. We wish you the best in your career pursuits.'}"

        cursor.execute(
            "INSERT INTO application_tracking (application_id, status, remarks, changed_by_user_id) VALUES (?, 'rejected', ?, ?)",
            (application_id, remarks, req.changed_by_user_id)
        )

        seeker = cursor.execute(
            """SELECT js.user_id, j.job_title, c.company_name 
               FROM applications a 
               JOIN job_seekers js ON a.seeker_id = js.seeker_id 
               JOIN jobs j ON a.job_id = j.job_id 
               JOIN companies c ON j.company_id = c.company_id 
               WHERE a.application_id = ?""",
            (application_id,)
        ).fetchone()

        if seeker:
            notif_msg = f"Update regarding '{seeker['job_title']}' at {seeker['company_name']}: Your application was not selected at this stage. Thank you for applying."
            cursor.execute(
                "INSERT INTO notifications (user_id, title, message, notification_type) VALUES (?, 'Application Update: Not Selected', ?, 'application')",
                (seeker["user_id"], notif_msg)
            )

        db.commit()
        invalidate_jobs_cache()
        return {
            "message": "Candidate application marked as rejected.",
            "application_id": application_id,
            "status": "rejected",
            "remarks": remarks
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reject application: {str(e)}")

@app.put("/api/recruiter/applications/{application_id}/status")
def update_application_status(application_id: int, req: UpdateStatusRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    app_record = cursor.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application record not found")

    old_status = app_record["current_status"]
    new_status = req.status

    try:
        cursor.execute("UPDATE applications SET current_status = ?, updated_at = CURRENT_TIMESTAMP WHERE application_id = ?", (new_status, application_id))
        
        remarks = req.remarks or f"Status updated from {old_status} to {new_status} by hiring manager."
        cursor.execute(
            "INSERT INTO application_tracking (application_id, status, remarks, changed_by_user_id) VALUES (?, ?, ?, ?)",
            (application_id, new_status, remarks, req.changed_by_user_id)
        )

        seeker = cursor.execute(
            """SELECT js.user_id, j.job_title 
               FROM applications a 
               JOIN job_seekers js ON a.seeker_id = js.seeker_id 
               JOIN jobs j ON a.job_id = j.job_id 
               WHERE a.application_id = ?""",
            (application_id,)
        ).fetchone()

        if seeker:
            if new_status in ('accepted', 'offered'):
                title = "🎉 Job Application Accepted!"
                msg = f"Congratulations! Your application for '{seeker['job_title']}' has been ACCEPTED / OFFER EXTENDED!"
            elif new_status == 'rejected':
                title = "Application Update: Not Selected"
                msg = f"Your application for '{seeker['job_title']}' has not been selected."
            else:
                title = "Application Status Updated"
                msg = f"Your application for '{seeker['job_title']}' has moved to: {new_status.replace('_', ' ').title()}"

            cursor.execute(
                "INSERT INTO notifications (user_id, title, message, notification_type) VALUES (?, ?, ?, 'application')",
                (seeker["user_id"], title, msg)
            )

        db.commit()
        invalidate_jobs_cache()
        return {"message": f"Status updated to '{new_status}' successfully", "application_id": application_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")

# -----------------------------------------------------------------------------
# 5. RECRUITER PREMIUM SUBSCRIPTIONS & RAZORPAY PAYMENT SIMULATION
# -----------------------------------------------------------------------------

@app.get("/api/subscriptions/plans")
def get_plans(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    plans = cursor.execute("SELECT * FROM subscription_plans ORDER BY price ASC").fetchall()
    return {"plans": [dict(p) for p in plans]}

@app.post("/api/subscriptions/purchase")
def purchase_subscription(req: PurchaseSubscriptionRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    plan = cursor.execute("SELECT * FROM subscription_plans WHERE plan_id = ?", (req.plan_id,)).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail="Selected subscription plan does not exist")

    try:
        # Expire existing subscription
        cursor.execute(
            "UPDATE recruiter_subscriptions SET status = 'expired' WHERE recruiter_id = ? AND status = 'active'",
            (req.recruiter_id,)
        )

        # Insert new subscription
        start_date = date.today()
        end_date = start_date + timedelta(days=plan["duration_days"])
        cursor.execute(
            "INSERT INTO recruiter_subscriptions (recruiter_id, plan_id, start_date, end_date, status, auto_renew) VALUES (?, ?, ?, ?, 'active', 1)",
            (req.recruiter_id, req.plan_id, str(start_date), str(end_date))
        )
        sub_id = cursor.lastrowid

        # Record payment
        txn_id = req.transaction_id or f"pay_RZP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute(
            "INSERT INTO payments (subscription_id, amount, payment_method, transaction_id, payment_status) VALUES (?, ?, ?, ?, 'success')",
            (sub_id, plan["price"], req.payment_method, txn_id)
        )
        payment_id = cursor.lastrowid

        # Generate official Invoice with 18% GST
        tax = round(plan["price"] * 0.18, 2)
        total = round(plan["price"] + tax, 2)
        inv_no = f"INV-{datetime.now().year}-{str(payment_id).zfill(5)}"
        cursor.execute(
            "INSERT INTO invoices (payment_id, invoice_number, tax_amount, total_amount, issued_date) VALUES (?, ?, ?, ?, ?)",
            (payment_id, inv_no, tax, total, str(start_date))
        )

        # Send notification to recruiter
        recruiter = cursor.execute("SELECT user_id FROM recruiters WHERE recruiter_id = ?", (req.recruiter_id,)).fetchone()
        if recruiter:
            cursor.execute(
                "INSERT INTO notifications (user_id, title, message, notification_type) VALUES (?, 'Subscription Activated', ?, 'subscription')",
                (recruiter["user_id"], f"Your {plan['plan_name']} is now active! Invoice #{inv_no} issued.")
            )

        db.commit()
        return {
            "message": "Payment successful! Subscription upgraded.",
            "subscription_id": sub_id,
            "invoice_number": inv_no,
            "transaction_id": txn_id,
            "plan_name": plan["plan_name"],
            "amount_paid": total
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process subscription purchase: {str(e)}")

@app.get("/api/invoices")
def get_invoices(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    rows = cursor.execute(
        """SELECT inv.*, p.transaction_id, p.payment_method, p.payment_date,
                  sp.plan_name, u.full_name AS recruiter_name, c.company_name
           FROM invoices inv
           JOIN payments p ON inv.payment_id = p.payment_id
           JOIN recruiter_subscriptions rs ON p.subscription_id = rs.subscription_id
           JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
           JOIN recruiters r ON rs.recruiter_id = r.recruiter_id
           JOIN users u ON r.user_id = u.user_id
           JOIN companies c ON r.company_id = c.company_id
           ORDER BY inv.invoice_id DESC"""
    ).fetchall()
    return {"invoices": [dict(r) for r in rows]}

# -----------------------------------------------------------------------------
# 6. RESUME & SAVED JOBS MODULE
# -----------------------------------------------------------------------------

@app.get("/api/seeker/{seeker_id}/resumes")
def get_resumes(seeker_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    rows = cursor.execute("SELECT * FROM resumes WHERE seeker_id = ? ORDER BY is_primary DESC, uploaded_at DESC", (seeker_id,)).fetchall()
    return {"resumes": [dict(r) for r in rows]}

@app.post("/api/seeker/resumes")
def upload_resume(req: ResumeUploadRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO resumes (seeker_id, file_name, file_path, file_size_kb, is_primary) VALUES (?, ?, ?, ?, 0)",
        (req.seeker_id, req.file_name, f"/media/resumes/{req.file_name}", req.file_size_kb)
    )
    db.commit()
    return {"message": "Resume uploaded successfully"}

@app.post("/api/seeker/{seeker_id}/saved-jobs/{job_id}")
def toggle_saved_job(seeker_id: int, job_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    existing = cursor.execute("SELECT saved_id FROM saved_jobs WHERE seeker_id = ? AND job_id = ?", (seeker_id, job_id)).fetchone()
    if existing:
        cursor.execute("DELETE FROM saved_jobs WHERE saved_id = ?", (existing["saved_id"],))
        db.commit()
        return {"saved": False, "message": "Job removed from bookmarks"}
    else:
        cursor.execute("INSERT INTO saved_jobs (seeker_id, job_id) VALUES (?, ?)", (seeker_id, job_id))
        db.commit()
        return {"saved": True, "message": "Job saved to bookmarks"}

@app.get("/api/seeker/{seeker_id}/saved-jobs")
def get_saved_jobs(seeker_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    rows = cursor.execute(
        """SELECT j.*, c.company_name, c.is_verified AS is_company_verified, sj.saved_at 
           FROM saved_jobs sj 
           JOIN jobs j ON sj.job_id = j.job_id 
           JOIN companies c ON j.company_id = c.company_id 
           WHERE sj.seeker_id = ? 
           ORDER BY sj.saved_at DESC""",
        (seeker_id,)
    ).fetchall()
    return {"saved_jobs": [dict(r) for r in rows]}

# -----------------------------------------------------------------------------
# 7. ADMIN, NOTIFICATIONS & SYSTEM MODULE
# -----------------------------------------------------------------------------

@app.get("/api/admin/stats")
def get_admin_stats(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    stats = {
        "job_seekers": cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'job_seeker'").fetchone()[0],
        "recruiters": cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'recruiter'").fetchone()[0],
        "companies": cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
        "active_jobs": cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'open'").fetchone()[0],
        "applications": cursor.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
        "active_premium": cursor.execute("SELECT COUNT(*) FROM recruiter_subscriptions WHERE status = 'active' AND plan_id > 1").fetchone()[0],
        "gross_revenue": cursor.execute("SELECT COALESCE(SUM(total_amount), 0.0) FROM invoices").fetchone()[0]
    }
    
    # Skills demand
    skills = cursor.execute(
        """SELECT s.skill_name, COUNT(js.job_id) AS demand 
           FROM skills s 
           JOIN job_skills js ON s.skill_id = js.skill_id 
           GROUP BY s.skill_id, s.skill_name 
           ORDER BY demand DESC LIMIT 6"""
    ).fetchall()
    stats["top_skills"] = [dict(s) for s in skills]

    # Status distribution
    funnel = cursor.execute(
        "SELECT current_status, COUNT(*) AS count FROM applications GROUP BY current_status"
    ).fetchall()
    stats["funnel"] = [dict(f) for f in funnel]

    return stats

@app.get("/api/notifications/{user_id}")
def get_notifications(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    notifs = cursor.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY is_read ASC, created_at DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    return {"notifications": [dict(n) for n in notifs]}

@app.put("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE notification_id = ?", (notification_id,))
    db.commit()
    return {"message": "Notification marked as read"}

@app.get("/api/skills")
def get_all_skills(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    skills = cursor.execute("SELECT * FROM skills ORDER BY category, skill_name").fetchall()
    return {"skills": [dict(s) for s in skills]}

class CustomQueryRequest(BaseModel):
    query: str

@app.post("/api/query")
def execute_custom_query(req: CustomQueryRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    # Remove multi-line comments /* ... */ and single line comments -- ...
    cleaned_query = req.query.strip()
    # Strip block comments
    cleaned_query = re.sub(r'/\*.*?\*/', '', cleaned_query, flags=re.DOTALL)
    # Strip line comments to find the first executable SQL keyword
    non_comment_lines = []
    for line in cleaned_query.splitlines():
        stripped_line = line.strip()
        if not stripped_line.startswith('--'):
            non_comment_lines.append(stripped_line)
    
    first_stmt = ' '.join(non_comment_lines).strip()
    first_word = first_stmt.split()[0].upper() if first_stmt.split() else ''
    
    allowed_verbs = ('SELECT', 'WITH', 'EXPLAIN', 'PRAGMA', 'SHOW', 'DESCRIBE')
    if first_word not in allowed_verbs:
        raise HTTPException(
            status_code=400, 
            detail=f"Only SELECT or analytical queries are permitted in the studio (detected statement starting with '{first_word}')."
        )
    try:
        rows = cursor.execute(req.query).fetchall()
        columns = [col[0] for col in cursor.description] if cursor.description else []
        return {"columns": columns, "rows": [dict(r) for r in rows], "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tables")
def get_tables_list(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    rows = cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return {"tables": [r["name"] for r in rows]}

@app.get("/api/table")
def get_table_content(name: str = "jobs", db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    valid = [r["name"] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()]
    if name not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {name}")
    rows = cursor.execute(f"SELECT * FROM {name} LIMIT 100").fetchall()
    columns = [col[0] for col in cursor.description] if cursor.description else []
    return {"table": name, "columns": columns, "rows": [dict(r) for r in rows], "count": len(rows)}

# Serve the static frontend index.html
@app.get("/")
def serve_home():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))
