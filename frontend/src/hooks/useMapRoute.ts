import { useEffect, useState } from "react";

export type RouteLocation = {
  source: string;
  destination: string;
};

export type Coordinates = [number, number];

export type RouteMapData = {
  source: {
    name: string;
    coordinates: Coordinates;
  };
  destination: {
    name: string;
    coordinates: Coordinates;
  };
  center: Coordinates;
  bounds: [Coordinates, Coordinates];
  distanceKm: number;
  durationMinutes: number;
  routeSource: "osrm" | "fallback";
  geojson: GeoJSON.Feature<GeoJSON.LineString>;
};

const INDIA_CENTER: Coordinates = [78.9629, 20.5937];

const KNOWN_CITY_COORDINATES: Record<string, Coordinates> = {
  chennai: [80.270186, 13.083694],
  coimbatore: [76.955833, 11.001812],
  hosur: [77.8252923, 12.739585],
  bangalore: [77.594566, 12.971599],
  bengaluru: [77.594566, 12.971599],
  mumbai: [72.877656, 19.075984],
  delhi: [77.209006, 28.613895],
  hyderabad: [78.486671, 17.385044],
  pune: [73.856744, 18.52043],
  madurai: [78.119775, 9.925201],
  goa: [73.82785, 15.49891],
  kolkata: [88.363895, 22.572646],
};

async function geocodeCity(city: string) {
  const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=in&q=${encodeURIComponent(`${city}, India`)}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Geocoding failed for ${city}`);
  }

  const payload = (await response.json()) as Array<{ lat?: string; lon?: string }>;
  const coordinates = payload[0]
    ? ([Number(payload[0].lon), Number(payload[0].lat)] as Coordinates)
    : null;

  if (!coordinates || Number.isNaN(coordinates[0]) || Number.isNaN(coordinates[1])) {
    const fallback = KNOWN_CITY_COORDINATES[city.toLowerCase().trim()];
    if (fallback) {
      return fallback;
    }
    throw new Error(`No coordinates found for ${city}`);
  }

  return coordinates;
}

type OsrmRouteResponse = {
  code: string;
  routes?: Array<{
    distance: number;
    duration: number;
    geometry: {
      coordinates: Coordinates[];
      type: "LineString";
    };
  }>;
};

async function fetchRoadRoute(source: Coordinates, destination: Coordinates) {
  const [srcLng, srcLat] = source;
  const [dstLng, dstLat] = destination;
  const url =
    `https://router.project-osrm.org/route/v1/driving/` +
    `${srcLng},${srcLat};${dstLng},${dstLat}` +
    `?overview=full&geometries=geojson&steps=false&alternatives=false`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Unable to fetch road route.");
  }

  const payload = (await response.json()) as OsrmRouteResponse;
  if (payload.code !== "Ok" || !payload.routes?.length) {
    throw new Error("Road route is unavailable for this pair of cities.");
  }

  const route = payload.routes[0];
  return {
    coordinates: route.geometry.coordinates,
    distanceKm: route.distance / 1000,
    durationMinutes: route.duration / 60,
    routeSource: "osrm" as const,
  };
}

function haversineDistanceKm(a: Coordinates, b: Coordinates) {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const earthRadiusKm = 6371;
  const dLat = toRad(b[1] - a[1]);
  const dLng = toRad(b[0] - a[0]);
  const lat1 = toRad(a[1]);
  const lat2 = toRad(b[1]);

  const sinLat = Math.sin(dLat / 2);
  const sinLng = Math.sin(dLng / 2);
  const value = sinLat * sinLat + Math.cos(lat1) * Math.cos(lat2) * sinLng * sinLng;
  const c = 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
  return earthRadiusKm * c;
}

function buildFallbackRoadRoute(source: Coordinates, destination: Coordinates) {
  const distanceKm = haversineDistanceKm(source, destination) * 1.25;
  // Approximate highway driving speed with route factor.
  const durationMinutes = (distanceKm / 45) * 60;
  return {
    coordinates: [source, destination] as Coordinates[],
    distanceKm,
    durationMinutes,
    routeSource: "fallback" as const,
  };
}

function routeBoundsFromCoordinates(points: Coordinates[]): [Coordinates, Coordinates] {
  let minLng = Number.POSITIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLng = Number.NEGATIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;

  points.forEach(([lng, lat]) => {
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  });

  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ];
}

export function useMapRoute(route: RouteLocation | null) {
  const [mapData, setMapData] = useState<RouteMapData | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [isMapLoading, setIsMapLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRoute() {
      if (!route?.source || !route.destination) {
        setMapData(null);
        return;
      }

      try {
        setIsMapLoading(true);
        setMapError(null);
        const [sourceCoordinates, destinationCoordinates] = await Promise.all([
          geocodeCity(route.source),
          geocodeCity(route.destination),
        ]);

        if (cancelled) {
          return;
        }

        let roadRoute;
        try {
          roadRoute = await fetchRoadRoute(sourceCoordinates, destinationCoordinates);
        } catch {
          roadRoute = buildFallbackRoadRoute(sourceCoordinates, destinationCoordinates);
        }

        if (cancelled) {
          return;
        }

        const center: Coordinates = [
          (sourceCoordinates[0] + destinationCoordinates[0]) / 2,
          (sourceCoordinates[1] + destinationCoordinates[1]) / 2,
        ];

        const bounds = routeBoundsFromCoordinates(roadRoute.coordinates);

        setMapData({
          source: {
            name: route.source,
            coordinates: sourceCoordinates,
          },
          destination: {
            name: route.destination,
            coordinates: destinationCoordinates,
          },
          center,
          bounds,
          distanceKm: roadRoute.distanceKm,
          durationMinutes: roadRoute.durationMinutes,
          routeSource: roadRoute.routeSource,
          geojson: {
            type: "Feature",
            geometry: {
              type: "LineString",
              coordinates: roadRoute.coordinates,
            },
            properties: {},
          },
        });
      } catch (error) {
        if (!cancelled) {
          setMapData(null);
          setMapError(error instanceof Error ? error.message : "Unable to update the map right now.");
        }
      } finally {
        if (!cancelled) {
          setIsMapLoading(false);
        }
      }
    }

    void loadRoute();

    return () => {
      cancelled = true;
    };
  }, [route?.destination, route?.source]);

  return {
    indiaCenter: INDIA_CENTER,
    isMapLoading,
    mapData,
    mapError,
  };
}
