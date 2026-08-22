#!/usr/bin/env python3
"""
Pizza Agent Runner for Mistralathon / Vibe Arena

Runs the Oracle Pizza Agent with real browser control using Mistral as the reasoning engine.

Usage:
    python3 execution/runner.py oracle

Environment:
    MISTRAL_API_KEY: Required for Mistral API access
    AUTO_PURCHASE: Set to "true" to allow final purchase (default: false)
"""

import json
import os
import sys
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
from browser import SyncBrowserController


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


# =============================================================================
# Event Logging Helpers
# =============================================================================

def log_browser_started(team: str):
    log_event(team, "execution", "runner", "browser_started", "Browser launched")


def log_browser_stopped(team: str):
    log_event(team, "execution", "runner", "browser_stopped", "Browser closed")


def log_navigate(team: str, url: str):
    log_event(team, "execution", "runner", "navigate", f"Navigated to: {url}")


def log_page_inspected(team: str, url: str):
    log_event(team, "execution", "runner", "page_inspected", f"Inspected: {url}")


def log_restaurant_found(team: str, name: str):
    log_event(team, "execution", "runner", "restaurant_found", f"Found: {name}")


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
    """Invoke Mistral with a prompt."""
    try:
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Mistral invocation failed: {e}")


# =============================================================================
# Pizza Agent Runner
# =============================================================================

class PizzaAgentRunner:
    """Runs the Pizza Agent with browser control."""
    
    def __init__(self, team: str):
        self.team = team
        self.browser = SyncBrowserController(headless=False)
        self.client = get_mistral_client()
        self.actions_taken = 0
        self.orders_submitted = 0
        self.start_time = None
        
    def _check_safety_limits(self):
        """Check if we've hit safety limits."""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if self.actions_taken >= MAX_ACTIONS:
            return False, "Max actions reached"
        if elapsed >= MAX_RUNTIME_SECONDS:
            return False, "Max runtime reached"
        return True, ""
    
    def _validate_action(self, action: dict) -> tuple[bool, str]:
        """Validate action from the model."""
        if not isinstance(action, dict):
            return False, "Invalid action format"
        
        valid_actions = ["navigate", "click", "type", "inspect", "screenshot", "finish", "fail"]
        if action.get("action") not in valid_actions:
            return False, f"Invalid action: {action.get('action')}"
        
        if action.get("action") == "navigate":
            if not action.get("target") or not action.get("target").startswith("http"):
                return False, "Navigate requires valid URL"
        
        return True, ""
    
    def _get_agent_prompt(self, agent_spec: dict, browser_state: dict) -> str:
        """Build prompt for the Pizza Agent."""
        system_prompt = agent_spec.get("system_prompt", "")
        objective = agent_spec.get("objective", "")
        constraints = agent_spec.get("constraints", [])
        success_conditions = agent_spec.get("success_conditions", [])
        
        # Build browser state summary (truncated)
        page_text = browser_state.get("text", "")
        if page_text:
            page_text = page_text[:4000]  # Limit context
        
        current_url = browser_state.get("url", "")
        
        auto_purchase = os.environ.get("AUTO_PURCHASE", "false").lower() == "true"
        
        prompt = f"""You are the Pizza Agent for the Oracle team.

{system_prompt}

OBJECTIVE: {objective}

CONSTRAINTS:
{json.dumps(constraints, indent=2)}

SUCCESS CONDITIONS:
{json.dumps(success_conditions, indent=2)}

AUTO_PURCHASE: {"ENABLED" if auto_purchase else "DISABLED"}

Current browser state:
- URL: {current_url}
- Visible text preview: {page_text[:500]}...

Return ONE action as JSON with these fields:
{{
  "action": "navigate"|"click"|"type"|"inspect"|"screenshot"|"finish"|"fail",
  "target": "...",  // URL for navigate, element for click/type
  "value": "...",   // text to type (for type action)
  "reason_summary": "short observable explanation"
}}

RULES:
- Only return valid JSON
- action must be one of: navigate, click, type, inspect, screenshot, finish, fail
- reason_summary must be short and observable (no private thoughts)
- For navigate: target must be a valid URL
- For click/type: target must be visible on the page
- If you detect we're ready to purchase but AUTO_PURCHASE is DISABLED, return action:"finish" with reason_summary:"READY_TO_PURCHASE"
- Never bypass CAPTCHA, MFA, authentication, or payment security
- Never expose private information

What is your ONE next action?"""
        
        return prompt
    
    def _get_browser_state(self) -> dict:
        """Get current browser state."""
        try:
            url = self.browser.current_url()
        except Exception:
            url = ""
        
        try:
            text = self.browser.visible_page_text()
        except Exception:
            text = ""
        
        return {
            "url": url,
            "text": text
        }
    
    def _execute_action(self, action: dict) -> dict:
        """Execute a browser action."""
        act = action.get("action")
        target = action.get("target", "")
        value = action.get("value", "")
        
        result = {"success": False, "error": "", "output": ""}
        
        try:
            if act == "navigate":
                success = self.browser.navigate(target)
                if success:
                    log_navigate(self.team, target)
                    result["output"] = f"Navigated to {target}"
                result["success"] = success
                
            elif act == "click":
                success = self.browser.click(target)
                result["output"] = f"Clicked: {target}"
                result["success"] = success
                
            elif act == "type":
                success = self.browser.type_into(target, value)
                result["output"] = f"Typed '{value}' into: {target}"
                result["success"] = success
                
            elif act == "inspect":
                text = self.browser.visible_page_text()
                log_page_inspected(self.team, target)
                result["output"] = f"Page text length: {len(text)}"
                result["success"] = True
                
            elif act == "screenshot":
                path = self.browser.screenshot()
                result["output"] = f"Screenshot: {path}"
                result["success"] = bool(path)
                
            elif act == "finish":
                reason = action.get("reason_summary", "")
                if "READY_TO_PURCHASE" in reason:
                    log_ready_to_purchase(self.team)
                result["success"] = True
                result["output"] = reason
                
            elif act == "fail":
                reason = action.get("reason_summary", "Unknown failure")
                result["output"] = reason
                result["success"] = False
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def run(self):
        """Run the Pizza Agent."""
        print(f"\n{'='*60}")
        print(f"Pizza Agent Runner - {self.team}")
        print(f"{'='*60}\n")
        
        # Load challenge
        challenge_path = RUNS_DIR / self.team / "challenge.json"
        if not challenge_path.exists():
            challenge_path = CHALLENGE_PATH
        
        with open(challenge_path) as f:
            challenge = json.load(f)
        print(f"Challenge: {challenge.get('title', 'Unknown')}")
        
        # Load agent spec
        agent_spec_path = RUNS_DIR / self.team / "pizza-agent" / "agent_spec.json"
        with open(agent_spec_path) as f:
            agent_spec = json.load(f)
        print(f"Agent: {agent_spec.get('agent_id', 'Unknown')}")
        
        # Start browser
        print(f"\nStarting browser...")
        self.browser.start()
        log_browser_started(self.team)
        self.start_time = datetime.now(timezone.utc)
        
        try:
            # Initial navigation
            print(f"Navigating to blank page...")
            self.browser.navigate("about:blank")
            
            # Main loop
            while True:
                # Check limits
                ok, reason = self._check_safety_limits()
                if not ok:
                    print(f"\nSafety limit reached: {reason}")
                    log_race_finished(self.team, f"STOPPED: {reason}")
                    return {"status": "stopped", "reason": reason}
                
                # Get browser state
                browser_state = self._get_browser_state()
                
                # Build prompt
                prompt = self._get_agent_prompt(agent_spec, browser_state)
                
                # Get action from Mistral
                print(f"\n[Action {self.actions_taken + 1}] Asking Pizza Agent for next action...")
                try:
                    response = invoke_mistral(self.client, prompt, max_tokens=2048)
                except Exception as e:
                    print(f"  Mistral error: {e}")
                    log_error(self.team, "execution", "runner", str(e))
                    break
                
                # Parse response
                try:
                    # Try to extract JSON from response
                    import re
                    json_match = re.search(r'\{[^}]*\}', response, re.DOTALL)
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
                
                # Check for specific events
                if action.get("action") == "navigate":
                    log_navigate(self.team, action.get("target", ""))
                elif action.get("action") == "click":
                    # Check if this might be checkout
                    if "checkout" in action.get("target", "").lower() or "place order" in action.get("target", "").lower():
                        log_checkout_reached(self.team)
                
            
            print(f"\nAgent stopped after {self.actions_taken} actions")
            return {"status": "completed", "actions": self.actions_taken}
            
        except KeyboardInterrupt:
            print(f"\nInterrupted by user")
            log_race_finished(self.team, "INTERRUPTED")
            return {"status": "interrupted", "actions": self.actions_taken}
        
        finally:
            print(f"\nStopping browser...")
            self.browser.stop()
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
