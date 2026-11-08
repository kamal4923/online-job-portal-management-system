"""Populate 500 realistic tech jobs in the online job portal database."""

import sqlite3
import random
import os
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "job_portal.db")

def populate(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    print("--> Expanding Companies...")
    companies = [
        ("Google India", "Internet & Cloud", "https://google.com/about/careers", "Bengaluru, Karnataka", "10000+ employees", "Global leader in search, cloud, and AI systems.", 1),
        ("Microsoft India", "Enterprise Software", "https://careers.microsoft.com", "Hyderabad, Telangana", "10000+ employees", "Empowering individuals and organizations with cloud & AI.", 1),
        ("Amazon Development Center", "E-Commerce & Cloud", "https://amazon.jobs", "Bengaluru, Karnataka", "10000+ employees", "Earth's most customer-centric company and AWS cloud platform.", 1),
        ("Infosys Technologies", "Information Technology", "https://infosys.com", "Bengaluru, Karnataka", "10000+ employees", "Next-generation digital services and consulting.", 1),
        ("Tata Consultancy Services", "Enterprise IT", "https://tcs.com", "Mumbai, Maharashtra", "10000+ employees", "World-renowned IT consulting and enterprise software.", 1),
        ("Wipro Technologies", "IT & Consulting", "https://wipro.com", "Bengaluru, Karnataka", "10000+ employees", "Global information technology and business consulting.", 1),
        ("Razorpay", "FinTech & Payments", "https://razorpay.com", "Bengaluru, Karnataka", "1001-5000 employees", "India's leading full-stack financial services and payment gateway.", 1),
        ("CRED", "FinTech & SaaS", "https://cred.club", "Bengaluru, Karnataka", "501-1000 employees", "Reward-centric credit card bill payment and lifestyle platform.", 1),
        ("Zerodha", "Stockbroking & Fintech", "https://zerodha.com", "Bengaluru, Karnataka", "1001-5000 employees", "Pioneering Indian discount brokerage and investment tech.", 1),
        ("Swiggy", "Consumer Tech & Food", "https://swiggy.com", "Bengaluru, Karnataka", "5001-10000 employees", "Leading on-demand food delivery and quick commerce network.", 1),
        ("Zomato", "FoodTech & Logistics", "https://zomato.com", "Gurgaon, Haryana", "5001-10000 employees", "Connecting consumers with dining and quick commerce delivery.", 1),
        ("Flipkart", "E-Commerce", "https://flipkart.com", "Bengaluru, Karnataka", "10000+ employees", "India's homegrown e-commerce marketplace.", 1),
        ("Postman", "API Platform", "https://postman.com", "Bengaluru, Karnataka", "501-1000 employees", "The world's leading API development and collaboration platform.", 1),
        ("BrowserStack", "Developer Tools", "https://browserstack.com", "Mumbai, Maharashtra", "1001-5000 employees", "World's leading software testing and cross-browser cloud platform.", 1),
        ("Freshworks", "Enterprise SaaS", "https://freshworks.com", "Chennai, Tamil Nadu", "5001-10000 employees", "Delightful modern customer engagement and CRM software.", 1),
        ("Zoho Corporation", "Business Software", "https://zoho.com", "Chennai, Tamil Nadu", "10000+ employees", "Comprehensive business software operating system on the cloud.", 1),
        ("CloudScale Systems", "Cloud & DevOps", "https://cloudscale.io", "Pune, Maharashtra", "51-200 employees", "Automated multi-cloud architecture and Kubernetes platforms.", 1),
        ("FinEdge Innovations", "Financial Technology", "https://finedge.io", "Hyderabad, Telangana", "201-500 employees", "Next-gen payment processing infrastructure.", 1),
        ("NextGen AI Labs", "Artificial Intelligence", "https://nextgenai.tech", "Bengaluru, Karnataka", "11-50 employees", "Enterprise Generative AI agents automation.", 1),
        ("PhonePe", "Digital Payments", "https://phonepe.com", "Bengaluru, Karnataka", "5001-10000 employees", "India's leading digital payment app on UPI network.", 1),
        ("Paytm", "FinTech & Payments", "https://paytm.com", "Noida, Uttar Pradesh", "10000+ employees", "Digital ecosystem for consumer payments and merchant commerce.", 1),
        ("Zepto", "Quick Commerce", "https://zeptonow.com", "Mumbai, Maharashtra", "1001-5000 employees", "Ultra-fast 10-minute grocery delivery network.", 1),
        ("Meesho", "Social E-Commerce", "https://meesho.io", "Bengaluru, Karnataka", "1001-5000 employees", "Democratizing internet commerce for small enterprises in India.", 1),
        ("Groww", "Investment Tech", "https://groww.in", "Bengaluru, Karnataka", "1001-5000 employees", "Fast-growing investment and direct mutual funds platform.", 1),
        ("Fractal Analytics", "Data & AI", "https://fractal.ai", "Mumbai, Maharashtra", "5001-10000 employees", "Powering human decisions through AI and analytics.", 1)
    ]

    for comp in companies:
        cursor.execute("""
            INSERT OR IGNORE INTO companies (company_name, industry, website, location, company_size, description, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, comp)
    conn.commit()

    # Get company IDs
    comp_ids = [r[0] for r in cursor.execute("SELECT company_id FROM companies").fetchall()]

    print("--> Expanding Recruiters...")
    # Add recruiter users if needed
    more_recruiters = [
        ("Anand Verma", "anand.verma@google.com", "+91 9811122233", "google.com"),
        ("Shweta Sen", "shweta.sen@microsoft.com", "+91 9822233344", "microsoft.com"),
        ("Ravi Shankar", "ravi.shankar@amazon.com", "+91 9833344455", "amazon.jobs"),
        ("Deepika Rao", "deepika.rao@razorpay.com", "+91 9844455566", "razorpay.com"),
        ("Vikram Malhotra", "vikram.m@cred.club", "+91 9855566677", "cred.club"),
        ("Nisha Agarwal", "nisha.a@swiggy.in", "+91 9866677788", "swiggy.com"),
        ("Siddharth Roy", "siddharth@postman.com", "+91 9877788899", "postman.com"),
        ("Pooja Hegde", "pooja.h@browserstack.com", "+91 9888899900", "browserstack.com"),
        ("Karthik Sundaram", "karthik.s@zoho.com", "+91 9899900011", "zoho.com"),
        ("Manoj Tiwari", "manoj.t@flipkart.com", "+91 9810011002", "flipkart.com")
    ]

    for name, email, phone, domain in more_recruiters:
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("""
                INSERT INTO users (full_name, email, password_hash, phone, role)
                VALUES (?, ?, '$2b$12$RecruiterAutoDemo', ?, 'recruiter')
            """, (name, email, phone))
            uid = cursor.lastrowid
            
            # Match company
            cid = random.choice(comp_ids)
            cursor.execute("""
                INSERT INTO recruiters (user_id, company_id, designation, department, is_verified)
                VALUES (?, ?, 'Lead Talent Partner', 'Technical Staffing', 1)
            """, (uid, cid))
            rid = cursor.lastrowid
            
            # Active enterprise subscription
            cursor.execute("""
                INSERT INTO recruiter_subscriptions (recruiter_id, plan_id, start_date, end_date, status, auto_renew)
                VALUES (?, 3, '2026-11-01', '2027-01-31', 'active', 1)
            """, (rid,))
    conn.commit()

    recruiter_ids = [r[0] for r in cursor.execute("SELECT recruiter_id FROM recruiters").fetchall()]

    print("--> Expanding Skills Taxonomy...")
    skills_list = [
        ("Python", "Programming Languages"),
        ("Django", "Frameworks & Web"),
        ("FastAPI", "Frameworks & Web"),
        ("Flask", "Frameworks & Web"),
        ("SQL / MySQL", "Databases"),
        ("PostgreSQL", "Databases"),
        ("MongoDB", "Databases"),
        ("Redis", "Databases & Caching"),
        ("React.js", "Frontend Frameworks"),
        ("Next.js", "Frontend Frameworks"),
        ("TypeScript", "Programming Languages"),
        ("JavaScript", "Programming Languages"),
        ("Vue.js", "Frontend Frameworks"),
        ("Node.js", "Backend Engineering"),
        ("Java", "Programming Languages"),
        ("Spring Boot", "Frameworks & Web"),
        ("Go (Golang)", "Programming Languages"),
        ("C++", "Programming Languages"),
        ("Rust", "Programming Languages"),
        ("AWS Cloud", "Cloud Infrastructure"),
        ("Microsoft Azure", "Cloud Infrastructure"),
        ("Google Cloud (GCP)", "Cloud Infrastructure"),
        ("Docker", "DevOps & Tools"),
        ("Kubernetes", "DevOps & Tools"),
        ("Terraform", "DevOps & Tools"),
        ("CI/CD Pipelines", "DevOps & Tools"),
        ("Data Analysis", "Data & Analytics"),
        ("Machine Learning", "Artificial Intelligence"),
        ("Deep Learning", "Artificial Intelligence"),
        ("PyTorch", "Artificial Intelligence"),
        ("TensorFlow", "Artificial Intelligence"),
        ("GraphQL", "Backend Engineering"),
        ("REST API Design", "Backend Engineering"),
        ("Microservices Architecture", "Architecture"),
        ("Flutter", "Mobile Development"),
        ("Swift (iOS)", "Mobile Development"),
        ("Kotlin (Android)", "Mobile Development"),
        ("Cyber Security", "Security"),
        ("Linux Administration", "Infrastructure"),
        ("Kafka", "Distributed Systems")
    ]

    for s_name, s_cat in skills_list:
        cursor.execute("INSERT OR IGNORE INTO skills (skill_name, category) VALUES (?, ?)", (s_name, s_cat))
    conn.commit()

    all_skills = cursor.execute("SELECT skill_id, skill_name FROM skills").fetchall()
    skill_id_map = {name: sid for sid, name in all_skills}
    skill_ids_pool = [sid for sid, _ in all_skills]

    print("--> Generating 500+ Tech Jobs...")
    # Job title templates with typical skill requirements
    templates = [
        ("Full Stack Python Developer", ["Python", "Django", "SQL / MySQL", "REST API Design", "React.js"], 800000, 1600000, "Full-time", "Mid"),
        ("Senior Python Backend Engineer", ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"], 1400000, 2400000, "Full-time", "Senior"),
        ("Junior Python Developer", ["Python", "SQL / MySQL", "REST API Design"], 450000, 750000, "Full-time", "Entry"),
        ("Python & Django Architect", ["Python", "Django", "Microservices Architecture", "PostgreSQL", "AWS Cloud"], 2400000, 3800000, "Full-time", "Lead"),
        ("AI / ML Python Engineer", ["Python", "Machine Learning", "Deep Learning", "PyTorch", "Data Analysis"], 1200000, 2600000, "Full-time", "Mid"),
        ("Data Analyst & SQL Specialist", ["SQL / MySQL", "Data Analysis", "Python", "PostgreSQL"], 600000, 1100000, "Full-time", "Mid"),
        ("Senior React Frontend Engineer", ["React.js", "TypeScript", "Next.js", "JavaScript", "REST API Design"], 1100000, 2000000, "Full-time", "Senior"),
        ("Frontend Developer (React / Next.js)", ["React.js", "JavaScript", "TypeScript"], 650000, 1200000, "Full-time", "Mid"),
        ("Junior Frontend Intern", ["JavaScript", "React.js"], 300000, 500000, "Internship", "Entry"),
        ("Java & Spring Boot Engineer", ["Java", "Spring Boot", "SQL / MySQL", "Microservices Architecture"], 850000, 1600000, "Full-time", "Mid"),
        ("Senior Java Microservices Architect", ["Java", "Spring Boot", "Kafka", "Docker", "Kubernetes"], 2000000, 3500000, "Full-time", "Lead"),
        ("Cloud DevOps Engineer", ["AWS Cloud", "Docker", "Kubernetes", "CI/CD Pipelines", "Linux Administration"], 1000000, 1900000, "Full-time", "Mid"),
        ("Senior Site Reliability Engineer (SRE)", ["Kubernetes", "Docker", "Linux Administration", "Terraform", "Go (Golang)"], 1800000, 3200000, "Full-time", "Senior"),
        ("AWS Cloud Infrastructure Specialist", ["AWS Cloud", "Terraform", "Docker", "CI/CD Pipelines"], 1200000, 2200000, "Full-time", "Senior"),
        ("Node.js Backend Developer", ["Node.js", "TypeScript", "MongoDB", "REST API Design"], 800000, 1500000, "Full-time", "Mid"),
        ("Golang High-Concurrency Systems Engineer", ["Go (Golang)", "Docker", "Kafka", "PostgreSQL", "Microservices Architecture"], 1600000, 3000000, "Full-time", "Senior"),
        ("Mobile App Developer (Flutter)", ["Flutter", "REST API Design", "TypeScript"], 700000, 1400000, "Full-time", "Mid"),
        ("iOS Engineer (Swift)", ["Swift (iOS)", "REST API Design"], 900000, 1800000, "Full-time", "Mid"),
        ("Android Engineer (Kotlin)", ["Kotlin (Android)", "REST API Design"], 850000, 1700000, "Full-time", "Mid"),
        ("Cyber Security Analyst", ["Cyber Security", "Linux Administration", "Python"], 900000, 1800000, "Full-time", "Mid"),
        ("Database Administrator (DBA)", ["SQL / MySQL", "PostgreSQL", "Linux Administration"], 1100000, 2000000, "Full-time", "Senior"),
        ("Generative AI & LLM Prompt Engineer", ["Python", "Deep Learning", "Machine Learning", "PyTorch"], 1500000, 2800000, "Full-time", "Senior"),
        ("SDET / Automation Test Engineer", ["Python", "Java", "CI/CD Pipelines", "Docker"], 750000, 1400000, "Full-time", "Mid"),
        ("Backend Engineer (C++)", ["C++", "Linux Administration", "Docker"], 1200000, 2400000, "Full-time", "Senior"),
        ("Systems Programmer (Rust)", ["Rust", "Linux Administration", "Docker"], 1600000, 3200000, "Full-time", "Senior")
    ]

    locations = [
        "Bengaluru, Karnataka", "Bengaluru, Karnataka", "Bengaluru, Karnataka", # Weighted
        "Hyderabad, Telangana", "Hyderabad, Telangana",
        "Pune, Maharashtra", "Pune, Maharashtra",
        "Mumbai, Maharashtra",
        "Gurgaon, Haryana",
        "Noida, Uttar Pradesh",
        "Chennai, Tamil Nadu",
        "Remote", "Remote", "Remote" # High demand for remote
    ]

    job_types = ["Full-time", "Full-time", "Full-time", "Remote", "Contract", "Internship"]

    # Current job count
    curr_jobs = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    target_jobs = 500
    needed = target_jobs - curr_jobs

    print(f"Currently have {curr_jobs} jobs. Adding {needed} more...")

    today = date.today()

    for i in range(needed):
        tmpl = random.choice(templates)
        title, req_skills, min_sal, max_sal, default_type, exp_lvl = tmpl
        
        # Add random variations
        prefixes = ["", "Senior ", "Lead ", "Staff ", "Associate ", "Principal ", ""]
        prefix = random.choice(prefixes) if exp_lvl != "Entry" else ""
        if prefix and not title.startswith("Senior") and not title.startswith("Lead"):
            final_title = f"{prefix}{title}".strip()
        else:
            final_title = title

        # Salary jitter
        jitter = random.randint(-50000, 150000)
        actual_min = max(350000, min_sal + jitter)
        actual_max = max(actual_min + 200000, max_sal + jitter * 2)

        loc = random.choice(locations)
        jtype = "Remote" if loc == "Remote" else random.choice(job_types)
        comp_id = random.choice(comp_ids)
        rec_id = random.choice(recruiter_ids)
        vacancies = random.choice([1, 2, 3, 4, 5, 8])
        is_featured = 1 if random.random() < 0.25 else 0

        deadline_days = random.randint(15, 120)
        deadline = str(today + timedelta(days=deadline_days))

        desc = f"We are hiring a passionate {final_title} to join our high-impact engineering team at {loc}. In this role, you will design, build, and deploy production systems at scale. You will work closely with cross-functional product and engineering leaders."
        requirements = f"Hands-on experience with {', '.join(req_skills[:3])}. Strong computer science fundamentals, algorithm design, clean architecture, and teamwork."

        cursor.execute("""
            INSERT INTO jobs (recruiter_id, company_id, job_title, job_type, experience_level, location, salary_min, salary_max, description, requirements, open_vacancies, is_featured, deadline, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (rec_id, comp_id, final_title, jtype, exp_lvl, loc, actual_min, actual_max, desc, requirements, vacancies, is_featured, deadline))

        job_id = cursor.lastrowid

        # Insert skill mappings
        for sname in req_skills:
            sid = skill_id_map.get(sname)
            if sid:
                cursor.execute("INSERT OR IGNORE INTO job_skills (job_id, skill_id, is_required) VALUES (?, ?, 1)", (job_id, sid))

    conn.commit()

    total_jobs = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    total_skills_tagged = cursor.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0]
    print(f"\n[SUCCESS] Total Jobs in Database now: {total_jobs}")
    print(f"[SUCCESS] Total Job-Skill mappings tagged: {total_skills_tagged}")

    conn.close()
    return total_jobs

if __name__ == "__main__":
    populate()
