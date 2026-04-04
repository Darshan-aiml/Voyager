export type PlannerRecommendation = {
  mode: string;
  price: number;
  duration: string;
  reason: string;
};

export type PlannerItineraryDay = {
  day: number;
  plan: string;
};

export type PlannerData = {
  source: string;
  destination: string;
  best_option: PlannerRecommendation;
  alternatives: PlannerRecommendation[];
  itinerary: PlannerItineraryDay[];
  insight: string;
  booking_url: string;
};

export type PlannerApiResponse = {
  status: "incomplete" | "complete";
  missing_field?: "source" | "destination" | "date" | "people" | "days" | "preference";
  slot_state?: Partial<TripSlots>;
  data?: PlannerData;
};

export type MessageData = {
  best_option: PlannerRecommendation;
  alternatives: PlannerRecommendation[];
  itinerary: PlannerItineraryDay[];
  insight: string;
  source: string;
  destination: string;
  booking_url: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  data?: MessageData;
};

export type TripState = {
  title: string;
  route: string;
  initialMessages: ChatMessage[];
};

export type TripMeta = {
  title: string;
  route: string;
  source?: string;
  destination?: string;
};

export type TripSlots = {
  source: string | null;
  destination: string | null;
  date: string | null;
  days: number | null;
  people: number | null;
  preference: "cheap" | "comfort" | "luxury" | null;
};

export type TripExtractionResponse = TripSlots & {
  raw_text: string;
};

/** Conversation language for planner prompts and UI copy (text chat). */
export type VoiceLanguage = "en" | "hi" | "ta";

export function detectLanguage(text: string): VoiceLanguage {
  if (/[\u0B80-\u0BFF]/.test(text)) return "ta";
  if (/[\u0900-\u097F]/.test(text)) return "hi";
  return "en";
}

export function resolveConversationLanguage(text: string, previousLanguage: VoiceLanguage): VoiceLanguage {
  const detected = detectLanguage(text);
  if (detected !== "en") {
    return detected;
  }

  const normalized = text.trim().toLowerCase();
  if (previousLanguage === "ta" && /(\bla\b|\bpoganum\b|\bvenum\b|\birundhu\b)/.test(normalized)) {
    return "ta";
  }
  if (previousLanguage === "hi" && /(\bjana\b|\bchahiye\b|\byaar\b|\bkarna\b)/.test(normalized)) {
    return "hi";
  }
  return detected;
}

export function formatPrice(price: number) {
  if (!Number.isFinite(price) || price <= 0) {
    return null;
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(price);
}

export function titleCase(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function isRecommendation(value: unknown): value is PlannerRecommendation {
  return Boolean(
    value &&
      typeof value === "object" &&
      "mode" in value &&
      "price" in value &&
      "duration" in value &&
      "reason" in value,
  );
}

function sanitizeRecommendation(value: unknown): PlannerRecommendation | null {
  if (!isRecommendation(value)) {
    return null;
  }

  return {
    mode: typeof value.mode === "string" ? value.mode.trim() : "",
    price: typeof value.price === "number" ? value.price : Number(value.price),
    duration: typeof value.duration === "string" ? value.duration.trim() : "",
    reason: typeof value.reason === "string" ? value.reason.trim() : "",
  };
}

function sanitizeItinerary(items: unknown): PlannerItineraryDay[] {
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .map((item, index) => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const day = "day" in item && typeof item.day === "number" ? item.day : index + 1;
      const plan = "plan" in item && typeof item.plan === "string" ? item.plan.trim() : "";
      if (!plan) {
        return null;
      }
      return { day, plan };
    })
    .filter((item): item is PlannerItineraryDay => Boolean(item));
}

function sanitizeAlternatives(items: unknown): PlannerRecommendation[] {
  if (!Array.isArray(items)) {
    return [];
  }

  return items.map(sanitizeRecommendation).filter((item): item is PlannerRecommendation => Boolean(item));
}

function isNonEmptyText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export function normalizePlannerResponse(payload: PlannerApiResponse): ChatMessage | null {
  if (payload.status !== "complete" || !payload.data) {
    return null;
  }

  const data = payload.data;
  if (!isNonEmptyText(data.source) || !isNonEmptyText(data.destination) || !isNonEmptyText(data.insight) || !isNonEmptyText(data.booking_url)) {
    console.warn("Invalid planner data");
    return null;
  }

  const bestOption = sanitizeRecommendation(data.best_option);
  if (!bestOption || !bestOption.mode || !bestOption.duration || !bestOption.reason || !Number.isFinite(bestOption.price) || bestOption.price <= 0) {
    console.warn("Invalid planner data");
    return null;
  }

  const itinerary = sanitizeItinerary(data.itinerary);
  if (itinerary.length === 0) {
    console.warn("Invalid planner data");
    return null;
  }

  const alternatives = sanitizeAlternatives(data.alternatives);
  const validAlternatives = alternatives.filter(
    (item) => item.mode && item.duration && item.reason && Number.isFinite(item.price) && item.price > 0,
  );
  if (validAlternatives.length < 2) {
    console.warn("Invalid planner data");
    return null;
  }

  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "Your trip plan is ready.",
    data: {
      best_option: bestOption,
      alternatives: validAlternatives.slice(0, 2),
      itinerary,
      insight: data.insight,
      source: data.source,
      destination: data.destination,
      booking_url: data.booking_url,
    },
  };
}

export const toAssistantMessage = normalizePlannerResponse;

/** Convert API or tool JSON (full response or `{ data: {...} }` body) into UI message data. */
export function plannerPayloadToMessageData(raw: unknown): MessageData | null {
  if (raw == null) return null;
  let obj: unknown = raw;
  if (typeof obj === "string") {
    try {
      obj = JSON.parse(obj);
    } catch {
      return null;
    }
  }
  if (typeof obj !== "object" || obj === null) return null;
  const o = obj as Record<string, unknown>;
  const inner = o.data !== undefined && o.data !== null && typeof o.data === "object" ? (o.data as Record<string, unknown>) : o;

  const looksLikePlan =
    inner.best_option !== undefined ||
    (typeof inner.source === "string" && typeof inner.destination === "string");
  if (!looksLikePlan) {
    return null;
  }

  const payload: PlannerApiResponse = {
    status: o.status === "incomplete" ? "incomplete" : "complete",
    data: inner as PlannerData,
  };

  const normalized = normalizePlannerResponse(payload);
  return normalized?.data ?? null;
}

export type VapiTravelParseResult = {
  messageData: MessageData | null;
  /** Show “Processing travel plan…” when a plan tool ran but structured data is not ready yet */
  pendingTool: boolean;
};

function toolNameLooksLikePlan(name: string): boolean {
  const n = name.toLowerCase();
  return n.includes("plan_trip") || n.includes("plan-trip") || (n.includes("plan") && !n.includes("booking"));
}

/** Extract planner UI data from Vapi client `message` events (tool call + tool result shapes). */
export function parseVapiMessageForTravelPlan(msg: unknown): VapiTravelParseResult {
  const idle: VapiTravelParseResult = { messageData: null, pendingTool: false };
  if (msg == null || typeof msg !== "object") {
    return idle;
  }

  const root = msg as Record<string, unknown>;
  const type = typeof root.type === "string" ? root.type : "";

  // Standalone tool result (e.g. tool-calls-result / OpenAI-style)
  if (root.result !== undefined && (typeof root.name === "string" || type.includes("tool"))) {
    const name = typeof root.name === "string" ? root.name : "";
    if (name && !toolNameLooksLikePlan(name) && name.toLowerCase().includes("booking")) {
      return idle;
    }
    let rawResult: unknown = root.result;
    if (typeof rawResult === "string") {
      try {
        rawResult = JSON.parse(rawResult);
      } catch {
        return { messageData: null, pendingTool: toolNameLooksLikePlan(name) || !name };
      }
    }
    console.log("TOOL RESULT:", JSON.stringify(rawResult, null, 2));
    const payload = plannerPayloadToMessageData(rawResult);
    if (payload) {
      return { messageData: payload, pendingTool: false };
    }
    return { messageData: null, pendingTool: toolNameLooksLikePlan(name) || !name };
  }

  const nested =
    root.message && typeof root.message === "object" ? (root.message as Record<string, unknown>) : root;
  const toolCalls = (nested.toolCalls as unknown[] | undefined) ?? (root.toolCalls as unknown[] | undefined);
  if (!toolCalls?.length) {
    return idle;
  }

  const first = toolCalls[0];
  if (first == null || typeof first !== "object") {
    return { messageData: null, pendingTool: true };
  }

  const call = first as Record<string, unknown>;
  const fn = call.function && typeof call.function === "object" ? (call.function as Record<string, unknown>) : null;
  const name = String(call.name ?? fn?.name ?? "").toLowerCase();
  if (name && name.includes("booking") && !name.includes("plan")) {
    return idle;
  }

  let rawResult: unknown = call.result ?? call.response ?? fn?.arguments;
  if (typeof rawResult === "string") {
    try {
      rawResult = JSON.parse(rawResult);
    } catch {
      return { messageData: null, pendingTool: true };
    }
  }

  if (rawResult == null) {
    return { messageData: null, pendingTool: true };
  }

  console.log("TOOL RESULT:", JSON.stringify(rawResult, null, 2));

  const payload = plannerPayloadToMessageData(rawResult);
  if (payload) {
    return { messageData: payload, pendingTool: false };
  }

  return { messageData: null, pendingTool: true };
}
