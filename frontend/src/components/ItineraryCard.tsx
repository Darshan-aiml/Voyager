import { CalendarRange } from "lucide-react";

import type { PlannerItineraryDay } from "@/lib/travel";

export function ItineraryCard({ itinerary }: { itinerary: PlannerItineraryDay[] }) {
  return (
    <section className="liquid-glass rounded-[30px] p-5 animate-slide-up">
      <div className="mb-5 flex items-center gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/8 p-2.5 text-white/80">
          <CalendarRange className="h-4.5 w-4.5" />
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">Itinerary</p>
          <h3 className="mt-1 font-display text-3xl italic text-white">Day-by-day flow</h3>
        </div>
      </div>
      <div className="space-y-4">
        {itinerary.map((item, index) => (
          <div
            key={item.day}
            className="grid gap-3 rounded-[24px] border border-white/8 bg-black/20 px-4 py-4 opacity-0 md:grid-cols-[72px,1fr] animate-slide-up"
            style={{ animationDelay: `${index * 110}ms` }}
          >
            <div className="text-[11px] uppercase tracking-[0.24em] text-white/42">Day {item.day}</div>
            <div className="text-sm leading-7 text-white/72">{item.plan}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
