from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

from app.core.config import Settings
from app.models.travel_response import TravelPlanApiResponse, TravelPlanData
from app.services.data.mock_transport_data import get_transport_grounding
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.normalizer import normalize_plan_payload
from app.services.llm.parser import LLMOutputParseError, parse_json_response
from app.services.llm.prompt_builder import build_planning_prompt, build_retry_prompt
from app.services.planner.scoring import calculate_score

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TravelPlannerResult:
    summary: str
    data: TravelPlanData


class TravelPlanner:
    def __init__(self, settings: Settings, gemini_client: GeminiClient | None = None) -> None:
        self.settings = settings
        self.gemini_client = gemini_client or GeminiClient(settings)

    async def generate_travel_plan(self, query: str) -> TravelPlanApiResponse:
        result = await self._generate_plan_result(query)
        return TravelPlanApiResponse(text_response=result.summary, response=result.summary, data=result.data)

    async def _generate_plan_result(self, query: str) -> TravelPlannerResult:
        prompt = build_planning_prompt(query)
        last_error = "Unknown planner failure"
        last_raw_response = ""
        started_at = perf_counter()
        logger.info("Travel planner received query=%s", query)

        for attempt in range(2):
            raw_response = ""
            try:
                raw_response = await self.gemini_client.generate_response(prompt)
                logger.info("Travel planner raw_llm_output attempt=%s output=%s", attempt + 1, raw_response)
                structured_payload = parse_json_response(raw_response)
                if not self._is_valid_llm_payload(structured_payload):
                    raise ValueError("LLM payload missing required fields: best_option, alternatives, itinerary")
                finalized_payload = self._post_process_payload(structured_payload)
                structured_data = TravelPlanData.model_validate(finalized_payload)
                summary = self._build_summary(structured_data)
                elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
                logger.info(
                    "Travel planner final_response query=%s duration_ms=%s response=%s",
                    query,
                    elapsed_ms,
                    structured_data.model_dump(),
                )
                return TravelPlannerResult(summary=summary, data=structured_data)
            except (LLMOutputParseError, ValueError) as exc:
                last_error = str(exc)
                last_raw_response = raw_response
                logger.warning("Planner output validation failed on attempt %s: %s", attempt + 1, exc)
                prompt = build_retry_prompt(query, last_raw_response, last_error)
            except Exception as exc:
                last_error = str(exc)
                last_raw_response = raw_response
                logger.warning("Planner request failed on attempt %s: %s", attempt + 1, exc)
                prompt = build_retry_prompt(query, last_raw_response, last_error)

        raise RuntimeError(f"Planner failed after retries: {last_error}")

    @staticmethod
    def _is_valid_llm_payload(payload: dict) -> bool:
        best_option = payload.get("best_option")
        alternatives = payload.get("alternatives")
        itinerary = payload.get("itinerary")

        if not payload or not isinstance(payload, dict):
            return False
        if not best_option or not isinstance(best_option, dict):
            return False
        if not all(best_option.get(field) for field in ("mode", "price", "duration", "reason")):
            return False
        if not alternatives or not isinstance(alternatives, list):
            return False
        if not itinerary or not isinstance(itinerary, list):
            return False
        return True

    def _post_process_payload(self, payload: dict) -> dict:
        normalized = normalize_plan_payload(
            payload,
            max_itinerary_days=self.settings.max_itinerary_days,
        )
        source = normalized["source"]
        destination = normalized["destination"]
        travel_style = normalized["preferences"]["travel_style"]
        budget = normalized["preferences"]["budget"]
        options = [normalized["best_option"], *normalized["alternatives"]]
        grounded_options = [
            self._ground_and_score_option(source, destination, option, travel_style=travel_style, budget=budget)
            for option in options
        ]
        ranked_options = sorted(grounded_options, key=lambda item: item["score"], reverse=True)
        if len(ranked_options) < 3:
            raise ValueError("Planner requires at least 3 transport options (1 best + 2 alternatives).")

        best_option = ranked_options[0]
        alternatives = ranked_options[1:3]
        normalized["best_option"] = self._serialize_option(best_option)
        normalized["alternatives"] = [self._serialize_option(option) for option in alternatives]
        normalized["insight"] = self._append_hybrid_insight(normalized["insight"], best_option)
        return normalized

    def _ground_and_score_option(
        self,
        source: str,
        destination: str,
        option: dict,
        *,
        travel_style: str,
        budget: float,
    ) -> dict:
        grounded = dict(option)
        bounds = get_transport_grounding(source, destination, grounded["mode"])
        grounded.update(bounds)
        grounded["price"] = max(grounded["price"], float(bounds["price_min"]))
        grounded["price"] = min(grounded["price"], float(bounds["price_max"]))
        grounded["duration_minutes"] = max(grounded["duration_minutes"], int(bounds["duration_min"]))
        grounded["duration_minutes"] = min(grounded["duration_minutes"], int(bounds["duration_max"]))
        grounded["duration"] = self._format_duration(grounded["duration_minutes"])
        if grounded.get("rating", 0.0) <= 0:
            grounded["rating"] = float(bounds.get("rating", 4.0))
        grounded["score"] = calculate_score(grounded, travel_style=travel_style, budget=budget)
        return grounded

    def _serialize_option(self, option: dict) -> dict:
        return {
            "mode": option["mode"],
            "price": round(float(option["price"]), 2),
            "duration": option["duration"],
            "reason": f"{option['reason']} Deterministic score: {option['score']:.2f}.",
        }

    def _append_hybrid_insight(self, insight: str, best_option: dict) -> str:
        return (
            f"{insight} Final selection validated with deterministic scoring and route grounding. "
            f"Chosen mode: {best_option['mode']} with score {best_option['score']:.2f}."
        )

    def _build_summary(self, plan: TravelPlanData) -> str:
        return (
            f"The best option is a {plan.best_option.mode} for {self._format_price(plan.best_option.price)} "
            f"because {plan.best_option.reason}. I also created a {plan.preferences.days}-day itinerary "
            f"for your trip to {plan.destination}."
        )

    @staticmethod
    def _format_duration(total_minutes: int) -> str:
        hours, minutes = divmod(int(total_minutes), 60)
        if minutes:
            return f"{hours}h {minutes}m"
        return f"{hours}h"

    @staticmethod
    def _format_price(price: float) -> str:
        return f"Rs {price:,.0f}"
