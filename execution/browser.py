"""
Browser Controller for Mistralathon / Vibe Arena

Provides simple browser automation capabilities using Playwright.
Runs Chromium in visible/headed mode with persistent profile.
"""

import os
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


# Profile directory - MUST be gitignored
PROFILE_DIR = Path(__file__).parent / ".browser_profile"


class BrowserController:
    """Simple browser controller with basic actions."""
    
    def __init__(self, headless: bool = False, profile_dir: Path = None):
        self.headless = headless
        self.profile_dir = profile_dir or PROFILE_DIR
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        
    async def start(self):
        """Start browser with persistent profile."""
        self._playwright = await async_playwright().start()
        
        # Create profile directory if it doesn't exist
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Use installed Chrome browser with persistent context
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            channel="chrome",
        )
        self._page = await self._context.new_page()
        
    async def stop(self):
        """Stop browser and cleanup."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._playwright = None
    
    async def navigate(self, url: str) -> bool:
        """Navigate to URL."""
        try:
            await self._page.goto(url, timeout=30000)
            return True
        except Exception as e:
            print(f"  [Browser] Navigate error: {e}")
            return False
    
    async def visible_page_text(self) -> str:
        """Get all visible text on the page."""
        try:
            # Get body text, excluding script/style content
            text = await self._page.evaluate("""
                () => {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let text = '';
                    let node;
                    while (node = walker.nextNode()) {
                        const trimmed = node.textContent.trim();
                        if (trimmed && node.parentElement && !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(node.parentElement.tagName)) {
                            text += trimmed + ' ';
                        }
                    }
                    return text.substring(0, 100000);
                }
            """)
            return text
        except Exception as e:
            print(f"  [Browser] visible_page_text error: {e}")
            return ""
    
    async def click(self, target: str) -> bool:
        """Click on an element. Uses text-based locator first, then CSS."""
        try:
            # Try text-based click first (more robust)
            try:
                await self._page.get_by_text(target, exact=False).first.click(timeout=5000)
                return True
            except Exception:
                pass
            
            # Try CSS selector
            try:
                await self._page.click(target, timeout=5000)
                return True
            except Exception:
                pass
            
            # Try role-based click
            try:
                await self._page.get_by_role("button", name=target).first.click(timeout=5000)
                return True
            except Exception:
                pass
            
            return False
        except Exception as e:
            print(f"  [Browser] Click error for '{target}': {e}")
            return False
    
    async def type_into(self, target: str, value: str) -> bool:
        """Type text into a field."""
        try:
            # Try to find by label/placeholder text
            try:
                await self._page.get_by_text(target, exact=False).first.fill(value)
                return True
            except Exception:
                pass
            
            # Try CSS selector
            try:
                await self._page.fill(target, value)
                return True
            except Exception:
                pass
            
            # Try placeholder
            try:
                await self._page.get_by_placeholder(target).first.fill(value)
                return True
            except Exception:
                pass
            
            return False
        except Exception as e:
            print(f"  [Browser] Type error for '{target}': {e}")
            return False
    
    async def screenshot(self, path: str = None) -> str:
        """Take a screenshot. Returns path to saved image."""
        try:
            if path is None:
                import uuid
                path = str(Path(__file__).parent / "screenshots" / f"{uuid.uuid4()}.png")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            await self._page.screenshot(path=path)
            return path
        except Exception as e:
            print(f"  [Browser] Screenshot error: {e}")
            return ""
    
    async def current_url(self) -> str:
        """Get current page URL."""
        try:
            return self._page.url
        except Exception as e:
            print(f"  [Browser] current_url error: {e}")
            return ""
    
    async def cart_state(self) -> dict:
        """Extract cart/state information from page."""
        try:
            # Try to find common cart elements
            cart_data = {}
            
            # Get page text for analysis
            text = await self.visible_page_text()
            
            # Extract price information
            import re
            prices = re.findall(r'\$[\d,.]+', text)
            if prices:
                cart_data['prices'] = prices
            
            # Check for quantity
            qty_matches = re.findall(r'(\d+)\s*(?:x|qty|quantity)', text, re.IGNORECASE)
            if qty_matches:
                cart_data['quantity'] = int(qty_matches[0])
            
            # Check for items
            cart_data['page_text'] = text[:2000]
            
            return cart_data
        except Exception as e:
            print(f"  [Browser] cart_state error: {e}")
            return {"error": str(e)}


# Sync wrapper for convenience
class SyncBrowserController:
    """Synchronous wrapper around BrowserController."""
    
    def __init__(self, headless: bool = False, profile_dir: Path = None):
        self.headless = headless
        self.profile_dir = profile_dir
        self._browser = BrowserController(headless, profile_dir)
        self._loop = None
        
    def start(self):
        """Start browser synchronously."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._browser.start())
        
    def stop(self):
        """Stop browser synchronously."""
        if self._loop:
            self._loop.run_until_complete(self._browser.stop())
            self._loop.close()
        
    def navigate(self, url: str) -> bool:
        return self._loop.run_until_complete(self._browser.navigate(url))
    
    def visible_page_text(self) -> str:
        return self._loop.run_until_complete(self._browser.visible_page_text())
    
    def click(self, target: str) -> bool:
        return self._loop.run_until_complete(self._browser.click(target))
    
    def type_into(self, target: str, value: str) -> bool:
        return self._loop.run_until_complete(self._browser.type_into(target, value))
    
    def screenshot(self, path: str = None) -> str:
        return self._loop.run_until_complete(self._browser.screenshot(path))
    
    def current_url(self) -> str:
        return self._loop.run_until_complete(self._browser.current_url())
    
    def cart_state(self) -> dict:
        return self._loop.run_until_complete(self._browser.cart_state())
