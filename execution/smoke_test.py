#!/usr/bin/env python3
"""
Smoke test for Papa John's ordering adapter.

Tests basic browser capabilities:
1. Launch visible Chromium
2. Navigate to Papa John's website
3. Extract visible page text
4. Verify menu is reachable
5. Close successfully
"""

import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")
load_dotenv()

# Add execution to path
sys.path.insert(0, str(Path(__file__).parent))

from papa_johns import SyncPapaJohnsOrderingTool


def test_papa_johns_adapter():
    """Run smoke test for Papa John's adapter."""
    print("=" * 60)
    print("Papa John's Adapter Smoke Test")
    print("=" * 60)
    
    # Use visible browser
    tool = SyncPapaJohnsOrderingTool(headless=False)
    
    try:
        print("\n1. Starting Papa John's tool...")
        tool.start()
        print("   Tool started successfully")
        
        print("\n2. Opening https://www.papajohns.com/...")
        result = tool.open()
        if result.get("status") != "success":
            print(f"   FAILED: Could not open - {result}")
            return False
        print(f"   Opened successfully")
        
        print("\n3. Checking for CAPTCHA...")
        if tool.is_captcha_blocked():
            print("   FAILED: CAPTCHA detected")
            return False
        print("   No CAPTCHA detected")
        
        print("\n4. Inspecting menu...")
        menu_result = tool.inspect_menu()
        if menu_result.get("status") != "success":
            print(f"   FAILED: Could not inspect menu - {menu_result}")
            return False
        
        pizza_options = menu_result.get("pizza_options", [])
        print(f"   Found {len(pizza_options)} pizza options")
        if pizza_options:
            print(f"   Pizza options: {[p['name'] for p in pizza_options]}")
        
        sizes = menu_result.get("sizes_available", [])
        print(f"   Sizes available: {sizes}")
        
        page_text = menu_result.get("page_text", "")
        if not page_text or len(page_text) < 100:
            print("   WARNING: Page text seems short")
        else:
            print(f"   Extracted {len(page_text)} characters from page")
        
        print("\n5. Getting order state...")
        state = tool.get_order_state()
        print(f"   Order state: {state}")
        
        print("\n" + "=" * 60)
        print("SMOKE TEST PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n6. Stopping tool...")
        tool.stop()
        print("   Tool stopped")


if __name__ == "__main__":
    success = test_papa_johns_adapter()
    sys.exit(0 if success else 1)
