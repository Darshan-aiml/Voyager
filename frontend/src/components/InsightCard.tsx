import { Lightbulb } from "lucide-react";

export function InsightCard({ insight }: { insight: string }) {
  return (
    <section className="liquid-glass rounded-[30px] p-5 animate-slide-up">
      <div className="mb-3 flex items-center gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/8 p-2.5 text-white/80">
          <Lightbulb className="h-4.5 w-4.5" />
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">Insight</p>
          <h3 className="mt-1 font-display text-3xl italic text-white">Why this works</h3>
        </div>
      </div>
      <p className="max-w-3xl text-sm leading-7 text-white/68">{insight}</p>
    </section>
  );
}
