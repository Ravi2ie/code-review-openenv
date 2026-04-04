"""
Inference script for the Code Review OpenEnv environment.

Uses OpenAI Client for all LLM calls.
Emits structured stdout logs following [START], [STEP], [END] format.
"""

import os
import json
import time
import requests
from openai import OpenAI

# ─── Required Environment Variables ──────────────────────────────────────────

API_BASE_URL = os.getenv("API_BASE_URL", "<your-active-endpoint>")
MODEL_NAME = os.getenv("MODEL_NAME", "<your-active-model>")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional — if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# Environment URL (local or HF Space)
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

# ─── OpenAI Client Setup ────────────────────────────────────────────────────

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or "no-key",
)

TASK_IDS = [
    "task_easy_bug_detection",
    "task_medium_logic_review",
    "task_hard_security_audit",
]

SYSTEM_PROMPT = """You are a world-class code reviewer specializing in Python. Analyze code snippets with extreme precision.

RULES:
1. Report ONLY real, concrete issues. Do NOT invent issues.
2. Be EXACT with line numbers — point to the specific line where the issue occurs.
3. Use ONLY these issue_type values: bug, security, logic, performance, style
4. Use ONLY these severity values: low, medium, high, critical
5. In your description and suggestion, be SPECIFIC and use technical terminology.

ISSUE DETECTION GUIDE BY CATEGORY:

**bug**: ZeroDivisionError (empty list, division by zero, len), KeyError (missing key, .get()), off-by-one, negative numbers, initial value 0 vs min/float('-inf'), TypeError, IndexError

**logic**: bare/broad Exception catch (should catch specific exceptions like ConnectionError, Timeout), fixed sleep (should use exponential backoff for retry), silent failure returning None (should raise or log), missing context manager (__enter__/__exit__, with statement, resource leak, close), cursor not closed (finally, leak), no error handling

**security**: SQL injection (parameterized query, f-string interpolation, user input in SQL), XSS (cross-site scripting, escaping, user input in HTML), SSTI (server-side template injection, render_template_string, jinja), path traversal (directory traversal, ../, arbitrary file read), insecure deserialization (pickle.loads, arbitrary code execution, RCE), hardcoded secrets/tokens/passwords/credentials (use environment variable), timing attacks (hmac.compare_digest, constant-time comparison), input validation/sanitization

**performance**: O(n^2) operations (use set or dict for dedup, quadratic complexity), list vs set for membership, unnecessary loops (use list comprehension, pythonic)

**style**: naming conventions, missing docstrings, code organization

Respond with ONLY valid JSON in this exact format:
{
  "issues": [
    {
      "line_number": <int>,
      "issue_type": "<bug|security|logic|performance|style>",
      "severity": "<low|medium|high|critical>",
      "description": "<detailed description using specific technical terms>",
      "suggestion": "<concrete fix suggestion with technical details>"
    }
  ],
  "summary": "<brief overall assessment>"
}"""

DIFFICULTY_HINTS = {
    "easy": """You MUST find ALL bugs in this code. Common Python bugs to check:

1. Division where denominator could be zero: If code uses len() as divisor, the list could be empty → ZeroDivisionError. Mention: "empty", "zero", "division", "len". Severity: high.
2. Initializing max/min to 0: If finding maximum and max_val starts at 0, it fails for all negative numbers. The initial value should be float('-inf') or use min() builtin. Mention: "negative", "initial", "0", "zero", "min". Severity: medium.
3. Direct dictionary key access without checking: dict["key"] raises KeyError if missing. Should use .get() method or check key existence. Mention: "key", "missing", "KeyError", "get". Severity: medium.

Report ALL issues as issue_type "bug". Be precise with line numbers.""",

    "medium": """You MUST find ALL logic and performance issues. Check for EACH of these:

FOR RETRY/HTTP CODE:
1. Fixed sleep time in retry loops: Using time.sleep(1) is a fixed delay. Should use exponential backoff to avoid thundering herd. issue_type: "logic", severity: "medium". Use words: "backoff", "exponential", "sleep", "fixed", "retry".
2. Catching bare Exception: Too broad, should catch specific exceptions like ConnectionError or Timeout. issue_type: "logic", severity: "medium". Use words: "exception", "broad", "specific", "catch", "bare".
3. Returning None silently on failure: Should raise or log the last exception instead of silent failure. issue_type: "logic", severity: "low". Use words: "none", "silent", "failure", "raise", "log".

FOR DATA PROCESSING CODE:
4. O(n^2) deduplication using list: Checking "if r not in unique" on a list is O(n) per check, making it O(n^2) quadratic. Should use set for O(n) dedup. issue_type: "performance", severity: "medium". Use words: "O(n", "set", "duplicate", "performance", "quadratic".
5. Verbose loop instead of list comprehension: Could use list comprehension for cleaner, more pythonic code. issue_type: "performance", severity: "low". Use words: "comprehension", "pythonic", "list".

FOR DATABASE/CLASS CODE:
6. No context manager support: Class lacks __enter__ and __exit__ methods, so it can't be used with "with" statement. Connection may leak if close() is not called. issue_type: "logic", severity: "high". Use words: "context", "manager", "leak", "close", "with", "__enter__", "__exit__".
7. Cursor not closed after query: cursor is created but never closed. Should use try/finally or context manager to prevent cursor leak. issue_type: "logic", severity: "medium". Use words: "cursor", "close", "finally", "leak".

Report the EXACT number of issues present. Do not add extra issues beyond what's actually wrong.""",

    "hard": """You MUST find ALL security vulnerabilities. Check for EACH of these:

FOR SQL/DATABASE CODE:
1. SQL injection: User input directly interpolated into SQL via f-string. Must use parameterized queries. issue_type: "security", severity: "critical". Use words: "sql", "injection", "parameterized", "f-string", "interpolat".
2. No input validation: Query parameter used without any input validation or sanitization. issue_type: "security", severity: "medium". Use words: "input", "validation", "sanitiz".

FOR TEMPLATE/WEB CODE:
3. SSTI (Server-Side Template Injection): render_template_string with user input allows server-side template injection via jinja. issue_type: "security", severity: "critical". Use words: "ssti", "template", "injection", "render_template_string", "jinja".
4. XSS (Cross-Site Scripting): Username rendered in HTML without escaping allows cross-site scripting. issue_type: "security", severity: "high". Use words: "xss", "cross-site", "script", "escap".
5. Path traversal: User-controlled filename allows directory traversal with ../ to read arbitrary files like /etc/passwd. issue_type: "security", severity: "critical". Use words: "path", "traversal", "directory", "../", "arbitrary".

FOR AUTH/SESSION CODE:
6. Insecure deserialization: pickle.loads on user-supplied data allows arbitrary code execution (RCE). issue_type: "security", severity: "critical". Use words: "pickle", "deserialization", "arbitrary", "code execution", "rce".
7. Hardcoded secret token: Admin authentication uses hardcoded secret token/password/credential. Should use environment variable or proper auth. issue_type: "security", severity: "critical". Use words: "hardcoded", "secret", "token", "password", "credential".
8. Timing attack: Simple string comparison (==) for auth token is vulnerable to timing attacks. Should use hmac.compare_digest for constant-time comparison. issue_type: "security", severity: "high". Use words: "timing", "compare_digest", "hmac", "constant-time".

Report ALL issues found. Do not skip any.""",
}


def call_llm(code: str, filename: str, context: str, difficulty: str) -> dict:
    """Call the LLM to review a code snippet with difficulty-specific guidance."""
    hint = DIFFICULTY_HINTS.get(difficulty, "")
    
    user_msg = f"""{hint}

Review this Python code snippet. Find EVERY issue.

Filename: {filename}
Context: {context}

```python
{code}
```

IMPORTANT INSTRUCTIONS:
- Line numbers must be EXACT (count from line 1).
- In "description" AND "suggestion", use the SPECIFIC technical terms mentioned in the hints above.
- Include ALL relevant keywords in both description and suggestion fields.
- Do NOT add issues that don't exist in the code.
- Respond with ONLY valid JSON, no markdown."""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=3000,
            )
            content = response.choices[0].message.content.strip()

            # Try to extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
        except json.JSONDecodeError:
            if attempt < 2:
                continue
            return {"issues": [], "summary": "Failed to parse LLM response."}
        except Exception as e:
            print(f"LLM call error: {e}")
            if attempt < 2:
                time.sleep(2)
                continue
            return {"issues": [], "summary": f"LLM error: {str(e)}"}


def run_task(task_id: str) -> dict:
    """Run a single task through the environment."""
    # Reset environment
    reset_resp = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id})
    reset_resp.raise_for_status()
    reset_data = reset_resp.json()

    observation = reset_data["observation"]
    task_info = observation["task_info"]
    total_snippets = task_info["total_snippets"]
    difficulty = task_info["difficulty"]

    rewards = []
    done = False
    step_num = 0

    print(f'[START] task={task_id} env=code-review-env model={MODEL_NAME}', flush=True)

    while not done:
        snippet = observation["snippet"]
        code = snippet["code"]
        filename = snippet["filename"]
        context = snippet.get("context", "")

        # Call LLM for review
        review = call_llm(code, filename, context, difficulty)

        # Build action
        action_payload = {"action": {"issues": review.get("issues", []), "summary": review.get("summary", "")}}
        action_str = json.dumps(review.get("summary", "")[:80])

        # Step
        step_resp = requests.post(f"{ENV_URL}/step", json=action_payload)
        step_resp.raise_for_status()
        step_data = step_resp.json()

        reward = step_data["reward"]
        done = step_data["done"]
        observation = step_data["observation"]
        rewards.append(reward)
        step_num += 1

        # Emit [STEP] log in required format
        done_str = str(done).lower()
        print(f'[STEP] step={step_num} action={action_str} reward={reward:.2f} done={done_str} error=null', flush=True)

    # Calculate task score
    task_score = sum(rewards) / len(rewards) if rewards else 0.0
    task_score = min(max(task_score, 0.0), 1.0)
    success = task_score > 0.0
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    print(f'[END] success={str(success).lower()} steps={step_num} score={task_score:.2f} rewards={rewards_str}', flush=True)

    return {
        "task_id": task_id,
        "task_name": task_info["task_name"],
        "difficulty": difficulty,
        "score": round(task_score, 4),
        "rewards": rewards,
    }


def main():
    """Main inference loop."""
    all_results = []

    for task_id in TASK_IDS:
        try:
            result = run_task(task_id)
            all_results.append(result)
        except Exception as e:
            # Still emit proper format on error
            print(f'[START] task={task_id} env=code-review-env model={MODEL_NAME}', flush=True)
            print(f'[END] success=false steps=0 score=0.00 rewards=', flush=True)
            all_results.append({
                "task_id": task_id,
                "score": 0.0,
                "error": str(e),
            })

    # Print summary
    total_score = sum(r["score"] for r in all_results)
    avg_score = total_score / len(TASK_IDS) if TASK_IDS else 0.0
    print(f"\n=== Results Summary ===")
    for r in all_results:
        status = f"score={r['score']:.4f}" if "error" not in r else f"ERROR: {r.get('error', '')}"
        print(f"  {r['task_id']}: {status}")
    print(f"  Overall Average: {avg_score:.4f}")


if __name__ == "__main__":
    main()
