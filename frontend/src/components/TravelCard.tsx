import { ArrowRight, Clock3, IndianRupee, Sparkles } from "lucide-react";

import { formatPrice, titleCase, type PlannerRecommendation } from "@/lib/travel";

export function TravelCard({ option }: { option: PlannerRecommendation }) {
  const tag = option.mode === "bus" ? "Best Value" : option.mode === "flight" ? "Fastest" : "Balanced";
  const priceLabel = formatPrice(option.price);
  if (!priceLabel) {
    return null;
  }

  return (
    <div className="liquid-glass-strong relative overflow-hidden rounded-[30px] p-5 animate-slide-up">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/45">Recommended Route</p>
          <h3 className="mt-2 font-display text-4xl italic leading-none text-white">{titleCase(option.mode)}</h3>
        </div>
        <div className="rounded-full border border-white/12 bg-white/8 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-white/72">
          {tag}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] border border-white/8 bg-black/20 p-4">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-white/45">
            <IndianRupee className="h-3.5 w-3.5" />
            Price
          </div>
          <div className="mt-3 text-2xl font-semibold text-white">{priceLabel}</div>
        </div>
        <div className="rounded-[22px] border border-white/8 bg-black/20 p-4">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-white/45">
            <Clock3 className="h-3.5 w-3.5" />
            Duration
          </div>
          <div className="mt-3 text-2xl font-semibold text-white">{option.duration}</div>
        </div>
        <div className="rounded-[22px] border border-white/8 bg-black/20 p-4 sm:col-span-2 xl:col-span-1">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-white/45">
            <Sparkles className="h-3.5 w-3.5" />
            Why This
          </div>
          <div className="mt-3 flex items-start gap-2 text-sm leading-6 text-white/72">
            <ArrowRight className="mt-1 h-3.5 w-3.5 flex-none" />
            <span>{option.reason}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
