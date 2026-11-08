-- =============================================================================
-- ONLINE JOB PORTAL MANAGEMENT SYSTEM - QUERIES & ANALYTICAL REPORTS
-- Production Query Suite covering all 12 modules and advanced SQL concepts
-- =============================================================================

USE online_job_portal;

-- =============================================================================
-- MODULE 1: USER REGISTRATION & AUTHENTICATION
-- =============================================================================

-- Query 1.1: User Login Verification (Retrieves user credentials and role)
SELECT 
    user_id,
    full_name,
    email,
    password_hash,
    role,
    is_active
FROM users
WHERE email = 'kamal.sen@email.com' AND is_active = TRUE;

-- Query 1.2: User Platform Distribution Count (KPI)
SELECT 
    role,
    COUNT(user_id) AS total_users,
    SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) AS active_users
FROM users
GROUP BY role;


-- =============================================================================
-- MODULE 2: JOB SEEKER MANAGEMENT
-- =============================================================================

-- Query 2.1: Complete Job Seeker Profile with Skills and Primary Resume
SELECT 
    js.seeker_id,
    u.full_name,
    u.email,
    u.phone,
    js.headline,
    js.qualification,
    js.experience_years,
    js.current_location,
    js.expected_salary,
    r.file_name AS primary_resume_file,
    GROUP_CONCAT(CONCAT(s.skill_name, ' (', ss.proficiency_level, ')') ORDER BY s.skill_name SEPARATOR ', ') AS seeker_skills
FROM job_seekers js
JOIN users u ON js.user_id = u.user_id
LEFT JOIN resumes r ON js.seeker_id = r.seeker_id AND r.is_primary = TRUE
LEFT JOIN seeker_skills ss ON js.seeker_id = ss.seeker_id
LEFT JOIN skills s ON ss.skill_id = s.skill_id
WHERE js.seeker_id = 1
GROUP BY js.seeker_id, u.full_name, u.email, u.phone, js.headline, js.qualification, 
         js.experience_years, js.current_location, js.expected_salary, r.file_name;


-- =============================================================================
-- MODULE 3: RECRUITER & COMPANY MANAGEMENT
-- =============================================================================

-- Query 3.1: Recruiter Profile with Company and Verification Details
SELECT 
    r.recruiter_id,
    u.full_name AS recruiter_name,
    u.email AS recruiter_email,
    r.designation,
    r.department,
    c.company_name,
    c.industry,
    c.location AS company_headquarters,
    c.website,
    c.is_verified AS is_company_verified,
    sp.plan_name AS active_subscription_plan
FROM recruiters r
JOIN users u ON r.user_id = u.user_id
JOIN companies c ON r.company_id = c.company_id
LEFT JOIN recruiter_subscriptions rs 
    ON r.recruiter_id = rs.recruiter_id AND rs.status = 'active' AND rs.end_date >= CURDATE()
LEFT JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
ORDER BY c.company_name;


-- =============================================================================
-- MODULE 4 & 5: JOB POSTING, SEARCH & SMART SKILL-MATCHING
-- =============================================================================

-- Query 4.1: Public Job Search with Multi-Filter (Location, Salary Range, Type)
SELECT 
    j.job_id,
    j.job_title,
    c.company_name,
    c.is_verified AS verified_company,
    j.job_type,
    j.experience_level,
    j.location,
    j.salary_min,
    j.salary_max,
    j.is_featured,
    j.deadline,
    COUNT(a.application_id) AS total_applicants
FROM jobs j
JOIN companies c ON j.company_id = c.company_id
LEFT JOIN applications a ON j.job_id = a.job_id
WHERE j.status = 'open'
  AND (j.location LIKE '%Bengaluru%' OR j.job_type = 'Remote')
  AND j.salary_min >= 500000.00
GROUP BY j.job_id, j.job_title, c.company_name, c.is_verified, j.job_type, 
         j.experience_level, j.location, j.salary_min, j.salary_max, j.is_featured, j.deadline
ORDER BY j.is_featured DESC, j.created_at DESC;

-- Query 4.2: SMART MATCHING - Candidate Skill Match Percentage for Open Jobs
-- (Calculates how many required skills the candidate possesses for each job)
SELECT 
    j.job_id,
    j.job_title,
    c.company_name,
    j.location,
    j.salary_min,
    j.salary_max,
    COUNT(js_req.skill_id) AS total_skills_required,
    COUNT(cand_s.skill_id) AS candidate_skills_matched,
    ROUND((COUNT(cand_s.skill_id) * 100.0 / NULLIF(COUNT(js_req.skill_id), 0)), 1) AS match_percentage
FROM jobs j
JOIN companies c ON j.company_id = c.company_id
JOIN job_skills js_req ON j.job_id = js_req.job_id
LEFT JOIN seeker_skills cand_s 
    ON js_req.skill_id = cand_s.skill_id AND cand_s.seeker_id = 1  -- Match for Seeker ID 1 (Kamal)
WHERE j.status = 'open'
GROUP BY j.job_id, j.job_title, c.company_name, j.location, j.salary_min, j.salary_max
HAVING match_percentage > 0
ORDER BY match_percentage DESC;


-- =============================================================================
-- MODULE 6 & 8: ONLINE APPLICATIONS & APPLICATION TRACKING
-- =============================================================================

-- Query 6.1: Recruiter Applicant Review List for a Specific Job
SELECT 
    a.application_id,
    u.full_name AS applicant_name,
    u.email AS applicant_email,
    u.phone AS applicant_phone,
    js.qualification,
    js.experience_years,
    a.current_status,
    a.applied_at,
    r.file_name AS resume_file,
    r.file_path AS resume_download_path,
    a.cover_letter
FROM applications a
JOIN job_seekers js ON a.seeker_id = js.seeker_id
JOIN users u ON js.user_id = u.user_id
JOIN resumes r ON a.resume_id = r.resume_id
WHERE a.job_id = 1
ORDER BY a.applied_at DESC;

-- Query 6.2: Candidate's Applied Jobs Dashboard & Status Tracker
SELECT 
    a.application_id,
    j.job_title,
    c.company_name,
    j.location,
    a.applied_at,
    a.current_status,
    CASE 
        WHEN a.current_status = 'applied' THEN 'Step 1 of 5: Applied'
        WHEN a.current_status = 'screening' THEN 'Step 2 of 5: In Review / Screening'
        WHEN a.current_status = 'shortlisted' THEN 'Step 3 of 5: Shortlisted for Interview'
        WHEN a.current_status = 'interview_scheduled' THEN 'Step 4 of 5: Interview Scheduled'
        WHEN a.current_status = 'offered' THEN 'Step 5 of 5: Offer Extended!'
        WHEN a.current_status = 'rejected' THEN 'Archived: Application Not Selected'
    END AS application_progress_milestone
FROM applications a
JOIN jobs j ON a.job_id = j.job_id
JOIN companies c ON j.company_id = c.company_id
WHERE a.seeker_id = 1
ORDER BY a.applied_at DESC;

-- Query 6.3: Audit Trail of Application Tracking Timeline (Full History)
SELECT 
    at.tracking_id,
    a.application_id,
    j.job_title,
    u_cand.full_name AS candidate_name,
    at.status,
    at.remarks,
    u_changer.full_name AS updated_by,
    at.changed_at
FROM application_tracking at
JOIN applications a ON at.application_id = a.application_id
JOIN jobs j ON a.job_id = j.job_id
JOIN job_seekers js ON a.seeker_id = js.seeker_id
JOIN users u_cand ON js.user_id = u_cand.user_id
LEFT JOIN users u_changer ON at.changed_by_user_id = u_changer.user_id
WHERE a.application_id = 1
ORDER BY at.changed_at ASC;


-- =============================================================================
-- MODULE 10: RECRUITER PREMIUM SUBSCRIPTION & QUOTA MONITORING
-- =============================================================================

-- Query 10.1: Recruiter Subscription Quota & Limit Enforcement Check
SELECT 
    r.recruiter_id,
    u.full_name AS recruiter_name,
    c.company_name,
    COALESCE(sp.plan_name, 'Free Plan') AS active_plan,
    COALESCE(sp.job_posting_limit, 2) AS max_jobs_allowed,
    COUNT(j.job_id) AS current_jobs_posted,
    (COALESCE(sp.job_posting_limit, 2) - COUNT(j.job_id)) AS remaining_job_slots,
    CASE 
        WHEN COUNT(j.job_id) >= COALESCE(sp.job_posting_limit, 2) 
        THEN 'QUOTA EXHAUSTED - UPGRADE REQUIRED'
        ELSE 'QUOTA AVAILABLE'
    END AS posting_permission_status
FROM recruiters r
JOIN users u ON r.user_id = u.user_id
JOIN companies c ON r.company_id = c.company_id
LEFT JOIN recruiter_subscriptions rs 
    ON r.recruiter_id = rs.recruiter_id AND rs.status = 'active' AND rs.end_date >= CURDATE()
LEFT JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
LEFT JOIN jobs j ON r.recruiter_id = j.recruiter_id AND j.status = 'open'
GROUP BY r.recruiter_id, u.full_name, c.company_name, sp.plan_name, sp.job_posting_limit;


-- =============================================================================
-- MODULE 11: PAYMENT MANAGEMENT & FINANCIAL INVOICING
-- =============================================================================

-- Query 11.1: Payment History with Invoice and Recruiter Breakdown
SELECT 
    p.payment_id,
    p.transaction_id,
    p.payment_date,
    u.full_name AS recruiter_name,
    c.company_name,
    sp.plan_name,
    p.amount AS base_amount,
    inv.tax_amount AS gst_18_percent,
    inv.total_amount AS invoice_total,
    inv.invoice_number,
    p.payment_method,
    p.payment_status
FROM payments p
JOIN invoices inv ON p.payment_id = inv.payment_id
JOIN recruiter_subscriptions rs ON p.subscription_id = rs.subscription_id
JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
JOIN recruiters r ON rs.recruiter_id = r.recruiter_id
JOIN companies c ON r.company_id = c.company_id
JOIN users u ON r.user_id = u.user_id
ORDER BY p.payment_date DESC;

-- Query 11.2: Platform Revenue Summary by Plan
SELECT 
    sp.plan_name,
    sp.price AS unit_price,
    COUNT(p.payment_id) AS successful_transactions,
    SUM(p.amount) AS total_base_revenue,
    SUM(inv.tax_amount) AS total_tax_collected,
    SUM(inv.total_amount) AS total_gross_revenue
FROM subscription_plans sp
LEFT JOIN recruiter_subscriptions rs ON sp.plan_id = rs.plan_id
LEFT JOIN payments p ON rs.subscription_id = p.subscription_id AND p.payment_status = 'success'
LEFT JOIN invoices inv ON p.payment_id = inv.payment_id
GROUP BY sp.plan_id, sp.plan_name, sp.price
ORDER BY total_gross_revenue DESC;


-- =============================================================================
-- MODULE 9: ADMIN DASHBOARD & ADVANCED ANALYTICAL REPORTS
-- =============================================================================

-- Query 9.1: Comprehensive System KPI Snapshot
SELECT 
    (SELECT COUNT(*) FROM users WHERE role = 'job_seeker') AS total_job_seekers,
    (SELECT COUNT(*) FROM users WHERE role = 'recruiter') AS total_recruiters,
    (SELECT COUNT(*) FROM companies) AS registered_companies,
    (SELECT COUNT(*) FROM jobs WHERE status = 'open') AS active_job_vacancies,
    (SELECT COUNT(*) FROM applications) AS total_applications_submitted,
    (SELECT COUNT(*) FROM recruiter_subscriptions WHERE status = 'active' AND plan_id > 1) AS active_premium_subscribers,
    (SELECT COALESCE(SUM(total_amount), 0.00) FROM invoices) AS cumulative_revenue_inr;

-- Query 9.2: Top In-Demand Technical Skills across All Open Vacancies
SELECT 
    s.skill_name,
    s.category,
    COUNT(js.job_id) AS demand_frequency,
    ROUND(COUNT(js.job_id) * 100.0 / (SELECT COUNT(*) FROM jobs WHERE status = 'open'), 1) AS percentage_of_open_jobs
FROM skills s
JOIN job_skills js ON s.skill_id = js.skill_id
JOIN jobs j ON js.job_id = j.job_id AND j.status = 'open'
GROUP BY s.skill_id, s.skill_name, s.category
ORDER BY demand_frequency DESC
LIMIT 5;

-- Query 9.3: Recruitment Funnel Conversion Drop-off (Application to Offer)
SELECT 
    current_status,
    COUNT(*) AS total_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM applications), 1) AS funnel_percentage
FROM applications
GROUP BY current_status
ORDER BY total_count DESC;

-- Query 9.4: ADVANCED SQL - Window Function: Rank Highest Paying Jobs per Industry
SELECT 
    c.industry,
    j.job_title,
    c.company_name,
    j.salary_max,
    DENSE_RANK() OVER (PARTITION BY c.industry ORDER BY j.salary_max DESC) AS industry_salary_rank
FROM jobs j
JOIN companies c ON j.company_id = c.company_id
WHERE j.status = 'open';

-- Query 9.5: Recruiter Performance Score (Applicant to Shortlist Conversion Rate)
SELECT 
    r.recruiter_id,
    u.full_name AS recruiter_name,
    c.company_name,
    COUNT(a.application_id) AS total_applicants,
    SUM(CASE WHEN a.current_status IN ('shortlisted', 'interview_scheduled', 'offered') THEN 1 ELSE 0 END) AS progressed_candidates,
    ROUND(SUM(CASE WHEN a.current_status IN ('shortlisted', 'interview_scheduled', 'offered') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(a.application_id), 0), 1) AS candidate_progression_rate_pct
FROM recruiters r
JOIN users u ON r.user_id = u.user_id
JOIN companies c ON r.company_id = c.company_id
LEFT JOIN jobs j ON r.recruiter_id = j.recruiter_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY r.recruiter_id, u.full_name, c.company_name
HAVING total_applicants > 0
ORDER BY candidate_progression_rate_pct DESC;


-- =============================================================================
-- MODULE 12: NOTIFICATIONS
-- =============================================================================

-- Query 12.1: Unread Notifications for a Logged-in User
SELECT 
    notification_id,
    title,
    message,
    notification_type,
    created_at
FROM notifications
WHERE user_id = 6 AND is_read = FALSE
ORDER BY created_at DESC;

-- Query 12.2: Mark All Notifications as Read for User
-- UPDATE notifications SET is_read = TRUE WHERE user_id = 6;
