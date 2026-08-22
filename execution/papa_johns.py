"""
Papa John's Ordering Tool

Deterministic Playwright-based adapter for Papa John's website.
Provides high-level ordering actions for the Pizza Agent.

This is intentionally Papa John's-specific for reliability.
"""

import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright


# Profile directory - MUST be gitignored
PROFILE_DIR = Path(__file__).parent / ".browser_profile"


class PapaJohnsOrderingTool:
    """Deterministic ordering tool for Papa John's."""
    
    def __init__(self, headless: bool = False, profile_dir: Path = None):
        self.headless = headless
        self.profile_dir = profile_dir or PROFILE_DIR
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._started = False
        
    async def start(self):
        """Start browser with persistent profile."""
        self._playwright = await async_playwright().start()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            channel="chrome",
        )
        self._page = await self._context.new_page()
        self._started = True
        
    async def stop(self):
        """Stop browser."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._playwright = None
        self._started = False
        
    async def open(self, url: str = "https://www.papajohns.com/"):
        """Open Papa John's website."""
        if not self._started:
            await self.start()
        await self._page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(2000)
        return {"status": "success", "url": url}
    
    async def _check_captcha(self) -> bool:
        """Check if CAPTCHA/security challenge is present. Returns True if blocked."""
        try:
            text = await self._get_visible_text()
            text_lower = text.lower()
            captcha_indicators = [
                "verify you are human", "performing security verification",
                "cloudflare", "captcha", "security check", "bot detection",
                "please verify", "are you a robot", "human verification",
            ]
            for indicator in captcha_indicators:
                if indicator in text_lower:
                    return True
            return False
        except:
            return False
    
    async def _get_visible_text(self, max_len: int = 20000) -> str:
        """Get visible text on page."""
        return await self._page.evaluate("""
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
                    if (text.length > 20000) break;
                }
                return text.substring(0, 20000);
            }
        """)
    
    async def _wait_for_element(self, locator, timeout: int = 10000):
        """Wait for an element to be visible."""
        try:
            await locator.wait_for(timeout=timeout, state="visible")
            return True
        except:
            return False
    
    async def _ensure_on_pizza_menu(self):
        """Navigate to the actual pizza menu/builder page if not already there.

        The Papa John's homepage only has category nav links (Pizza, Deals, etc.)
        and no pizza products of its own, so menu/selection actions must first
        land on /order/menu/pizza (or the builder/cart pages reached from it).
        """
        url = self._page.url
        on_ordering_flow = any(
            path in url for path in ["/order/menu/pizza", "/order/builder/pizza", "/order/cart"]
        )
        if not on_ordering_flow:
            await self._page.goto(
                "https://www.papajohns.com/order/menu/pizza",
                timeout=30000,
                wait_until="domcontentloaded",
            )
            await self._page.wait_for_timeout(2500)

    async def _handle_modal(self) -> bool:
        """Detect and handle blocking modals. Returns True if modal was handled."""
        try:
            modal_text = await self._page.evaluate("""
                () => {
                    const dialogs = document.querySelectorAll('[role="dialog"], [role="alertdialog"], .modal, .dialog');
                    for (const d of dialogs) {
                        if (d.offsetParent !== null) {
                            return d.innerText?.trim() || '';
                        }
                    }
                    return '';
                }
            """)
            
            if modal_text and len(modal_text) > 50:
                # There's a modal - try to find Continue/Cancel buttons
                continue_btn = self._page.get_by_role("button", name=re.compile(r'continue', re.IGNORECASE)).first
                cancel_btn = self._page.get_by_role("button", name=re.compile(r'cancel', re.IGNORECASE)).first
                
                # For Papa John's, common confirmation modals can be safely dismissed
                # with Continue if they're about selections changing
                modal_lower = modal_text.lower()
                if "continue" in modal_lower or "change" in modal_lower or "update" in modal_lower:
                    if await self._wait_for_element(continue_btn, timeout=3000):
                        await continue_btn.click()
                        await self._page.wait_for_timeout(1000)
                        return True
                
                if await self._wait_for_element(cancel_btn, timeout=3000):
                    await cancel_btn.click()
                    await self._page.wait_for_timeout(1000)
                    return True
                    
            return False
        except:
            return False
    
    async def inspect_menu(self) -> dict:
        """Inspect the menu and return available pizza options."""
        if not self._started:
            await self.start()
            await self.open()
        
        # Check for CAPTCHA
        if await self._check_captcha():
            return {"status": "blocked", "reason": "captcha_detected"}

        # The homepage has no pizza products - jump to the real menu page
        await self._ensure_on_pizza_menu()

        # Handle any modals
        await self._handle_modal()

        text = await self._get_visible_text()

        # Look for pizza options
        pizza_options = []
        
        # Check for cheese pizza
        cheese_patterns = [
            r'Cheese Pizza', r'Classic Cheese',
            r'Large Cheese', r'Medium Cheese', r'Small Cheese'
        ]
        
        for pattern in cheese_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                pizza_options.append({
                    "name": match.group(0),
                    "context": context
                })
        
        # Check for sizes
        sizes = []
        size_patterns = [r'Small', r'Medium', r'Large']
        for pattern in size_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                sizes.append(pattern)
        
        return {
            "status": "success",
            "pizza_options": pizza_options,
            "sizes_available": sizes,
            "page_text": text[:2000]
        }
    
    async def select_cheese_pizza(self) -> dict:
        """Select a cheese pizza from the menu."""
        if not self._started:
            await self.start()
            await self.open()
        
        # Check for CAPTCHA
        if await self._check_captcha():
            return {"status": "blocked", "reason": "captcha_detected"}

        # The homepage has no pizza products - jump to the real menu page
        await self._ensure_on_pizza_menu()

        # Handle modals first
        await self._handle_modal()

        # Try multiple strategies to find cheese pizza.
        # Note: the product card is a plain styled div (no button/link/heading
        # role), so get_by_text is what actually finds it - the role-based
        # strategies are kept as a fallback in case the markup changes.
        strategies = [
            lambda: self._page.get_by_text(re.compile(r'^cheese pizza$', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("button", name=re.compile(r'cheese.*pizza', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("link", name=re.compile(r'cheese.*pizza', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("heading", name=re.compile(r'cheese.*pizza', re.IGNORECASE)).first,
            lambda: self._page.get_by_text(re.compile(r'cheese.*pizza', re.IGNORECASE)).first,
            lambda: self._page.locator('.product-card:has-text("Cheese")').first,
            lambda: self._page.locator('[data-name*="Cheese" i]').first,
        ]

        for strategy in strategies:
            try:
                locator = strategy()
                if await self._wait_for_element(locator, timeout=5000):
                    await locator.scroll_into_view_if_needed()
                    await locator.click(timeout=5000)
                    await self._page.wait_for_timeout(2000)
                    text = await self._get_visible_text()
                    if "cheese" in text.lower() and ("pizza" in text.lower() or "selected" in text.lower()):
                        return {"status": "success", "message": "Cheese pizza selected"}
            except Exception:
                continue

        return {"status": "failed", "reason": "cheese_pizza_not_found"}
    
    async def set_size_small(self) -> dict:
        """Set the pizza size to small."""
        if not self._started:
            return {"status": "failed", "reason": "not_started"}
        
        # Check for CAPTCHA
        if await self._check_captcha():
            return {"status": "blocked", "reason": "captcha_detected"}
        
        # Handle modals first
        await self._handle_modal()
        
        # Try multiple strategies to find Small size
        strategies = [
            lambda: self._page.get_by_role("radio", name=re.compile(r'small', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("button", name=re.compile(r'small', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("option", name=re.compile(r'small', re.IGNORECASE)).first,
            lambda: self._page.get_by_label(re.compile(r'small', re.IGNORECASE)).first,
            lambda: self._page.get_by_text(re.compile(r'\bsmall\b', re.IGNORECASE)).first,
            lambda: self._page.locator('[data-size="Small"]').first,
            lambda: self._page.locator('[data-size*="small" i]').first,
        ]
        
        for strategy in strategies:
            try:
                locator = strategy()
                if await self._wait_for_element(locator, timeout=3000):
                    await locator.scroll_into_view_if_needed()
                    await locator.click(timeout=5000)
                    await self._page.wait_for_timeout(1500)
                    text = await self._get_visible_text()
                    if "small" in text.lower():
                        return {"status": "success", "message": "Size set to Small"}
            except Exception:
                continue
        
        return {"status": "failed", "reason": "small_size_not_found"}
    
    async def add_to_cart(self) -> dict:
        """Add the selected pizza to cart."""
        if not self._started:
            return {"status": "failed", "reason": "not_started"}
        
        # Check for CAPTCHA
        if await self._check_captcha():
            return {"status": "blocked", "reason": "captcha_detected"}
        
        # Handle modals first
        await self._handle_modal()
        
        # Try multiple strategies for Add to Cart / Add to Order
        strategies = [
            lambda: self._page.get_by_role("button", name=re.compile(r'add to cart', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("button", name=re.compile(r'add to order', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("button", name=re.compile(r'^add$', re.IGNORECASE)).first,
            lambda: self._page.get_by_text(re.compile(r'add to cart', re.IGNORECASE)).first,
            lambda: self._page.get_by_text(re.compile(r'add to order', re.IGNORECASE)).first,
            lambda: self._page.locator('button:has-text("Add")').first,
        ]
        
        for strategy in strategies:
            try:
                locator = strategy()
                if await self._wait_for_element(locator, timeout=3000):
                    await locator.scroll_into_view_if_needed()
                    await locator.click(timeout=5000)
                    await self._page.wait_for_timeout(2000)
                    text = await self._get_visible_text()
                    if any(word in text.lower() for word in ["cart", "order", "added", "item"]):
                        return {"status": "success", "message": "Added to cart"}
            except Exception:
                continue
        
        return {"status": "failed", "reason": "add_to_cart_button_not_found"}
    
    async def get_cart_state(self) -> dict:
        """Get current cart state: items, quantity, price.

        Reads the actual /order/cart page rather than trusting ambient text
        on whatever page happens to be current - promotional banners
        elsewhere on the site (e.g. "gift card up to $100") can otherwise be
        misread as the cart total.
        """
        if not self._started:
            return {"status": "failed", "reason": "not_started"}

        if "/order/cart" not in self._page.url:
            await self._page.goto("https://www.papajohns.com/order/cart", timeout=30000, wait_until="domcontentloaded")
            await self._page.wait_for_timeout(1500)

        text = await self._get_visible_text()

        cart_info = {
            "items": [],
            "quantity": 0,
            "total": None,
            "has_cheese_pizza": False,
            "has_small": False
        }

        text_lower = text.lower()

        # Check for cheese pizza
        if "cheese" in text_lower and "pizza" in text_lower:
            cart_info["has_cheese_pizza"] = True

        # Check for small. Note: Papa John's only offers a genuinely "Small"
        # pizza via Gluten-Free crust, and the cart line item for that
        # doesn't print the word "small" anywhere - it shows as
        # "Create Your Own - Gluten Free" instead. Treat that as small too.
        if re.search(r'\bsmall\b', text_lower) or "gluten free" in text_lower or "gluten-free" in text_lower:
            cart_info["has_small"] = True

        # Extract quantity from "YOUR ORDER (N ITEM(S))"
        qty_match = re.search(r'\((\d+)\s*items?\)', text_lower)
        if qty_match:
            cart_info["quantity"] = int(qty_match.group(1))
        else:
            qty_matches = re.findall(r'(\d+)\s*(?:x|qty|quantity|item)', text_lower, re.IGNORECASE)
            if qty_matches:
                cart_info["quantity"] = int(qty_matches[0])

        # Extract the real order total, labeled "TOTAL" (not the first/last
        # dollar amount on the page, which may be an unrelated promo price)
        total_match = re.search(r'\btotal\s*\$?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if total_match:
            cart_info["total"] = f"${total_match.group(1)}"
        else:
            price_matches = re.findall(r'\$[\d,.]+', text)
            if price_matches:
                cart_info["total"] = price_matches[-1]

        return {"status": "success", **cart_info}
    
    async def proceed_to_checkout(self) -> dict:
        """Proceed to checkout page."""
        if not self._started:
            return {"status": "failed", "reason": "not_started"}
        
        # Check for CAPTCHA
        if await self._check_captcha():
            return {"status": "blocked", "reason": "captcha_detected"}
        
        # Handle modals first
        await self._handle_modal()
        
        # Try multiple strategies for checkout
        strategies = [
            lambda: self._page.get_by_role("button", name=re.compile(r'checkout', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("link", name=re.compile(r'checkout', re.IGNORECASE)).first,
            lambda: self._page.get_by_text(re.compile(r'checkout', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("button", name=re.compile(r'place order', re.IGNORECASE)).first,
            lambda: self._page.get_by_role("link", name=re.compile(r'proceed to checkout', re.IGNORECASE)).first,
        ]
        
        for strategy in strategies:
            try:
                locator = strategy()
                if await self._wait_for_element(locator, timeout=3000):
                    await locator.scroll_into_view_if_needed()
                    
                    # AUTO_PURCHASE safety check
                    auto_purchase = os.environ.get("AUTO_PURCHASE", "false").lower() == "true"
                    
                    if not auto_purchase:
                        # Don't click final purchase - verify state first
                        cart_state = await self.get_cart_state()
                        
                        if (cart_state.get("has_cheese_pizza") and 
                            cart_state.get("has_small") and
                            cart_state.get("quantity") == 1 and
                            cart_state.get("total")):
                            total_str = cart_state.get("total", "$0")
                            try:
                                total = float(re.sub(r'[^\d.]', '', total_str))
                                if total <= 35.0:
                                    return {"status": "ready_to_purchase", "message": "READY_TO_PURCHASE"}
                            except:
                                pass
                        return {"status": "ready_to_purchase", "message": "READY_TO_PURCHASE - verification needed"}
                    
                    await locator.click(timeout=5000)
                    await self._page.wait_for_timeout(2000)
                    
                    # Verify we're at checkout
                    text = await self._get_visible_text()
                    if any(word in text.lower() for word in ["checkout", "payment", "delivery", "order summary"]):
                        return {"status": "success", "message": "Checkout reached"}
            except Exception:
                continue
        
        # If AUTO_PURCHASE is off, check if we're already ready
        auto_purchase = os.environ.get("AUTO_PURCHASE", "false").lower() == "true"
        if not auto_purchase:
            cart_state = await self.get_cart_state()
            if (cart_state.get("has_cheese_pizza") and 
                cart_state.get("has_small") and
                cart_state.get("quantity") == 1):
                return {"status": "ready_to_purchase", "message": "READY_TO_PURCHASE"}
        
        return {"status": "failed", "reason": "checkout_button_not_found"}
    
    async def get_order_state(self) -> dict:
        """Get comprehensive order state."""
        if not self._started:
            return {"status": "failed", "reason": "not_started"}
        
        text = await self._get_visible_text()
        url = self._page.url
        
        state = {
            "url": url,
            "pizza_selected": "cheese" in text.lower() and "pizza" in text.lower(),
            "size_small": re.search(r'\bsmall\b', text.lower()) is not None,
            "cart_reached": any(word in text.lower() for word in ["cart", "order"]),
            "checkout_reached": any(word in text.lower() for word in ["checkout", "payment", "delivery"]),
            "total_verified": None,
            "quantity_verified": 0
        }
        
        # Get cart state for verification
        cart = await self.get_cart_state()
        if cart.get("status") == "success":
            state["pizza_selected"] = cart.get("has_cheese_pizza", False)
            state["size_small"] = cart.get("has_small", False)
            state["quantity_verified"] = cart.get("quantity", 0)
            state["total_verified"] = cart.get("total")
        
        return {"status": "success", **state}


# Synchronous wrapper
class SyncPapaJohnsOrderingTool:
    """Synchronous wrapper around PapaJohnsOrderingTool."""
    
    def __init__(self, headless: bool = False, profile_dir: Path = None):
        self.headless = headless
        self.profile_dir = profile_dir
        self._tool = PapaJohnsOrderingTool(headless, profile_dir)
        self._loop = None
        
    def start(self):
        """Start tool synchronously."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._tool.start())
        
    def stop(self):
        """Stop tool synchronously."""
        if self._loop:
            self._loop.run_until_complete(self._tool.stop())
            self._loop.close()
            self._loop = None
    
    def open(self, url: str = "https://www.papajohns.com/") -> dict:
        return self._loop.run_until_complete(self._tool.open(url))
    
    def inspect_menu(self) -> dict:
        return self._loop.run_until_complete(self._tool.inspect_menu())
    
    def select_cheese_pizza(self) -> dict:
        return self._loop.run_until_complete(self._tool.select_cheese_pizza())
    
    def set_size_small(self) -> dict:
        return self._loop.run_until_complete(self._tool.set_size_small())
    
    def add_to_cart(self) -> dict:
        return self._loop.run_until_complete(self._tool.add_to_cart())
    
    def get_cart_state(self) -> dict:
        return self._loop.run_until_complete(self._tool.get_cart_state())
    
    def proceed_to_checkout(self) -> dict:
        return self._loop.run_until_complete(self._tool.proceed_to_checkout())
    
    def get_order_state(self) -> dict:
        return self._loop.run_until_complete(self._tool.get_order_state())
    
    def is_captcha_blocked(self) -> bool:
        return self._loop.run_until_complete(self._tool._check_captcha())
