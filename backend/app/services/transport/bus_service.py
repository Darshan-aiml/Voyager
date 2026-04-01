from app.models.response import TravelOption
from app.utils.helpers import slugify_city


class BusService:
    async def generate_option(
        self,
        source: str,
        destination: str,
        inferred_price: float = 0.0,
        inferred_duration_minutes: int = 0,
    ) -> TravelOption:
        source_slug = slugify_city(source)
        destination_slug = slugify_city(destination)
        booking_url = f"https://www.redbus.in/bus-tickets/{source_slug}-to-{destination_slug}"

        return TravelOption(
            mode="bus",
            route=f"{source} -> {destination}",
            price=inferred_price,
            duration=f"{inferred_duration_minutes // 60}h" if inferred_duration_minutes else "N/A",
            duration_minutes=inferred_duration_minutes,
            reliability=0.65,
            availability="Likely",
            reason="Always available backup",
            booking_url=booking_url,
        )
