import { useState } from "react";

import { ChatPanel } from "@/components/ChatPanel";
import { MapPanel } from "@/components/MapPanel";
import { Sidebar } from "@/components/Sidebar";
import { initialTrip } from "@/data/mockTrip";
import { type TripMeta } from "@/lib/travel";

function App() {
  const [tripMeta, setTripMeta] = useState<TripMeta>({
    title: initialTrip.title,
    route: initialTrip.route,
    source: undefined,
    destination: undefined,
  });

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-[-10%] top-[-12%] h-[28rem] w-[28rem] rounded-full bg-white/6 blur-3xl" />
        <div className="absolute bottom-[-16%] right-[-4%] h-[32rem] w-[32rem] rounded-full bg-white/[0.04] blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.08),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.03),transparent_35%)]" />
      </div>

      <div className="relative flex min-h-screen">
        <Sidebar />
        <ChatPanel trip={initialTrip} title={tripMeta.title} onMetaChange={setTripMeta} />
        <MapPanel route={tripMeta.route} source={tripMeta.source} destination={tripMeta.destination} />
      </div>
    </div>
  );
}

export default App;
