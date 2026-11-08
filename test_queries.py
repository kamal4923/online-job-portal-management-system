"""
Automated Test Suite for SQL Queries
Online Job Portal Management System
"""

import sqlite3
import os
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "job_portal.db")

class TestJobPortalDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(DB_PATH)
        cls.conn.execute("PRAGMA foreign_keys = ON;")
        cls.cursor = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_user_authentication(self):
        """Test Query 1.1: Verify user authentication lookup"""
        query = "SELECT user_id, role, is_active FROM users WHERE email = 'kamal.sen@email.com'"
        res = self.cursor.execute(query).fetchone()
        self.assertIsNotNone(res)
        self.assertEqual(res[1], 'job_seeker')
        self.assertEqual(res[2], 1)

    def test_02_job_seeker_profile(self):
        """Test Query 2.1: Verify seeker profile retrieval"""
        query = """
        SELECT u.full_name, js.qualification, COUNT(ss.skill_id)
        FROM job_seekers js
        JOIN users u ON js.user_id = u.user_id
        LEFT JOIN seeker_skills ss ON js.seeker_id = ss.seeker_id
        WHERE js.seeker_id = 1
        GROUP BY u.full_name, js.qualification
        """
        res = self.cursor.execute(query).fetchone()
        self.assertEqual(res[0], 'Kamal Sen')
        self.assertGreaterEqual(res[2], 4)

    def test_03_active_jobs_view(self):
        """Test View: vw_active_jobs_with_company"""
        query = "SELECT COUNT(*) FROM vw_active_jobs_with_company"
        count = self.cursor.execute(query).fetchone()[0]
        self.assertGreaterEqual(count, 5)

    def test_04_recruiter_subscriptions_and_limits(self):
        """Test Query 10.1: Check premium recruiter plan limits"""
        query = """
        SELECT sp.plan_name, sp.job_posting_limit
        FROM recruiter_subscriptions rs
        JOIN subscription_plans sp ON rs.plan_id = sp.plan_id
        WHERE rs.recruiter_id = 1 AND rs.status = 'active'
        """
        res = self.cursor.execute(query).fetchone()
        self.assertIn(res[0], ['Recruiter Premium', 'Enterprise Unlimited'])
        self.assertGreaterEqual(res[1], 10)

    def test_05_application_tracking_trigger(self):
        """Test Trigger: updating application status generates tracking record"""
        # Get count of tracking records before update
        initial_count = self.cursor.execute(
            "SELECT COUNT(*) FROM application_tracking WHERE application_id = 7"
        ).fetchone()[0]
        
        # Update status
        self.cursor.execute(
            "UPDATE applications SET current_status = 'screening' WHERE application_id = 7"
        )
        self.conn.commit()

        # Count after update
        new_count = self.cursor.execute(
            "SELECT COUNT(*) FROM application_tracking WHERE application_id = 7"
        ).fetchone()[0]
        
        self.assertEqual(new_count, initial_count + 1)
        
        # Verify notification was also created
        notif = self.cursor.execute(
            "SELECT message FROM notifications WHERE user_id = 11 ORDER BY notification_id DESC LIMIT 1"
        ).fetchone()
        self.assertIn("screening", notif[0])

    def test_06_revenue_summary(self):
        """Test Query 11.2: Check total gross revenue calculation"""
        query = "SELECT SUM(total_amount) FROM invoices"
        total = self.cursor.execute(query).fetchone()[0]
        self.assertGreaterEqual(total, 2356.0)

    def test_07_prevent_duplicate_application(self):
        """Test Constraint: Seeker cannot apply twice for same job"""
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "INSERT INTO applications (job_id, seeker_id, resume_id) VALUES (1, 1, 1)"
            )
            self.conn.commit()

if __name__ == "__main__":
    unittest.main()
