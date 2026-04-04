import type { PlannerRecommendation } from "@/lib/travel";

import { OptionCard } from "./OptionCard";

export function OptionList({ options }: { options: PlannerRecommendation[] }) {
  if (options.length === 0) {
    return null;
  }

  return (
    <section className="rounded-[32px] border border-white/8 bg-white/[0.02] p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">More Options</p>
          <h3 className="mt-1 font-display text-3xl italic text-white">Alternative routes</h3>
        </div>
        <div className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-white/55">
          AI compared
        </div>
      </div>
      <div className="space-y-3">
        {options.map((option, index) => (
          <OptionCard key={`${option.mode}-${option.duration}-${option.price}`} option={option} index={index + 1} />
        ))}
      </div>
    </section>
  );
}
