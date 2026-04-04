import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";
import type { ChatMessage, MessageData } from "@/lib/travel";

import { InsightCard } from "./InsightCard";
import { ItineraryCard } from "./ItineraryCard";
import { OptionList } from "./OptionList";
import { TravelCard } from "./TravelCard";

function LandingState() {
  return (
    <div className="grid gap-5 xl:grid-cols-[1.3fr,0.9fr]">
      <section className="liquid-glass-strong rounded-[32px] p-6 md:p-8">
        <p className="text-[11px] uppercase tracking-[0.3em] text-white/42">AI Travel Planner</p>
        <h2 className="mt-3 font-display text-4xl italic text-white md:text-5xl">Plan smarter trips from one prompt.</h2>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-white/68">
          Ask for routes, budgets, night travel options, or day-by-day itineraries. Voyager will compare choices, explain the answer, and update the route map after your first query.
        </p>
      </section>

      <section className="rounded-[32px] border border-white/8 bg-white/[0.03] p-5">
        <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">Try prompts</p>
        <div className="mt-4 space-y-3 text-sm leading-7 text-white/70">
          <div className="rounded-[22px] border border-white/8 bg-black/20 px-4 py-3">
            Plan a budget weekend trip from Bangalore to Coorg for 2 people.
          </div>
          <div className="rounded-[22px] border border-white/8 bg-black/20 px-4 py-3">
            Find the best overnight option from Chennai to Madurai with a 3-day itinerary.
          </div>
          <div className="rounded-[22px] border border-white/8 bg-black/20 px-4 py-3">
            Compare train and bus options from Hyderabad to Goa under 4000 INR.
          </div>
        </div>
      </section>
    </div>
  );
}

function VoicePlanProcessing() {
  return (
    <div className="liquid-glass rounded-[28px] border border-white/10 p-5 text-sm leading-7 text-white/70 animate-fade-in">
      Processing travel plan...
    </div>
  );
}

function LoadingBlock({ message }: { message: string }) {
  return (
    <div className="liquid-glass-strong rounded-[30px] p-5 animate-pulseglass">
      <div className="mb-4 flex items-center gap-3 text-[11px] uppercase tracking-[0.28em] text-white/46">
        <span className="h-2.5 w-2.5 rounded-full bg-white/70" />
        {message}
      </div>
      <div className="space-y-3">
        <div className="h-20 rounded-[24px] bg-white/8" />
        <div className="h-20 rounded-[24px] bg-white/6" />
        <div className="h-20 rounded-[24px] bg-white/5" />
      </div>
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="liquid-glass rounded-[28px] border border-white/10 p-5 text-sm leading-7 text-white/70 animate-fade-in">
      {message}
    </div>
  );
}

export function MessageList({
  messages,
  isLoading,
  error,
  loadingMessage,
  voiceTravelData,
  voicePlanProcessing,
}: {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  loadingMessage: string;
  voiceTravelData?: MessageData | null;
  voicePlanProcessing?: boolean;
}) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading, error, voiceTravelData, voicePlanProcessing]);

  return (
    <div className="scrollbar-hidden flex-1 space-y-6 overflow-y-auto pr-2 pb-32">
      {messages.length === 0 && !isLoading && !error ? <LandingState /> : null}
      {messages.map((message, messageIndex) =>
        message.role === "user" ? (
          <div key={message.id} className="flex justify-end opacity-0 animate-fade-in" style={{ animationDelay: `${messageIndex * 120}ms` }}>
            <div className="max-w-[34rem] rounded-[28px] border border-white/10 bg-white/[0.06] px-5 py-4 text-sm leading-7 text-white/80 shadow-glow">
              {message.content}
            </div>
          </div>
        ) : message.data ? (
          <div key={message.id} className={cn("space-y-5 opacity-0 animate-fade-in")} style={{ animationDelay: `${messageIndex * 120}ms` }}>
            <TravelCard option={message.data.best_option} />
            <OptionList options={message.data.alternatives} />
            <ItineraryCard itinerary={message.data.itinerary} />
            <InsightCard insight={message.data.insight} />
          </div>
        ) : (
          <div key={message.id} className={cn("space-y-5 opacity-0 animate-fade-in")} style={{ animationDelay: `${messageIndex * 120}ms` }}>
            <div className="liquid-glass rounded-[28px] border border-white/10 p-5 text-sm leading-7 text-white/70">{message.content}</div>
          </div>
        ),
      )}
      {voicePlanProcessing ? <VoicePlanProcessing /> : null}
      {voiceTravelData ? (
        <div className="space-y-5 opacity-0 animate-fade-in">
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">Voice assistant plan</p>
          <TravelCard option={voiceTravelData.best_option} />
          <OptionList options={voiceTravelData.alternatives} />
          <ItineraryCard itinerary={voiceTravelData.itinerary} />
          <InsightCard insight={voiceTravelData.insight} />
        </div>
      ) : null}
      {isLoading ? <LoadingBlock message={loadingMessage} /> : null}
      {error ? <ErrorBlock message={error} /> : null}
      <div ref={endRef} />
    </div>
  );
}
