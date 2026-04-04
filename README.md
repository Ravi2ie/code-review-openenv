---
title: Code Review OpenEnv
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
tags:
  - openenv
---

# Code Review OpenEnv Environment

A real-world OpenEnv environment where an AI agent reviews Python code snippets for bugs, security vulnerabilities, logic errors, and style issues.

## Environment Description

The agent receives code snippets and must identify issues, classify their severity, and suggest fixes. Tasks scale from simple bug detection to complex security vulnerability auditing.

### Action Space

The agent submits a `ReviewAction` containing:
- `issues`: List of `CodeIssue` objects, each with:
  - `line_number` (int): Line where the issue occurs
  - `issue_type` (str): One of `bug`, `security`, `logic`, `performance`, `style`
  - `severity` (str): One of `low`, `medium`, `high`, `critical`
  - `description` (str): What the issue is
  - `suggestion` (str): How to fix it
- `summary` (str): Overall review summary

### Observation Space

Each observation contains:
- `snippet`: The code to review (`code`, `language`, `filename`, `context`)
- `task_info`: Current task metadata (`task_id`, `difficulty`, `total_snippets`, `current_snippet_index`)
- `step_number`: Current step index
- `done`: Whether the episode is complete

### Reward Function

Rewards range from 0.0 to 1.0 per step, based on:
- **Keyword matching** (40%): How well the agent's description matches known issue keywords
- **Severity accuracy** (20%): Correct severity classification
- **Issue type match** (20%): Correct categorization (bug/security/logic/etc.)
- **Line proximity** (20%): How close the reported line is to the actual issue
- Small penalty for excessive false positives

## Tasks

| Task ID | Difficulty | Description | Snippets |
|---------|-----------|-------------|----------|
| `task_easy_bug_detection` | Easy | Identify obvious bugs (ZeroDivisionError, KeyError, off-by-one) | 3 |
| `task_medium_logic_review` | Medium | Find logic errors, performance anti-patterns, missing error handling | 3 |
| `task_hard_security_audit` | Hard | Detect SQL injection, XSS, SSTI, path traversal, insecure deserialization | 3 |

## Setup & Run

### Local Development

```bash
pip install -r requirements.txt
python app.py
```

The server starts at `http://localhost:7860`.

### Docker

```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

### Running Inference

Set the required environment variables:

```bash
export API_BASE_URL="<your-llm-endpoint>"
export MODEL_NAME="<your-model>"
export HF_TOKEN="<your-hf-token>"
export ENV_URL="http://localhost:7860"
python inference.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check and environment info |
| `/reset` | POST | Reset environment for a task. Body: `{"task_id": "task_easy_bug_detection"}` |
| `/step` | POST | Submit a review action. Body: `{"action": {"issues": [...], "summary": "..."}}` |
| `/state` | GET | Get current environment state |
| `/tasks` | GET | List all available tasks |

## OpenEnv Spec Compliance

- ✅ Typed Pydantic models for all inputs/outputs
- ✅ `step()` / `reset()` / `state()` endpoints
- ✅ `openenv.yaml` configuration
- ✅ 3 tasks with agent graders (easy → medium → hard)
- ✅ Reward scores in 0.0–1.0 range
- ✅ Baseline inference script with reproducible scores
- ✅ Dockerfile for deployment

## Baseline Scores

Model: `Qwen/Qwen3.5-27B` via Hugging Face Inference API

| Task | Difficulty | Score |
|------|-----------|-------|
| `task_easy_bug_detection` | Easy | 0.9467 |
| `task_medium_logic_review` | Medium | 0.9822 |
| `task_hard_security_audit` | Hard | 0.9917 |
| **Overall Average** | | **0.9735** |
