from __future__ import annotations

from dataclasses import dataclass

from app.models.response import BrowserAutomationStub


@dataclass
class StubContext:
    booking_url: str
    provider_label: str
    next_action: str


class BasePlaywrightAutomationStub:
    provider_label = ""
    runner_name = ""
    script_path = ""
    browser = "chromium"
    launch_mode = "headless-disabled-for-manual-review"
    supported_actions: tuple[str, ...] = ()
    checkpoint_labels: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def build_stub(self, *, booking_url: str, next_action: str) -> BrowserAutomationStub:
        context = StubContext(
            booking_url=booking_url,
            provider_label=self.provider_label,
            next_action=next_action,
        )
        return BrowserAutomationStub(
            provider=self.provider_label,
            runner_name=self.runner_name,
            script_path=self.script_path,
            browser=self.browser,
            launch_mode=self.launch_mode,
            current_target_url=booking_url,
            supported_actions=list(self.supported_actions),
            checkpoint_labels=list(self.checkpoint_labels),
            next_stub_instruction=self.next_instruction(context),
            notes=list(self.notes),
        )

    def next_instruction(self, context: StubContext) -> str:
        return f"Open {context.booking_url} with Playwright and prepare the {context.next_action} step."


class IrctcPlaywrightStub(BasePlaywrightAutomationStub):
    provider_label = "IRCTC"
    runner_name = "irctc_playwright_stub"
    script_path = "backend/app/services/booking/stubs/irctc_playwright_stub.py"
    supported_actions = (
        "search_and_select",
        "fill_traveller_details",
        "verify_user",
        "payment",
    )
    checkpoint_labels = (
        "Login or account verification",
        "IRCTC captcha / OTP",
        "Payment handoff",
    )
    notes = (
        "Use Playwright selectors against the IRCTC search form and traveller form.",
        "Do not submit payment automatically; stop after the payment page is ready.",
    )

    def next_instruction(self, context: StubContext) -> str:
        if context.next_action == "search_and_select":
            return "Launch IRCTC search, populate source, destination, and journey date, then capture candidate trains."
        if context.next_action == "fill_traveller_details":
            return "Navigate to the chosen IRCTC itinerary and stub-fill passenger, berth, and contact details."
        if context.next_action == "verify_user":
            return "Pause the Playwright flow for IRCTC login, captcha, or OTP resolution."
        if context.next_action == "payment":
            return "Advance to the IRCTC payment gateway and stop before confirming payment."
        return super().next_instruction(context)


class FlightCheckoutPlaywrightStub(BasePlaywrightAutomationStub):
    provider_label = "Google Flights / airline checkout"
    runner_name = "flight_checkout_playwright_stub"
    script_path = "backend/app/services/booking/stubs/flight_checkout_playwright_stub.py"
    supported_actions = (
        "search_and_select",
        "fill_traveller_details",
        "verify_user",
        "payment",
    )
    checkpoint_labels = (
        "Fare family confirmation",
        "Airline account verification or OTP",
        "Payment handoff",
    )
    notes = (
        "Use Google Flights or airline checkout pages to identify a matching itinerary.",
        "Persist fare metadata before handoff because airline checkout URLs can expire quickly.",
    )

    def next_instruction(self, context: StubContext) -> str:
        if context.next_action == "search_and_select":
            return "Open the flight search page, reconcile itinerary details, and stub-select the best fare family."
        if context.next_action == "fill_traveller_details":
            return "Stub-fill traveller names, contact info, and cabin preferences on the airline checkout form."
        if context.next_action == "verify_user":
            return "Pause for airline account login, OTP, or document verification."
        if context.next_action == "payment":
            return "Drive the airline checkout up to the final payment review screen and stop there."
        return super().next_instruction(context)


class RedBusPlaywrightStub(BasePlaywrightAutomationStub):
    provider_label = "RedBus"
    runner_name = "redbus_playwright_stub"
    script_path = "backend/app/services/booking/stubs/redbus_playwright_stub.py"
    supported_actions = (
        "search_and_select",
        "fill_traveller_details",
        "payment",
    )
    checkpoint_labels = (
        "Seat and boarding point confirmation",
        "RedBus account verification / OTP",
        "Payment handoff",
    )
    notes = (
        "Target the bus listing, seat map, and passenger forms with Playwright page objects.",
        "Pause before payment or wallet confirmation.",
    )

    def next_instruction(self, context: StubContext) -> str:
        if context.next_action == "search_and_select":
            return "Open RedBus results, choose operator, boarding point, and seat map selections."
        if context.next_action == "fill_traveller_details":
            return "Stub-fill passenger names, age, gender, and contact details in the RedBus checkout form."
        if context.next_action == "verify_user":
            return "Pause for RedBus OTP or sign-in verification before payment."
        if context.next_action == "payment":
            return "Advance through RedBus checkout and stop before final payment confirmation."
        return super().next_instruction(context)


def get_playwright_stub(mode: str) -> BasePlaywrightAutomationStub:
    stubs = {
        "train": IrctcPlaywrightStub(),
        "flight": FlightCheckoutPlaywrightStub(),
        "bus": RedBusPlaywrightStub(),
    }
    return stubs[mode]
