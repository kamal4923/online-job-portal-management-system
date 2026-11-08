"""
Zero-Dependency Web Server and SQL API for Online Job Portal
Uses only Python standard library (http.server, sqlite3, json)
"""

import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "job_portal.db")

class PortalRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/stats":
            self.handle_stats()
        elif path == "/api/table":
            table_name = params.get("name", ["users"])[0]
            self.handle_table_data(table_name)
        elif path == "/api/tables":
            self.handle_table_list()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/query":
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                data = json.loads(body)
                query = data.get("query", "")
                self.handle_custom_query(query)
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=400)
        else:
            self.send_error(404, "Endpoint not found")

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode('utf-8'))

    def get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def handle_stats(self):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            stats = {
                "seekers": cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'job_seeker'").fetchone()[0],
                "recruiters": cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'recruiter'").fetchone()[0],
                "companies": cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
                "open_jobs": cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'open'").fetchone()[0],
                "applications": cursor.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
                "active_premium": cursor.execute("SELECT COUNT(*) FROM recruiter_subscriptions WHERE status = 'active' AND plan_id > 1").fetchone()[0],
                "revenue": cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM invoices").fetchone()[0]
            }
            conn.close()
            self.send_json_response(stats)
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_table_list(self):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            rows = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            tables = [r['name'] for r in rows]
            conn.close()
            self.send_json_response({"tables": tables})
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_table_data(self, table_name):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            # Sanitize table name against known tables
            valid_tables = [r['name'] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()]
            if table_name not in valid_tables:
                self.send_json_response({"error": f"Invalid table: {table_name}"}, status=400)
                conn.close()
                return

            rows = cursor.execute(f"SELECT * FROM {table_name} LIMIT 100").fetchall()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            data = [dict(r) for r in rows]
            conn.close()
            self.send_json_response({"table": table_name, "columns": columns, "rows": data, "count": len(data)})
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=500)

    def handle_custom_query(self, query):
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            # Only allow SELECT queries for security in the demo
            trimmed = query.strip()
            if not (trimmed.upper().startswith("SELECT") or trimmed.upper().startswith("WITH") or trimmed.upper().startswith("EXPLAIN")):
                self.send_json_response({"error": "Only SELECT, WITH, or EXPLAIN queries are permitted in the web demo"}, status=400)
                conn.close()
                return

            rows = cursor.execute(query).fetchall()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            data = [dict(r) for r in rows]
            conn.close()
            self.send_json_response({"columns": columns, "rows": data, "count": len(data)})
        except Exception as e:
            self.send_json_response({"error": str(e)}, status=400)

if __name__ == "__main__":
    print(f"Starting Online Job Portal Server on http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    with socketserver.TCPServer(("", PORT), PortalRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
