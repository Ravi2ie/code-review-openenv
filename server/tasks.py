"""Task definitions with code snippets and ground-truth issues for grading."""

from models import Severity

# ─── EASY: Bug Detection ─────────────────────────────────────────────────────

EASY_SNIPPETS = [
    {
        "code": '''def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)
''',
        "filename": "math_utils.py",
        "context": "Utility function to calculate average of a list of numbers.",
        "ground_truth": [
            {
                "line_number": 5,
                "issue_type": "bug",
                "severity": Severity.HIGH,
                "description": "ZeroDivisionError when numbers list is empty",
                "keywords": ["empty", "zero", "division", "len"],
            }
        ],
    },
    {
        "code": '''def find_max(items):
    max_val = 0
    for item in items:
        if item > max_val:
            max_val = item
    return max_val
''',
        "filename": "search.py",
        "context": "Find the maximum value in a list.",
        "ground_truth": [
            {
                "line_number": 2,
                "issue_type": "bug",
                "severity": Severity.MEDIUM,
                "description": "Initializing max_val to 0 fails for lists with all negative numbers",
                "keywords": ["negative", "initial", "0", "zero", "min"],
            }
        ],
    },
    {
        "code": '''def get_user_name(user_dict):
    name = user_dict["name"]
    return name

def greet(user_dict):
    print(f"Hello, {get_user_name(user_dict)}!")
''',
        "filename": "greet.py",
        "context": "Greeting utility that reads user name from a dictionary.",
        "ground_truth": [
            {
                "line_number": 2,
                "issue_type": "bug",
                "severity": Severity.MEDIUM,
                "description": "KeyError if 'name' key is missing from user_dict; should use .get() or check key existence",
                "keywords": ["key", "missing", "KeyError", "get"],
            }
        ],
    },
]

# ─── MEDIUM: Logic & Best Practice Review ────────────────────────────────────

MEDIUM_SNIPPETS = [
    {
        "code": '''import time

def retry_request(url, max_retries=3):
    for i in range(max_retries):
        try:
            response = make_request(url)
            return response
        except Exception:
            time.sleep(1)
    return None
''',
        "filename": "http_client.py",
        "context": "HTTP client with retry logic.",
        "ground_truth": [
            {
                "line_number": 9,
                "issue_type": "logic",
                "severity": Severity.MEDIUM,
                "description": "Fixed sleep time; should use exponential backoff to avoid thundering herd",
                "keywords": ["backoff", "exponential", "sleep", "fixed", "retry"],
            },
            {
                "line_number": 8,
                "issue_type": "logic",
                "severity": Severity.MEDIUM,
                "description": "Catching bare Exception is too broad; should catch specific exceptions like ConnectionError or Timeout",
                "keywords": ["exception", "broad", "specific", "catch", "bare"],
            },
            {
                "line_number": 10,
                "issue_type": "logic",
                "severity": Severity.LOW,
                "description": "Returning None silently on failure; should raise or log the last exception",
                "keywords": ["none", "silent", "failure", "raise", "log"],
            },
        ],
    },
    {
        "code": '''def process_records(records):
    results = []
    for record in records:
        result = transform(record)
        if result is not None:
            results.append(result)
    
    # Remove duplicates
    unique = []
    for r in results:
        if r not in unique:
            unique.append(r)
    return unique
''',
        "filename": "data_pipeline.py",
        "context": "Data processing pipeline that transforms and deduplicates records.",
        "ground_truth": [
            {
                "line_number": 9,
                "issue_type": "performance",
                "severity": Severity.MEDIUM,
                "description": "O(n^2) deduplication using list; should use set or dict for O(n) dedup",
                "keywords": ["O(n", "set", "duplicate", "performance", "quadratic"],
            },
            {
                "line_number": 3,
                "issue_type": "performance",
                "severity": Severity.LOW,
                "description": "Could use list comprehension for cleaner, more Pythonic code",
                "keywords": ["comprehension", "pythonic", "list"],
            },
        ],
    },
    {
        "code": '''class DatabaseConnection:
    def __init__(self, host, port):
        self.conn = connect(host, port)
    
    def query(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    
    def close(self):
        self.conn.close()
''',
        "filename": "db.py",
        "context": "Database connection wrapper class.",
        "ground_truth": [
            {
                "line_number": 1,
                "issue_type": "logic",
                "severity": Severity.HIGH,
                "description": "No context manager support (__enter__/__exit__); connection may leak if close() is not called",
                "keywords": ["context", "manager", "leak", "close", "with", "__enter__", "__exit__"],
            },
            {
                "line_number": 6,
                "issue_type": "logic",
                "severity": Severity.MEDIUM,
                "description": "Cursor is not closed after query; should use try/finally or context manager",
                "keywords": ["cursor", "close", "finally", "leak"],
            },
        ],
    },
]

# ─── HARD: Security Vulnerability Audit ──────────────────────────────────────

HARD_SNIPPETS = [
    {
        "code": '''from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route("/search")
def search():
    query = request.args.get("q", "")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE name LIKE '%{query}%'")
    results = cursor.fetchall()
    conn.close()
    return {"results": results}
''',
        "filename": "api.py",
        "context": "Flask API endpoint for product search.",
        "ground_truth": [
            {
                "line_number": 11,
                "issue_type": "security",
                "severity": Severity.CRITICAL,
                "description": "SQL injection vulnerability: user input directly interpolated into SQL query",
                "keywords": ["sql", "injection", "parameterized", "f-string", "interpolat"],
            },
            {
                "line_number": 7,
                "issue_type": "security",
                "severity": Severity.MEDIUM,
                "description": "No input validation or sanitization on query parameter",
                "keywords": ["input", "validation", "sanitiz"],
            },
        ],
    },
    {
        "code": '''from flask import Flask, request, render_template_string

app = Flask(__name__)

@app.route("/profile")
def profile():
    username = request.args.get("name", "Guest")
    template = f"<h1>Welcome, {username}!</h1>"
    return render_template_string(template)

@app.route("/download")
def download():
    filename = request.args.get("file", "")
    filepath = f"/var/data/{filename}"
    with open(filepath, "r") as f:
        return f.read()
''',
        "filename": "web_app.py",
        "context": "Flask web application with user profile and file download.",
        "ground_truth": [
            {
                "line_number": 8,
                "issue_type": "security",
                "severity": Severity.CRITICAL,
                "description": "Server-Side Template Injection (SSTI) via render_template_string with user input",
                "keywords": ["ssti", "template", "injection", "render_template_string", "jinja"],
            },
            {
                "line_number": 8,
                "issue_type": "security",
                "severity": Severity.HIGH,
                "description": "Cross-Site Scripting (XSS): username rendered without escaping",
                "keywords": ["xss", "cross-site", "script", "escap"],
            },
            {
                "line_number": 14,
                "issue_type": "security",
                "severity": Severity.CRITICAL,
                "description": "Path traversal vulnerability: user-controlled filename allows reading arbitrary files (e.g., ../../etc/passwd)",
                "keywords": ["path", "traversal", "directory", "../", "arbitrary"],
            },
        ],
    },
    {
        "code": '''import pickle
import base64
from flask import Flask, request

app = Flask(__name__)

@app.route("/load_session", methods=["POST"])
def load_session():
    data = request.form.get("session_data", "")
    session = pickle.loads(base64.b64decode(data))
    return {"user": session.get("user", "anonymous")}

@app.route("/admin", methods=["POST"])
def admin():
    token = request.headers.get("X-Admin-Token", "")
    if token == "supersecrettoken123":
        return {"status": "admin access granted"}
    return {"status": "denied"}, 403
''',
        "filename": "auth_service.py",
        "context": "Session management and admin authentication service.",
        "ground_truth": [
            {
                "line_number": 10,
                "issue_type": "security",
                "severity": Severity.CRITICAL,
                "description": "Insecure deserialization: pickle.loads on user-supplied data allows arbitrary code execution",
                "keywords": ["pickle", "deserialization", "arbitrary", "code execution", "rce"],
            },
            {
                "line_number": 16,
                "issue_type": "security",
                "severity": Severity.CRITICAL,
                "description": "Hardcoded secret token for admin auth; should use environment variable or proper auth mechanism",
                "keywords": ["hardcoded", "secret", "token", "password", "credential"],
            },
            {
                "line_number": 16,
                "issue_type": "security",
                "severity": Severity.HIGH,
                "description": "Simple string comparison for auth is vulnerable to timing attacks; use hmac.compare_digest",
                "keywords": ["timing", "compare_digest", "hmac", "constant-time"],
            },
        ],
    },
]


TASKS = {
    "task_easy_bug_detection": {
        "name": "Easy: Bug Detection",
        "difficulty": "easy",
        "description": "Identify obvious bugs in Python code snippets.",
        "snippets": EASY_SNIPPETS,
    },
    "task_medium_logic_review": {
        "name": "Medium: Logic & Best Practice Review",
        "difficulty": "medium",
        "description": "Review code for logical errors, performance issues, and best practice violations.",
        "snippets": MEDIUM_SNIPPETS,
    },
    "task_hard_security_audit": {
        "name": "Hard: Security Vulnerability Audit",
        "difficulty": "hard",
        "description": "Detect security vulnerabilities in realistic web application code.",
        "snippets": HARD_SNIPPETS,
    },
}
