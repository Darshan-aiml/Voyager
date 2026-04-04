import { Bookmark, Briefcase, Compass, MessageSquare, Plus, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navigation = [
  { label: "Chats", icon: MessageSquare, active: true },
  { label: "Trips", icon: Briefcase },
  { label: "Saved", icon: Bookmark },
];

export function Sidebar() {
  return (
    <aside className="hidden w-[240px] flex-col border-r border-white/8 bg-black/70 px-5 py-6 lg:flex">
      <div className="liquid-glass-strong relative overflow-hidden rounded-[28px] px-5 py-4 noise animate-fade-in">
        <div className="mb-2 flex items-center gap-3 text-[11px] uppercase tracking-[0.32em] text-white/45">
          <Sparkles className="h-3.5 w-3.5" />
          Premium AI Travel
        </div>
        <div className="font-display text-[2rem] italic leading-none tracking-tight text-white">Voyager</div>
      </div>

      <Button className="mt-6 gap-2">
        <Plus className="h-4 w-4" />
        New Chat
      </Button>

      <nav className="mt-8 space-y-2">
        {navigation.map(({ label, icon: Icon, active }) => (
          <button
            key={label}
            className={cn(
              "group flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm transition duration-300",
              active ? "liquid-glass-strong text-white" : "text-white/55 hover:bg-white/5 hover:text-white",
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="mt-10 flex-1 rounded-[30px] border border-white/6 bg-white/[0.02] p-4 text-white/42">
        <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.28em]">
          <Compass className="h-3.5 w-3.5" />
          Recent Route
        </div>
        <div className="font-display text-2xl italic text-white">Southbound Quiet</div>
        <p className="mt-3 text-sm leading-6 text-white/45">
          Your latest planning thread is saved and ready to resume whenever you want to refine timings or swap transport.
        </p>
      </div>
    </aside>
  );
}
