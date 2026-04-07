"""Grading logic for evaluating agent code reviews against ground truth."""

from typing import List, Dict
from models import CodeIssue, Severity


# Severity weights for scoring
SEVERITY_WEIGHT = {
    Severity.LOW: 0.5,
    Severity.MEDIUM: 1.0,
    Severity.HIGH: 2.0,
    Severity.CRITICAL: 3.0,
}


def _keyword_match(agent_issue: CodeIssue, gt_issue: dict, line_tolerance: int = 5) -> float:
    """
    Score how well an agent-found issue matches a ground-truth issue.
    Returns a match score between 0.0 and 1.0.
    """
    score = 0.0

    # Line number proximity (within tolerance)
    line_diff = abs(agent_issue.line_number - gt_issue["line_number"])
    if line_diff <= line_tolerance:
        score += 0.2 * (1.0 - line_diff / line_tolerance)

    # Issue type match
    gt_type = gt_issue["issue_type"]
    if agent_issue.issue_type.lower() == gt_type.lower():
        score += 0.2
    elif agent_issue.issue_type.lower() in ["bug", "logic", "security", "performance", "style"]:
        score += 0.05  # partial credit for valid category

    # Severity match
    gt_severity = gt_issue["severity"]
    if agent_issue.severity == gt_severity:
        score += 0.2
    elif abs(list(Severity).index(agent_issue.severity) - list(Severity).index(gt_severity)) == 1:
        score += 0.1  # close severity

    # Keyword matching in description + suggestion
    agent_text = (agent_issue.description + " " + agent_issue.suggestion).lower()
    keywords = gt_issue.get("keywords", [])
    if keywords:
        matched = sum(1 for kw in keywords if kw.lower() in agent_text)
        keyword_ratio = matched / len(keywords)
        score += 0.4 * keyword_ratio

    return min(score, 1.0)


def _clamp_score(score: float) -> float:
    """Clamp score to strictly between 0 and 1 (exclusive), as required by the validator."""
    return max(0.001, min(0.999, score))


def grade_review(agent_issues: List[CodeIssue], ground_truth: List[dict]) -> float:
    """
    Grade an agent's code review against ground truth issues.
    Returns a score strictly between 0.0 and 1.0 (exclusive).
    
    Scoring:
    - Each ground truth issue has a weight based on severity
    - Agent gets credit for matching issues (keyword + line proximity)
    - Penalty for excessive false positives (diminishing)
    """
    if not ground_truth:
        # No issues expected; penalize if agent reported issues
        if not agent_issues:
            return _clamp_score(1.0)
        return _clamp_score(1.0 - 0.1 * len(agent_issues))

    total_weight = sum(SEVERITY_WEIGHT[gt["severity"]] for gt in ground_truth)
    earned_weight = 0.0
    matched_gt = set()

    for gt_idx, gt_issue in enumerate(ground_truth):
        best_match_score = 0.0
        for agent_issue in agent_issues:
            match_score = _keyword_match(agent_issue, gt_issue)
            best_match_score = max(best_match_score, match_score)

        if best_match_score > 0.2:  # threshold to count as a match
            matched_gt.add(gt_idx)
            earned_weight += SEVERITY_WEIGHT[gt_issue["severity"]] * best_match_score

    # Base score from matched issues
    base_score = earned_weight / total_weight if total_weight > 0 else 0.0

    # Small penalty for excessive false positives (more than 2x ground truth)
    excess = max(0, len(agent_issues) - 2 * len(ground_truth))
    fp_penalty = min(0.15, excess * 0.03)

    final_score = base_score - fp_penalty
    return _clamp_score(round(final_score, 4))


def grade_task(all_step_results: List[Dict]) -> float:
    """
    Grade an entire task (multiple snippets).
    Returns average score strictly between 0.0 and 1.0 (exclusive).
    """
    if not all_step_results:
        return _clamp_score(0.0)
    scores = [r["reward"] for r in all_step_results]
    return _clamp_score(round(sum(scores) / len(scores), 4))
