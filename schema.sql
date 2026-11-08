-- =============================================================================
-- ONLINE JOB PORTAL MANAGEMENT SYSTEM WITH RECRUITER PREMIUM SUBSCRIPTION
-- Database Schema Definition (MySQL 8.0+ Compatible)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS online_job_portal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE online_job_portal;

-- Disable foreign key checks during table setup
SET FOREIGN_KEY_CHECKS = 0;

-- Drop existing tables to allow clean re-runs
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

-- Drop views if existing
DROP VIEW IF EXISTS vw_active_jobs_with_company;
DROP VIEW IF EXISTS vw_recruiter_dashboard_stats;
DROP VIEW IF EXISTS vw_job_seeker_applications;
DROP VIEW IF EXISTS vw_admin_revenue_and_subscriptions;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- MODULE 1: USER REGISTRATION & AUTHENTICATION
-- =============================================================================

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    role ENUM('admin', 'recruiter', 'job_seeker') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_role (role),
    INDEX idx_user_email (email)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 3 & 4 (SUPPORTING): COMPANIES
-- =============================================================================

CREATE TABLE companies (
    company_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL UNIQUE,
    industry VARCHAR(100) NOT NULL,
    website VARCHAR(255),
    location VARCHAR(100) NOT NULL,
    company_size VARCHAR(50) DEFAULT '11-50 employees',
    description TEXT,
    logo_url VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_company_name (company_name),
    INDEX idx_company_location (location)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 2: JOB SEEKER MANAGEMENT
-- =============================================================================

CREATE TABLE job_seekers (
    seeker_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    headline VARCHAR(150),
    qualification VARCHAR(100) NOT NULL,
    experience_years DECIMAL(3, 1) DEFAULT 0.0,
    current_location VARCHAR(100) NOT NULL,
    expected_salary DECIMAL(10, 2),
    bio TEXT,
    linkedin_url VARCHAR(255),
    github_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_seekers_users FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_seeker_location (current_location),
    INDEX idx_seeker_experience (experience_years)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 3: RECRUITER MANAGEMENT
-- =============================================================================

CREATE TABLE recruiters (
    recruiter_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    company_id INT NOT NULL,
    designation VARCHAR(100) NOT NULL,
    department VARCHAR(100) DEFAULT 'Human Resources',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_recruiters_users FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_recruiters_companies FOREIGN KEY (company_id) 
        REFERENCES companies(company_id) ON DELETE RESTRICT,
    INDEX idx_recruiter_company (company_id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 10: RECRUITER PREMIUM SUBSCRIPTION PLANS
-- =============================================================================

CREATE TABLE subscription_plans (
    plan_id INT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(50) NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    duration_days INT NOT NULL DEFAULT 30,
    job_posting_limit INT NOT NULL DEFAULT 2,
    candidate_search_limit INT NOT NULL DEFAULT 20,
    featured_jobs_allowed BOOLEAN DEFAULT FALSE,
    priority_support BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 10 (CONT.): RECRUITER SUBSCRIPTION PURCHASES
-- =============================================================================

CREATE TABLE recruiter_subscriptions (
    subscription_id INT AUTO_INCREMENT PRIMARY KEY,
    recruiter_id INT NOT NULL,
    plan_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('active', 'expired', 'cancelled', 'pending') DEFAULT 'active',
    auto_renew BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_recruiter_sub_recruiter FOREIGN KEY (recruiter_id) 
        REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
    CONSTRAINT fk_recruiter_sub_plan FOREIGN KEY (plan_id) 
        REFERENCES subscription_plans(plan_id) ON DELETE RESTRICT,
    INDEX idx_sub_status (status),
    INDEX idx_sub_dates (start_date, end_date)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 11: PAYMENT MANAGEMENT & INVOICING
-- =============================================================================

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    subscription_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL DEFAULT 'Razorpay',
    transaction_id VARCHAR(100) NOT NULL UNIQUE,
    payment_status ENUM('success', 'pending', 'failed', 'refunded') NOT NULL DEFAULT 'success',
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    gateway_response TEXT,
    CONSTRAINT fk_payments_subscription FOREIGN KEY (subscription_id) 
        REFERENCES recruiter_subscriptions(subscription_id) ON DELETE CASCADE,
    INDEX idx_payment_status (payment_status),
    INDEX idx_payment_txn (transaction_id)
) ENGINE=InnoDB;

CREATE TABLE invoices (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    payment_id INT NOT NULL UNIQUE,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    tax_amount DECIMAL(10, 2) DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL,
    issued_date DATE NOT NULL,
    invoice_pdf_path VARCHAR(255),
    CONSTRAINT fk_invoices_payments FOREIGN KEY (payment_id) 
        REFERENCES payments(payment_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 4 & 5: JOB POSTING, MANAGEMENT & SEARCH
-- =============================================================================

CREATE TABLE jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    recruiter_id INT NOT NULL,
    company_id INT NOT NULL,
    job_title VARCHAR(150) NOT NULL,
    job_type ENUM('Full-time', 'Part-time', 'Contract', 'Internship', 'Remote') NOT NULL DEFAULT 'Full-time',
    experience_level ENUM('Entry', 'Mid', 'Senior', 'Lead') NOT NULL DEFAULT 'Mid',
    location VARCHAR(100) NOT NULL,
    salary_min DECIMAL(10, 2) NOT NULL,
    salary_max DECIMAL(10, 2) NOT NULL,
    description TEXT NOT NULL,
    requirements TEXT,
    open_vacancies INT DEFAULT 1,
    is_featured BOOLEAN DEFAULT FALSE,
    deadline DATE NOT NULL,
    status ENUM('open', 'closed', 'paused') DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_jobs_recruiters FOREIGN KEY (recruiter_id) 
        REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
    CONSTRAINT fk_jobs_companies FOREIGN KEY (company_id) 
        REFERENCES companies(company_id) ON DELETE RESTRICT,
    CONSTRAINT chk_salary CHECK (salary_max >= salary_min),
    INDEX idx_job_title (job_title),
    INDEX idx_job_location (location),
    INDEX idx_job_type (job_type),
    INDEX idx_job_status (status),
    INDEX idx_job_salary (salary_min, salary_max)
) ENGINE=InnoDB;

-- =============================================================================
-- SKILLS MODULE (SUPPORTING SEARCH & FILTERING)
-- =============================================================================

CREATE TABLE skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(50) NOT NULL UNIQUE,
    category VARCHAR(50) DEFAULT 'Technical'
) ENGINE=InnoDB;

CREATE TABLE job_skills (
    job_id INT NOT NULL,
    skill_id INT NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (job_id, skill_id),
    CONSTRAINT fk_job_skills_job FOREIGN KEY (job_id) 
        REFERENCES jobs(job_id) ON DELETE CASCADE,
    CONSTRAINT fk_job_skills_skill FOREIGN KEY (skill_id) 
        REFERENCES skills(skill_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE seeker_skills (
    seeker_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level ENUM('Beginner', 'Intermediate', 'Expert') DEFAULT 'Intermediate',
    PRIMARY KEY (seeker_id, skill_id),
    CONSTRAINT fk_seeker_skills_seeker FOREIGN KEY (seeker_id) 
        REFERENCES job_seekers(seeker_id) ON DELETE CASCADE,
    CONSTRAINT fk_seeker_skills_skill FOREIGN KEY (skill_id) 
        REFERENCES skills(skill_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 7: RESUME UPLOAD & MANAGEMENT
-- =============================================================================

CREATE TABLE resumes (
    resume_id INT AUTO_INCREMENT PRIMARY KEY,
    seeker_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    file_size_kb INT NOT NULL,
    is_primary BOOLEAN DEFAULT TRUE,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resumes_seeker FOREIGN KEY (seeker_id) 
        REFERENCES job_seekers(seeker_id) ON DELETE CASCADE,
    INDEX idx_resume_seeker (seeker_id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 6: ONLINE JOB APPLICATIONS
-- =============================================================================

CREATE TABLE applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    seeker_id INT NOT NULL,
    resume_id INT NOT NULL,
    cover_letter TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_status ENUM('applied', 'screening', 'shortlisted', 'interview_scheduled', 'offered', 'accepted', 'rejected') 
        DEFAULT 'applied',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_seeker_job_application UNIQUE (seeker_id, job_id),
    CONSTRAINT fk_applications_job FOREIGN KEY (job_id) 
        REFERENCES jobs(job_id) ON DELETE CASCADE,
    CONSTRAINT fk_applications_seeker FOREIGN KEY (seeker_id) 
        REFERENCES job_seekers(seeker_id) ON DELETE CASCADE,
    CONSTRAINT fk_applications_resume FOREIGN KEY (resume_id) 
        REFERENCES resumes(resume_id) ON DELETE RESTRICT,
    INDEX idx_app_status (current_status),
    INDEX idx_app_job (job_id),
    INDEX idx_app_seeker (seeker_id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 8: APPLICATION TRACKING TIMELINE
-- =============================================================================

CREATE TABLE application_tracking (
    tracking_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    status ENUM('applied', 'screening', 'shortlisted', 'interview_scheduled', 'offered', 'accepted', 'rejected') NOT NULL,
    remarks TEXT,
    changed_by_user_id INT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tracking_application FOREIGN KEY (application_id) 
        REFERENCES applications(application_id) ON DELETE CASCADE,
    CONSTRAINT fk_tracking_user FOREIGN KEY (changed_by_user_id) 
        REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_tracking_app (application_id)
) ENGINE=InnoDB;

-- =============================================================================
-- BOOKMARKED / SAVED JOBS
-- =============================================================================

CREATE TABLE saved_jobs (
    saved_id INT AUTO_INCREMENT PRIMARY KEY,
    seeker_id INT NOT NULL,
    job_id INT NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_seeker_saved_job UNIQUE (seeker_id, job_id),
    CONSTRAINT fk_saved_seeker FOREIGN KEY (seeker_id) 
        REFERENCES job_seekers(seeker_id) ON DELETE CASCADE,
    CONSTRAINT fk_saved_job FOREIGN KEY (job_id) 
        REFERENCES jobs(job_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================================
-- MODULE 12: NOTIFICATIONS
-- =============================================================================

CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    notification_type ENUM('application', 'subscription', 'job_alert', 'system') DEFAULT 'application',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) 
        REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_notif_user (user_id, is_read)
) ENGINE=InnoDB;

-- =============================================================================
-- VIEWS FOR REPORTING & DASHBOARDS
-- =============================================================================

-- 1. Active Jobs with Company details (for Job Seeker search)
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
WHERE j.status = 'open' AND j.deadline >= CURDATE()
GROUP BY j.job_id, c.company_id, r.recruiter_id, u.full_name;

-- 2. Recruiter Dashboard Stats
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
    ON r.recruiter_id = rs.recruiter_id AND rs.status = 'active' AND rs.end_date >= CURDATE()
LEFT JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
LEFT JOIN jobs j ON r.recruiter_id = j.recruiter_id
LEFT JOIN applications a ON j.job_id = a.job_id
GROUP BY r.recruiter_id, u.full_name, c.company_name, sp.plan_name, rs.status, sp.job_posting_limit;

-- 3. Job Seeker Application Pipeline
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

-- 4. Admin Revenue and Subscription Analytics
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

-- =============================================================================
-- STORED PROCEDURES & TRIGGERS
-- =============================================================================

DELIMITER $$

-- Procedure 1: Apply for Job (Safe transactional application)
CREATE PROCEDURE sp_apply_for_job(
    IN p_seeker_id INT,
    IN p_job_id INT,
    IN p_resume_id INT,
    IN p_cover_letter TEXT,
    OUT p_application_id INT,
    OUT p_status_message VARCHAR(255)
)
BEGIN
    DECLARE v_job_status VARCHAR(20);
    DECLARE v_already_applied INT DEFAULT 0;

    -- Check if job is open
    SELECT status INTO v_job_status FROM jobs WHERE job_id = p_job_id;
    
    IF v_job_status IS NULL THEN
        SET p_status_message = 'ERROR: Job does not exist';
        SET p_application_id = -1;
    ELSEIF v_job_status <> 'open' THEN
        SET p_status_message = 'ERROR: Job is not currently open for applications';
        SET p_application_id = -1;
    ELSE
        -- Check duplicate
        SELECT COUNT(*) INTO v_already_applied 
        FROM applications 
        WHERE seeker_id = p_seeker_id AND job_id = p_job_id;

        IF v_already_applied > 0 THEN
            SET p_status_message = 'ERROR: Candidate has already applied for this job';
            SET p_application_id = -1;
        ELSE
            INSERT INTO applications (job_id, seeker_id, resume_id, cover_letter, current_status)
            VALUES (p_job_id, p_seeker_id, p_resume_id, p_cover_letter, 'applied');
            
            SET p_application_id = LAST_INSERT_ID();
            
            -- Insert initial tracking record
            INSERT INTO application_tracking (application_id, status, remarks, changed_by_user_id)
            SELECT p_application_id, 'applied', 'Application submitted by candidate', user_id
            FROM job_seekers WHERE seeker_id = p_seeker_id;

            SET p_status_message = 'SUCCESS: Application submitted successfully';
        END IF;
    END IF;
END$$

-- Procedure 2: Recruiter Post Job (Validates subscription posting limit)
CREATE PROCEDURE sp_post_job(
    IN p_recruiter_id INT,
    IN p_company_id INT,
    IN p_job_title VARCHAR(150),
    IN p_job_type VARCHAR(50),
    IN p_experience_level VARCHAR(20),
    IN p_location VARCHAR(100),
    IN p_salary_min DECIMAL(10,2),
    IN p_salary_max DECIMAL(10,2),
    IN p_description TEXT,
    IN p_requirements TEXT,
    IN p_vacancies INT,
    IN p_is_featured BOOLEAN,
    IN p_deadline DATE,
    OUT p_job_id INT,
    OUT p_status_message VARCHAR(255)
)
BEGIN
    DECLARE v_plan_limit INT DEFAULT 2; -- Default free plan limit
    DECLARE v_current_jobs_count INT DEFAULT 0;

    -- Check current active subscription plan limit
    SELECT COALESCE(sp.job_posting_limit, 2) INTO v_plan_limit
    FROM recruiters r
    LEFT JOIN recruiter_subscriptions rs 
        ON r.recruiter_id = rs.recruiter_id AND rs.status = 'active' AND rs.end_date >= CURDATE()
    LEFT JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
    WHERE r.recruiter_id = p_recruiter_id
    ORDER BY rs.created_at DESC
    LIMIT 1;

    -- Count active jobs currently posted by recruiter
    SELECT COUNT(*) INTO v_current_jobs_count
    FROM jobs
    WHERE recruiter_id = p_recruiter_id AND status = 'open';

    IF v_current_jobs_count >= v_plan_limit THEN
        SET p_status_message = CONCAT('LIMIT REACHED: Your plan allows max ', v_plan_limit, ' active jobs. Please upgrade to Premium.');
        SET p_job_id = -1;
    ELSE
        INSERT INTO jobs (
            recruiter_id, company_id, job_title, job_type, experience_level,
            location, salary_min, salary_max, description, requirements,
            open_vacancies, is_featured, deadline, status
        ) VALUES (
            p_recruiter_id, p_company_id, p_job_title, p_job_type, p_experience_level,
            p_location, p_salary_min, p_salary_max, p_description, p_requirements,
            p_vacancies, p_is_featured, p_deadline, 'open'
        );

        SET p_job_id = LAST_INSERT_ID();
        SET p_status_message = 'SUCCESS: Job vacancy published successfully';
    END IF;
END$$

-- Procedure 3: Purchase Recruiter Subscription & Process Payment
CREATE PROCEDURE sp_purchase_subscription(
    IN p_recruiter_id INT,
    IN p_plan_id INT,
    IN p_payment_method VARCHAR(50),
    IN p_transaction_id VARCHAR(100),
    OUT p_subscription_id INT,
    OUT p_status_message VARCHAR(255)
)
BEGIN
    DECLARE v_duration INT;
    DECLARE v_price DECIMAL(10,2);
    DECLARE v_start_date DATE;
    DECLARE v_end_date DATE;
    DECLARE v_payment_id INT;
    DECLARE v_invoice_no VARCHAR(50);

    SELECT duration_days, price INTO v_duration, v_price
    FROM subscription_plans WHERE plan_id = p_plan_id;

    IF v_duration IS NULL THEN
        SET p_status_message = 'ERROR: Plan not found';
        SET p_subscription_id = -1;
    ELSE
        SET v_start_date = CURDATE();
        SET v_end_date = DATE_ADD(CURDATE(), INTERVAL v_duration DAY);

        -- Expire any current active subscription
        UPDATE recruiter_subscriptions 
        SET status = 'expired'
        WHERE recruiter_id = p_recruiter_id AND status = 'active';

        -- Insert new subscription
        INSERT INTO recruiter_subscriptions (recruiter_id, plan_id, start_date, end_date, status)
        VALUES (p_recruiter_id, p_plan_id, v_start_date, v_end_date, 'active');
        
        SET p_subscription_id = LAST_INSERT_ID();

        -- Record payment
        INSERT INTO payments (subscription_id, amount, payment_method, transaction_id, payment_status)
        VALUES (p_subscription_id, v_price, p_payment_method, p_transaction_id, 'success');
        
        SET v_payment_id = LAST_INSERT_ID();

        -- Generate invoice
        SET v_invoice_no = CONCAT('INV-', YEAR(CURDATE()), '-', LPAD(v_payment_id, 5, '0'));
        INSERT INTO invoices (payment_id, invoice_number, tax_amount, total_amount, issued_date)
        VALUES (v_payment_id, v_invoice_no, ROUND(v_price * 0.18, 2), ROUND(v_price * 1.18, 2), CURDATE());

        -- Send notification to recruiter
        INSERT INTO notifications (user_id, title, message, notification_type)
        SELECT u.user_id, 'Subscription Activated', 
               CONCAT('Your plan has been upgraded successfully. Valid until ', v_end_date), 'subscription'
        FROM recruiters r JOIN users u ON r.user_id = u.user_id
        WHERE r.recruiter_id = p_recruiter_id;

        SET p_status_message = 'SUCCESS: Premium subscription activated and invoice generated';
    END IF;
END$$

-- Trigger: Automatically log status change history in application_tracking
CREATE TRIGGER trg_after_application_status_update
AFTER UPDATE ON applications
FOR EACH ROW
BEGIN
    IF OLD.current_status <> NEW.current_status THEN
        INSERT INTO application_tracking (application_id, status, remarks, changed_by_user_id)
        VALUES (NEW.application_id, NEW.current_status, 
                CONCAT('Status updated from ', OLD.current_status, ' to ', NEW.current_status), NULL);
        
        -- Send notification to the job seeker
        INSERT INTO notifications (user_id, title, message, notification_type)
        SELECT js.user_id, 'Application Status Update',
               CONCAT('Your application status has changed to: ', NEW.current_status), 'application'
        FROM job_seekers js WHERE js.seeker_id = NEW.seeker_id;
    END IF;
END$$

DELIMITER ;
