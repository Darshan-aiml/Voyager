from __future__ import annotations

from datetime import datetime
from textwrap import dedent

SYSTEM_PROMPT = dedent(
    """
    You are an intelligent travel planning assistant.

    You must:
    - Understand user intent
    - Consider budget, time, comfort, passengers
    - Compare exactly 3 realistic bus choices for the requested route
    - Choose the optimal bus option based on tradeoffs
    - Generate a realistic itinerary
    - Provide reasoning (insight)

    Return ONLY valid JSON in this format:

    {
      "source": "",
      "destination": "",
      "preferences": {
        "budget": number,
        "travel_style": "budget|comfort|fast",
        "people": number,
        "days": number
      },
      "best_option": {
        "mode": "",
        "price": number,
        "duration": "",
        "reason": ""
      },
      "alternatives": [
        {
          "mode": "",
          "price": number,
          "duration": "",
          "reason": ""
        }
      ],
      "itinerary": [
        {
          "day": number,
          "plan": ""
        }
      ],
      "insight": ""
    }

    Do NOT hallucinate unrealistic values.
    Use reasonable approximations when exact data is unavailable.
    Use numeric prices only.
    Keep durations human-readable, such as "8h 30m".
    Prefer internally consistent estimates over false precision.
    Respond in the SAME language as the user's input.
    If the user speaks Tamil, respond in Tamil.
    If the user speaks Hindi, respond in Hindi.
    If the user speaks English, respond in English.
    If the user mixes languages, keep the free-text fields naturally mixed, such as Hinglish or Tanglish.
    Keep all free-text string fields like reason, itinerary plan, and insight in that same language style.
    Do not wrap the JSON in markdown.
    """
).strip()


def build_planning_prompt(query: str) -> str:
    today = datetime.now().date().isoformat()
    return dedent(
        f"""
        Today's date: {today}

        User travel request:
        {query}

        Return STRICT JSON only with all fields filled.
        Required fields:
        - source and destination must be non-empty strings
        - best_option (must include mode, price, duration, reason)
        - alternatives (array, exactly 2 items)
        - all 3 options must be bus options for the same route
        - itinerary (day-wise, non-empty plan text for every day)
        - insight (string)
        If any field missing -> regenerate.
        DO NOT return partial output.

        Produce one balanced recommendation, 1 to 3 alternatives, a day-by-day itinerary, and a concise insight.
        If the user does not explicitly state a preference, infer the most likely intent from the wording.
        Keep the response grounded and realistic.
        """
    ).strip()


def build_retry_prompt(query: str, invalid_response: str, error_message: str) -> str:
    return dedent(
        f"""
        The previous response could not be parsed or validated.

        Original user request:
        {query}

        Validation error:
        {error_message}

        Previous response:
        {invalid_response}

        Return STRICT JSON only with all fields filled.
        Required fields:
        - source and destination must be non-empty strings
        - best_option (must include mode, price, duration, reason)
        - alternatives (array, exactly 2 items)
        - all 3 options must be bus options for the same route
        - itinerary (day-wise, non-empty plan text for every day)
        - insight (string)
        If any field missing -> regenerate.
        DO NOT return partial output.
        Return corrected JSON only, with the required schema and no extra text.
        """
    ).strip()
