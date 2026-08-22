#!/usr/bin/env python3
"""
Pizza Agent Runner for Mistralathon / Vibe Arena

Runs the Oracle Pizza Agent with Papa John's high-level ordering actions.
Mistral provides reasoning/decision, Playwright provides deterministic execution.

Usage:
    python3 execution/runner.py oracle

Environment:
    MISTRAL_API_KEY: Required for Mistral API access
    AUTO_PURCHASE: Set to "true" to allow final purchase (default: false)
    PIZZA_START_URL: Papa John's URL (default: https://www.papajohns.com/)
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Load environment variables from root .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")
load_dotenv()  # Also try current dir and parent

# Add shared to path for event_logger
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
sys.path.insert(0, str(Path(__file__).parent))

from event_logger import (
    log_event, log_error
)
from papa_johns import SyncPapaJohnsOrderingTool


# =============================================================================
# Configuration
# =============================================================================

SHARED_DIR = Path(__file__).parent.parent / "shared"
RUNS_DIR = Path(__file__).parent.parent / "runs"
CHALLENGE_PATH = SHARED_DIR / "challenge.json"

# Safety limits
MAX_ACTIONS = 40
MAX_RUNTIME_SECONDS = 600  # 10 minutes

# Mistral model
MISTRAL_MODEL = "mistral-large-latest"

# Starting URL for pizza ordering
PIZZA_START_URL = os.environ.get("PIZZA_START_URL", "https://www.papajohns.com/")

# Default AUTO_PURCHASE is false
AUTO_PURCHASE = os.environ.get("AUTO_PURCHASE", "false").lower() == "true"


# =============================================================================
# Event Logging Helpers
# =============================================================================

def log_browser_started(team: str):
    log_event(team, "execution", "runner", "browser_started", "Papa John's browser launched")


def log_browser_stopped(team: str):
    log_event(team, "execution", "runner", "browser_stopped", "Browser closed")


def log_navigate(team: str, url: str):
    log_event(team, "execution", "runner", "navigate", f"Navigated to: {url}")


def log_pizza_found(team: str, details: str):
    log_event(team, "execution", "runner", "pizza_found", f"Pizza: {details}")


def log_cart_updated(team: str, items: str):
    log_event(team, "execution", "runner", "cart_updated", f"Cart: {items}")


def log_price_checked(team: str, amount: str):
    log_event(team, "execution", "runner", "price_checked", f"Price: {amount}")


def log_checkout_reached(team: str):
    log_event(team, "execution", "runner", "checkout_reached", "Checkout page reached")


def log_ready_to_purchase(team: str):
    log_event(team, "execution", "runner", "ready_to_purchase", "Ready to purchase - waiting for AUTO_PURCHASE")


def log_order_submitted(team: str):
    log_event(team, "execution", "runner", "order_submitted", "Order submitted")


def log_ordering_channel_blocked(team: str):
    log_event(team, "execution", "runner", "ordering_channel_blocked", "Ordering channel blocked by CAPTCHA/security")


def log_race_finished(team: str, status: str):
    log_event(team, "execution", "runner", "race_finished", f"Status: {status}")


# =============================================================================
# Mistral Client
# =============================================================================

def get_mistral_client():
    """Get Mistral client."""
    try:
        from mistralai.client import Mistral
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        return Mistral(api_key=api_key)
    except ImportError:
        raise ImportError("mistralai client not installed. Run: pip install mistralai")


def invoke_mistral(client, prompt: str, model: str = MISTRAL_MODEL, max_tokens: int = 2048) -> str:
    """Invoke Mistral with a prompt. Includes retry with backoff for 429."""
    import httpx
    
    # Rate limiting - wait between calls
    time.sleep(1.5)
    
    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return response.choices[0].message.content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  [Mistral] Rate limited (429), retrying in {delay}s...")
                time.sleep(delay)
                continue
            raise RuntimeError(f"Mistral HTTP {e.response.status_code}: rate_limited")
        except Exception as e:
            raise RuntimeError(f"Mistral invocation failed: {e}")
    
    raise RuntimeError("Mistral invocation failed after retries: rate_limited")


# =============================================================================
# High-Level Action Mapping
# =============================================================================

# Map high-level action names to PapaJohnsOrderingTool methods
ACTION_TO_METHOD = {
    "inspect_menu": "inspect_menu",
    "select_cheese_pizza": "select_cheese_pizza",
    "set_size_small": "set_size_small",
    "add_to_cart": "add_to_cart",
    "inspect_cart": "get_cart_state",
    "proceed_to_checkout": "proceed_to_checkout",
}


# =============================================================================
# Pizza Agent Runner
# =============================================================================

class PizzaAgentRunner:
    """Runs the Pizza Agent with high-level Papa John's ordering actions."""
    
    def __init__(self, team: str):
        self.team = team
        self.pj_tool = SyncPapaJohnsOrderingTool(headless=False)
        self.client = get_mistral_client()
        self.actions_taken = 0
        self.orders_submitted = 0
        self.start_time = None
        self.action_history = []
        self.consecutive_failures = 0
        
    def _check_safety_limits(self):
        """Check if we've hit safety limits."""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if self.actions_taken >= MAX_ACTIONS:
            return False, "Max actions reached"
        if elapsed >= MAX_RUNTIME_SECONDS:
            return False, "Max runtime reached"
        return True, ""
    
    def _validate_action(self, action: dict) -> tuple[bool, str]:
        """Validate high-level action from the model."""
        if not isinstance(action, dict):
            return False, "Invalid action format"
        
        valid_actions = list(ACTION_TO_METHOD.keys()) + ["finish", "fail"]
        if action.get("action") not in valid_actions:
            return False, f"Invalid action: {action.get('action')}. Valid: {valid_actions}"
        
        if action.get("action") == "finish":
            if not action.get("reason_summary"):
                return False, "Finish action requires reason_summary"
        
        return True, ""
    
    def _get_agent_prompt(self, agent_spec: dict, order_state: dict) -> str:
        """Build prompt for the Pizza Agent with high-level actions."""
        system_prompt = agent_spec.get("system_prompt", "")
        objective = agent_spec.get("objective", "")
        
        # Load current challenge
        challenge_path = CHALLENGE_PATH
        with open(challenge_path) as f:
            current_challenge = json.load(f)
        
        # Format order state
        state_str = "\n".join([
            f"  {k}: {v}"
            for k, v in order_state.items()
        ])
        
        # Format available actions
        available_actions = list(ACTION_TO_METHOD.keys())
        actions_str = "\n".join([
            f"  - {action}"
            for action in available_actions
        ])
        
        # Format recent history (last 5)
        history_str = "\n".join([
            f"  {i+1}. {act} -> {res}"
            for i, (act, res) in enumerate(self.action_history[-5:])
        ]) if self.action_history else "  None"
        
        auto_purchase = os.environ.get("AUTO_PURCHASE", "false").lower() == "true"
        
        prompt = f"""You are the Pizza Agent for the Oracle team.

IMPORTANT: CURRENT CHALLENGE OVERRIDES ANY OUTDATED REQUIREMENTS IN THE AGENT SPEC.
Current challenge: {current_challenge.get('title', 'Unknown')}

Challenge constraints:
  - Pizza: {current_challenge.get('constraints', {}).get('pizza_type', 'unknown')}
  - Size: {current_challenge.get('constraints', {}).get('size', 'unknown')}
  - Quantity: {current_challenge.get('constraints', {}).get('quantity', 'unknown')}
  - Max total: ${current_challenge.get('constraints', {}).get('maximum_delivered_total', 'unknown')}

{system_prompt}

OBJECTIVE: {objective}

CURRENT ORDER STATE:
{state_str}

AVAILABLE HIGH-LEVEL ACTIONS:
{actions_str}

AUTO_PURCHASE: {"ENABLED" if auto_purchase else "DISABLED"}

Previous actions (last 5):
{history_str}

Return ONE high-level action as JSON with these fields:
{{
  "action": "{available_actions[0]}"|"{'"|"'.join(available_actions[1:])}"|"finish"|"fail",
  "reason_summary": "short observable explanation"
}}

RULES:
- Only return valid JSON
- action must be one of the AVAILABLE HIGH-LEVEL ACTIONS above, or "finish", or "fail"
- reason_summary must be short and observable (no private thoughts)
- Do NOT invent DOM selectors, element IDs, or button text
- Use ONLY the high-level actions provided
- If you detect we're ready to purchase but AUTO_PURCHASE is DISABLED, return action:"finish" with reason_summary:"READY_TO_PURCHASE"
- Never bypass CAPTCHA, MFA, authentication, or payment security
- Never expose private information
- Prefer the simplest sequence: select_cheese_pizza -> set_size_small -> add_to_cart -> proceed_to_checkout

CURRENT CHALLENGE REMINDER: You MUST order a small cheese pizza. A plain small cheese pizza satisfies the requirement. Do not add extra toppings or customize unnecessarily.

What is your ONE next high-level action?"""
        
        return prompt
    
    def _execute_action(self, action: dict) -> dict:
        """Execute a high-level action using PapaJohnsOrderingTool."""
        act = action.get("action")
        result = {"success": False, "error": "", "output": ""}
        
        # Handle finish/fail
        if act in ["finish", "fail"]:
            reason = action.get("reason_summary", "Unknown")
            result["output"] = reason
            result["success"] = (act == "finish")
            return result
        
        # Look up the method
        method_name = ACTION_TO_METHOD.get(act)
        if not method_name:
            result["error"] = f"Unknown action: {act}"
            return result
        
        # Call the method on pj_tool
        try:
            method = getattr(self.pj_tool, method_name)
            tool_result = method()
            
            result["output"] = str(tool_result)
            result["success"] = tool_result.get("status") == "success"
            
            if tool_result.get("status") == "blocked":
                result["error"] = tool_result.get("reason", "blocked")
                result["success"] = False
            elif tool_result.get("status") == "ready_to_purchase":
                result["output"] = tool_result.get("message", "READY_TO_PURCHASE")
                result["success"] = True
            
        except Exception as e:
            result["error"] = f"Execution error: {str(e)}"
        
        return result
    
    def _get_order_state(self) -> dict:
        """Get current order state from the tool."""
        try:
            state = self.pj_tool.get_order_state()
            if state.get("status") == "success":
                return {k: v for k, v in state.items() if k != "status"}
        except:
            pass
        return {
            "pizza_selected": False,
            "size_small": False,
            "cart_reached": False,
            "checkout_reached": False,
            "total_verified": None,
            "quantity_verified": 0,
            "url": "unknown"
        }
    
    def run(self):
        """Run the Pizza Agent with high-level actions."""
        print(f"\n{'='*60}")
        print(f"Pizza Agent Runner - {self.team} (High-Level Actions)")
        print(f"{'='*60}\n")
        
        # Load challenge
        challenge_path = CHALLENGE_PATH
        with open(challenge_path) as f:
            challenge = json.load(f)
        print(f"Challenge: {challenge.get('title', 'Unknown')}")
        
        # Load agent spec
        agent_spec_path = RUNS_DIR / self.team / "pizza-agent" / "agent_spec.json"
        with open(agent_spec_path) as f:
            agent_spec = json.load(f)
        print(f"Agent: {agent_spec.get('agent_id', 'Unknown')}")
        
        # Start browser/tool
        print(f"\nStarting Papa John's tool...")
        self.pj_tool.start()
        log_browser_started(self.team)
        self.start_time = datetime.now(timezone.utc)
        
        # Open starting URL
        print(f"Opening {PIZZA_START_URL}...")
        open_result = self.pj_tool.open(PIZZA_START_URL)
        if open_result.get("status") != "success":
            print(f"Failed to open: {open_result}")
            log_race_finished(self.team, "FAILED_TO_OPEN")
            return {"status": "failed", "reason": "Failed to open Papa John's"}
        
        log_navigate(self.team, PIZZA_START_URL)
        
        try:
            # Main loop
            while True:
                # Check limits
                ok, reason = self._check_safety_limits()
                if not ok:
                    print(f"\nSafety limit reached: {reason}")
                    log_race_finished(self.team, f"STOPPED: {reason}")
                    return {"status": "stopped", "reason": reason}
                
                # Get order state
                order_state = self._get_order_state()
                print(f"\nOrder state: {json.dumps(order_state, indent=2)}")
                
                # Check for CAPTCHA
                if self.pj_tool.is_captcha_blocked():
                    print(f"\n[CAPTCHA DETECTED]")
                    print(f"Ordering channel blocked. Stopping agent.")
                    log_ordering_channel_blocked(self.team)
                    log_race_finished(self.team, "ordering_channel_blocked")
                    return {"status": "blocked", "reason": "ordering_channel_blocked"}
                
                # Check if we're done
                if (order_state.get("pizza_selected") and
                    order_state.get("size_small") and
                    order_state.get("checkout_reached")):
                    print("\nReached checkout with correct pizza!")
                    log_checkout_reached(self.team)
                    
                    # Verify total
                    if order_state.get("total_verified"):
                        log_price_checked(self.team, order_state.get("total_verified"))
                    
                    if order_state.get("quantity_verified") == 1:
                        log_cart_updated(self.team, "1 small cheese pizza")
                    
                    # Check AUTO_PURCHASE
                    if not AUTO_PURCHASE:
                        log_ready_to_purchase(self.team)
                        print(f"\n  *** READY_TO_PURCHASE - Set AUTO_PURCHASE=true to complete order ***")
                        log_race_finished(self.team, "READY_TO_PURCHASE")
                        return {"status": "ready", "reason": "READY_TO_PURCHASE"}
                
                # Build prompt
                prompt = self._get_agent_prompt(agent_spec, order_state)
                
                # Get action from Mistral
                print(f"\n[Action {self.actions_taken + 1}] Asking Pizza Agent for next high-level action...")
                try:
                    response = invoke_mistral(self.client, prompt, max_tokens=2048)
                except RuntimeError as e:
                    error_msg = str(e)
                    print(f"  Mistral error: {error_msg}")
                    if "rate_limited" in error_msg:
                        log_error(self.team, "execution", "runner", error_msg)
                        log_race_finished(self.team, "rate_limited")
                        return {"status": "rate_limited", "reason": error_msg}
                    else:
                        log_error(self.team, "execution", "runner", error_msg)
                        break
                
                # Parse response
                try:
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        action = json.loads(json_match.group(0))
                    else:
                        action = json.loads(response)
                except json.JSONDecodeError:
                    print(f"  Invalid JSON response: {response[:200]}")
                    action = {"action": "fail", "reason_summary": "Invalid response format"}
                
                # Validate action
                valid, error = self._validate_action(action)
                if not valid:
                    print(f"  Invalid action: {error}")
                    action = {"action": "fail", "reason_summary": error}
                
                # Check for finish/fail
                if action.get("action") in ["finish", "fail"]:
                    reason = action.get("reason_summary", "")
                    print(f"  Agent returned: {action.get('action')} - {reason}")
                    
                    if action.get("action") == "finish" and "READY_TO_PURCHASE" in reason:
                        log_ready_to_purchase(self.team)
                        print(f"\n  *** READY_TO_PURCHASE - Set AUTO_PURCHASE=true to complete order ***")
                        log_race_finished(self.team, "READY_TO_PURCHASE")
                    else:
                        log_race_finished(self.team, f"Finished: {reason}")
                    break
                
                # Execute action
                result = self._execute_action(action)
                self.actions_taken += 1
                
                print(f"  Action: {action.get('action')} -> {result.get('output')}")
                if not result.get("success"):
                    print(f"  Error: {result.get('error', 'Unknown')}")
                    self.consecutive_failures += 1
                else:
                    self.consecutive_failures = 0
                
                # Track in history
                status = result.get("output", "") or result.get("error", "failed")
                self.action_history.append((action.get("action"), status))
                
                # If too many consecutive failures, stop
                if self.consecutive_failures >= 5:
                    print(f"\nToo many consecutive failures ({self.consecutive_failures}). Stopping.")
                    log_race_finished(self.team, "stuck")
                    return {"status": "stuck", "reason": "Too many consecutive failures"}
                
                # Check for specific events
                if action.get("action") == "select_cheese_pizza":
                    log_pizza_found(self.team, "cheese")
                elif action.get("action") == "add_to_cart":
                    log_cart_updated(self.team, "pizza added")
                elif action.get("action") == "inspect_cart":
                    state = self._get_order_state()
                    if state.get("total_verified"):
                        log_price_checked(self.team, state.get("total_verified"))
                elif action.get("action") == "proceed_to_checkout":
                    log_checkout_reached(self.team)
            
            print(f"\nAgent stopped after {self.actions_taken} actions")
            return {"status": "completed", "actions": self.actions_taken}
            
        except KeyboardInterrupt:
            print(f"\nInterrupted by user")
            log_race_finished(self.team, "INTERRUPTED")
            return {"status": "interrupted", "actions": self.actions_taken}
        
        finally:
            print(f"\nStopping Papa John's tool...")
            self.pj_tool.stop()
            log_browser_stopped(self.team)


def run_pizza_agent(team: str):
    """Run the Pizza Agent for a team."""
    runner = PizzaAgentRunner(team)
    return runner.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 execution/runner.py <team>")
        print("Example: python3 execution/runner.py oracle")
        sys.exit(1)
    
    team = sys.argv[1].lower()
    
    try:
        result = run_pizza_agent(team)
        print(f"\nResult: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
