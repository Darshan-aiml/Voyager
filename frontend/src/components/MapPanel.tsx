import "maplibre-gl/dist/maplibre-gl.css";
import { MapPinned, MoveRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useMapRoute } from "@/hooks/useMapRoute";

type MapLibreModule = typeof import("maplibre-gl");

type MapPanelProps = {
  route: string;
  source?: string;
  destination?: string;
};

export function MapPanel({ route, source, destination }: MapPanelProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<InstanceType<MapLibreModule["Map"]> | null>(null);
  const markersRef = useRef<Array<InstanceType<MapLibreModule["Marker"]>>>([]);
  const [maplibre, setMaplibre] = useState<MapLibreModule | null>(null);
  const [mapInitError, setMapInitError] = useState<string | null>(null);
  const { indiaCenter, isMapLoading, mapData, mapError } = useMapRoute(
    source && destination ? { source, destination } : null,
  );

  function formatRoadDuration(minutes: number) {
    const rounded = Math.max(1, Math.round(minutes));
    const hours = Math.floor(rounded / 60);
    const remaining = rounded % 60;
    if (hours <= 0) {
      return `${remaining} min`;
    }
    if (remaining === 0) {
      return `${hours}h`;
    }
    return `${hours}h ${remaining}m`;
  }

  useEffect(() => {
    let active = true;

    void import("maplibre-gl")
      .then((module) => {
        if (active) {
          setMaplibre(module);
        }
      })
      .catch((error) => {
        console.error("MapLibre failed to load:", error);
        if (active) {
          setMapInitError(error instanceof Error ? error.message : "Map library failed to load.");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current || !maplibre) {
      return;
    }

    try {
      mapRef.current = new maplibre.Map({
        container: mapContainerRef.current,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "&copy; OpenStreetMap contributors",
            },
          },
          layers: [
            {
              id: "osm",
              type: "raster",
              source: "osm",
            },
          ],
        },
        center: indiaCenter,
        zoom: 3.7,
      });

      mapRef.current.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");
      mapRef.current.addControl(new maplibre.AttributionControl({ compact: true }));
      setMapInitError(null);
    } catch (error) {
      console.error("Map initialization failed:", error);
      setMapInitError(error instanceof Error ? error.message : "Map failed to initialize.");
    }

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [indiaCenter, maplibre]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapData || !maplibre) {
      return;
    }

    const renderRoute = () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [
        new maplibre.Marker({ color: "#f8fafc" })
          .setLngLat(mapData.source.coordinates)
          .setPopup(new maplibre.Popup().setText(mapData.source.name))
          .addTo(map),
        new maplibre.Marker({ color: "#f59e0b" })
          .setLngLat(mapData.destination.coordinates)
          .setPopup(new maplibre.Popup().setText(mapData.destination.name))
          .addTo(map),
      ];

      const existingSource = map.getSource("route-line");
      if (existingSource && "setData" in existingSource) {
        (existingSource as InstanceType<MapLibreModule["GeoJSONSource"]>).setData(mapData.geojson);
      } else {
        map.addSource("route-line", {
          type: "geojson",
          data: mapData.geojson,
        });
        map.addLayer({
          id: "route-line",
          type: "line",
          source: "route-line",
          paint: {
            "line-color": "#f59e0b",
            "line-width": 4,
            "line-opacity": 0.9,
          },
        });
      }

      const bounds = new maplibre.LngLatBounds();
      bounds.extend(mapData.bounds[0]);
      bounds.extend(mapData.bounds[1]);
      map.fitBounds(bounds, {
        padding: 100,
        duration: 1400,
        maxZoom: 11.5,
      });
    };

    if (map.isStyleLoaded()) {
      renderRoute();
      return;
    }

    map.once("load", renderRoute);
  }, [mapData, maplibre]);

  const routeParts = route.includes(" → ") ? route.split(" → ") : [source ?? "Origin", destination ?? "Destination"];
  const routeMeta =
    mapData
      ? `Road route: ${formatRoadDuration(mapData.durationMinutes)} (${mapData.distanceKm.toFixed(1)} km)${mapData.routeSource === "fallback" ? " (estimated)" : ""}.`
      : null;
  const statusMessage =
    mapInitError ??
    mapError ??
    (isMapLoading
      ? "Calculating road route and travel time..."
      : routeMeta ?? "Live route markers update after every new travel plan with MapLibre and OpenStreetMap data.");
  const hasActiveRoute = Boolean(source && destination);

  return (
    <aside className="hidden w-[38%] shrink-0 px-0 py-4 pr-4 xl:block">
      <div className="liquid-glass-strong relative h-[calc(100vh-2rem)] overflow-hidden rounded-[36px] p-5 animate-pulseglass">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(255,255,255,0.15),transparent_20%),radial-gradient(circle_at_78%_26%,rgba(255,255,255,0.08),transparent_22%),radial-gradient(circle_at_52%_72%,rgba(255,255,255,0.07),transparent_18%)]" />
        <div className="relative h-full rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] p-5">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">Map Preview</p>
              <h2 className="mt-1 font-display text-4xl italic text-white">Route canvas</h2>
            </div>
            <div className="rounded-full border border-white/10 bg-white/6 p-3 text-white/70">
              <MapPinned className="h-4.5 w-4.5" />
            </div>
          </div>

          <div className="relative flex h-[calc(100%-5rem)] flex-col overflow-hidden rounded-[28px] border border-white/10 bg-black/25 p-6">
            <div ref={mapContainerRef} className="absolute inset-0" />
            <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-black/55" />
            <div className="relative z-10 mt-auto flex items-end justify-between gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-[0.28em] text-white/42">Current route</p>
                <div className="mt-3 flex items-center gap-3 font-display text-3xl italic text-white">
                  <span>{routeParts[0]}</span>
                  <MoveRight className="h-5 w-5 text-white/55" />
                  <span>{routeParts[1] ?? "Destination"}</span>
                </div>
                <p className="mt-4 max-w-sm text-sm leading-7 text-white/52">
                  {hasActiveRoute ? statusMessage : "The live map stays idle on the landing page and activates after the first planned route."}
                </p>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-white/6 px-4 py-3 text-right">
                <div className="text-[11px] uppercase tracking-[0.24em] text-white/42">Status</div>
                <div className="mt-1 text-sm text-white/72">
                  {hasActiveRoute ? (isMapLoading ? "Updating route" : mapData ? "Map synced" : mapInitError || mapError ? "Map unavailable" : "Waiting for route") : "Landing mode"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
