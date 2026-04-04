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


async def _recommend_and_highlight_bus(page) -> dict[str, str] | None:
    return await page.evaluate(
        """
        () => {
            const cleanText = (value) => (value || "").replace(/\\s+/g, " ").trim();
            const firstText = (root, selectors) => {
                for (const selector of selectors) {
                    const node = root.querySelector(selector);
                    const text = cleanText(node?.textContent);
                    if (text) return text;
                }
                return "";
            };
            const parsePrice = (text) => {
                const digits = (text || "").replace(/[^0-9]/g, "");
                return digits ? Number.parseInt(digits, 10) : 999999;
            };
            const parseRating = (text) => {
                const match = (text || "").match(/\\d+(?:\\.\\d+)?/);
                return match ? Number.parseFloat(match[0]) : 0;
            };
            const scoreBus = (price, rating, busType) => {
                let score = rating * 2;
                score += Math.max(0, 2000 - price) / 500;
                const normalizedType = (busType || "").toLowerCase();
                if (normalizedType.includes("sleeper")) score += 2;
                if (normalizedType.includes("ac")) score += 1;
                return score;
            };

            const candidateSelectors = [
                ".bus-items > div",
                ".tupleWrapper",
                "li.row-sec.clearfix",
                "[class*='travels']"
            ];
            const cards = [];
            for (const selector of candidateSelectors) {
                for (const element of document.querySelectorAll(selector)) {
                    if (!cards.includes(element)) cards.push(element);
                }
            }

            const buses = cards
                .map((card) => {
                    const name = firstText(card, [
                        ".travels",
                        "[class*='travels']",
                        "[class*='operator']",
                        "h6",
                        "h4"
                    ]);
                    const priceText = firstText(card, [
                        ".fare",
                        ".seat-fare",
                        "[class*='fare']",
                        "[class*='price']"
                    ]);
                    const ratingText = firstText(card, [
                        ".rating-sec",
                        "[class*='rating']"
                    ]);
                    const busType = firstText(card, [
                        ".bus-type",
                        "[class*='bus-type']",
                        "[class*='busType']"
                    ]);

                    if (!name || !priceText) return null;

                    const price = parsePrice(priceText);
                    const rating = parseRating(ratingText);
                    const score = scoreBus(price, rating, busType);
                    return { card, name, priceText, ratingText, busType, score };
                })
                .filter(Boolean);

            if (!buses.length) return null;

            buses.sort((a, b) => b.score - a.score);
            const best = buses[0];
            best.card.scrollIntoView({ behavior: "smooth", block: "center" });
            best.card.style.border = "4px solid #00C853";
            best.card.style.boxShadow = "0 0 20px rgba(0, 200, 83, 0.8)";
            best.card.style.borderRadius = "10px";
            best.card.style.transform = "scale(1.02)";
            best.card.style.background = "rgba(0, 200, 83, 0.05)";

            if (!best.card.querySelector("[data-voyager-recommended='true']")) {
                const badge = document.createElement("div");
                badge.innerText = "Voyager Recommended";
                badge.dataset.voyagerRecommended = "true";
                badge.style.background = "#00C853";
                badge.style.color = "white";
                badge.style.padding = "6px 10px";
                badge.style.fontSize = "12px";
                badge.style.borderRadius = "6px";
                badge.style.marginBottom = "8px";
                badge.style.fontWeight = "bold";
                badge.style.display = "inline-block";
                best.card.prepend(badge);
            }

            return {
                name: best.name,
                price: best.priceText,
                rating: best.ratingText || "N/A",
                type: best.busType || "Unknown",
                reason: "Best balance of price, comfort, and rating"
            };
        }
        """
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
        source_slug = slugify_city(source)
        destination_slug = slugify_city(destination)
        results_url = f"https://www.redbus.in/bus-tickets/{source_slug}-to-{destination_slug}"

        print("Opening results page...")
        await page.goto(results_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        if date:
            print(f"Received travel date: {date}")

        await page.wait_for_selector(
            ".bus-items, [class*='bus-items'], [class*='travels'], [class*='search-page']",
            state="visible",
        )
        print("Current URL:", page.url)

        recommended_bus = await _recommend_and_highlight_bus(page)

        current_url = page.url
        success = True
        message = f"RedBus search results opened successfully. Current URL: {current_url}"
        if recommended_bus:
            message = (
                f"{message} Recommended bus: {recommended_bus['name']} "
                f"({recommended_bus['type']}, {recommended_bus['price']}, rating {recommended_bus['rating']})."
            )
        return {
            "status": "success",
            "message": message,
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
