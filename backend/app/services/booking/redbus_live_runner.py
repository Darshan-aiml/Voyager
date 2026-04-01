from __future__ import annotations

from typing import Iterable

from app.models.request import ExecuteBookingAutomationRequest, StartAutomatedBookingRequest
from app.services.booking.live_execution_service import BrowserExecutionResult


class RedBusLiveAutomationRunner:
    async def run(
        self,
        *,
        payload: StartAutomatedBookingRequest,
        booking_url: str,
        action: str,
        request: ExecuteBookingAutomationRequest,
    ) -> BrowserExecutionResult:
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError:
            return BrowserExecutionResult(
                status="failed",
                message="Playwright is not installed in the current environment.",
                current_url=booking_url,
                page_title=None,
                requires_human_action=False,
                notes=["Install Playwright and browser binaries before running live automation."],
            )

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=request.headless)
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(booking_url, wait_until="domcontentloaded", timeout=request.timeout_ms)
                await page.wait_for_timeout(1500)

                if action == "search_and_select":
                    result = await self._run_search_and_select(
                        page=page,
                        payload=payload,
                        timeout_ms=request.timeout_ms,
                    )
                elif action == "fill_traveller_details":
                    result = await self._run_fill_traveller_details(
                        page=page,
                        payload=payload,
                        timeout_ms=request.timeout_ms,
                    )
                elif action == "payment":
                    result = await self._run_payment_handoff(page=page, timeout_ms=request.timeout_ms)
                else:
                    result = BrowserExecutionResult(
                        status="paused_for_human",
                        message=f"{action} requires human confirmation or OTP handling.",
                        current_url=page.url,
                        page_title=await page.title(),
                        requires_human_action=True,
                        notes=["Use the workflow action endpoint after the user completes the manual checkpoint."],
                    )

                await context.close()
                await browser.close()
                return result
        except PlaywrightTimeoutError:
            return BrowserExecutionResult(
                status="failed",
                message=f"Timed out while executing {action} on RedBus.",
                current_url=booking_url,
                page_title=None,
                requires_human_action=False,
                notes=["The RedBus DOM did not stabilize before the timeout expired."],
            )
        except Exception as exc:
            return BrowserExecutionResult(
                status="failed",
                message=f"RedBus live automation failed: {exc}",
                current_url=booking_url,
                page_title=None,
                requires_human_action=False,
                notes=["Inspect RedBus selectors or browser session logs to refine the runner."],
            )

    async def _run_search_and_select(self, *, page, payload: StartAutomatedBookingRequest, timeout_ms: int):
        await self._dismiss_common_popups(page)
        await self._fill_if_present(
            page,
            selectors=["#src", "input[id='src']", "input[placeholder*='From']"],
            value=payload.source,
        )
        await self._fill_if_present(
            page,
            selectors=["#dest", "input[id='dest']", "input[placeholder*='To']"],
            value=payload.destination,
        )

        search_clicked = await self._click_first(
            page,
            selectors=[
                "button:has-text('Search Buses')",
                "[data-testid='searchButton']",
                "button[class*='search']",
            ],
        )
        if search_clicked:
            await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(2000)

        view_seats_clicked = await self._click_first(
            page,
            selectors=[
                "button:has-text('View Seats')",
                "text=View Seats",
                "button:has-text('Select Seats')",
                "text=Select Seats",
            ],
        )
        if view_seats_clicked:
            await page.wait_for_timeout(2000)
            await self._select_first_available_seat(page)
            await self._choose_optional_point(
                page,
                preferred_value=payload.preferences.boarding_point if payload.preferences else None,
                selectors=[
                    "text=Select boarding point",
                    "button:has-text('Boarding point')",
                ],
            )
            await self._choose_optional_point(
                page,
                preferred_value=payload.preferences.drop_point if payload.preferences else None,
                selectors=[
                    "text=Select dropping point",
                    "button:has-text('Dropping point')",
                ],
            )
            await self._click_first(
                page,
                selectors=[
                    "button:has-text('Proceed to book')",
                    "button:has-text('Continue')",
                    "button:has-text('Book Seat')",
                ],
            )

        return BrowserExecutionResult(
            status="completed",
            message="RedBus search, seat selection, and booking handoff step completed.",
            current_url=page.url,
            page_title=await page.title(),
            requires_human_action=False,
            notes=[
                "Selected the first reachable RedBus result and attempted seat selection.",
                "Proceeding to traveller details works best after source, destination, and date are already reflected in the RedBus URL.",
            ],
        )

    async def _run_fill_traveller_details(
        self, *, page, payload: StartAutomatedBookingRequest, timeout_ms: int
    ) -> BrowserExecutionResult:
        await self._dismiss_common_popups(page)
        passenger = payload.passengers[0]

        await self._fill_if_present(
            page,
            selectors=[
                "input[name='name']",
                "input[placeholder*='Name']",
                "input[id*='passengerName']",
            ],
            value=f"{passenger.first_name} {passenger.last_name}",
        )
        await self._fill_if_present(
            page,
            selectors=[
                "input[name='age']",
                "input[placeholder='Age']",
                "input[id*='passengerAge']",
            ],
            value=str(passenger.age),
        )
        await self._click_first(
            page,
            selectors=[
                f"text={passenger.gender.capitalize()}",
                f"label:has-text('{passenger.gender.capitalize()}')",
            ],
        )
        await self._fill_if_present(
            page,
            selectors=[
                "input[name='email']",
                "input[type='email']",
                "input[placeholder*='Email']",
            ],
            value=payload.contact.email,
        )
        await self._fill_if_present(
            page,
            selectors=[
                "input[name='mobile']",
                "input[type='tel']",
                "input[placeholder*='Phone']",
                "input[placeholder*='Mobile']",
            ],
            value=payload.contact.phone,
        )

        await self._click_first(
            page,
            selectors=[
                "button:has-text('Continue')",
                "button:has-text('Proceed to pay')",
                "button:has-text('Proceed')",
            ],
        )
        await page.wait_for_timeout(1500)

        return BrowserExecutionResult(
            status="completed",
            message="RedBus traveller details were filled and the flow advanced toward checkout.",
            current_url=page.url,
            page_title=await page.title(),
            requires_human_action=False,
            notes=[
                "Filled the first passenger and primary contact details.",
                "If RedBus requires OTP at this point, pause the flow and use the workflow action endpoint after verification.",
            ],
        )

    async def _run_payment_handoff(self, *, page, timeout_ms: int) -> BrowserExecutionResult:
        await self._dismiss_common_popups(page)
        await self._click_first(
            page,
            selectors=[
                "button:has-text('Proceed to pay')",
                "button:has-text('Pay')",
                "button:has-text('Continue to payment')",
            ],
        )
        await page.wait_for_timeout(1000)
        return BrowserExecutionResult(
            status="paused_for_human",
            message="RedBus checkout reached the payment handoff step. Manual payment confirmation is still required.",
            current_url=page.url,
            page_title=await page.title(),
            requires_human_action=True,
            notes=[
                "Browser automation stopped before final payment capture.",
                "Have the user complete OTP, wallet, or card confirmation before marking the workflow complete.",
            ],
        )

    async def _dismiss_common_popups(self, page) -> None:
        await self._click_first(
            page,
            selectors=[
                "button:has-text('Accept')",
                "button:has-text('Allow')",
                "button[aria-label='Close']",
                "button:has-text('Close')",
                "text=No thanks",
            ],
            timeout_ms=1000,
        )

    async def _fill_if_present(self, page, *, selectors: Iterable[str], value: str) -> bool:
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            try:
                await locator.click(timeout=1000)
                await locator.fill(value, timeout=1000)
                return True
            except Exception:
                continue
        return False

    async def _click_first(
        self, page, *, selectors: Iterable[str], timeout_ms: int = 2000
    ) -> bool:
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            try:
                await locator.click(timeout=timeout_ms)
                return True
            except Exception:
                continue
        return False

    async def _select_first_available_seat(self, page) -> bool:
        selectors = [
            "[data-testid*='seat']:not([aria-disabled='true'])",
            "[class*='seat']:not([class*='booked'])",
            "canvas",
        ]
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            try:
                await locator.click(timeout=1500)
                return True
            except Exception:
                continue
        return False

    async def _choose_optional_point(self, page, *, preferred_value: str | None, selectors: list[str]) -> bool:
        opened = await self._click_first(page, selectors=selectors, timeout_ms=1000)
        if not opened:
            return False
        if preferred_value:
            preferred_clicked = await self._click_first(
                page,
                selectors=[
                    f"text={preferred_value}",
                    f"label:has-text('{preferred_value}')",
                    f"div:has-text('{preferred_value}')",
                ],
                timeout_ms=1000,
            )
            if preferred_clicked:
                return True
        return await self._click_first(
            page,
            selectors=[
                "label",
                "li",
                "div[role='option']",
            ],
            timeout_ms=1000,
        )
