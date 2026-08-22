#!/usr/bin/env python3
"""
Smoke test for browser automation.

Tests basic browser capabilities:
1. Launch visible Chromium
2. Navigate to a public website
3. Extract visible page text
4. Print current URL
5. Take a screenshot
6. Close successfully
"""

import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")
load_dotenv()

# Add execution to path
sys.path.insert(0, str(Path(__file__).parent))

from browser import SyncBrowserController


def test_browser():
    """Run smoke test."""
    print("=" * 60)
    print("Browser Smoke Test")
    print("=" * 60)
    
    # Use visible browser
    browser = SyncBrowserController(headless=False)
    
    try:
        print("\n1. Starting browser...")
        browser.start()
        print("   Browser started successfully")
        
        print("\n2. Navigating to https://www.google.com...")
        success = browser.navigate("https://www.google.com")
        if not success:
            print("   FAILED: Could not navigate")
            return False
        print("   Navigated successfully")
        
        print("\n3. Getting current URL...")
        url = browser.current_url()
        print(f"   Current URL: {url}")
        if not url or "google" not in url.lower():
            print("   FAILED: URL not as expected")
            return False
        
        print("\n4. Extracting visible page text...")
        text = browser.visible_page_text()
        if not text or len(text) < 100:
            print("   FAILED: Could not extract page text")
            return False
        print(f"   Extracted {len(text)} characters of visible text")
        print(f"   First 200 chars: {text[:200]}...")
        
        print("\n5. Taking screenshot...")
        screenshot_path = browser.screenshot()
        if not screenshot_path:
            print("   FAILED: Could not take screenshot")
            return False
        print(f"   Screenshot saved to: {screenshot_path}")
        
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
        print("\n6. Stopping browser...")
        browser.stop()
        print("   Browser stopped")


if __name__ == "__main__":
    success = test_browser()
    sys.exit(0 if success else 1)
