import type { PlannerApiResponse, TripExtractionResponse } from "@/lib/travel";

const PLAN_TRIP_URL = "http://localhost:8000/api/plan-trip";
const EXTRACT_TRIP_URL = "http://localhost:8000/api/extract-trip";
const EXECUTE_BOOKING_URL = "http://localhost:8000/api/execute-booking";

type PlanTripPayload = {
  query?: string;
  source?: string;
  destination?: string;
  date?: string;
  people?: number;
  days?: number;
  preference?: "cheap" | "comfort" | "luxury";
  slot_state?: {
    source?: string | null;
    destination?: string | null;
    date?: string | null;
    people?: number | null;
    days?: number | null;
    preference?: "cheap" | "comfort" | "luxury" | null;
  };
};

async function requestPlan(payload: PlanTripPayload): Promise<PlannerApiResponse> {
  try {
    const res = await fetch(PLAN_TRIP_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const rawBody = await res.text();
    const data = rawBody ? (JSON.parse(rawBody) as unknown) : null;
    console.log("API response:", data);

    if (!res.ok) {
      const message =
        data && typeof data === "object" && "detail" in data && typeof data.detail === "string"
          ? data.detail
          : `Request failed with status ${res.status}`;
      throw new Error(message);
    }

    return (data ?? {}) as PlannerApiResponse;
  } catch (err) {
    console.error("API error:", err);
    throw err;
  }
}

export async function planTrip(query: string): Promise<PlannerApiResponse> {
  try {
    return await requestPlan({ query });
  } catch (firstError) {
    await new Promise((resolve) => window.setTimeout(resolve, 800));
    return requestPlan({ query }).catch((secondError) => {
      throw secondError instanceof Error ? secondError : firstError;
    });
  }
}

export async function planTripWithSlots(payload: PlanTripPayload): Promise<PlannerApiResponse> {
  return requestPlan(payload);
}

export async function extractTrip(text: string): Promise<TripExtractionResponse> {
  try {
    const res = await fetch(EXTRACT_TRIP_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
    });

    const data = (await res.json()) as TripExtractionResponse | { detail?: string };
    console.log("API response:", data);

    if (!res.ok) {
      const message = "detail" in data && typeof data.detail === "string" ? data.detail : `Request failed with status ${res.status}`;
      throw new Error(message);
    }

    return data as TripExtractionResponse;
  } catch (err) {
    console.error("API error:", err);
    throw err;
  }
}

export async function executeBooking(payload: {
  source: string;
  destination: string;
}) {
  try {
    const res = await fetch(EXECUTE_BOOKING_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        source: payload.source,
        destination: payload.destination,
      }),
    });

    const data = (await res.json()) as { status?: string; booking_url?: string; detail?: string };
    console.log("API response:", data);

    if (!res.ok || data.status !== "success" || !data.booking_url) {
      throw new Error(typeof data.detail === "string" ? data.detail : "Unable to open booking flow.");
    }

    return data.booking_url;
  } catch (err) {
    console.error("API error:", err);
    throw err;
  }
}
