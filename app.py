"""
Code Review OpenEnv Environment

A real-world environment where an AI agent reviews code snippets for bugs,
security vulnerabilities, and style issues. Implements the OpenEnv spec:
step(), reset(), state() API.
"""

import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from models import (
    ReviewAction,
    CodeSnippet,
    TaskInfo,
    Observation,
    StepResult,
    EnvState,
    CodeIssue,
)
from tasks import TASKS
from grader import grade_review

app = FastAPI(
    title="Code Review OpenEnv",
    description="AI agent reviews code for bugs, security issues, and best practices.",
    version="1.0.0",
)

# ─── Environment State ───────────────────────────────────────────────────────

_env_state = {
    "task_id": None,
    "current_step": 0,
    "total_steps": 0,
    "cumulative_reward": 0.0,
    "done": True,
    "history": [],
    "snippets": [],
}


# ─── Helper ──────────────────────────────────────────────────────────────────

def _build_observation(task_id: str, step_idx: int, done: bool = False) -> dict:
    task = TASKS[task_id]
    snippet_data = task["snippets"][step_idx] if step_idx < len(task["snippets"]) else task["snippets"][-1]
    return {
        "snippet": {
            "code": snippet_data["code"],
            "language": "python",
            "filename": snippet_data["filename"],
            "context": snippet_data.get("context", ""),
        },
        "task_info": {
            "task_id": task_id,
            "task_name": task["name"],
            "difficulty": task["difficulty"],
            "description": task["description"],
            "total_snippets": len(task["snippets"]),
            "current_snippet_index": step_idx,
        },
        "step_number": step_idx,
        "done": done,
    }


# ─── API Endpoints ───────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    action: ReviewAction


@app.get("/")
def root():
    return {
        "name": "code-review-env",
        "description": "AI code review environment with bug, logic, and security tasks.",
        "tasks": list(TASKS.keys()),
        "status": "ready",
    }


@app.post("/reset")
def reset(req: ResetRequest = None):
    """Reset the environment for a given task. Returns initial observation."""
    task_id = (req.task_id if req and req.task_id else None) or "task_easy_bug_detection"

    if task_id not in TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown task_id: {task_id}. Available: {list(TASKS.keys())}")

    task = TASKS[task_id]
    _env_state["task_id"] = task_id
    _env_state["current_step"] = 0
    _env_state["total_steps"] = len(task["snippets"])
    _env_state["cumulative_reward"] = 0.0
    _env_state["done"] = False
    _env_state["history"] = []
    _env_state["snippets"] = task["snippets"]

    observation = _build_observation(task_id, 0)
    return {"observation": observation}


@app.post("/step")
def step(req: StepRequest):
    """
    Submit a review action for the current code snippet.
    Returns reward, next observation, and done flag.
    """
    if _env_state["done"]:
        raise HTTPException(status_code=400, detail="Episode is done. Call /reset to start a new one.")

    if _env_state["task_id"] is None:
        raise HTTPException(status_code=400, detail="No active task. Call /reset first.")

    task_id = _env_state["task_id"]
    step_idx = _env_state["current_step"]
    snippet_data = _env_state["snippets"][step_idx]
    ground_truth = snippet_data["ground_truth"]

    # Grade the agent's review
    reward = grade_review(req.action.issues, ground_truth)

    # Record history
    _env_state["history"].append({
        "step": step_idx,
        "snippet_filename": snippet_data["filename"],
        "agent_issues_count": len(req.action.issues),
        "ground_truth_count": len(ground_truth),
        "reward": reward,
    })
    _env_state["cumulative_reward"] += reward
    _env_state["current_step"] += 1

    # Check if done
    done = _env_state["current_step"] >= _env_state["total_steps"]
    _env_state["done"] = done

    # Build next observation (or final)
    if done:
        observation = _build_observation(task_id, step_idx, done=True)
    else:
        observation = _build_observation(task_id, _env_state["current_step"])

    avg_reward = _env_state["cumulative_reward"] / _env_state["current_step"]

    return {
        "observation": observation,
        "reward": reward,
        "done": done,
        "info": {
            "step_reward": reward,
            "cumulative_reward": round(_env_state["cumulative_reward"], 4),
            "average_reward": round(avg_reward, 4),
            "steps_completed": _env_state["current_step"],
            "steps_remaining": _env_state["total_steps"] - _env_state["current_step"],
        },
    }


@app.get("/state")
def state():
    """Return the full environment state."""
    return {
        "task_id": _env_state["task_id"],
        "current_step": _env_state["current_step"],
        "total_steps": _env_state["total_steps"],
        "cumulative_reward": round(_env_state["cumulative_reward"], 4),
        "done": _env_state["done"],
        "history": _env_state["history"],
    }


@app.get("/tasks")
def list_tasks():
    """List all available tasks."""
    return {
        task_id: {
            "name": t["name"],
            "difficulty": t["difficulty"],
            "description": t["description"],
            "num_snippets": len(t["snippets"]),
        }
        for task_id, t in TASKS.items()
    }


def start_server():
    """Entry point for project.scripts."""
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    start_server()
