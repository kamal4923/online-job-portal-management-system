"""
Database Setup & Automated Verification Engine
Online Job Portal Management System
"""

import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "job_portal.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema_sqlite.sql")

def init_database():
    print("=" * 80)
    print("ONLINE JOB PORTAL MANAGEMENT SYSTEM - DATABASE INITIALIZATION")
    print("=" * 80)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[OK] Cleaned previous database file: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. Execute Schema
    print("\n--> [1/4] Executing Database Schema (15 Tables, 4 Views, Triggers)...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    print("[SUCCESS] Schema executed successfully.")

    # 2. Populate Seed Data
    print("\n--> [2/4] Populating Seed Data across all 12 modules...")
    seed_sql = """
    -- Users (Admin, 4 Recruiters, 6 Job Seekers)
    INSERT INTO users (user_id, full_name, email, password_hash, phone, role) VALUES
    (1, 'System Administrator', 'admin@jobportal.com', '$2b$12$AdminHashDemo', '+91 9876543210', 'admin'),
    (2, 'Rajesh Varma', 'rajesh.varma@infosys.com', '$2b$12$Recruiter1Demo', '+91 9820011223', 'recruiter'),
    (3, 'Priya Nair', 'priya.nair@tcs.com', '$2b$12$Recruiter2Demo', '+91 9830022334', 'recruiter'),
    (4, 'Amitabh Roy', 'amitabh@finedge.com', '$2b$12$Recruiter3Demo', '+91 9840033445', 'recruiter'),
    (5, 'Sneha Kapoor', 'sneha@cloudscale.io', '$2b$12$Recruiter4Demo', '+91 9850044556', 'recruiter'),
    (6, 'Kamal Sen', 'kamal.sen@email.com', '$2b$12$Seeker1Demo', '+91 9910011223', 'job_seeker'),
    (7, 'Ananya Patel', 'ananya.patel@email.com', '$2b$12$Seeker2Demo', '+91 9920022334', 'job_seeker'),
    (8, 'Rohan Mehta', 'rohan.mehta@email.com', '$2b$12$Seeker3Demo', '+91 9930033445', 'job_seeker'),
    (9, 'Divya Krishnan', 'divya.krishnan@email.com', '$2b$12$Seeker4Demo', '+91 9940044556', 'job_seeker'),
    (10, 'Arjun Singh', 'arjun.singh@email.com', '$2b$12$Seeker5Demo', '+91 9950055667', 'job_seeker'),
    (11, 'Meera Joshi', 'meera.joshi@email.com', '$2b$12$Seeker6Demo', '+91 9960066778', 'job_seeker');

    -- Companies
    INSERT INTO companies (company_id, company_name, industry, website, location, company_size, description, is_verified) VALUES
    (1, 'Infosys Technologies', 'Information Technology', 'https://www.infosys.com', 'Bengaluru, Karnataka', '10000+ employees', 'Global leader in next-generation digital services.', 1),
    (2, 'Tata Consultancy Services', 'Enterprise Software', 'https://www.tcs.com', 'Mumbai, Maharashtra', '10000+ employees', 'Leading IT services and consulting provider.', 1),
    (3, 'FinEdge Innovations', 'Financial Technology', 'https://www.finedge.io', 'Hyderabad, Telangana', '201-500 employees', 'Next-gen payment processing infrastructure.', 1),
    (4, 'CloudScale Systems', 'Cloud & DevOps', 'https://www.cloudscale.io', 'Pune, Maharashtra', '51-200 employees', 'Automated multi-cloud architecture and platforms.', 1),
    (5, 'NextGen AI Labs', 'Artificial Intelligence', 'https://www.nextgenai.tech', 'Bengaluru, Karnataka', '11-50 employees', 'Enterprise Generative AI agents automation.', 0);

    -- Job Seekers
    INSERT INTO job_seekers (seeker_id, user_id, headline, qualification, experience_years, current_location, expected_salary, bio, linkedin_url, github_url) VALUES
    (1, 6, 'Full-Stack Python & Django Developer', 'B.Tech Computer Science', 2.5, 'Bengaluru', 850000.00, 'Passionate software engineer skilled in Python, Django, MySQL.', 'https://linkedin.com/in/kamalsen', 'https://github.com/kamalsen'),
    (2, 7, 'Frontend Engineer | React & TypeScript', 'B.Tech Information Technology', 3.0, 'Pune', 950000.00, 'Frontend specialist building accessible, pixel-perfect user interfaces.', 'https://linkedin.com/in/ananyapatel', 'https://github.com/ananyapatel'),
    (3, 8, 'Data Analyst & SQL Specialist', 'B.Sc Statistics & Data Science', 1.5, 'Hyderabad', 650000.00, 'Specialized in relational database modeling and advanced SQL queries.', 'https://linkedin.com/in/rohanmehta', 'https://github.com/rohanmehta'),
    (4, 9, 'DevOps & Cloud Engineer', 'B.Tech Electronics & Comm', 4.0, 'Bengaluru', 1400000.00, 'AWS Certified Solutions Architect with deep Docker and CI/CD expertise.', 'https://linkedin.com/in/divyakrishnan', 'https://github.com/divyakrishnan'),
    (5, 10, 'Backend Java & Spring Boot Developer', 'MCA Computer Applications', 2.0, 'Mumbai', 750000.00, 'Microservices engineer building high-throughput financial backends.', 'https://linkedin.com/in/arjunsingh', 'https://github.com/arjunsingh'),
    (6, 11, 'Junior Software Engineer & Intern', 'B.Tech IT (Final Year)', 0.5, 'Bengaluru', 500000.00, 'Enthusiastic entry-level developer with strong foundation in DSA & Python.', 'https://linkedin.com/in/meerajoshi', 'https://github.com/meerajoshi');

    -- Recruiters
    INSERT INTO recruiters (recruiter_id, user_id, company_id, designation, department, is_verified) VALUES
    (1, 2, 1, 'Senior Talent Acquisition Lead', 'Global Talent Acquisition', 1),
    (2, 3, 2, 'Technical Hiring Manager', 'Engineering Talent Solutions', 1),
    (3, 4, 3, 'HR Business Partner', 'Fintech Recruitment Group', 1),
    (4, 5, 4, 'People & Culture Specialist', 'Talent Operations', 1);

    -- Subscription Plans
    INSERT INTO subscription_plans (plan_id, plan_name, price, duration_days, job_posting_limit, candidate_search_limit, featured_jobs_allowed, priority_support) VALUES
    (1, 'Free Starter', 0.00, 30, 2, 20, 0, 0),
    (2, 'Recruiter Premium', 499.00, 30, 10, 100, 1, 0),
    (3, 'Enterprise Unlimited', 999.00, 60, 50, 500, 1, 1);

    -- Recruiter Subscriptions
    INSERT INTO recruiter_subscriptions (subscription_id, recruiter_id, plan_id, start_date, end_date, status, auto_renew) VALUES
    (1, 1, 2, '2026-10-15', '2026-11-14', 'active', 1),
    (2, 2, 3, '2026-10-01', '2026-11-30', 'active', 1),
    (3, 3, 2, '2026-10-20', '2026-11-19', 'active', 0),
    (4, 4, 1, '2026-11-01', '2026-11-30', 'active', 0);

    -- Payments
    INSERT INTO payments (payment_id, subscription_id, amount, payment_method, transaction_id, payment_status, payment_date) VALUES
    (1, 1, 499.00, 'Razorpay UPI', 'pay_RZP_1001_849201', 'success', '2026-10-15 10:14:32'),
    (2, 2, 999.00, 'Razorpay Credit Card', 'pay_RZP_1002_958102', 'success', '2026-10-01 14:22:05'),
    (3, 3, 499.00, 'Razorpay NetBanking', 'pay_RZP_1003_341908', 'success', '2026-10-20 09:45:18');

    -- Invoices
    INSERT INTO invoices (invoice_id, payment_id, invoice_number, tax_amount, total_amount, issued_date, invoice_pdf_path) VALUES
    (1, 1, 'INV-2026-00001', 89.82, 588.82, '2026-10-15', '/media/invoices/INV_2026_00001.pdf'),
    (2, 2, 'INV-2026-00002', 179.82, 1178.82, '2026-10-01', '/media/invoices/INV_2026_00002.pdf'),
    (3, 3, 'INV-2026-00003', 89.82, 588.82, '2026-10-20', '/media/invoices/INV_2026_00003.pdf');

    -- Skills
    INSERT INTO skills (skill_id, skill_name, category) VALUES
    (1, 'Python', 'Programming Languages'),
    (2, 'Django', 'Frameworks & Web'),
    (3, 'SQL / MySQL', 'Databases'),
    (4, 'React.js', 'Frontend Frameworks'),
    (5, 'TypeScript', 'Programming Languages'),
    (6, 'Docker', 'DevOps & Tools'),
    (7, 'AWS Cloud', 'Cloud Infrastructure'),
    (8, 'Java', 'Programming Languages'),
    (9, 'Spring Boot', 'Frameworks & Web'),
    (10, 'Data Analysis', 'Data & Analytics'),
    (11, 'REST API Design', 'Backend Engineering'),
    (12, 'Kubernetes', 'DevOps & Tools');

    -- Seeker Skills
    INSERT INTO seeker_skills (seeker_id, skill_id, proficiency_level) VALUES
    (1, 1, 'Expert'), (1, 2, 'Expert'), (1, 3, 'Expert'), (1, 11, 'Expert'),
    (2, 4, 'Expert'), (2, 5, 'Intermediate'), (2, 11, 'Intermediate'),
    (3, 3, 'Expert'), (3, 10, 'Expert'), (3, 1, 'Intermediate'),
    (4, 6, 'Expert'), (4, 7, 'Expert'), (4, 12, 'Intermediate'),
    (5, 8, 'Expert'), (5, 9, 'Expert'), (5, 3, 'Intermediate'),
    (6, 1, 'Intermediate'), (6, 3, 'Intermediate'), (6, 11, 'Beginner');

    -- Jobs
    INSERT INTO jobs (job_id, recruiter_id, company_id, job_title, job_type, experience_level, location, salary_min, salary_max, description, requirements, open_vacancies, is_featured, deadline, status) VALUES
    (1, 1, 1, 'Full Stack Python Developer', 'Full-time', 'Mid', 'Bengaluru, Karnataka', 800000.00, 1200000.00, 'Develop resilient web backends using Django REST APIs.', 'Proficiency in Python, Django, SQL databases, and REST APIs.', 3, 1, '2026-12-15', 'open'),
    (2, 1, 1, 'Senior Cloud DevOps Architect', 'Full-time', 'Senior', 'Bengaluru, Karnataka', 1500000.00, 2200000.00, 'Manage multi-region AWS cloud infrastructure.', '4+ years of AWS experience, Docker, Kubernetes.', 2, 1, '2026-12-30', 'open'),
    (3, 2, 2, 'React Frontend Engineer', 'Full-time', 'Mid', 'Pune, Maharashtra', 750000.00, 1100000.00, 'Craft high-performance single page applications using React.', '3+ years with React.js, TypeScript, and modern CSS.', 4, 0, '2026-12-20', 'open'),
    (4, 2, 2, 'Java & Spring Boot Engineer', 'Full-time', 'Mid', 'Mumbai, Maharashtra', 800000.00, 1300000.00, 'Build scalable microservices for enterprise banking.', 'Solid core Java 17, Spring Boot, Hibernate, and SQL.', 2, 0, '2026-12-10', 'open'),
    (5, 3, 3, 'FinTech Data & SQL Analyst', 'Full-time', 'Mid', 'Hyderabad, Telangana', 700000.00, 1000000.00, 'Analyze payment transaction flows and detect fraud anomalies.', 'Advanced SQL queries, window functions, statistical analysis.', 1, 1, '2026-11-28', 'open'),
    (6, 4, 4, 'Junior Backend Developer (Python)', 'Full-time', 'Entry', 'Remote', 450000.00, 650000.00, 'Entry-level position for passionate coders.', 'Python, relational database schemas, and Git.', 2, 0, '2026-12-05', 'open');

    -- Job Skills Required
    INSERT INTO job_skills (job_id, skill_id, is_required) VALUES
    (1, 1, 1), (1, 2, 1), (1, 3, 1), (1, 11, 1),
    (2, 6, 1), (2, 7, 1), (2, 12, 1),
    (3, 4, 1), (3, 5, 1),
    (4, 8, 1), (4, 9, 1), (4, 3, 1),
    (5, 3, 1), (5, 10, 1), (5, 1, 0),
    (6, 1, 1), (6, 3, 1);

    -- Resumes
    INSERT INTO resumes (resume_id, seeker_id, file_name, file_path, file_size_kb, is_primary) VALUES
    (1, 1, 'Kamal_Sen_Python_Fullstack_Resume.pdf', '/media/resumes/kamal_sen_cv_2026.pdf', 245, 1),
    (2, 2, 'Ananya_Patel_Frontend_Engineer.pdf', '/media/resumes/ananya_patel_cv.pdf', 312, 1),
    (3, 3, 'Rohan_Mehta_Data_Analyst_CV.pdf', '/media/resumes/rohan_mehta_cv.pdf', 198, 1),
    (4, 4, 'Divya_Krishnan_DevOps_Cloud.pdf', '/media/resumes/divya_cv.pdf', 280, 1),
    (5, 5, 'Arjun_Singh_Java_Backend.pdf', '/media/resumes/arjun_singh_cv.pdf', 210, 1),
    (6, 6, 'Meera_Joshi_Junior_Software.pdf', '/media/resumes/meera_joshi_cv.pdf', 175, 1);

    -- Applications
    INSERT INTO applications (application_id, job_id, seeker_id, resume_id, cover_letter, applied_at, current_status) VALUES
    (1, 1, 1, 1, 'I have 2.5 years of experience developing Django and REST APIs with MySQL.', '2026-10-25 11:30:00', 'shortlisted'),
    (2, 6, 1, 1, 'Experienced in Python backend development and eager to work remotely.', '2026-10-26 14:10:00', 'interview_scheduled'),
    (3, 3, 2, 2, 'Senior React developer with 3 years building modern responsive dashboards.', '2026-10-27 10:05:00', 'offered'),
    (4, 5, 3, 3, 'Data Analyst skilled in SQL query optimization and financial data metrics.', '2026-10-28 16:45:00', 'screening'),
    (5, 2, 4, 4, 'Certified AWS Cloud Architect with deep Docker and Kubernetes experience.', '2026-10-29 09:15:00', 'shortlisted'),
    (6, 4, 5, 5, 'Backend Java engineer with microservices expertise using Spring Boot.', '2026-10-30 12:20:00', 'screening'),
    (7, 1, 6, 6, 'Eager fresh graduate looking forward to starting software engineering career.', '2026-11-01 15:30:00', 'applied'),
    (8, 6, 6, 6, 'Good knowledge of Python and SQL fundamentals, eager for Junior Developer role.', '2026-11-02 11:00:00', 'screening');

    -- Application Tracking History
    INSERT INTO application_tracking (tracking_id, application_id, status, remarks, changed_by_user_id, changed_at) VALUES
    (1, 1, 'applied', 'Application received from job seeker', 6, '2026-10-25 11:30:00'),
    (2, 1, 'screening', 'Initial resume screening cleared. Matched skill criteria.', 2, '2026-10-26 09:30:00'),
    (3, 1, 'shortlisted', 'Candidate shortlisted for Technical Interview Round 1.', 2, '2026-10-28 14:00:00'),
    (4, 2, 'applied', 'Application received from candidate', 6, '2026-10-26 14:10:00'),
    (5, 2, 'screening', 'Profile reviewed by hiring coordinator.', 5, '2026-10-27 11:00:00'),
    (6, 2, 'shortlisted', 'Passed coding assessment test.', 5, '2026-10-29 16:00:00'),
    (7, 2, 'interview_scheduled', 'Technical round scheduled on Google Meet for Friday 3 PM.', 5, '2026-10-31 10:00:00'),
    (8, 3, 'applied', 'Application received', 7, '2026-10-27 10:05:00'),
    (9, 3, 'screening', 'Portfolio evaluated. Great UI designs.', 3, '2026-10-28 12:00:00'),
    (10, 3, 'shortlisted', 'Shortlisted directly for final round.', 3, '2026-10-29 15:00:00'),
    (11, 3, 'interview_scheduled', 'Client interview completed successfully.', 3, '2026-10-30 11:00:00'),
    (12, 3, 'offered', 'Offer letter rolled out with competitive CTC.', 3, '2026-11-02 16:30:00'),
    (13, 4, 'applied', 'Application received', 8, '2026-10-28 16:45:00'),
    (14, 4, 'screening', 'HR screening in progress for FinTech requirements.', 4, '2026-10-30 10:00:00'),
    (15, 5, 'applied', 'Application submitted', 9, '2026-10-29 09:15:00'),
    (16, 5, 'shortlisted', 'Strong AWS profile; forwarded to Engineering Director.', 2, '2026-10-31 14:00:00');

    -- Saved Jobs
    INSERT INTO saved_jobs (saved_id, seeker_id, job_id) VALUES
    (1, 1, 2), (2, 1, 5), (3, 2, 1), (4, 3, 1), (5, 6, 1);

    -- Notifications
    INSERT INTO notifications (notification_id, user_id, title, message, notification_type, is_read) VALUES
    (1, 6, 'Application Shortlisted', 'Your application for Full Stack Python Developer at Infosys Technologies has been shortlisted!', 'application', 0),
    (2, 6, 'Interview Scheduled', 'Interview scheduled for Junior Backend Developer (Python) on Google Meet.', 'application', 0),
    (3, 7, 'Job Offer Released', 'Congratulations! You have received an employment offer from Tata Consultancy Services.', 'application', 1),
    (4, 2, 'Subscription Activated', 'Your Recruiter Premium plan has been renewed successfully. Valid until 2026-11-14.', 'subscription', 1),
    (5, 3, 'Enterprise Plan Active', 'Your Enterprise Unlimited plan is active with 50 job postings allowed.', 'subscription', 1),
    (6, 6, 'New Job Alert', 'A new job matching your skill "Python" was posted: Junior Backend Developer.', 'job_alert', 0);
    """
    cursor.executescript(seed_sql)
    conn.commit()
    print("[SUCCESS] Seed data loaded.")

    # 3. Integrity Verification
    print("\n--> [3/4] Verifying Foreign Key Integrity and Table Row Counts...")
    fk_check = cursor.execute("PRAGMA foreign_key_check;").fetchall()
    if fk_check:
        print(f"[ERROR] Foreign key violations found: {fk_check}")
        sys.exit(1)
    else:
        print("[SUCCESS] PRAGMA foreign_key_check passed with 0 violations.")

    tables = [
        "users", "companies", "job_seekers", "recruiters", "subscription_plans",
        "recruiter_subscriptions", "payments", "invoices", "jobs", "skills",
        "job_skills", "seeker_skills", "resumes", "applications", "application_tracking",
        "saved_jobs", "notifications"
    ]
    print(f"\n{'Table Name':<28} | {'Rows':<6}")
    print("-" * 38)
    for tbl in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0]
        print(f"{tbl:<28} | {count:<6}")

    # 4. Run Sample Analytical Reports
    print("\n--> [4/4] Executing Key Analytical Queries...")
    
    print("\n[Report A] Admin KPI Summary:")
    kpi_query = """
    SELECT 
        (SELECT COUNT(*) FROM users WHERE role = 'job_seeker') AS total_job_seekers,
        (SELECT COUNT(*) FROM users WHERE role = 'recruiter') AS total_recruiters,
        (SELECT COUNT(*) FROM jobs WHERE status = 'open') AS open_jobs,
        (SELECT COUNT(*) FROM applications) AS applications_count,
        (SELECT SUM(total_amount) FROM invoices) AS total_revenue_inr;
    """
    row = cursor.execute(kpi_query).fetchone()
    print(f"Seekers: {row[0]} | Recruiters: {row[1]} | Open Jobs: {row[2]} | Applications: {row[3]} | Total Revenue: INR {row[4]:,.2f}")

    print("\n[Report B] Recruiter Quota & Plan Status:")
    quota_query = """
    SELECT 
        u.full_name AS recruiter,
        c.company_name,
        COALESCE(sp.plan_name, 'Free') AS plan,
        COALESCE(sp.job_posting_limit, 2) AS limit_allowed,
        COUNT(j.job_id) AS jobs_posted
    FROM recruiters r
    JOIN users u ON r.user_id = u.user_id
    JOIN companies c ON r.company_id = c.company_id
    LEFT JOIN recruiter_subscriptions rs ON r.recruiter_id = rs.recruiter_id AND rs.status = 'active'
    LEFT JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
    LEFT JOIN jobs j ON r.recruiter_id = j.recruiter_id
    GROUP BY r.recruiter_id, u.full_name, c.company_name, sp.plan_name, sp.job_posting_limit;
    """
    for r in cursor.execute(quota_query).fetchall():
        print(f"  * {r[0]} ({r[1]}): {r[2]} Plan | Limit: {r[3]} jobs | Posted: {r[4]} jobs")

    print("\n[Report C] Candidate Skill-Matching for Kamal Sen (Seeker #1):")
    match_query = """
    SELECT 
        j.job_title,
        c.company_name,
        COUNT(js_req.skill_id) AS required_skills,
        COUNT(cand_s.skill_id) AS matched_skills,
        ROUND((COUNT(cand_s.skill_id) * 100.0 / COUNT(js_req.skill_id)), 1) AS match_pct
    FROM jobs j
    JOIN companies c ON j.company_id = c.company_id
    JOIN job_skills js_req ON j.job_id = js_req.job_id
    LEFT JOIN seeker_skills cand_s ON js_req.skill_id = cand_s.skill_id AND cand_s.seeker_id = 1
    WHERE j.status = 'open'
    GROUP BY j.job_id, j.job_title, c.company_name
    HAVING match_pct > 0
    ORDER BY match_pct DESC;
    """
    for r in cursor.execute(match_query).fetchall():
        print(f"  * {r[0]} @ {r[1]}: {r[3]}/{r[2]} skills ({r[4]}% match)")

    conn.close()
    print("\n" + "=" * 80)
    print(f"[SUCCESS] Database initialized and verified at: {DB_PATH}")
    print("=" * 80)

if __name__ == "__main__":
    init_database()
