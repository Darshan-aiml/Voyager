from __future__ import annotations

from app.models.request import TravelAdvisorRequest
from app.models.response import (
    AdvisorTalkingPoint,
    BookingWorkflowResponse,
    PlanTripResponse,
    TravelAdvisorResponse,
)
from app.services.booking.automation_service import BookingAutomationService
from app.services.planner.plan_service import PlanService


class AdvisorService:
    def __init__(
        self,
        plan_service: PlanService,
        booking_automation_service: BookingAutomationService,
    ) -> None:
        self.plan_service = plan_service
        self.booking_automation_service = booking_automation_service

    async def respond(self, payload: TravelAdvisorRequest) -> TravelAdvisorResponse:
        if payload.intent in {"plan_trip", "explain_fallback"}:
            return await self._build_plan_response(payload)
        if payload.intent in {"booking_status", "booking_next_step"}:
            return await self._build_booking_response(payload)
        return self._build_general_guidance(payload)

    async def _build_plan_response(self, payload: TravelAdvisorRequest) -> TravelAdvisorResponse:
        if not all([payload.source, payload.destination, payload.date, payload.budget]):
            return self._missing_fields_response(
                payload,
                missing_fields=["source", "destination", "date", "budget"],
                recommended_tools=["ask_follow_up_question"],
            )

        plan = await self.plan_service.plan_trip(
            source=payload.source,
            destination=payload.destination,
            travel_date=payload.date,
            budget=payload.budget,
        )
        answer_brief = self._build_plan_brief(plan)
        talking_points = [
            AdvisorTalkingPoint(
                label="Recommendation",
                content=(
                    f"Lead with the {plan.best_option.mode} option because it best fits the planner scoring logic."
                ),
            ),
            AdvisorTalkingPoint(
                label="Why it fits",
                content=(
                    f"It costs {plan.best_option.price}, takes about {plan.best_option.duration}, and has reliability {plan.best_option.reliability}."
                ),
            ),
            AdvisorTalkingPoint(
                label="Fallback",
                content=(
                    f"If the user dislikes the primary choice or availability changes, offer the fallback {plan.fallback_option.mode} option on {plan.fallback_option.route}."
                ),
            ),
        ]

        if payload.intent == "explain_fallback":
            answer_brief = (
                f"The fallback is {plan.fallback_option.mode} on {plan.fallback_option.route}. "
                f"It exists so the system can still give the user a workable option even if the preferred route is rejected or changes."
            )
            talking_points.append(
                AdvisorTalkingPoint(
                    label="Fallback reasoning",
                    content=plan.fallback_option.reason or "Fallback was selected as the safest backup path.",
                )
            )

        return TravelAdvisorResponse(
            intent=payload.intent,
            user_message=payload.user_message,
            answer_brief=answer_brief,
            llm_system_guidance=(
                "Answer naturally and confidently. Use the structured planner result as ground truth, "
                "explain tradeoffs in plain language, and avoid sounding like a rule engine reading JSON."
            ),
            talking_points=talking_points,
            suggested_follow_ups=[
                "Would you like the fastest option instead of the most balanced one?",
                "Should I start the booking flow for this option?",
            ],
            recommended_tools=["plan_trip", "automate_booking"],
            structured_context={
                "best_option": plan.best_option.model_dump(),
                "fallback_option": plan.fallback_option.model_dump(),
            },
        )

    async def _build_booking_response(self, payload: TravelAdvisorRequest) -> TravelAdvisorResponse:
        if not payload.workflow_id:
            return self._missing_fields_response(
                payload,
                missing_fields=["workflow_id"],
                recommended_tools=["get_booking_workflow"],
            )

        workflow = await self.booking_automation_service.get_workflow(payload.workflow_id)
        answer_brief = self._build_booking_brief(workflow)
        next_step = next((step for step in workflow.steps if step.id == workflow.next_action), None)
        next_step_text = next_step.details if next_step else "No further step is pending."

        return TravelAdvisorResponse(
            intent=payload.intent,
            user_message=payload.user_message,
            answer_brief=answer_brief,
            llm_system_guidance=(
                "Speak like a helpful travel concierge. Summarize workflow progress, tell the user what is already automated, "
                "and clearly call out any human checkpoint such as OTP or payment."
            ),
            talking_points=[
                AdvisorTalkingPoint(
                    label="Workflow status",
                    content=f"The booking workflow is currently {workflow.status} for {workflow.provider}.",
                ),
                AdvisorTalkingPoint(
                    label="Next step",
                    content=f"The next action is {workflow.next_action}. {next_step_text}",
                ),
                AdvisorTalkingPoint(
                    label="Automation capability",
                    content=workflow.browser_automation.next_stub_instruction,
                ),
            ],
            suggested_follow_ups=[
                "Do you want me to continue the browser automation now?",
                "Are you ready for OTP or payment confirmation if the site asks for it?",
            ],
            recommended_tools=["get_booking_workflow", "execute_booking_workflow"],
            structured_context={
                "workflow": workflow.model_dump(),
            },
        )

    def _build_general_guidance(self, payload: TravelAdvisorRequest) -> TravelAdvisorResponse:
        return TravelAdvisorResponse(
            intent=payload.intent,
            user_message=payload.user_message,
            answer_brief=(
                "Use the planner for concrete itinerary decisions and the booking workflow tools for execution. "
                "If the user is vague, ask one sharp follow-up, then ground the answer in tool results."
            ),
            llm_system_guidance=(
                "Do not answer with generic travel platitudes. Ask focused clarifying questions when key trip facts are missing, "
                "and once enough details are available, call the backend tools before making strong recommendations."
            ),
            talking_points=[
                AdvisorTalkingPoint(
                    label="Clarify",
                    content="If source, destination, date, or budget are missing, gather them first.",
                ),
                AdvisorTalkingPoint(
                    label="Grounding",
                    content="Use backend plan and booking tools for decisions that affect travel recommendations or booking actions.",
                ),
            ],
            suggested_follow_ups=[
                "What city are you leaving from?",
                "What date do you want to travel?",
                "Is your priority price, speed, or comfort?",
            ],
            recommended_tools=["plan_trip", "travel_advisor"],
            structured_context={},
        )

    def _missing_fields_response(
        self,
        payload: TravelAdvisorRequest,
        *,
        missing_fields: list[str],
        recommended_tools: list[str],
    ) -> TravelAdvisorResponse:
        return TravelAdvisorResponse(
            intent=payload.intent,
            user_message=payload.user_message,
            answer_brief=(
                f"The assistant should ask for the missing fields before answering fully: {', '.join(missing_fields)}."
            ),
            llm_system_guidance=(
                "Ask only for the missing information. Keep it natural, concise, and context-aware."
            ),
            talking_points=[
                AdvisorTalkingPoint(
                    label="Missing information",
                    content=", ".join(missing_fields),
                )
            ],
            suggested_follow_ups=[
                f"Please share your {missing_fields[0]}.",
            ],
            recommended_tools=recommended_tools,
            structured_context={"missing_fields": missing_fields},
        )

    def _build_plan_brief(self, plan: PlanTripResponse) -> str:
        return (
            f"The best current option is {plan.best_option.mode} via {plan.best_option.route}, "
            f"with a fallback of {plan.fallback_option.mode} if the user wants a backup."
        )

    def _build_booking_brief(self, workflow: BookingWorkflowResponse) -> str:
        return (
            f"The booking is in {workflow.status} state with {workflow.provider}. "
            f"The next step is {workflow.next_action}, and the assistant should explain whether human action is needed."
        )
