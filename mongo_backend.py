"""FastAPI application for the job portal, backed by MongoDB collections."""

import os
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pymongo.errors import (
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)

from mongo_store import COLLECTION_KEYS, get_database, next_id

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(
    title="Online Job Portal API",
    description="REST API for the Online Job Portal backed by MongoDB",
    version="3.0.0",
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    try:
        return get_database()
    except OperationFailure as exc:
        if exc.code != 18:
            raise HTTPException(
                status_code=503,
                detail=(
                    "MongoDB request failed. Check the Atlas database user, "
                    "connection string, and Network Access settings."
                ),
            ) from exc
        raise HTTPException(
            status_code=503,
            detail=(
                "MongoDB Atlas rejected the database credentials. Verify the Atlas "
                "database user, password, and URL-encoding of special password characters."
            ),
        ) from exc
    except ServerSelectionTimeoutError as exc:
        if not os.environ.get("MONGODB_URI"):
            detail = (
                "MONGODB_URI is not configured. The app is trying local MongoDB "
                "at 127.0.0.1:27017. Add your Atlas connection string to the "
                "project .env file, or start a local MongoDB server."
            )
        else:
            detail = (
                "Cannot reach MongoDB Atlas. Verify the connection string and "
                "add your current IP address in Atlas Network Access."
            )
        raise HTTPException(
            status_code=503,
            detail=detail,
        ) from exc
    except PyMongoError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "MongoDB request failed. Check the Atlas database user, connection "
                "string, and Network Access settings."
            ),
        ) from exc


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def documents(db, collection, query=None, sort=None, limit=0):
    cursor = db[collection].find(query or {}, {"_id": 0})
    if sort:
        cursor = cursor.sort(sort)
    if limit:
        cursor = cursor.limit(limit)
    return list(cursor)


def find_by_id(db, collection, key, value):
    return db[collection].find_one({key: value}, {"_id": 0})


def insert_document(db, collection, values):
    key = COLLECTION_KEYS[collection]
    record = dict(values)
    if key:
        record[key] = next_id(db, collection)
    result = db[collection].insert_one(record)
    return record.get(key, result.inserted_id)


def add_notification(db, user_id, title, message, notification_type):
    insert_document(db, "notifications", {
        "user_id": user_id,
        "title": title,
        "message": message,
        "notification_type": notification_type,
        "is_read": 0,
        "created_at": now_text(),
    })


def get_subscription(db, recruiter_id):
    subscriptions = documents(
        db, "recruiter_subscriptions",
        {"recruiter_id": recruiter_id, "status": "active"},
        [("subscription_id", -1)],
        1,
    )
    if not subscriptions:
        return None
    subscription = subscriptions[0]
    plan = find_by_id(db, "subscription_plans", "plan_id", subscription["plan_id"])
    if not plan:
        return None
    return {**subscription, **{
        field: plan[field]
        for field in ("plan_name", "job_posting_limit", "candidate_search_limit", "featured_jobs_allowed")
        if field in plan
    }}


def enrich_job(db, job, include_recruiter=False):
    result = dict(job)
    company = find_by_id(db, "companies", "company_id", job.get("company_id")) or {}
    recruiter = find_by_id(db, "recruiters", "recruiter_id", job.get("recruiter_id")) or {}
    user = find_by_id(db, "users", "user_id", recruiter.get("user_id")) or {}
    result.update({
        "company_name": company.get("company_name"),
        "industry": company.get("industry"),
        "logo_url": company.get("logo_url"),
        "is_company_verified": company.get("is_verified", 0),
        "applicants_count": db.applications.count_documents({"job_id": job.get("job_id")}),
        "required_skills": [],
    })
    if include_recruiter:
        result.update({
            "recruiter_name": user.get("full_name"),
            "recruiter_email": user.get("email"),
        })
    for relation in documents(db, "job_skills", {"job_id": job.get("job_id")}):
        skill = find_by_id(db, "skills", "skill_id", relation["skill_id"])
        if skill:
            result["required_skills"].append({
                "skill_id": skill["skill_id"],
                "skill_name": skill["skill_name"],
                "category": skill.get("category"),
                "is_required": relation.get("is_required", 0),
            })
    return result


def load_job_listings(db):
    companies = {item["company_id"]: item for item in documents(db, "companies")}
    recruiters = {item["recruiter_id"]: item for item in documents(db, "recruiters")}
    users = {item["user_id"]: item for item in documents(db, "users")}
    skills = {item["skill_id"]: item for item in documents(db, "skills")}
    applicant_counts = {}
    for application in documents(db, "applications"):
        job_id = application.get("job_id")
        applicant_counts[job_id] = applicant_counts.get(job_id, 0) + 1
    skills_by_job = {}
    for relation in documents(db, "job_skills"):
        skill = skills.get(relation.get("skill_id"))
        if skill:
            skills_by_job.setdefault(relation["job_id"], []).append({
                "skill_id": skill["skill_id"],
                "skill_name": skill["skill_name"],
                "category": skill.get("category"),
                "is_required": relation.get("is_required", 0),
            })

    listings = []
    for job in documents(
        db, "jobs", {"status": "open"}, [("is_featured", -1), ("created_at", -1)]
    ):
        company = companies.get(job.get("company_id"), {})
        recruiter = recruiters.get(job.get("recruiter_id"), {})
        user = users.get(recruiter.get("user_id"), {})
        listings.append({
            **job,
            "company_name": company.get("company_name"),
            "industry": company.get("industry"),
            "logo_url": company.get("logo_url"),
            "is_company_verified": company.get("is_verified", 0),
            "recruiter_name": user.get("full_name"),
            "applicants_count": applicant_counts.get(job.get("job_id"), 0),
            "required_skills": skills_by_job.get(job.get("job_id"), []),
        })
    return listings


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    phone: Optional[str] = ""
    role: str
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
    skill_ids: List[int] = Field(default_factory=list)


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


class CustomQueryRequest(BaseModel):
    query: str


def is_exact_filter(value):
    if isinstance(value, dict):
        return all(not key.startswith("$") and is_exact_filter(item) for key, item in value.items())
    if isinstance(value, list):
        return all(is_exact_filter(item) for item in value)
    return value is None or isinstance(value, (str, int, float, bool))


@app.get("/api/health")
def health_check(db=Depends(get_db)):
    return {"status": "ok", "database": db.name}


@app.post("/api/auth/login")
def login(req: LoginRequest, db=Depends(get_db)):
    user = db.users.find_one(
        {"email": req.email.strip(), "is_active": 1}, {"_id": 0}
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or inactive account")
    user.pop("password_hash", None)
    if user["role"] == "job_seeker":
        seeker = db.job_seekers.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if seeker:
            user.update({key: seeker.get(key) for key in (
                "seeker_id", "headline", "qualification", "experience_years",
                "current_location", "expected_salary",
            )})
    elif user["role"] == "recruiter":
        recruiter = db.recruiters.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if recruiter:
            company = find_by_id(db, "companies", "company_id", recruiter["company_id"]) or {}
            user.update({
                "recruiter_id": recruiter["recruiter_id"],
                "company_id": recruiter["company_id"],
                "company_name": company.get("company_name"),
                "designation": recruiter.get("designation"),
                "is_company_verified": bool(company.get("is_verified")),
            })
            subscription = get_subscription(db, recruiter["recruiter_id"])
            user["subscription"] = subscription or {
                "plan_name": "Free Starter", "job_posting_limit": 2, "status": "active"
            }
    return {"message": "Login successful", "user": user}


@app.post("/api/auth/register")
def register(req: RegisterRequest, db=Depends(get_db)):
    email = req.email.strip()
    if db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    try:
        user_id = insert_document(db, "users", {
            "full_name": req.full_name, "email": email,
            "password_hash": "$2b$12$HashedPwdDemo", "phone": req.phone,
            "role": req.role, "is_active": 1, "created_at": now_text(),
            "updated_at": now_text(),
        })
        if req.role == "job_seeker":
            seeker_id = insert_document(db, "job_seekers", {
                "user_id": user_id, "headline": f"{req.qualification} Professional",
                "qualification": req.qualification, "experience_years": req.experience_years,
                "current_location": req.current_location, "expected_salary": req.expected_salary,
                "created_at": now_text(), "updated_at": now_text(),
            })
            insert_document(db, "resumes", {
                "seeker_id": seeker_id,
                "file_name": f"{req.full_name.replace(' ', '_')}_Resume.pdf",
                "file_path": f"/media/resumes/{user_id}_cv.pdf",
                "file_size_kb": 210, "is_primary": 1, "uploaded_at": now_text(),
            })
        elif req.role == "recruiter":
            company_name = req.company_name or "Enterprise Hiring Co."
            company = db.companies.find_one({"company_name": company_name}, {"_id": 0})
            company_id = company["company_id"] if company else insert_document(
                db, "companies", {
                    "company_name": company_name, "industry": "Technology",
                    "location": "Bengaluru", "is_verified": 1,
                }
            )
            recruiter_id = insert_document(db, "recruiters", {
                "user_id": user_id, "company_id": company_id,
                "designation": req.designation, "is_verified": 1,
            })
            today = date.today()
            insert_document(db, "recruiter_subscriptions", {
                "recruiter_id": recruiter_id, "plan_id": 1,
                "start_date": str(today), "end_date": str(today + timedelta(days=30)),
                "status": "active",
            })
        return {"message": "Account created successfully. You can now log in.", "user_id": user_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error during registration: {exc}") from exc


@app.get("/api/jobs")
def get_jobs(
    keyword: Optional[str] = None, location: Optional[str] = None,
    job_type: Optional[str] = None, seeker_id: Optional[int] = None,
    db=Depends(get_db),
):
    jobs = load_job_listings(db)
    if keyword:
        term = keyword.strip().lower()
        jobs = [job for job in jobs if term in (job.get("job_title") or "").lower()
                or term in (job.get("description") or "").lower()
                or term in (job.get("company_name") or "").lower()]
    if location:
        term = location.strip().lower()
        jobs = [job for job in jobs if term in (job.get("location") or "").lower()]
    if job_type and job_type != "All":
        jobs = [job for job in jobs if job.get("job_type") == job_type.strip()]

    candidate_skills = {
        item["skill_id"] for item in documents(db, "seeker_skills", {"seeker_id": seeker_id})
    } if seeker_id else set()
    applications = {
        item["job_id"]: item["current_status"]
        for item in documents(db, "applications", {"seeker_id": seeker_id})
    } if seeker_id else {}
    saved = {
        item["job_id"] for item in documents(db, "saved_jobs", {"seeker_id": seeker_id})
    } if seeker_id else set()
    for job in jobs:
        skills = job["required_skills"]
        if seeker_id:
            skill_ids = {skill["skill_id"] for skill in skills}
            matched = len(candidate_skills & skill_ids)
            job["match_percentage"] = round(matched / len(skill_ids) * 100, 1) if skill_ids else 100.0
            job["matched_skills_count"] = matched
            job["total_skills_count"] = len(skill_ids)
            job["already_applied"] = job["job_id"] in applications
            job["application_status"] = applications.get(job["job_id"])
            job["is_saved"] = job["job_id"] in saved
        else:
            job.update({"match_percentage": None, "already_applied": False, "is_saved": False})
    return {"jobs": jobs, "total": len(jobs)}


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: int, seeker_id: Optional[int] = None, db=Depends(get_db)):
    job = find_by_id(db, "jobs", "job_id", job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    result = enrich_job(db, job, include_recruiter=True)
    company = find_by_id(db, "companies", "company_id", job["company_id"]) or {}
    result.update({
        "website": company.get("website"),
        "company_desc": company.get("description"),
        "company_hq": company.get("location"),
    })
    if seeker_id:
        application = db.applications.find_one(
            {"job_id": job_id, "seeker_id": seeker_id}, {"_id": 0}
        )
        result["already_applied"] = bool(application)
        result["application_status"] = application.get("current_status") if application else None
    return result


@app.post("/api/jobs/{job_id}/apply")
def apply_job(job_id: int, req: ApplyJobRequest, db=Depends(get_db)):
    if not find_by_id(db, "jobs", "job_id", job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    if db.applications.find_one({"job_id": job_id, "seeker_id": req.seeker_id}):
        raise HTTPException(status_code=400, detail="You have already submitted an application for this vacancy.")
    app_id = insert_document(db, "applications", {
        "job_id": job_id, "seeker_id": req.seeker_id, "resume_id": req.resume_id,
        "cover_letter": req.cover_letter, "current_status": "applied",
        "applied_at": now_text(), "updated_at": now_text(),
    })
    seeker = find_by_id(db, "job_seekers", "seeker_id", req.seeker_id)
    insert_document(db, "application_tracking", {
        "application_id": app_id, "status": "applied",
        "remarks": "Application successfully submitted by applicant.",
        "changed_by_user_id": seeker.get("user_id") if seeker else None,
        "changed_at": now_text(),
    })
    job = find_by_id(db, "jobs", "job_id", job_id)
    recruiter = find_by_id(db, "recruiters", "recruiter_id", job["recruiter_id"]) if job else None
    if recruiter:
        add_notification(
            db, recruiter["user_id"], "New Job Application",
            f"A new candidate applied for: {job['job_title']}", "application",
        )
    return {"message": "Application submitted successfully!", "application_id": app_id}


@app.get("/api/seeker/{seeker_id}/applications")
def get_seeker_applications(seeker_id: int, db=Depends(get_db)):
    result = []
    apps = documents(db, "applications", {"seeker_id": seeker_id}, [("applied_at", -1)])
    for application in apps:
        job = find_by_id(db, "jobs", "job_id", application["job_id"]) or {}
        company = find_by_id(db, "companies", "company_id", job.get("company_id")) or {}
        resume = find_by_id(db, "resumes", "resume_id", application.get("resume_id")) or {}
        item = {
            **application, "job_title": job.get("job_title"), "location": job.get("location"),
            "salary_min": job.get("salary_min"), "salary_max": job.get("salary_max"),
            "job_type": job.get("job_type"), "company_name": company.get("company_name"),
            "is_company_verified": company.get("is_verified", 0),
            "resume_file": resume.get("file_name"),
        }
        timeline = documents(
            db, "application_tracking", {"application_id": application["application_id"]},
            [("changed_at", 1)],
        )
        for event in timeline:
            user = find_by_id(db, "users", "user_id", event.get("changed_by_user_id"))
            if user:
                event["changed_by_name"] = user.get("full_name")
        item["timeline"] = timeline
        result.append(item)
    return {"applications": result, "count": len(result)}


@app.get("/api/recruiter/{recruiter_id}/dashboard")
def get_recruiter_dashboard(recruiter_id: int, db=Depends(get_db)):
    subscription = get_subscription(db, recruiter_id)
    plan_limit = subscription.get("job_posting_limit", 2) if subscription else 2
    jobs = documents(db, "jobs", {"recruiter_id": recruiter_id}, [("created_at", -1)])
    for job in jobs:
        job["applicants_count"] = db.applications.count_documents({"job_id": job["job_id"]})
    active_jobs = sum(job.get("status") == "open" for job in jobs)
    applicants = sum(
        db.applications.count_documents({"job_id": job["job_id"]}) for job in jobs
    )
    return {
        "recruiter_id": recruiter_id,
        "subscription": {
            "plan_name": subscription.get("plan_name", "Free Starter") if subscription else "Free Starter",
            "job_posting_limit": plan_limit, "jobs_posted": active_jobs,
            "jobs_remaining": max(0, plan_limit - active_jobs),
            "is_quota_exhausted": active_jobs >= plan_limit,
            "featured_jobs_allowed": bool(subscription.get("featured_jobs_allowed")) if subscription else False,
            "end_date": subscription.get("end_date") if subscription else None,
        },
        "stats": {
            "total_jobs_posted": len(jobs), "active_jobs": active_jobs,
            "total_applicants": applicants,
        },
        "jobs": jobs,
    }


@app.post("/api/recruiter/post-job")
def post_job(req: PostJobRequest, db=Depends(get_db)):
    subscription = get_subscription(db, req.recruiter_id)
    limit = subscription.get("job_posting_limit", 2) if subscription else 2
    featured_allowed = bool(subscription.get("featured_jobs_allowed")) if subscription else False
    active_count = db.jobs.count_documents({"recruiter_id": req.recruiter_id, "status": "open"})
    if active_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Subscription posting quota exhausted! Your active plan allows maximum {limit} active jobs. Please upgrade to Recruiter Premium or Enterprise.",
        )
    job_id = insert_document(db, "jobs", {
        "recruiter_id": req.recruiter_id, "company_id": req.company_id,
        "job_title": req.job_title, "job_type": req.job_type,
        "experience_level": req.experience_level, "location": req.location,
        "salary_min": req.salary_min, "salary_max": req.salary_max,
        "description": req.description, "requirements": req.requirements,
        "open_vacancies": req.open_vacancies, "is_featured": int(req.is_featured and featured_allowed),
        "deadline": req.deadline, "status": "open", "created_at": now_text(),
        "updated_at": now_text(),
    })
    for skill_id in set(req.skill_ids):
        db.job_skills.update_one(
            {"job_id": job_id, "skill_id": skill_id},
            {"$setOnInsert": {"job_id": job_id, "skill_id": skill_id, "is_required": 1}},
            upsert=True,
        )
    return {"message": "Job vacancy published successfully!", "job_id": job_id}


@app.get("/api/recruiter/jobs/{job_id}/applicants")
def get_job_applicants(job_id: int, db=Depends(get_db)):
    result = []
    for application in documents(db, "applications", {"job_id": job_id}, [("applied_at", -1)]):
        seeker = find_by_id(db, "job_seekers", "seeker_id", application["seeker_id"]) or {}
        user = find_by_id(db, "users", "user_id", seeker.get("user_id")) or {}
        resume = find_by_id(db, "resumes", "resume_id", application.get("resume_id")) or {}
        result.append({
            **application, "full_name": user.get("full_name"), "email": user.get("email"),
            "phone": user.get("phone"), "qualification": seeker.get("qualification"),
            "experience_years": seeker.get("experience_years"),
            "current_location": seeker.get("current_location"),
            "expected_salary": seeker.get("expected_salary"),
            "resume_file": resume.get("file_name"), "resume_path": resume.get("file_path"),
        })
    return {"applicants": result, "count": len(result)}


def change_application_status(db, application_id, status, remarks, changed_by_user_id):
    application = find_by_id(db, "applications", "application_id", application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application record not found")
    db.applications.update_one(
        {"application_id": application_id},
        {"$set": {"current_status": status, "updated_at": now_text()}},
    )
    insert_document(db, "application_tracking", {
        "application_id": application_id, "status": status, "remarks": remarks,
        "changed_by_user_id": changed_by_user_id, "changed_at": now_text(),
    })
    seeker = find_by_id(db, "job_seekers", "seeker_id", application["seeker_id"])
    job = find_by_id(db, "jobs", "job_id", application["job_id"])
    if seeker and job:
        company = find_by_id(db, "companies", "company_id", job.get("company_id")) or {}
        if status in ("accepted", "offered"):
            title = "🎉 Job Application Accepted!"
            message = (
                f"Congratulations! Your application for '{job['job_title']}' "
                f"at {company.get('company_name', 'the company')} has been ACCEPTED / OFFER EXTENDED!"
            )
        elif status == "rejected":
            title = "Application Update: Not Selected"
            message = f"Your application for '{job['job_title']}' has not been selected."
        else:
            title = "Application Status Updated"
            message = (
                f"Your application for '{job['job_title']}' has moved to: "
                f"{status.replace('_', ' ').title()}"
            )
        add_notification(
            db, seeker["user_id"], title, message, "application"
        )
    return application


@app.post("/api/recruiter/applications/{application_id}/accept")
def accept_application(application_id: int, req: AcceptApplicationRequest, db=Depends(get_db)):
    details = []
    if req.offered_ctc:
        details.append(f"Offered CTC: ₹{req.offered_ctc:,.2f}")
    if req.joining_date:
        details.append(f"Joining Date: {req.joining_date}")
    detail_text = f" [{', '.join(details)}]" if details else ""
    remarks = f"🎉 Application Accepted & Offer Released: {req.remarks or 'Candidate selected for the position.'}{detail_text}"
    change_application_status(db, application_id, "accepted", remarks, req.changed_by_user_id)
    return {
        "message": "Candidate application accepted and employment offer extended!",
        "application_id": application_id, "status": "accepted", "remarks": remarks,
    }


@app.post("/api/recruiter/applications/{application_id}/reject")
def reject_application(application_id: int, req: RejectApplicationRequest, db=Depends(get_db)):
    remarks = (
        f"Application Rejected ({req.reason}): "
        f"{req.remarks or 'Thank you for your interest. We wish you the best in your career pursuits.'}"
    )
    change_application_status(db, application_id, "rejected", remarks, req.changed_by_user_id)
    return {"message": "Candidate application marked as rejected.", "application_id": application_id,
            "status": "rejected", "remarks": remarks}


@app.put("/api/recruiter/applications/{application_id}/status")
def update_application_status(application_id: int, req: UpdateStatusRequest, db=Depends(get_db)):
    application = find_by_id(db, "applications", "application_id", application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application record not found")
    remarks = req.remarks or (
        f"Status updated from {application['current_status']} to {req.status} by hiring manager."
    )
    change_application_status(db, application_id, req.status, remarks, req.changed_by_user_id)
    return {"message": f"Status updated to '{req.status}' successfully", "application_id": application_id}


@app.get("/api/subscriptions/plans")
def get_plans(db=Depends(get_db)):
    return {"plans": documents(db, "subscription_plans", sort=[("price", 1)])}


@app.post("/api/subscriptions/purchase")
def purchase_subscription(req: PurchaseSubscriptionRequest, db=Depends(get_db)):
    plan = find_by_id(db, "subscription_plans", "plan_id", req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Selected subscription plan does not exist")
    db.recruiter_subscriptions.update_many(
        {"recruiter_id": req.recruiter_id, "status": "active"},
        {"$set": {"status": "expired"}},
    )
    today = date.today()
    subscription_id = insert_document(db, "recruiter_subscriptions", {
        "recruiter_id": req.recruiter_id, "plan_id": req.plan_id,
        "start_date": str(today), "end_date": str(today + timedelta(days=plan["duration_days"])),
        "status": "active", "auto_renew": 1,
    })
    transaction_id = req.transaction_id or f"pay_RZP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    payment_id = insert_document(db, "payments", {
        "subscription_id": subscription_id, "amount": plan["price"],
        "payment_method": req.payment_method, "transaction_id": transaction_id,
        "payment_status": "success", "payment_date": now_text(),
    })
    tax = round(plan["price"] * 0.18, 2)
    total = round(plan["price"] + tax, 2)
    invoice_number = f"INV-{datetime.now().year}-{str(payment_id).zfill(5)}"
    insert_document(db, "invoices", {
        "payment_id": payment_id, "invoice_number": invoice_number,
        "tax_amount": tax, "total_amount": total, "issued_date": str(today),
    })
    recruiter = find_by_id(db, "recruiters", "recruiter_id", req.recruiter_id)
    if recruiter:
        add_notification(
            db, recruiter["user_id"], "Subscription Activated",
            f"Your {plan['plan_name']} is now active! Invoice #{invoice_number} issued.",
            "subscription",
        )
    return {
        "message": "Payment successful! Subscription upgraded.",
        "subscription_id": subscription_id, "invoice_number": invoice_number,
        "transaction_id": transaction_id, "plan_name": plan["plan_name"],
        "amount_paid": total,
    }


@app.get("/api/invoices")
def get_invoices(db=Depends(get_db)):
    invoices = []
    for invoice in documents(db, "invoices", sort=[("invoice_id", -1)]):
        payment = find_by_id(db, "payments", "payment_id", invoice.get("payment_id")) or {}
        subscription = find_by_id(
            db, "recruiter_subscriptions", "subscription_id", payment.get("subscription_id")
        ) or {}
        plan = find_by_id(db, "subscription_plans", "plan_id", subscription.get("plan_id")) or {}
        recruiter = find_by_id(db, "recruiters", "recruiter_id", subscription.get("recruiter_id")) or {}
        user = find_by_id(db, "users", "user_id", recruiter.get("user_id")) or {}
        company = find_by_id(db, "companies", "company_id", recruiter.get("company_id")) or {}
        invoices.append({
            **invoice, "transaction_id": payment.get("transaction_id"),
            "payment_method": payment.get("payment_method"), "payment_date": payment.get("payment_date"),
            "plan_name": plan.get("plan_name"), "recruiter_name": user.get("full_name"),
            "company_name": company.get("company_name"),
        })
    return {"invoices": invoices}


@app.get("/api/seeker/{seeker_id}/resumes")
def get_resumes(seeker_id: int, db=Depends(get_db)):
    return {"resumes": documents(
        db, "resumes", {"seeker_id": seeker_id},
        [("is_primary", -1), ("uploaded_at", -1)],
    )}


@app.post("/api/seeker/resumes")
def upload_resume(req: ResumeUploadRequest, db=Depends(get_db)):
    insert_document(db, "resumes", {
        "seeker_id": req.seeker_id, "file_name": req.file_name,
        "file_path": f"/media/resumes/{req.file_name}",
        "file_size_kb": req.file_size_kb, "is_primary": 0, "uploaded_at": now_text(),
    })
    return {"message": "Resume uploaded successfully"}


@app.post("/api/seeker/{seeker_id}/saved-jobs/{job_id}")
def toggle_saved_job(seeker_id: int, job_id: int, db=Depends(get_db)):
    existing = db.saved_jobs.find_one({"seeker_id": seeker_id, "job_id": job_id}, {"_id": 0})
    if existing:
        db.saved_jobs.delete_one({"saved_id": existing["saved_id"]})
        return {"saved": False, "message": "Job removed from bookmarks"}
    insert_document(db, "saved_jobs", {
        "seeker_id": seeker_id, "job_id": job_id, "saved_at": now_text(),
    })
    return {"saved": True, "message": "Job saved to bookmarks"}


@app.get("/api/seeker/{seeker_id}/saved-jobs")
def get_saved_jobs(seeker_id: int, db=Depends(get_db)):
    saved_jobs = []
    for saved in documents(db, "saved_jobs", {"seeker_id": seeker_id}, [("saved_at", -1)]):
        job = find_by_id(db, "jobs", "job_id", saved["job_id"])
        if not job:
            continue
        company = find_by_id(db, "companies", "company_id", job.get("company_id")) or {}
        saved_jobs.append({
            **job, "company_name": company.get("company_name"),
            "is_company_verified": company.get("is_verified", 0),
            "saved_at": saved.get("saved_at"),
        })
    return {"saved_jobs": saved_jobs}


@app.get("/api/admin/stats")
def get_admin_stats(db=Depends(get_db)):
    stats = {
        "job_seekers": db.users.count_documents({"role": "job_seeker"}),
        "recruiters": db.users.count_documents({"role": "recruiter"}),
        "companies": db.companies.count_documents({}),
        "active_jobs": db.jobs.count_documents({"status": "open"}),
        "applications": db.applications.count_documents({}),
        "active_premium": db.recruiter_subscriptions.count_documents(
            {"status": "active", "plan_id": {"$gt": 1}}
        ),
        "gross_revenue": sum(
            invoice.get("total_amount", 0) for invoice in documents(db, "invoices")
        ),
    }
    demand = {}
    for relation in documents(db, "job_skills"):
        skill = find_by_id(db, "skills", "skill_id", relation["skill_id"])
        if skill:
            demand[skill["skill_id"]] = (skill["skill_name"], demand.get(skill["skill_id"], ("", 0))[1] + 1)
    stats["top_skills"] = [
        {"skill_name": name, "demand": count}
        for name, count in sorted(demand.values(), key=lambda item: item[1], reverse=True)[:6]
    ]
    funnel = {}
    for application in documents(db, "applications"):
        status = application.get("current_status")
        funnel[status] = funnel.get(status, 0) + 1
    stats["funnel"] = [{"current_status": status, "count": count} for status, count in funnel.items()]
    return stats


@app.get("/api/notifications/{user_id}")
def get_notifications(user_id: int, db=Depends(get_db)):
    return {"notifications": documents(
        db, "notifications", {"user_id": user_id},
        [("is_read", 1), ("created_at", -1)], 20,
    )}


@app.put("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db=Depends(get_db)):
    db.notifications.update_one(
        {"notification_id": notification_id}, {"$set": {"is_read": 1}}
    )
    return {"message": "Notification marked as read"}


@app.get("/api/skills")
def get_all_skills(db=Depends(get_db)):
    return {"skills": documents(db, "skills", sort=[("category", 1), ("skill_name", 1)])}


@app.post("/api/query")
def execute_custom_query(req: CustomQueryRequest, db=Depends(get_db)):
    query = req.query.strip()
    if not query.startswith("{"):
        raise HTTPException(
            status_code=400,
            detail="This endpoint now accepts a JSON MongoDB find request, not SQL.",
        )
    import json

    try:
        request = json.loads(query)
        collection = request["collection"]
        filter_query = request.get("filter", {})
        if collection not in COLLECTION_KEYS or not isinstance(filter_query, dict):
            raise ValueError("Choose a valid collection and provide a JSON filter object.")
        if not is_exact_filter(filter_query):
            raise ValueError("MongoDB filter operators are not accepted; use exact field values.")
        rows = documents(db, collection, filter_query, limit=100)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid MongoDB find request: {exc}") from exc
    columns = sorted({key for row in rows for key in row})
    return {"columns": columns, "rows": rows, "count": len(rows)}


@app.get("/api/tables")
def get_tables_list(db=Depends(get_db)):
    return {"tables": sorted(COLLECTION_KEYS)}


@app.get("/api/table")
def get_table_content(name: str = "jobs", db=Depends(get_db)):
    if name not in COLLECTION_KEYS:
        raise HTTPException(status_code=400, detail=f"Invalid collection name: {name}")
    rows = documents(db, name, limit=100)
    columns = sorted({key for row in rows for key in row})
    return {"table": name, "columns": columns, "rows": rows, "count": len(rows)}


@app.get("/")
def serve_home():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


media_dir = os.path.join(BASE_DIR, "media")
if os.path.isdir(media_dir):
    app.mount("/media", StaticFiles(directory=media_dir), name="media")
