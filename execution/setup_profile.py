#!/usr/bin/env python3
"""
Setup persistent browser profile for Mistralathon.

Launches Chrome with the same persistent profile used by runner.py.
Lets user manually log in, save address, and save payment method.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from browser import SyncBrowserController


def main():
    print("Launching browser with persistent profile...")
    print("This uses the same profile as execution/runner.py")
    print()
    
    browser = SyncBrowserController(headless=False)
    browser.start()
    
    print()
    print("=" * 60)
    print("Browser launched with persistent profile.")
    print("=" * 60)
    print()
    print("Log into any pizza/delivery services you want available to the agents.")
    print()
    print("While Chrome is open, manually:")
    print("  - log in to delivery/restaurant websites")
    print("  - save your delivery address")
    print("  - save payment method in Chrome's profile")
    print()
    print("Press Enter in this terminal when you are done...")
    print()
    
    input()
    
    print()
    print("Closing browser...")
    browser.stop()
    print("Browser closed. Profile is saved and will be reused.")


if __name__ == "__main__":
    main()
