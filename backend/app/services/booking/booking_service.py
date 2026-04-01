from datetime import date

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
