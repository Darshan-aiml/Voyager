import { Menu, Stars } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { executeBooking, extractTrip, planTrip } from "@/lib/api";
import { vapi } from "@/lib/vapi";
import {
  parseVapiMessageForTravelPlan,
  resolveConversationLanguage,
  toAssistantMessage,
  type ChatMessage,
  type MessageData,
  type TripMeta,
  type TripSlots,
  type TripState,
  type VoiceLanguage,
} from "@/lib/travel";

import { InputBar } from "./InputBar";
import { MessageList } from "./MessageList";

const DEFAULT_ASSISTANT_ID = "a52fba8c-6ecd-4293-9283-bd41eb58a865";

const EMPTY_TRIP: TripSlots = {
  source: null,
  destination: null,
  date: null,
  people: null,
  days: null,
  preference: null,
};

type LockedSlots = {
  source: boolean;
  destination: boolean;
  date: boolean;
  people: boolean;
  days: boolean;
  preference: boolean;
};

const EMPTY_LOCKED: LockedSlots = {
  source: false,
  destination: false,
  date: false,
  people: false,
  days: false,
  preference: false,
};

const KNOWN_CITIES = [
  "chennai",
  "mumbai",
  "bangalore",
  "bengaluru",
  "hosur",
  "coimbatore",
  "goa",
  "hyderabad",
  "madurai",
  "delhi",
  "pune",
  "kolkata",
];

const COPY: Record<
  VoiceLanguage,
  {
    greeting: string;
    source: string;
    destination: string;
    date: string;
    people: string;
    days: string;
    preference: string;
    filler: string;
    checking: string;
    partialDestination: string;
    plannerError: string;
    bookingMissing: string;
    bookingOpening: string;
    bookingPrompt: string;
  }
> = {
  en: {
    greeting: "Hey, I am Voyager. Tell me about your trip.",
    source: "Where are you traveling from?",
    destination: "Where do you want to go?",
    date: "When do you want to travel?",
    people: "How many people?",
    days: "How many days?",
    preference: "Do you prefer cheap, comfort, or luxury?",
    filler: "Got that partially... let me line it up.",
    checking: "One second... checking options.",
    partialDestination: "Got that partially... can you confirm the destination?",
    plannerError: "I could not generate a valid plan right now. Please retry with your route details.",
    bookingMissing: "I can open booking after I know the source and destination.",
    bookingOpening: "Opening the booking page now.",
    bookingPrompt: "If you want to continue, say book tickets and I will open the booking page.",
  },
  hi: {
    greeting: "Hey, main Voyager hoon. Apni trip ke baare mein batao.",
    source: "Aap kahan se travel kar rahe ho?",
    destination: "Aapko kahan jaana hai?",
    date: "Kab travel karna hai?",
    people: "Kitne log hain?",
    days: "Kitne din ka plan chahiye?",
    preference: "Cheap, comfort, ya luxury mein kya prefer karoge?",
    filler: "Thoda mil gaya... main line up kar raha hoon.",
    checking: "Ek second... options check kar raha hoon.",
    partialDestination: "Thoda samjha... destination confirm kar doge?",
    plannerError: "Valid plan generate nahi ho paaya. Route details ke saath dobara try karo.",
    bookingMissing: "Booking kholne se pehle mujhe source aur destination chahiye.",
    bookingOpening: "Booking page abhi khol raha hoon.",
    bookingPrompt: "Aage badhna hai toh bolo book tickets, main booking page khol dunga.",
  },
  ta: {
    greeting: "Hey, நான் Voyager. உங்க trip பத்தி சொல்லுங்க.",
    source: "நீங்கள் எங்கிருந்து travel பண்ணுறீங்க?",
    destination: "எங்கே போகணும்?",
    date: "எப்போது travel பண்ணணும்?",
    people: "எத்தனை பேர்?",
    days: "எத்தனை நாட்கள் plan வேண்டும்?",
    preference: "Cheap, comfort, இல்ல luxury ல என்ன prefer பண்ணுறீங்க?",
    filler: "பார்ஷியலா கிடைச்சிருக்கு... நான் set பண்ணுறேன்.",
    checking: "ஒரு second... options check பண்ணுறேன்.",
    partialDestination: "பகுதியா புரிஞ்சுச்சு... destination confirm பண்ணுவீங்களா?",
    plannerError: "Valid plan உருவாக்க முடியவில்லை. Route details உடன் மீண்டும் முயற்சி செய்யவும்.",
    bookingMissing: "Booking open பண்ண source மற்றும் destination தேவை.",
    bookingOpening: "Booking page இப்போ open பண்ணுறேன்.",
    bookingPrompt: "Continue பண்ணணும்னா book tickets nu சொல்லுங்க, booking page open பண்ணுறேன்.",
  },
};

function normalizeInput(text: string) {
  return text.toLowerCase().trim().replace(/\s+/g, " ");
}

function titleize(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function ruleExtract(text: string) {
  const normalized = normalizeInput(text);
  const result: Partial<TripSlots> = {};
  const foundCities = KNOWN_CITIES.filter((city) => normalized.includes(city));

  foundCities.forEach((city) => {
    const normalizedCity = city === "bengaluru" ? "Bangalore" : titleize(city);
    if (!result.source) {
      result.source = normalizedCity;
    } else if (!result.destination && result.source !== normalizedCity) {
      result.destination = normalizedCity;
    }
  });

  const routeMatch = normalized.match(/from ([a-z\s]+?) to ([a-z\s]+?)(?: for| on| under| with|$)/);
  if (routeMatch) {
    result.source = titleize(routeMatch[1]);
    result.destination = titleize(routeMatch[2]);
  }

  const dateMatch = normalized.match(/\b(today|tomorrow|day after tomorrow|next \w+|this \w+|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2} [a-z]+(?: \d{2,4})?)\b/);
  if (dateMatch) {
    result.date = dateMatch[1];
  }

  const peopleMatch = normalized.match(/(\d+)\s*(people|persons|travellers|travelers|adults|tickets)\b/);
  if (peopleMatch) {
    result.people = Number(peopleMatch[1]);
  } else if (/^\d+$/.test(normalized)) {
    result.people = Number(normalized);
  }

  const daysMatch = normalized.match(/(\d+)\s*(day|days|night|nights)\b/);
  if (daysMatch) {
    result.days = Number(daysMatch[1]);
  }

  if (/\b(cheap|budget|affordable|low cost)\b/.test(normalized)) {
    result.preference = "cheap";
  } else if (/\b(comfort|comfortable|balanced|sleeper)\b/.test(normalized)) {
    result.preference = "comfort";
  } else if (/\b(luxury|premium|high-end|luxurious)\b/.test(normalized)) {
    result.preference = "luxury";
  }

  return result;
}

function mergeExtraction(rule: Partial<TripSlots>, llm: Partial<TripSlots>, prev: TripSlots): TripSlots {
  return {
    source: rule.source || llm.source || prev.source,
    destination: rule.destination || llm.destination || prev.destination,
    date: rule.date || llm.date || prev.date,
    people: rule.people || llm.people || prev.people,
    days: rule.days || llm.days || prev.days,
    preference: rule.preference || llm.preference || prev.preference,
  };
}

function deriveLocked(trip: TripSlots, previous: LockedSlots): LockedSlots {
  return {
    source: previous.source || Boolean(trip.source),
    destination: previous.destination || Boolean(trip.destination),
    date: previous.date || Boolean(trip.date),
    people: previous.people || Boolean(trip.people),
    days: previous.days || Boolean(trip.days),
    preference: previous.preference || Boolean(trip.preference),
  };
}

function getNextQuestion(locked: LockedSlots, language: VoiceLanguage) {
  const copy = COPY[language];
  if (!locked.source) return copy.source;
  if (!locked.destination) return copy.destination;
  if (!locked.date) return copy.date;
  if (!locked.people) return copy.people;
  if (!locked.preference) return copy.preference;
  return null;
}

function buildPlannerQuery(trip: TripSlots, language: VoiceLanguage) {
  const tripDays = trip.days ?? 1;
  if (language === "ta") {
    return `User language Tamil or Tanglish. Respond in the same style. Plan a ${trip.preference} trip from ${trip.source} to ${trip.destination} on ${trip.date} for ${trip.people} people for ${tripDays} days.`;
  }
  if (language === "hi") {
    return `User language Hindi or Hinglish. Respond in the same style. Plan a ${trip.preference} trip from ${trip.source} to ${trip.destination} on ${trip.date} for ${trip.people} people for ${tripDays} days.`;
  }
  return `User language English. Respond in the same style. Plan a ${trip.preference} trip from ${trip.source} to ${trip.destination} on ${trip.date} for ${trip.people} people for ${tripDays} days.`;
}

function bookingIntent(text: string) {
  const normalized = normalizeInput(text);
  return /\b(yes|book|book tickets|proceed|confirm|confirm booking|go ahead|book it|ticket book)\b/.test(normalized);
}

export function ChatPanel({
  trip,
  title,
  onMetaChange,
}: {
  trip: TripState;
  title: string;
  onMetaChange: (meta: TripMeta) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(trip.initialMessages);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [tripSlots, setTripSlots] = useState<TripSlots>(EMPTY_TRIP);
  const [locked, setLocked] = useState<LockedSlots>(EMPTY_LOCKED);
  const [hasWelcomed, setHasWelcomed] = useState(false);
  const [activeLanguage, setActiveLanguage] = useState<VoiceLanguage>("en");
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const [vapiSessionActive, setVapiSessionActive] = useState(false);
  const [travelData, setTravelData] = useState<MessageData | null>(null);
  const [voicePlanProcessing, setVoicePlanProcessing] = useState(false);
  const plannerRequestedRef = useRef(false);
  const processingRef = useRef(false);
  const plannedTripRef = useRef<TripSlots>(EMPTY_TRIP);
  const onMetaChangeRef = useRef(onMetaChange);
  onMetaChangeRef.current = onMetaChange;

  const handleTravelPlan = useCallback((data: MessageData) => {
    setTravelData(data);
    setVoicePlanProcessing(false);
    if (data.source && data.destination) {
      onMetaChangeRef.current({
        title: `${data.source} to ${data.destination} Trip`,
        route: `${data.source} → ${data.destination}`,
        source: data.source,
        destination: data.destination,
      });
      plannedTripRef.current = {
        ...plannedTripRef.current,
        source: data.source,
        destination: data.destination,
      };
    }
  }, []);

  const loadingMessages = useMemo(() => ["Analyzing routes...", "Comparing prices...", "Optimizing itinerary..."], []);

  const queueAssistantMessage = useCallback((content: string, _language: VoiceLanguage) => {
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content,
      },
    ]);
  }, []);

  useEffect(() => {
    const onMessage = (msg: unknown) => {
      console.log("Vapi message:", msg);
      console.log(JSON.stringify(msg, null, 2));

      const root = msg && typeof msg === "object" ? (msg as Record<string, unknown>) : null;
      const nested = root?.message && typeof root.message === "object" ? (root.message as Record<string, unknown>) : root;
      const toolCalls = (nested?.toolCalls as Array<Record<string, unknown>> | undefined) ??
        (root?.toolCalls as Array<Record<string, unknown>> | undefined) ??
        [];
      if (toolCalls.length > 0) {
        console.log("VAPI TOOL:", toolCalls);

        for (const call of toolCalls) {
          const toolName = String(call?.name ?? "").toLowerCase();
          let result: unknown = call?.result;
          if (typeof result === "string") {
            try {
              result = JSON.parse(result);
            } catch {
              result = null;
            }
          }

          if (toolName === "plan_trip") {
            const payload = result && typeof result === "object" ? (result as Record<string, unknown>) : null;
            const status = typeof payload?.status === "string" ? payload.status : null;
            if (status === "complete") {
              const { messageData } = parseVapiMessageForTravelPlan({
                type: "tool-calls-result",
                name: "plan_trip",
                result,
              });
              if (messageData) {
                handleTravelPlan(messageData);
                const best = messageData.best_option;
                queueAssistantMessage(
                  `The best option is a ${best.mode} costing ${new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(best.price)}. Two other options are also available. Would you like me to book this?`,
                  activeLanguage,
                );
              }
            }
          }

          if (toolName === "execute_booking") {
            const resultObj = result && typeof result === "object" ? (result as Record<string, unknown>) : {};
            const url = typeof resultObj.booking_url === "string" ? resultObj.booking_url : "";

            if (url) {
              window.open(url, "_blank", "noopener,noreferrer");
            } else {
              console.error("No booking URL returned");
            }

            queueAssistantMessage("I'm opening the booking page for you now.", activeLanguage);
          }
        }
      }

      const { messageData, pendingTool } = parseVapiMessageForTravelPlan(msg);
      if (messageData) {
        handleTravelPlan(messageData);
      } else if (pendingTool) {
        setVoicePlanProcessing(true);
      }
    };
    const onCallStart = () => {
      console.log("Voice session started");
      setVapiSessionActive(true);
    };
    const onCallEnd = () => {
      console.log("Voice session ended");
      setVapiSessionActive(false);
      setVoicePlanProcessing(false);
    };

    vapi.on("message", onMessage);
    vapi.on("call-start", onCallStart);
    vapi.on("call-end", onCallEnd);

    return () => {
      vapi.removeListener("message", onMessage);
      vapi.removeListener("call-start", onCallStart);
      vapi.removeListener("call-end", onCallEnd);
    };
  }, [activeLanguage, handleTravelPlan, queueAssistantMessage, travelData]);

  const startAgent = useCallback(async () => {
    setError(null);
    const key = import.meta.env.VITE_VAPI_PUBLIC_KEY ?? "";
    if (!key.trim()) {
      setError("Add VITE_VAPI_PUBLIC_KEY to your environment to use voice.");
      return;
    }
    const assistantId = import.meta.env.VITE_VAPI_ASSISTANT_ID ?? DEFAULT_ASSISTANT_ID;
    try {
      await vapi.start(assistantId);
    } catch (caught) {
      const detail = caught instanceof Error ? caught.message : "Unable to start voice session.";
      setError(import.meta.env.DEV ? detail : "Unable to start voice session.");
      console.error(caught);
    }
  }, []);

  const stopAgent = useCallback(async () => {
    try {
      await vapi.stop();
    } catch (caught) {
      console.error(caught);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      setLoadingStep(0);
      return;
    }

    const interval = window.setInterval(() => {
      setLoadingStep((current) => (current + 1) % loadingMessages.length);
    }, 1200);

    return () => window.clearInterval(interval);
  }, [isLoading, loadingMessages.length]);

  useEffect(() => {
    if (hasWelcomed) {
      return;
    }

    const greetingLanguage: VoiceLanguage = "en";
    const greeting = `${COPY[greetingLanguage].greeting} ${COPY[greetingLanguage].source}`;
    setHasWelcomed(true);
    setLastQuestion(COPY[greetingLanguage].source);
    setMessages([
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: greeting,
      },
    ]);
  }, [hasWelcomed]);

  useEffect(() => {
    if (!hasWelcomed || processingRef.current || isLoading) {
      return;
    }

    const question = getNextQuestion(locked, activeLanguage);
    if (question && question !== lastQuestion) {
      setLastQuestion(question);
      queueAssistantMessage(question, activeLanguage);
      return;
    }

    if (!question && !plannerRequestedRef.current) {
      plannerRequestedRef.current = true;
      void callPlanner(tripSlots, activeLanguage);
    }
  }, [activeLanguage, hasWelcomed, isLoading, lastQuestion, locked, queueAssistantMessage, tripSlots]);

  const callPlanner = useCallback(
    async (currentTrip: TripSlots, language: VoiceLanguage) => {
      setIsLoading(true);
      setError(null);
      plannedTripRef.current = currentTrip;
      queueAssistantMessage(COPY[language].checking, language);

      try {
        const plannerQuery = buildPlannerQuery(currentTrip, language);
        const firstPayload = await planTrip(plannerQuery);
        let assistantMessage = toAssistantMessage(firstPayload);

        if (!assistantMessage) {
          await new Promise((resolve) => window.setTimeout(resolve, 700));
          const retryPayload = await planTrip(plannerQuery);
          assistantMessage = toAssistantMessage(retryPayload);
        }

        if (!assistantMessage) {
          throw new Error("Invalid planner response after retry");
        }

        setMessages((current) => [...current, assistantMessage]);

        if (assistantMessage.data?.source && assistantMessage.data?.destination) {
          onMetaChange({
            title: `${assistantMessage.data.source} to ${assistantMessage.data.destination} Trip`,
            route: `${assistantMessage.data.source} → ${assistantMessage.data.destination}`,
            source: assistantMessage.data.source,
            destination: assistantMessage.data.destination,
          });
        }

        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: COPY[language].bookingPrompt,
          },
        ]);
      } catch (caughtError) {
        const detail = caughtError instanceof Error ? caughtError.message : "Unknown API error";
        setError(import.meta.env.DEV ? `Unable to fetch travel plan: ${detail}` : "Unable to fetch travel plan.");
        queueAssistantMessage(COPY[language].plannerError, language);
        plannerRequestedRef.current = false;
      } finally {
        setIsLoading(false);
      }
    },
    [onMetaChange, queueAssistantMessage],
  );

  async function handleBookingIntent(language: VoiceLanguage) {
    const currentPlan = plannedTripRef.current;
    if (!currentPlan.source || !currentPlan.destination) {
      queueAssistantMessage(COPY[language].bookingMissing, language);
      return;
    }

    const bookingUrl = await executeBooking({
      source: currentPlan.source,
      destination: currentPlan.destination,
    }).catch(() => "");

    if (bookingUrl) {
      window.open(bookingUrl, "_blank", "noopener,noreferrer");
      queueAssistantMessage(COPY[language].bookingOpening, language);
    }
  }

  async function handleUserMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || processingRef.current) {
      return;
    }

    processingRef.current = true;
    const normalized = normalizeInput(trimmed);
    const language = resolveConversationLanguage(trimmed, activeLanguage);
    setActiveLanguage(language);
    setError(null);
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
      },
    ]);

    try {
      if (bookingIntent(normalized)) {
        await handleBookingIntent(language);
        return;
      }

      const rules = ruleExtract(normalized);
      let llm: Partial<TripSlots> = {};
      const ruleCoverage = Object.values(rules).filter(Boolean).length;

      if (ruleCoverage < 2 || !rules.destination || !rules.date || !rules.preference) {
        llm = await extractTrip(trimmed);
      }

      const merged = mergeExtraction(rules, llm, tripSlots);
      const nextLocked = deriveLocked(merged, locked);

      plannerRequestedRef.current = false;
      setTripSlots(merged);
      setLocked(nextLocked);

      const changed = (Object.keys(merged) as Array<keyof TripSlots>).some((key) => merged[key] !== tripSlots[key]);
      if (!changed) {
        queueAssistantMessage(COPY[language].partialDestination, language);
      } else if (ruleCoverage < 2 && Object.values(llm).filter(Boolean).length === 0) {
        queueAssistantMessage(COPY[language].filler, language);
      }
    } catch (caughtError) {
      console.error("Message handling error:", caughtError);
      queueAssistantMessage(COPY[language].partialDestination, language);
    } finally {
      processingRef.current = false;
    }
  }

  async function handleSubmit() {
    const trimmed = query.trim();
    if (!trimmed || isLoading) {
      return;
    }

    await handleUserMessage(trimmed);
    setQuery("");
  }

  return (
    <main className="relative flex min-w-0 flex-1 flex-col px-4 py-4 md:px-6 md:py-6 xl:px-8">
      <div className="liquid-glass relative flex h-full min-h-[calc(100vh-2rem)] flex-col overflow-hidden rounded-[36px] p-5 md:p-7">
        <div className="mb-6 flex items-start justify-between gap-4 border-b border-white/8 pb-5">
          <div className="flex items-start gap-3">
            <button className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/6 text-white/78 lg:hidden">
              <Menu className="h-4.5 w-4.5" />
            </button>
            <div>
              <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.3em] text-white/42">
                <Stars className="h-3.5 w-3.5" />
                Mindful route planning
              </div>
              <h1 className="font-display text-4xl italic tracking-tight text-white md:text-5xl">{title}</h1>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 md:flex-row md:items-center">
            <div className="flex rounded-full border border-white/10 bg-white/5 px-3 py-2 text-[10px] uppercase tracking-[0.24em] text-white/50 md:px-4 md:text-[11px]">
              {vapiSessionActive ? "Voice session live" : "Vapi voice"}
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="default" size="default" onClick={() => void startAgent()}>
                Start Voice
              </Button>
              <Button type="button" variant="ghost" size="default" onClick={() => void stopAgent()}>
                Stop Voice
              </Button>
            </div>
          </div>
        </div>

        <MessageList
          messages={messages}
          isLoading={isLoading}
          error={error}
          loadingMessage={loadingMessages[loadingStep]}
          voiceTravelData={travelData}
          voicePlanProcessing={voicePlanProcessing}
        />
        <InputBar value={query} onChange={setQuery} onSubmit={handleSubmit} isLoading={isLoading} />
      </div>
    </main>
  );
}
