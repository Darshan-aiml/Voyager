from collections.abc import Sequence

from app.models.response import TravelOption


def generate_fallback(all_options: Sequence[TravelOption], bus_option: TravelOption) -> TravelOption:
    direct_non_bus = [opt for opt in all_options if opt.mode != "bus" and "->" in opt.route]
    if direct_non_bus:
        selected = min(direct_non_bus, key=lambda item: item.price)
        return selected.model_copy(update={"reason": "Fallback direct route if primary fails"})

    if not bus_option.reason:
        return bus_option.model_copy(update={"reason": "Always available backup"})
    return bus_option.model_copy()
