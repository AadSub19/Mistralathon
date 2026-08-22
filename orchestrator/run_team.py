#!/usr/bin/env python3
"""
Mistralathon / Vibe Arena - Team Orchestrator

Runs the Oracle team pipeline using REAL Mistral Vibe CLI sessions:
  Architect -> Developer -> QA

Each phase runs as a separate Vibe CLI subprocess with:
- Programmatic mode (-p flag)
- Maximum turn limits (--max-turns)
- Maximum token limits (--max-tokens)
- Auto-approve for tool calls (--auto-approve)
- Trust flag for non-interactive automation (--trust)
- Isolated working directories

Usage:
    python orchestrator/run_team.py oracle [--mock]

Without --mock: Uses real Vibe CLI subprocesses (DEFAULT production flow)
With --mock: Uses deterministic fallback for development
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add shared to path for event_logger
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from event_logger import (
    log_architect_started, log_architect_completed, log_plan_created,
    log_developer_started, log_developer_completed, log_agent_spec_created,
    log_qa_started, log_qa_completed, log_qa_issue_found, log_qa_fix_applied,
    log_agent_ready, log_error, log_vibe_started, log_vibe_completed,
    log_file_created, log_test_run, log_stage_started, log_stage_completed
)


# =============================================================================
# Configuration
# =============================================================================

TEAMS_DIR = Path(__file__).parent.parent / "teams"
SHARED_DIR = Path(__file__).parent.parent / "shared"
RUNS_DIR = Path(__file__).parent.parent / "runs"

# Vibe CLI configuration
VIBE_CMD = "vibe"
VIBE_MAX_TURNS = 20
VIBE_MAX_TOKENS = 16384
VIBE_TIMEOUT_SECONDS = 300

# File paths
CHALLENGE_PATH = SHARED_DIR / "challenge.json"


# =============================================================================
# Vibe CLI Subprocess Execution
# =============================================================================

def run_vibe_subprocess(
    team: str,
    phase: str,
    actor: str,
    workdir: Path,
    prompt: str,
    output_format: str = "text",
    max_turns: int = VIBE_MAX_TURNS,
    max_tokens: int = VIBE_MAX_TOKENS,
    timeout: int = VIBE_TIMEOUT_SECONDS,
    mock: bool = False
) -> tuple[str, int, str]:
    """
    Run a Vibe CLI subprocess and return (stdout, exit_code, stderr).
    
    Args:
        team: Team name
        phase: Current phase (architect/developer/qa)
        actor: Role name (architect/developer/qa)
        workdir: Working directory for the Vibe process
        prompt: The prompt to pass to Vibe
        output_format: Output format (text/json/streaming)
        max_turns: Maximum number of turns
        max_tokens: Maximum total tokens
        timeout: Process timeout in seconds
        mock: If True, skip actual Vibe execution
    
    Returns:
        Tuple of (stdout, exit_code, stderr)
    """
    if mock:
        return "", 0, ""
    
    log_vibe_started(team, phase, actor, str(workdir))
    
    cmd = [
        VIBE_CMD,
        "-p", prompt,
        "--output", output_format,
        "--max-turns", str(max_turns),
    ]
    if max_tokens is not None:
        cmd.extend(["--max-tokens", str(max_tokens)])
    cmd.extend(["--auto-approve", "--trust"])
    
    print(f"  [DEBUG] Vibe command: {' '.join(cmd[:6])}... (prompt truncated)")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(os.environ, VIBE_HOME=os.environ.get("VIBE_HOME", "~/.vibe"))
        )
        
        stdout = result.stdout
        exit_code = result.returncode
        stderr = result.stderr
        
        log_vibe_completed(team, phase, actor, str(workdir), exit_code)
        
        return stdout, exit_code, stderr
        
    except subprocess.TimeoutExpired:
        exit_code = -1
        stderr = f"Vibe process timed out after {timeout} seconds"
        log_vibe_completed(team, phase, actor, str(workdir), exit_code)
        log_error(team, phase, actor, stderr)
        return "", exit_code, stderr
    except FileNotFoundError:
        exit_code = -2
        stderr = f"Vibe CLI not found at {VIBE_CMD}. Ensure Vibe is installed and in PATH."
        log_vibe_completed(team, phase, actor, str(workdir), exit_code)
        log_error(team, phase, actor, stderr)
        return "", exit_code, stderr
    except Exception as e:
        exit_code = -3
        stderr = f"Unexpected error running Vibe: {str(e)}"
        log_vibe_completed(team, phase, actor, str(workdir), exit_code)
        log_error(team, phase, actor, stderr)
        return "", exit_code, stderr


# =============================================================================
# File I/O Helpers
# =============================================================================

def read_challenge() -> dict:
    if not CHALLENGE_PATH.exists():
        raise FileNotFoundError(f"Challenge file not found: {CHALLENGE_PATH}")
    with open(CHALLENGE_PATH) as f:
        return json.load(f)


def read_personality(team: str) -> str:
    personality_path = TEAMS_DIR / team / "personality.md"
    if not personality_path.exists():
        raise FileNotFoundError(f"Personality file not found: {personality_path}")
    with open(personality_path) as f:
        return f.read()


def read_file_safe(filepath: Path) -> str:
    if filepath.exists():
        with open(filepath) as f:
            return f.read()
    return ""


def write_file_atomic(filepath: Path, content: str) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    with open(temp_path, "w") as f:
        f.write(content)
    temp_path.replace(filepath)


# =============================================================================
# Prompt Templates
# =============================================================================

ARCHITECT_PROMPT_TEMPLATE = """You are the Architect for the Oracle team in the Mistralathon hackathon.

Your personality traits: Analytical, predictive, evidence-driven, thinks several moves ahead, considers downstream consequences. The fastest immediate action may not produce the fastest final outcome.

Challenge: Order one pepperoni + jalapeño pizza for delivery within $35 budget, fastest delivery possible.

Available execution tools: navigate(url), visible_page_text(), click(target), type_into(target, value), screenshot(), current_url(), cart_state()

Your task: Create PLAN.md with:
1. Overall strategy and approach
2. How to find suitable pizza options
3. How to verify requirements (pepperoni + jalapeño toppings, $35 max, quantity=1)
4. How to handle ordering process
5. How to confirm successful delivery
6. Risk assessment and mitigation
7. Execution environment assumptions

IMPORTANT:
- Do NOT prescribe specific vendors or technical architectures.
- Be strategic and principle-based.
- Output markdown starting with # header.
- Use write_file tool to create PLAN.md.
- Do NOT include chain-of-thought, only file creation.
"""

DEVELOPER_PROMPT_TEMPLATE = """You are the Developer for the Oracle team in the Mistralathon hackathon.

Your personality: Analytical, predictive, evidence-driven, strategic, deliberate.

Challenge: Order one pepperoni + jalapeño pizza for delivery within $35 budget.

Architect's Plan is in PLAN.md in the current directory. Read it first.

Your task: Create Pizza Agent specification in pizza-agent/ directory.

Create files in pizza-agent/:
1. agent_spec.json - Main agent specification as JSON
2. README.md - Brief agent description

agent_spec.json must contain: agent_id, team, objective, system_prompt, success_conditions, constraints, behavioral_guidelines, tool_use_instructions, fallback_behavior, execution_contract.

Available execution tools: navigate, click, type_into, visible_page_text, screenshot, current_url, cart_state.

IMPORTANT:
- Do NOT invent fixed strategies. Be flexible and adaptive.
- Do NOT hard-code vendor-specific logic.
- Do NOT modify /execution directory.
- Use write_file tool to create files in pizza-agent/ only.
- Do NOT include chain-of-thought, only file creation commands.
"""

QA_PROMPT_TEMPLATE = """You are QA for Oracle. Read pizza-agent/agent_spec.json.

Check:
1. Toppings: pepperoni and jalapeño required
2. <=$35 total
3. Quantity: 1
4. Tools: only navigate, click, type_into, visible_page_text, screenshot, current_url, cart_state
5. Has fallback_behavior

Return ONLY a concise markdown report with:
- PASS or FAIL
- Checks performed
- Issues found
- Recommended fixes"""


# =============================================================================
# Architect Phase
# =============================================================================

def run_architect(team: str, challenge: dict, personality: str, mock: bool) -> str:
    log_architect_started(team)
    log_stage_started(team, "architect")
    
    team_run_dir = RUNS_DIR / team
    team_run_dir.mkdir(parents=True, exist_ok=True)
    
    architect_workdir = team_run_dir
    
    prompt = ARCHITECT_PROMPT_TEMPLATE.format(
        plan=""
    )
    
    print(f"  Starting Architect Vibe session in {architect_workdir}")
    
    stdout, exit_code, stderr = run_vibe_subprocess(
        team=team,
        phase="architect",
        actor="architect",
        workdir=architect_workdir,
        prompt=prompt,
        max_turns=VIBE_MAX_TURNS,
        max_tokens=VIBE_MAX_TOKENS,
        timeout=VIBE_TIMEOUT_SECONDS,
        mock=mock
    )
    
    plan_path = architect_workdir / "PLAN.md"
    if plan_path.exists():
        plan_content = plan_path.read_text()
        log_plan_created(team, f"runs/{team}/PLAN.md")
        log_file_created(team, "architect", "architect", f"runs/{team}/PLAN.md")
        print(f"  Architect created PLAN.md")
    elif mock:
        plan_content = generate_architect_plan_deterministic(challenge)
        write_file_atomic(plan_path, plan_content)
        log_plan_created(team, f"runs/{team}/PLAN.md")
        log_file_created(team, "architect", "architect", f"runs/{team}/PLAN.md")
        print(f"  [MOCK] Created PLAN.md using deterministic fallback")
    else:
        raise RuntimeError(
            f"Architect phase failed. Vibe exit code: {exit_code}. "
            f"stderr: {stderr}. PLAN.md not created."
        )
    
    log_architect_completed(team)
    log_stage_completed(team, "architect")
    
    return plan_content


def generate_architect_plan_deterministic(challenge: dict) -> str:
    return """# Oracle Team - Pizza Agent Plan

## Overview
This plan describes the Oracle team's approach to ordering one pepperoni + jalapeño pizza for delivery within the $35 budget constraint, with the primary goal of fastest delivery.

## Challenge Analysis
- **Primary Objective**: Order 1 pizza with pepperoni and jalapeño toppings for delivery
- **Budget Constraint**: Maximum delivered total of $35 (including tax, fees, tips)
- **Quantity**: Exactly 1 pizza
- **Success Criteria**: Pizza ordered, confirmed for delivery, meets all constraints

## Strategic Approach

### Phase 1: Discovery
The agent will systematically search for available pizza delivery options by:
1. Identifying popular food delivery platforms and direct restaurant websites
2. Searching for "pepperoni jalapeño pizza delivery" in the user's location
3. Prioritizing vendors based on estimated delivery time

### Phase 2: Evaluation
For each candidate option, the agent will:
1. Verify the pizza can be customized with both pepperoni and jalapeño toppings
2. Check the base price + topping costs + delivery fee + tax estimate
3. Ensure the total remains under $35
4. Assess estimated delivery time
5. Verify the vendor is legitimate and operational

### Phase 3: Selection
The agent will select the option that:
1. Meets all requirements (toppings, quantity, budget)
2. Has the fastest estimated delivery time
3. Has the highest reliability based on available information

### Phase 4: Ordering
The agent will:
1. Navigate to the selected vendor's ordering interface
2. Configure the pizza: 1 pizza, add pepperoni, add jalapeño
3. Verify the total cost is <= $35
4. Provide necessary delivery information (address, payment)
5. Confirm the order without placing duplicate orders

### Phase 5: Verification
The agent will:
1. Capture order confirmation details
2. Verify the order includes pepperoni and jalapeño
3. Confirm the total is within budget
4. Note the estimated delivery time

## Risk Assessment and Mitigation

### Risk: No options under $35
**Mitigation**: Search multiple vendors, consider smaller pizza sizes, look for first-time customer discounts.

### Risk: Toppings not available
**Mitigation**: Verify topping availability before selection. If pepperoni or jalapeño unavailable, search for alternative vendors.

### Risk: Delivery time estimates unreliable
**Mitigation**: Cross-reference with multiple sources if possible. Prefer vendors with trackable delivery.

### Risk: CAPTCHA or authentication blocks
**Mitigation**: The execution layer will handle these within security constraints. The agent will not attempt to bypass them.

### Risk: Payment issues
**Mitigation**: Ensure payment information is complete and valid before submission. Verify order confirmation.

## Execution Layer Assumptions

The agent assumes the following browser/execution capabilities will be available:
- navigate(url): Navigate to a URL
- visible_page_text(): Get all visible text on the page
- click(target): Click on an element
- type_into(target, value): Type text into a field
- screenshot(): Capture a screenshot for debugging
- current_url(): Get the current page URL
- cart_state(): Get current cart/state information

The agent will use these tools to interact with web interfaces without making assumptions about specific implementations.

## Decision Principles

1. **Evidence First**: Only act on verified information from the page
2. **Constraint Compliance**: Never violate the $35 budget or one-order limit
3. **Speed vs. Reliability**: Choose the fastest option that reliably meets all requirements
4. **Minimal Assumptions**: Don't assume vendor-specific behavior; verify through the interface
5. **Single Order Guarantee**: Implement checks to prevent duplicate orders

## Fallback Strategy

If the primary vendor fails (out of stock, too expensive, etc.):
1. Move to the next best option from Phase 2
2. Re-evaluate all options if necessary
3. If no options work, report failure with details

## Outputs

The Developer will use this plan to create an agent specification that encodes these principles and strategies into executable instructions."""


# =============================================================================
# Developer Phase
# =============================================================================

def run_developer(team: str, challenge: dict, plan: str, personality: str, mock: bool) -> dict:
    log_developer_started(team)
    log_stage_started(team, "developer")
    
    team_run_dir = RUNS_DIR / team
    team_run_dir.mkdir(parents=True, exist_ok=True)
    
    developer_workdir = team_run_dir
    
    prompt = DEVELOPER_PROMPT_TEMPLATE
    
    print(f"  Starting Developer Vibe session in {developer_workdir}")
    
    plan_path = developer_workdir / "PLAN.md"
    if not plan_path.exists():
        write_file_atomic(plan_path, plan)
    
    stdout, exit_code, stderr = run_vibe_subprocess(
        team=team,
        phase="developer",
        actor="developer",
        workdir=developer_workdir,
        prompt=prompt,
        max_turns=VIBE_MAX_TURNS,
        max_tokens=VIBE_MAX_TOKENS,
        timeout=VIBE_TIMEOUT_SECONDS,
        mock=mock
    )
    
    agent_spec_path = developer_workdir / "pizza-agent" / "agent_spec.json"
    
    if agent_spec_path.exists():
        with open(agent_spec_path) as f:
            agent_spec = json.load(f)
        log_agent_spec_created(team, f"runs/{team}/pizza-agent/agent_spec.json")
        log_file_created(team, "developer", "developer", f"runs/{team}/pizza-agent/agent_spec.json")
        print(f"  Developer created pizza-agent/agent_spec.json")
    elif mock:
        agent_spec = generate_developer_spec_deterministic(challenge, plan)
        agent_spec_dir = developer_workdir / "pizza-agent"
        agent_spec_dir.mkdir(parents=True, exist_ok=True)
        write_file_atomic(agent_spec_path, json.dumps(agent_spec, indent=2))
        log_agent_spec_created(team, f"runs/{team}/pizza-agent/agent_spec.json")
        log_file_created(team, "developer", "developer", f"runs/{team}/pizza-agent/agent_spec.json")
        print(f"  [MOCK] Created pizza-agent/agent_spec.json using deterministic fallback")
    else:
        raise RuntimeError(
            f"Developer phase failed. Vibe exit code: {exit_code}. "
            f"stderr: {stderr}. pizza-agent/agent_spec.json not created."
        )
    
    log_developer_completed(team)
    log_stage_completed(team, "developer")
    
    return agent_spec


def generate_developer_spec_deterministic(challenge: dict, plan: str) -> dict:
    return {
        "agent_id": "oracle_pizza_agent_v1",
        "team": "oracle",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "objective": "Order one pepperoni + jalapeño pizza for delivery within $35 budget, as quickly as possible, using only legitimate vendors and without bypassing any security measures.",
        "system_prompt": "You are Oracle Pizza Agent. Your personality is analytical, predictive, evidence-driven. You think several moves ahead and consider downstream consequences. You understand that the fastest immediate action may not produce the fastest final outcome.\n\nYour mission: Order exactly 1 pizza with pepperoni and jalapeño toppings for delivery, with total cost (including tax, fees, delivery) not exceeding $35. Achieve this as quickly as possible.\n\nConstraints:\n- Never place more than one order\n- Never bypass CAPTCHA, MFA, authentication, or payment security\n- Only use legitimate restaurant or food-delivery websites\n- Verify all requirements before confirming order\n\nAvailable tools: navigate(url), visible_page_text(), click(target), type_into(target, value), screenshot(), current_url(), cart_state()\n\nDecision principles:\n1. Gather all necessary information before acting\n2. Verify toppings, quantity, and price meet requirements\n3. Choose the option with fastest reliable delivery\n4. If uncertain, investigate further rather than guessing\n5. Never violate constraints for speed",
        "success_conditions": [
            "Pizza with pepperoni and jalapeño toppings is in the cart/order",
            "Quantity is exactly 1",
            "Total delivered cost (including tax, fees, tips) is <= $35",
            "Order is confirmed for delivery",
            "Only one order was placed",
            "No security measures were bypassed"
        ],
        "constraints": [
            "Maximum delivered total: $35",
            "Required toppings: pepperoni, jalapeño",
            "Quantity: 1",
            "Never place more than one order",
            "Never bypass CAPTCHA, MFA, authentication, access controls, or payment security",
            "Only use available execution tools"
        ],
        "behavioral_guidelines": {
            "decision_making": "Analytical and evidence-driven. Consider multiple options and their consequences before deciding. Prioritize reliability and constraint compliance over raw speed.",
            "risk_assessment": "Evaluate risks at each step. Prefer actions with verifiable outcomes. Maintain awareness of budget constraints throughout.",
            "information_gathering": "Verify all critical information (price, toppings, delivery time) before committing. Use visible_page_text() to read page content thoroughly.",
            "adaptability": "If the primary approach fails, systematically try alternatives without violating constraints."
        },
        "tool_use_instructions": {
            "navigate": "Use to visit vendor websites and ordering pages",
            "visible_page_text": "Use to read and verify pizza options, prices, toppings, delivery information",
            "click": "Use to select pizza, add toppings, proceed to checkout",
            "type_into": "Use to enter delivery address, payment information, special instructions",
            "screenshot": "Use for debugging and verification of critical steps",
            "current_url": "Use to track navigation and confirm page location",
            "cart_state": "Use to verify pizza configuration, toppings, quantity, and total price before checkout"
        },
        "fallback_behavior": {
            "vendor_unavailable": "Move to next vendor in the search list",
            "toppings_unavailable": "Search for vendors that explicitly offer both pepperoni and jalapeño",
            "price_exceeds_budget": "Look for smaller sizes, special deals, or different vendors",
            "delivery_too_slow": "Evaluate if a slightly slower but more reliable option is better than a fast but risky one",
            "navigation_failure": "Retry with adjusted selectors or try alternative navigation path",
            "order_failure": "Do NOT retry immediately; investigate the cause first to avoid duplicate orders"
        },
        "execution_contract": {
            "expected_tools": ["navigate", "visible_page_text", "click", "type_into", "screenshot", "current_url", "cart_state"],
            "tool_signatures": {
                "navigate": "function(url: str) -> bool",
                "visible_page_text": "function() -> str",
                "click": "function(target: str) -> bool",
                "type_into": "function(target: str, value: str) -> bool",
                "screenshot": "function() -> str (path to image)",
                "current_url": "function() -> str",
                "cart_state": "function() -> dict"
            },
            "assumptions": "Tools will be provided by the execution layer. The agent must not make assumptions about their implementation beyond the stated signatures."
        }
    }


# =============================================================================
# QA Phase
# =============================================================================

def run_qa(team: str, mock: bool = False, max_turns: int = 4, max_tokens: int = 16384) -> tuple[dict, str]:
    log_qa_started(team)
    log_stage_started(team, "qa")
    
    team_run_dir = RUNS_DIR / team
    team_run_dir.mkdir(parents=True, exist_ok=True)
    qa_workdir = team_run_dir
    
    prompt = QA_PROMPT_TEMPLATE
    print(f"  Starting QA Vibe session in {qa_workdir}")
    
    stdout, exit_code, stderr = run_vibe_subprocess(
        team=team, phase="qa", actor="qa",
        workdir=qa_workdir, prompt=prompt,
        max_turns=max_turns, max_tokens=None,
        timeout=VIBE_TIMEOUT_SECONDS, mock=mock
    )
    
    qa_report_path = qa_workdir / "QA_REPORT.md"
    
    if exit_code == 0:
        qa_report = stdout
        write_file_atomic(qa_report_path, qa_report)
        log_file_created(team, "qa", "qa", f"runs/{team}/QA_REPORT.md")
        print(f"  QA report written to QA_REPORT.md")
    elif mock:
        qa_report = "# QA Report\n\nStatus: PASSED\n\nAll checks passed."
        write_file_atomic(qa_report_path, qa_report)
        log_file_created(team, "qa", "qa", f"runs/{team}/QA_REPORT.md")
        print(f"  [MOCK] Created QA_REPORT.md")
    else:
        raise RuntimeError(f"QA failed: exit_code={exit_code}, stderr={stderr}")
    
    final_spec = {}
    agent_spec_path = qa_workdir / "pizza-agent" / "agent_spec.json"
    if agent_spec_path.exists():
        with open(agent_spec_path) as f:
            final_spec = json.load(f)
    
    log_agent_ready(team)
    log_qa_completed(team)
    log_stage_completed(team, "qa")
    
    return final_spec, qa_report


def run_qa_checks_deterministic(challenge: dict, agent_spec: dict) -> tuple[list, dict]:
    issues = []
    modified_spec = dict(agent_spec)
    
    objective = modified_spec.get("objective", "").lower()
    
    if "pepperoni" not in objective or "jalapeño" not in objective:
        issues.append("Objective does not explicitly mention pepperoni and jalapeño toppings")
        modified_spec["objective"] = "Order one pepperoni + jalapeño pizza for delivery within $35 budget, as quickly as possible, using only legitimate vendors and without bypassing any security measures."
    
    if "$35" not in objective and "35" not in objective:
        issues.append("Objective does not explicitly mention the $35 budget constraint")
        modified_spec["objective"] = modified_spec.get("objective", "") + " Budget: $35 maximum."
    
    success_conditions = modified_spec.get("success_conditions", [])
    if not any("pepperoni" in str(sc).lower() and "jalapeño" in str(sc).lower() for sc in success_conditions):
        issues.append("Success conditions do not explicitly verify both toppings")
        if "Pizza with pepperoni and jalapeño toppings" not in success_conditions:
            modified_spec.setdefault("success_conditions", []).insert(0,
                "Pizza with pepperoni and jalapeño toppings is in the cart/order")
    
    constraints = modified_spec.get("constraints", [])
    required_constraints = ["$35", "pepperoni", "jalapeño", "one order", "CAPTCHA"]
    missing = []
    for rc in required_constraints:
        if not any(rc.lower() in str(c).lower() for c in constraints):
            missing.append(rc)
    
    if missing:
        issues.append(f"Constraints missing: {', '.join(missing)}")
        for rc in missing:
            if rc == "$35":
                modified_spec.setdefault("constraints", []).append("Maximum delivered total: $35")
            elif rc == "pepperoni" or rc == "jalapeño":
                modified_spec.setdefault("constraints", []).append("Required toppings: pepperoni, jalapeño")
            elif rc == "one order":
                modified_spec.setdefault("constraints", []).append("Never place more than one order")
            elif rc == "CAPTCHA":
                modified_spec.setdefault("constraints", []).append(
                    "Never bypass CAPTCHA, MFA, authentication, access controls, or payment security")
    
    tool_instructions = modified_spec.get("tool_use_instructions", {})
    required_tools = ["navigate", "visible_page_text", "click", "type_into", "screenshot", "current_url", "cart_state"]
    missing_tools = [t for t in required_tools if t not in tool_instructions]
    
    if missing_tools:
        issues.append(f"Tool use instructions missing: {', '.join(missing_tools)}")
        for tool in missing_tools:
            if tool == "navigate":
                modified_spec.setdefault("tool_use_instructions", {})[tool] = "Use to visit vendor websites and ordering pages"
            elif tool == "visible_page_text":
                modified_spec.setdefault("tool_use_instructions", {})[tool] = "Use to read and verify pizza options, prices, toppings, delivery information"
            elif tool == "click":
                modified_spec.setdefault("tool_use_instructions", {})[tool] = "Use to select pizza, add toppings, proceed to checkout"
            elif tool == "type_into":
                modified_spec.setdefault("tool_use_instructions", {})[tool] = "Use to enter delivery address, payment information"
            elif tool == "screenshot":
                modified_spec.setdefault("tool_use_instructions", {})[tool] = "Use for debugging and verification"
            elif tool == "current_url":
                modified_spec.setdefault("tool_use_instructions", {})[tool] = "Use to track navigation"
            elif tool == "cart_state":
                modified_spec.setdefault("tool_use_instructions", {})[tool] = "Use to verify pizza configuration and total price"
    
    if "fallback_behavior" not in modified_spec:
        issues.append("No fallback behavior defined")
        modified_spec["fallback_behavior"] = {
            "vendor_unavailable": "Move to next vendor",
            "price_exceeds_budget": "Look for smaller sizes or different vendors",
            "order_failure": "Investigate cause before retrying to avoid duplicates"
        }
    
    return issues, modified_spec


def generate_qa_report_deterministic(issues: list) -> str:
    if issues:
        return f"""# Oracle Team - QA Report

## Status: MODIFICATIONS APPLIED

### Issues Found:

""" + "\n".join(f"- {issue}" for issue in issues) + f"""

### Modifications Made:
The agent specification has been updated to address the above issues.

## Verification Results:
- [x] Toppings requirement (pepperoni + jalapeño): VERIFIED
- [x] $35 constraint: VERIFIED
- [x] One-order limit: VERIFIED
- [x] Goal alignment: VERIFIED
- [x] Execution-tool compatibility: VERIFIED
- [x] Reasonable failure handling: VERIFIED

## Conclusion:
Agent specification is now ready for execution."""
    else:
        return """# Oracle Team - QA Report

## Status: PASSED - NO MODIFICATIONS NEEDED

### Verification Results:
- [x] Toppings requirement (pepperoni + jalapeño): VERIFIED
- [x] $35 constraint: VERIFIED
- [x] One-order limit: VERIFIED
- [x] Goal alignment: VERIFIED
- [x] Execution-tool compatibility: VERIFIED
- [x] Reasonable failure handling: VERIFIED

## Conclusion:
Agent specification meets all requirements. Ready for execution."""


# =============================================================================
# Main Execution
# =============================================================================

def run_team(team: str, phase: str = None, mock: bool = False):
    if phase == "qa":
        print(f"\n{'='*60}")
        print(f"Running {team.capitalize()} QA Phase ONLY")
        if mock:
            print(f"MODE: MOCK (deterministic fallback)")
        else:
            print(f"MODE: PRODUCTION (real Vibe CLI)")
        print(f"{'='*60}\n")
        
        final_spec, qa_report = run_qa(team, mock=mock)
        print(f"QA complete. Report written to runs/{team}/QA_REPORT.md")
        
        print(f"\n{'='*60}")
        print(f"{team.capitalize()} QA Complete!")
        print(f"{'='*60}")
        return {
            "team": team,
            "qa_path": RUNS_DIR / team / "QA_REPORT.md",
            "events_path": RUNS_DIR / team / "events.jsonl",
            "mock_mode": mock
        }
    
    print(f"\n{'='*60}")
    print(f"Running {team.capitalize()} Team Pipeline")
    if mock:
        print(f"MODE: MOCK (deterministic fallback)")
    else:
        print(f"MODE: PRODUCTION (real Vibe CLI subprocesses)")
    print(f"{'='*60}\n")
    
    personality_path = TEAMS_DIR / team / "personality.md"
    if not personality_path.exists():
        raise ValueError(f"Team '{team}' not found. Personality file missing: {personality_path}")
    
    challenge = read_challenge()
    print(f"Challenge: {challenge.get('title', 'Unknown')}")
    
    personality = read_personality(team)
    
    print(f"\n--- Phase 1: Architect ---")
    plan = run_architect(team, challenge, personality, mock)
    print(f"Architect complete. Plan written to runs/{team}/PLAN.md")
    
    print(f"\n--- Phase 2: Developer ---")
    agent_spec = run_developer(team, challenge, plan, personality, mock)
    print(f"Developer complete. Agent spec written to runs/{team}/pizza-agent/agent_spec.json")
    
    print(f"\n--- Phase 3: QA ---")
    final_spec, qa_report = run_qa(team, mock=mock)
    
    print(f"\n{'='*60}")
    print(f"{team.capitalize()} Team Pipeline Complete!")
    print(f"{'='*60}")
    print(f"\nGenerated files:")
    print(f"  - runs/{team}/PLAN.md")
    print(f"  - runs/{team}/pizza-agent/agent_spec.json")
    print(f"  - runs/{team}/QA_REPORT.md")
    print(f"  - runs/{team}/events.jsonl")
    print(f"\nAgent is ready for execution layer integration.")
    
    return {
        "team": team,
        "plan_path": RUNS_DIR / team / "PLAN.md",
        "spec_path": RUNS_DIR / team / "pizza-agent" / "agent_spec.json",
        "qa_path": RUNS_DIR / team / "QA_REPORT.md",
        "events_path": RUNS_DIR / team / "events.jsonl",
        "mock_mode": mock
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Oracle team pipeline using Mistral Vibe CLI"
    )
    parser.add_argument(
        "team",
        help="Team name to run (e.g., oracle)"
    )
    parser.add_argument(
        "--phase",
        choices=["architect", "developer", "qa"],
        help="Run only a specific phase (default: run all phases)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic fallback instead of real Vibe CLI (for development only)"
    )
    
    args = parser.parse_args()
    team = args.team.lower()
    phase = args.phase
    mock = args.mock
    
    try:
        result = run_team(team, phase=phase, mock=mock)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
