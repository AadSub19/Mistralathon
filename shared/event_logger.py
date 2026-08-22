"""
Event Logger for Mistralathon / Vibe Arena

Logs observable events during team (Architect -> Developer -> QA) execution.
Events are written to runs/<team>/events.jsonl in JSON Lines format.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def log_event(team: str, phase: str, actor: str, action: str, detail: str = "", run_dir: str = "runs"):
    """
    Log a single event to the team's events.jsonl file.
    
    Args:
        team: Team name (e.g., 'oracle')
        phase: Current phase ('architect' | 'developer' | 'qa')
        actor: Who performed the action ('architect' | 'developer' | 'qa')
        action: Short event name (e.g., 'started', 'plan_created', 'issue_found')
        detail: Human-readable description
        run_dir: Directory for run artifacts (default: 'runs')
    """
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "team": team,
        "phase": phase,
        "actor": actor,
        "action": action,
        "detail": detail
    }
    
    # Ensure directory exists
    team_run_dir = Path(run_dir) / team
    team_run_dir.mkdir(parents=True, exist_ok=True)
    
    # Append to events.jsonl
    events_file = team_run_dir / "events.jsonl"
    with open(events_file, "a") as f:
        f.write(json.dumps(event) + "\n")


def log_architect_started(team: str, run_dir: str = "runs"):
    """Log when Architect phase begins."""
    log_event(team, "architect", "architect", "architect_started", 
              "Architect phase began for team", run_dir)


def log_architect_completed(team: str, run_dir: str = "runs"):
    """Log when Architect phase completes."""
    log_event(team, "architect", "architect", "architect_completed",
              "Architect phase completed", run_dir)


def log_plan_created(team: str, plan_path: str, run_dir: str = "runs"):
    """Log when PLAN.md is created."""
    log_event(team, "architect", "architect", "plan_created",
              f"Plan created at {plan_path}", run_dir)


def log_developer_started(team: str, run_dir: str = "runs"):
    """Log when Developer phase begins."""
    log_event(team, "developer", "developer", "developer_started",
              "Developer phase began", run_dir)


def log_developer_completed(team: str, run_dir: str = "runs"):
    """Log when Developer phase completes."""
    log_event(team, "developer", "developer", "developer_completed",
              "Developer phase completed", run_dir)


def log_agent_spec_created(team: str, spec_path: str, run_dir: str = "runs"):
    """Log when agent_spec.json is created."""
    log_event(team, "developer", "developer", "agent_spec_created",
              f"Agent specification created at {spec_path}", run_dir)


def log_qa_started(team: str, run_dir: str = "runs"):
    """Log when QA phase begins."""
    log_event(team, "qa", "qa", "qa_started",
              "QA phase began", run_dir)


def log_qa_completed(team: str, run_dir: str = "runs"):
    """Log when QA phase completes."""
    log_event(team, "qa", "qa", "qa_completed",
              "QA phase completed", run_dir)


def log_qa_issue_found(team: str, issue: str, run_dir: str = "runs"):
    """Log when QA finds an issue."""
    log_event(team, "qa", "qa", "qa_issue_found",
              f"Issue found: {issue}", run_dir)


def log_qa_fix_applied(team: str, fix: str, run_dir: str = "runs"):
    """Log when QA applies a fix."""
    log_event(team, "qa", "qa", "qa_fix_applied",
              f"Fix applied: {fix}", run_dir)


def log_agent_ready(team: str, run_dir: str = "runs"):
    """Log when the agent is ready for execution."""
    log_event(team, "qa", "qa", "agent_ready",
              "Agent is ready for execution", run_dir)


def log_error(team: str, phase: str, actor: str, error: str, run_dir: str = "runs"):
    """Log an error during any phase."""
    log_event(team, phase, actor, "error",
              f"Error: {error}", run_dir)


def log_vibe_started(team: str, phase: str, actor: str, workdir: str, run_dir: str = "runs"):
    """Log when a Vibe CLI process starts."""
    log_event(team, phase, actor, "vibe_started",
              f"Vibe CLI process started in {workdir}", run_dir)


def log_vibe_completed(team: str, phase: str, actor: str, workdir: str, exit_code: int, run_dir: str = "runs"):
    """Log when a Vibe CLI process completes."""
    log_event(team, phase, actor, "vibe_completed",
              f"Vibe CLI process completed in {workdir} with exit code {exit_code}", run_dir)


def log_file_created(team: str, phase: str, actor: str, filepath: str, run_dir: str = "runs"):
    """Log when a file is created by a Vibe session."""
    log_event(team, phase, actor, "file_created",
              f"File created: {filepath}", run_dir)


def log_test_run(team: str, phase: str, actor: str, test_name: str, result: str, run_dir: str = "runs"):
    """Log when a test is run."""
    log_event(team, phase, actor, "test_run",
              f"Test '{test_name}' result: {result}", run_dir)


def log_stage_started(team: str, phase: str, run_dir: str = "runs"):
    """Log when a stage (architect/developer/qa) starts."""
    log_event(team, phase, phase, "stage_started",
              f"Stage {phase} started", run_dir)


def log_stage_completed(team: str, phase: str, run_dir: str = "runs"):
    """Log when a stage (architect/developer/qa) completes."""
    log_event(team, phase, phase, "stage_completed",
              f"Stage {phase} completed", run_dir)
