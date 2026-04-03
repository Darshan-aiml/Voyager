from datetime import date

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.utils.helpers import slugify_city


class BookingService:
    async def get_booking_url(
        self, mode: str, source: str, destination: str, travel_date: date, external_id: str | None
    ) -> str:
        source_slug = slugify_city(source)
        destination_slug = slugify_city(destination)

        if mode == "train":
            return (
                "https://www.irctc.co.in/nget/train-search?"
                f"from={source_slug}&to={destination_slug}&date={travel_date.isoformat()}"
            )

        if mode == "flight":
            if external_id:
                return f"https://www.google.com/travel/flights?q={external_id}"
            return (
                "https://www.google.com/travel/flights?"
                f"from={source_slug}&to={destination_slug}&date={travel_date.isoformat()}"
            )

        onward = travel_date.strftime("%d-%b-%Y")
        return (
            f"https://www.redbus.in/bus-tickets/{source_slug}-to-{destination_slug}"
            f"?onward={onward}"
        )


async def execute_booking_flow(
    source: str,
    destination: str,
    date: str | None = None,
) -> dict[str, str]:
    playwright = None
    browser = None
    success = False

    try:
        print("Opening browser...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.redbus.in", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        print("Filling details...")
        await page.fill("#src", source)
        await page.wait_for_timeout(750)
        await page.press("#src", "ArrowDown")
        await page.wait_for_timeout(300)
        await page.press("#src", "Enter")

        await page.wait_for_timeout(750)
        await page.fill("#dest", destination)
        await page.wait_for_timeout(750)
        await page.press("#dest", "ArrowDown")
        await page.wait_for_timeout(300)
        await page.press("#dest", "Enter")

        if date:
            print(f"Received travel date: {date}")

        await page.wait_for_timeout(750)
        await page.click("#search_button")
        await page.wait_for_timeout(5000)

        current_url = page.url
        success = True
        return {
            "status": "success",
            "message": f"RedBus search results opened successfully. Current URL: {current_url}",
        }
    except (PlaywrightTimeoutError, PlaywrightError, Exception) as exc:
        return {
            "status": "error",
            "message": f"Booking execution failed: {exc}",
        }
    finally:
        if not success and browser is not None:
            await browser.close()
        if not success and playwright is not None:
            await playwright.stop()
