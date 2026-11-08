import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "job_portal.db")

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    # 1. Drop dependent views temporarily
    cursor.execute("DROP VIEW IF EXISTS vw_active_jobs_with_company;")
    cursor.execute("DROP VIEW IF EXISTS vw_recruiter_dashboard_stats;")
    cursor.execute("DROP VIEW IF EXISTS vw_job_seeker_applications;")
    cursor.execute("DROP VIEW IF EXISTS vw_revenue_and_invoicing;")
    
    # 2. Check if applications_new exists, if not create and copy
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications_new (
        application_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        seeker_id INTEGER NOT NULL,
        resume_id INTEGER NOT NULL,
        cover_letter TEXT,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        current_status TEXT CHECK(current_status IN ('applied', 'screening', 'shortlisted', 'interview_scheduled', 'offered', 'accepted', 'rejected')) DEFAULT 'applied',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(seeker_id, job_id),
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
        FOREIGN KEY (seeker_id) REFERENCES job_seekers(seeker_id) ON DELETE CASCADE,
        FOREIGN KEY (resume_id) REFERENCES resumes(resume_id) ON DELETE RESTRICT
    );
    """)
    
    # If applications table exists, copy data
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "applications" in tables:
        cursor.execute("INSERT OR REPLACE INTO applications_new SELECT * FROM applications;")
        cursor.execute("DROP TABLE applications;")
    
    cursor.execute("ALTER TABLE applications_new RENAME TO applications;")
    
    # 3. Recreate indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_seeker ON applications(seeker_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(current_status);")
    
    # 4. Recreate views
    cursor.execute("""
    CREATE VIEW vw_active_jobs_with_company AS
    SELECT 
        j.job_id, j.job_title, j.job_type, j.experience_level, j.location, j.salary_min, j.salary_max,
        j.is_featured, j.deadline, j.created_at, c.company_id, c.company_name, c.industry,
        c.is_verified AS is_company_verified, r.recruiter_id, u.full_name AS recruiter_name,
        COUNT(a.application_id) AS total_applications
    FROM jobs j
    JOIN companies c ON j.company_id = c.company_id
    JOIN recruiters r ON j.recruiter_id = r.recruiter_id
    JOIN users u ON r.user_id = u.user_id
    LEFT JOIN applications a ON j.job_id = a.job_id
    WHERE j.status = 'open' AND date(j.deadline) >= date('now')
    GROUP BY j.job_id, c.company_id, r.recruiter_id, u.full_name;
    """)
    
    cursor.execute("""
    CREATE VIEW vw_recruiter_dashboard_stats AS
    SELECT 
        r.recruiter_id, u.full_name AS recruiter_name, c.company_name,
        COALESCE(sp.plan_name, 'No Active Plan') AS current_plan,
        COALESCE(rs.status, 'inactive') AS subscription_status,
        COALESCE(sp.job_posting_limit, 2) AS max_jobs_allowed,
        COUNT(DISTINCT j.job_id) AS total_jobs_posted,
        COUNT(DISTINCT CASE WHEN j.status = 'open' THEN j.job_id END) AS active_jobs,
        COUNT(DISTINCT a.application_id) AS total_applicants_received,
        COUNT(DISTINCT CASE WHEN a.current_status = 'shortlisted' THEN a.application_id END) AS shortlisted_count,
        COUNT(DISTINCT CASE WHEN a.current_status IN ('offered', 'accepted') THEN a.application_id END) AS accepted_count
    FROM recruiters r
    JOIN users u ON r.user_id = u.user_id
    JOIN companies c ON r.company_id = c.company_id
    LEFT JOIN recruiter_subscriptions rs 
        ON r.recruiter_id = rs.recruiter_id AND rs.status = 'active' AND date(rs.end_date) >= date('now')
    LEFT JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
    LEFT JOIN jobs j ON r.recruiter_id = j.recruiter_id
    LEFT JOIN applications a ON j.job_id = a.job_id
    GROUP BY r.recruiter_id, u.full_name, c.company_name, sp.plan_name, rs.status, sp.job_posting_limit;
    """)
    
    cursor.execute("""
    CREATE VIEW vw_job_seeker_applications AS
    SELECT 
        a.application_id, a.seeker_id, u_cand.full_name AS candidate_name, u_cand.email AS candidate_email,
        j.job_id, j.job_title, c.company_name, j.location, a.current_status, a.applied_at,
        r.file_name AS resume_file, r.file_path AS resume_path
    FROM applications a
    JOIN jobs j ON a.job_id = j.job_id
    JOIN companies c ON j.company_id = c.company_id
    JOIN job_seekers js ON a.seeker_id = js.seeker_id
    JOIN users u_cand ON js.user_id = u_cand.user_id
    JOIN resumes r ON a.resume_id = r.resume_id;
    """)
    
    cursor.execute("""
    CREATE VIEW vw_revenue_and_invoicing AS
    SELECT 
        inv.invoice_id, inv.invoice_number, inv.tax_amount, inv.total_amount, inv.issued_date,
        p.transaction_id, p.payment_method, p.payment_status, p.payment_date,
        sp.plan_name, u.full_name AS recruiter_name, c.company_name
    FROM invoices inv
    JOIN payments p ON inv.payment_id = p.payment_id
    JOIN recruiter_subscriptions rs ON p.subscription_id = rs.subscription_id
    JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
    JOIN recruiters r ON rs.recruiter_id = r.recruiter_id
    JOIN users u ON r.user_id = u.user_id
    JOIN companies c ON r.company_id = c.company_id;
    """)
    
    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    count = cursor.execute("SELECT COUNT(*) FROM applications;").fetchone()[0]
    print(f"[SUCCESS] Migration complete! {count} applications loaded with 'accepted' & 'offered' support.")
    conn.close()

if __name__ == "__main__":
    upgrade()
