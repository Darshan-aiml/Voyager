import { ArrowUpRight, Clock3, IndianRupee } from "lucide-react";

import { formatPrice, titleCase, type PlannerRecommendation } from "@/lib/travel";

export function OptionCard({ option, index }: { option: PlannerRecommendation; index: number }) {
  const priceLabel = formatPrice(option.price);
  if (!priceLabel) {
    return null;
  }

  return (
    <div
      className="liquid-glass flex items-center justify-between rounded-[24px] px-4 py-4 opacity-0 animate-slide-up"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <div>
        <div className="text-base font-medium text-white">{titleCase(option.mode)} Option</div>
        <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-white/52">
          <span className="inline-flex items-center gap-1">
            <Clock3 className="h-3.5 w-3.5" />
            {option.duration}
          </span>
          <span className="inline-flex items-center gap-1">
            <ArrowUpRight className="h-3.5 w-3.5" />
            AI-ranked alternative
          </span>
        </div>
        <p className="mt-2 max-w-xl text-sm leading-6 text-white/58">{option.reason}</p>
      </div>
      <div className="text-right">
        <div className="text-[11px] uppercase tracking-[0.22em] text-white/42">Fare</div>
        <div className="mt-1 inline-flex items-center gap-1 text-lg font-semibold text-white">
          <IndianRupee className="h-4 w-4" />
          {priceLabel.replace("₹", "")}
        </div>
      </div>
    </div>
  );
}
