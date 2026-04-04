"""Typed Pydantic models for the Code Review OpenEnv environment."""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CodeIssue(BaseModel):
    """A single issue found in the code."""
    line_number: int = Field(..., description="Line number where the issue occurs")
    issue_type: str = Field(..., description="Category: bug, security, style, performance, logic")
    severity: Severity = Field(..., description="Issue severity")
    description: str = Field(..., description="Description of the issue")
    suggestion: str = Field(..., description="Suggested fix")


class ReviewAction(BaseModel):
    """Action submitted by the agent — a list of identified issues."""
    issues: List[CodeIssue] = Field(default_factory=list, description="List of issues found")
    summary: str = Field("", description="Overall review summary")


class CodeSnippet(BaseModel):
    """A code snippet to review."""
    code: str = Field(..., description="The source code to review")
    language: str = Field(default="python", description="Programming language")
    filename: str = Field(default="snippet.py", description="Filename context")
    context: str = Field(default="", description="Additional context about the code")


class TaskInfo(BaseModel):
    """Information about the current task."""
    task_id: str
    task_name: str
    difficulty: str
    description: str
    total_snippets: int
    current_snippet_index: int


class Observation(BaseModel):
    """What the agent observes at each step."""
    snippet: CodeSnippet
    task_info: TaskInfo
    step_number: int
    done: bool = False


class StepResult(BaseModel):
    """Result returned after each step."""
    observation: Observation
    reward: float = Field(..., ge=0.0, le=1.0, description="Reward for this step")
    done: bool = Field(default=False, description="Whether the episode is complete")
    info: dict = Field(default_factory=dict, description="Additional info")


class EnvState(BaseModel):
    """Full environment state."""
    task_id: str
    current_step: int
    total_steps: int
    cumulative_reward: float
    done: bool
    history: List[dict] = Field(default_factory=list)
