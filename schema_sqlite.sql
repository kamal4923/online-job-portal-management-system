-- =============================================================================
-- ONLINE JOB PORTAL MANAGEMENT SYSTEM
-- SQLite Schema (Zero-setup local execution engine)
-- =============================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS saved_jobs;
DROP TABLE IF EXISTS application_tracking;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS resumes;
DROP TABLE IF EXISTS seeker_skills;
DROP TABLE IF EXISTS job_skills;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS recruiter_subscriptions;
DROP TABLE IF EXISTS subscription_plans;
DROP TABLE IF EXISTS recruiters;
DROP TABLE IF EXISTS job_seekers;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS users;

-- 1. USERS
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    phone TEXT,
    role TEXT CHECK(role IN ('admin', 'recruiter', 'job_seeker')) NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. COMPANIES
CREATE TABLE companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE,
    industry TEXT NOT NULL,
    website TEXT,
    location TEXT NOT NULL,
    company_size TEXT DEFAULT '11-50 employees',
    description TEXT,
    logo_url TEXT,
    is_verified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. JOB SEEKERS
CREATE TABLE job_seekers (
    seeker_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    headline TEXT,
    qualification TEXT NOT NULL,
    experience_years REAL DEFAULT 0.0,
    current_location TEXT NOT NULL,
    expected_salary REAL,
    bio TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. RECRUITERS
CREATE TABLE recruiters (
    recruiter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    company_id INTEGER NOT NULL,
    designation TEXT NOT NULL,
    department TEXT DEFAULT 'Human Resources',
    is_verified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE RESTRICT
);

-- 5. SUBSCRIPTION PLANS
CREATE TABLE subscription_plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_name TEXT NOT NULL UNIQUE,
    price REAL NOT NULL DEFAULT 0.0,
    duration_days INTEGER NOT NULL DEFAULT 30,
    job_posting_limit INTEGER NOT NULL DEFAULT 2,
    candidate_search_limit INTEGER NOT NULL DEFAULT 20,
    featured_jobs_allowed INTEGER DEFAULT 0,
    priority_support INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. RECRUITER SUBSCRIPTIONS
CREATE TABLE recruiter_subscriptions (
    subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recruiter_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT CHECK(status IN ('active', 'expired', 'cancelled', 'pending')) DEFAULT 'active',
    auto_renew INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(plan_id) ON DELETE RESTRICT
);

-- 7. PAYMENTS
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'Razorpay',
    transaction_id TEXT NOT NULL UNIQUE,
    payment_status TEXT CHECK(payment_status IN ('success', 'pending', 'failed', 'refunded')) NOT NULL DEFAULT 'success',
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    gateway_response TEXT,
    FOREIGN KEY (subscription_id) REFERENCES recruiter_subscriptions(subscription_id) ON DELETE CASCADE
);

-- 8. INVOICES
CREATE TABLE invoices (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL UNIQUE,
    invoice_number TEXT NOT NULL UNIQUE,
    tax_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL,
    issued_date DATE NOT NULL,
    invoice_pdf_path TEXT,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id) ON DELETE CASCADE
);

-- 9. JOBS
CREATE TABLE jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recruiter_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    job_title TEXT NOT NULL,
    job_type TEXT CHECK(job_type IN ('Full-time', 'Part-time', 'Contract', 'Internship', 'Remote')) NOT NULL DEFAULT 'Full-time',
    experience_level TEXT CHECK(experience_level IN ('Entry', 'Mid', 'Senior', 'Lead')) NOT NULL DEFAULT 'Mid',
    location TEXT NOT NULL,
    salary_min REAL NOT NULL,
    salary_max REAL NOT NULL,
    description TEXT NOT NULL,
    requirements TEXT,
    open_vacancies INTEGER DEFAULT 1,
    is_featured INTEGER DEFAULT 0,
    deadline DATE NOT NULL,
    status TEXT CHECK(status IN ('open', 'closed', 'paused')) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE RESTRICT,
    CHECK (salary_max >= salary_min)
);

-- 10. SKILLS
CREATE TABLE skills (
    skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT 'Technical'
);

-- 11. JOB SKILLS
CREATE TABLE job_skills (
    job_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    is_required INTEGER DEFAULT 1,
    PRIMARY KEY (job_id, skill_id),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- 12. SEEKER SKILLS
CREATE TABLE seeker_skills (
    seeker_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    proficiency_level TEXT CHECK(proficiency_level IN ('Beginner', 'Intermediate', 'Expert')) DEFAULT 'Intermediate',
    PRIMARY KEY (seeker_id, skill_id),
    FOREIGN KEY (seeker_id) REFERENCES job_seekers(seeker_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- 13. RESUMES
CREATE TABLE resumes (
    resume_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seeker_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_kb INTEGER NOT NULL,
    is_primary INTEGER DEFAULT 1,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seeker_id) REFERENCES job_seekers(seeker_id) ON DELETE CASCADE
);

-- 14. APPLICATIONS
CREATE TABLE applications (
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

-- 15. APPLICATION TRACKING
CREATE TABLE application_tracking (
    tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    remarks TEXT,
    changed_by_user_id INTEGER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 16. SAVED JOBS
CREATE TABLE saved_jobs (
    saved_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seeker_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(seeker_id, job_id),
    FOREIGN KEY (seeker_id) REFERENCES job_seekers(seeker_id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

-- 17. NOTIFICATIONS
CREATE TABLE notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT CHECK(notification_type IN ('application', 'subscription', 'job_alert', 'system')) DEFAULT 'application',
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- VIEWS
CREATE VIEW vw_active_jobs_with_company AS
SELECT 
    j.job_id,
    j.job_title,
    j.job_type,
    j.experience_level,
    j.location,
    j.salary_min,
    j.salary_max,
    j.is_featured,
    j.deadline,
    j.created_at,
    c.company_id,
    c.company_name,
    c.industry,
    c.is_verified AS is_company_verified,
    r.recruiter_id,
    u.full_name AS recruiter_name,
    COUNT(a.application_id) AS total_applications
FROM jobs j
JOIN companies c ON j.company_id = c.company_id
JOIN recruiters r ON j.recruiter_id = r.recruiter_id
JOIN users u ON r.user_id = u.user_id
LEFT JOIN applications a ON j.job_id = a.job_id
WHERE j.status = 'open' AND date(j.deadline) >= date('now')
GROUP BY j.job_id, c.company_id, r.recruiter_id, u.full_name;

CREATE VIEW vw_recruiter_dashboard_stats AS
SELECT 
    r.recruiter_id,
    u.full_name AS recruiter_name,
    c.company_name,
    COALESCE(sp.plan_name, 'No Active Plan') AS current_plan,
    COALESCE(rs.status, 'inactive') AS subscription_status,
    COALESCE(sp.job_posting_limit, 2) AS max_jobs_allowed,
    COUNT(DISTINCT j.job_id) AS total_jobs_posted,
    COUNT(DISTINCT CASE WHEN j.status = 'open' THEN j.job_id END) AS active_jobs,
    COUNT(DISTINCT a.application_id) AS total_applicants_received,
    COUNT(DISTINCT CASE WHEN a.current_status = 'shortlisted' THEN a.application_id END) AS shortlisted_count
FROM recruiters r
JOIN users u ON r.user_id = u.user_id
JOIN companies c ON r.company_id = c.company_id
LEFT JOIN recruiter_subscriptions rs 
    ON r.recruiter_id = rs.recruiter_id AND rs.status = 'active' AND date(rs.end_date) >= date('now')
LEFT JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
LEFT JOIN jobs j ON r.recruiter_id = j.recruiter_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY r.recruiter_id, u.full_name, c.company_name, sp.plan_name, rs.status, sp.job_posting_limit;

CREATE VIEW vw_job_seeker_applications AS
SELECT 
    a.application_id,
    js.seeker_id,
    u.full_name AS applicant_name,
    j.job_id,
    j.job_title,
    c.company_name,
    j.location AS job_location,
    a.applied_at,
    a.current_status,
    r.file_name AS resume_used,
    (SELECT remarks FROM application_tracking at 
     WHERE at.application_id = a.application_id 
     ORDER BY at.changed_at DESC LIMIT 1) AS latest_remark
FROM applications a
JOIN job_seekers js ON a.seeker_id = js.seeker_id
JOIN users u ON js.user_id = u.user_id
JOIN jobs j ON a.job_id = j.job_id
JOIN companies c ON j.company_id = c.company_id
JOIN resumes r ON a.resume_id = r.resume_id;

CREATE VIEW vw_admin_revenue_and_subscriptions AS
SELECT 
    sp.plan_id,
    sp.plan_name,
    sp.price AS plan_price,
    COUNT(rs.subscription_id) AS total_subscriptions_sold,
    COUNT(CASE WHEN rs.status = 'active' THEN 1 END) AS active_subscribers,
    COALESCE(SUM(p.amount), 0.00) AS total_revenue_generated
FROM subscription_plans sp
LEFT JOIN recruiter_subscriptions rs ON sp.plan_id = rs.plan_id
LEFT JOIN payments p ON rs.subscription_id = p.subscription_id AND p.payment_status = 'success'
GROUP BY sp.plan_id, sp.plan_name, sp.price;

-- TRIGGERS
CREATE TRIGGER trg_after_application_status_update
AFTER UPDATE OF current_status ON applications
BEGIN
    INSERT INTO application_tracking (application_id, status, remarks, changed_by_user_id)
    VALUES (NEW.application_id, NEW.current_status, 
            'Status transitioned from ' || OLD.current_status || ' to ' || NEW.current_status, NULL);
    
    INSERT INTO notifications (user_id, title, message, notification_type)
    SELECT js.user_id, 'Application Status Update',
           'Your application status has been updated to: ' || NEW.current_status, 'application'
    FROM job_seekers js WHERE js.seeker_id = NEW.seeker_id;
END;
