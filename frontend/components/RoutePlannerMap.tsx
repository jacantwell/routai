import { useState, useEffect, useCallback } from "react";
import Map, {
  Source,
  Layer,
  NavigationControl,
  Marker,
  ViewState,
  ViewStateChangeEvent,
  LineLayerSpecification,
} from "react-map-gl/mapbox";
import { decodePolyline } from "@/lib/polyline";
import { formatDistance, formatTime } from "@/lib/dates";

interface Accommodation {
  name: string;
  address: string;
  map_link: string;
  rating?: number;
}

interface Route {
  polyline: string;
  origin: {
    latitude: number;
    longitude: number;
  };
  destination: {
    latitude: number;
    longitude: number;
  };
  distance: number;
  elevation_gain: number;
}

interface Segment {
  day: number;
  route: Route;
  accommodation_options: Accommodation[];
}

interface RoutePlannerMapProps {
  className?: string;
  sessionId: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Generate colors for different days
const generateSegmentColor = (dayNumber: number, isDarkMode: boolean) => {
  const colors = isDarkMode
    ? [
        "#3b82f6", // blue
        "#10b981", // green
        "#f59e0b", // amber
        "#ef4444", // red
        "#8b5cf6", // purple
        "#ec4899", // pink
      ]
    : [
        "#2563eb", // blue
        "#059669", // green
        "#d97706", // amber
        "#dc2626", // red
        "#7c3aed", // purple
        "#db2777", // pink
      ];
  return colors[(dayNumber - 1) % colors.length];
};

const RoutePlannerMap = ({ className, sessionId }: RoutePlannerMapProps) => {
  const [currentViewState, setCurrentViewState] = useState<ViewState>({
    longitude: 0,
    latitude: 45,
    zoom: 4,
    bearing: 0,
    pitch: 0,
    padding: { top: 40, bottom: 40, left: 40, right: 40 },
  });

  const [isDarkMode, setIsDarkMode] = useState(false);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [overallRoute, setOverallRoute] = useState<Route | null>(null);
  const [selectedAccommodation, setSelectedAccommodation] = useState<{
    day: number;
    accommodation: Accommodation;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Effect to handle dark mode
  useEffect(() => {
    const checkDarkMode = () => {
      setIsDarkMode(document.documentElement.classList.contains("dark"));
    };

    checkDarkMode();

    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => observer.disconnect();
  }, []);

  // Load route data
  useEffect(() => {
    let mounted = true;

    async function loadRouteData() {
      if (mounted) {
        setLoading(true);
        setError(null);
      }

      try {
        // Fetch segments
        const segmentsResponse = await fetch(
          `${API_URL}/sessions/${sessionId}/segments`
        );
        if (!segmentsResponse.ok) {
          throw new Error("Failed to fetch segments");
        }
        const segmentsData: Segment[] = await segmentsResponse.json();

        // Fetch overall route
        const routeResponse = await fetch(
          `${API_URL}/sessions/${sessionId}/route`
        );
        if (!routeResponse.ok) {
          throw new Error("Failed to fetch route");
        }
        const routeData: Route = await routeResponse.json();

        if (mounted) {
          setSegments(segmentsData);
          setOverallRoute(routeData);
        }
      } catch (err) {
        console.error("Failed to load route data:", err);
        if (mounted) {
          setError(
            err instanceof Error ? err.message : "Failed to load route data"
          );
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    if (sessionId) {
      loadRouteData();
    }

    return () => {
      mounted = false;
    };
  }, [sessionId]);

  // Process segments into GeoJSON
  const processedSegments = segments.map((segment) => {
    const coordinates = decodePolyline(segment.route.polyline);
    const geoJsonCoordinates = coordinates.map(([lat, lng]) => [lng, lat]);

    return {
      segment,
      geoJson: {
        type: "Feature" as const,
        properties: {
          day: segment.day,
          distance: segment.route.distance,
          elevation_gain: segment.route.elevation_gain,
        },
        geometry: {
          type: "LineString" as const,
          coordinates: geoJsonCoordinates,
        },
      },
    };
  });

  // Calculate total stats
  const totalStats = segments.length > 0 ? {
    totalDistance: segments.reduce((sum, seg) => sum + seg.route.distance, 0),
    totalElevationGain: segments.reduce(
      (sum, seg) => sum + seg.route.elevation_gain,
      0
    ),
    numDays: segments.length,
    daysWithAccommodation: segments.filter(
      (seg) => seg.accommodation_options.length > 0
    ).length,
  } : null;

  // Calculate bounds and fit map
  const fitBounds = useCallback(() => {
    if (processedSegments.length === 0) return;

    const allCoords: number[][] = [];
    processedSegments.forEach(({ geoJson }) => {
      allCoords.push(...geoJson.geometry.coordinates);
    });

    if (allCoords.length === 0) return;

    const lngs = allCoords.map((coord) => coord[0]);
    const lats = allCoords.map((coord) => coord[1]);

    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);

    const centerLng = (minLng + maxLng) / 2;
    const centerLat = (minLat + maxLat) / 2;

    const lngDiff = Math.abs(maxLng - minLng);
    const latDiff = Math.abs(maxLat - minLat);
    const maxDiff = Math.max(lngDiff, latDiff);

    let zoom = 1;
    if (maxDiff > 0) {
      zoom = Math.min(
        10,
        Math.max(2, Math.floor(8 - Math.log(maxDiff) / Math.log(2)))
      );
    }

    setCurrentViewState((prev) => ({
      ...prev,
      longitude: centerLng,
      latitude: centerLat,
      zoom: zoom,
    }));
  }, [processedSegments]);

  // Auto-fit bounds when segments load
  useEffect(() => {
    if (processedSegments.length > 0 && !loading) {
      const timer = setTimeout(fitBounds, 300);
      return () => clearTimeout(timer);
    }
  }, [processedSegments, loading, fitBounds]);

  // Map style based on dark/light mode
  const mapStyle = isDarkMode
    ? "mapbox://styles/mapbox/dark-v11"
    : "mapbox://styles/mapbox/outdoors-v12";

  return (
    <div className={`relative ${className || ""}`}>
      {/* Stats display */}
      {totalStats && (
        <div className="mb-6 rounded-lg bg-white p-4 shadow-sm dark:bg-slate-800">
          <h3 className="text-lg font-semibold mb-2">Route Overview</h3>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Total Distance
              </p>
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">
                {Math.round(totalStats.totalDistance / 1000)} km
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Elevation Gain
              </p>
              <p className="text-xl font-bold text-green-600 dark:text-green-400">
                {Math.round(totalStats.totalElevationGain)} m
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Days</p>
              <p className="text-xl font-bold text-purple-600 dark:text-purple-400">
                {totalStats.numDays}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Accommodation
              </p>
              <p className="text-xl font-bold text-amber-600 dark:text-amber-400">
                {totalStats.daysWithAccommodation}/{totalStats.numDays} days
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-4 dark:bg-red-900/50 dark:border-red-800">
          <p className="text-red-800 dark:text-red-200">
            <strong>Error:</strong> {error}
          </p>
        </div>
      )}

      {/* Map container */}
      <div className="relative h-96 w-full overflow-hidden rounded-lg md:h-[600px]">
        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/60 dark:bg-black/60">
            <div className="rounded-lg bg-white p-4 shadow-lg dark:bg-slate-800">
              <div className="flex items-center">
                <svg
                  className="-ml-1 mr-3 h-5 w-5 animate-spin text-blue-500"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                <span>Loading route...</span>
              </div>
            </div>
          </div>
        )}

        <Map
          {...currentViewState}
          onMove={(evt: ViewStateChangeEvent) =>
            setCurrentViewState(evt.viewState)
          }
          mapStyle={mapStyle}
          mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
          style={{ width: "100%", height: "100%" }}
        >
          <NavigationControl position="top-right" />

          {/* Fit bounds button */}
          <div className="absolute left-2 top-2">
            <button
              onClick={fitBounds}
              className="rounded bg-white p-2 shadow hover:bg-gray-100 dark:bg-slate-700 dark:hover:bg-slate-600"
              title="Fit map to route"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5"
                />
              </svg>
            </button>
          </div>

          {/* Render each segment */}
          {processedSegments.map(({ segment, geoJson }) => {
            const segmentLayer: LineLayerSpecification = {
              id: `segment-${segment.day}`,
              type: "line",
              source: `segment-${segment.day}`,
              paint: {
                "line-color": generateSegmentColor(segment.day, isDarkMode),
                "line-width": 4,
                "line-opacity": 0.8,
              },
            };

            return (
              <Source
                key={segment.day}
                id={`segment-${segment.day}`}
                type="geojson"
                data={geoJson}
              >
                <Layer {...segmentLayer} />
              </Source>
            );
          })}

          {/* Start marker */}
          {segments.length > 0 && (
            <Marker
              longitude={segments[0].route.origin.longitude}
              latitude={segments[0].route.origin.latitude}
              anchor="bottom"
            >
              <div className="flex flex-col items-center">
                <div className="bg-green-500 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold border-2 border-white shadow-lg">
                  S
                </div>
              </div>
            </Marker>
          )}

          {/* End marker */}
          {segments.length > 0 && (
            <Marker
              longitude={
                segments[segments.length - 1].route.destination.longitude
              }
              latitude={
                segments[segments.length - 1].route.destination.latitude
              }
              anchor="bottom"
            >
              <div className="flex flex-col items-center">
                <div className="bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold border-2 border-white shadow-lg">
                  E
                </div>
              </div>
            </Marker>
          )}

          {/* Accommodation markers */}
          {segments.map((segment) =>
            segment.accommodation_options.slice(0, 3).map((acc, idx) => (
              <Marker
                key={`${segment.day}-${idx}`}
                longitude={segment.route.destination.longitude}
                latitude={segment.route.destination.latitude}
                anchor="center"
                offset={[idx * 8, idx * 8]}
              >
                <div
                  className="h-3 w-3 cursor-pointer rounded-full border-2 border-white bg-blue-500 hover:h-4 hover:w-4 transition-all"
                  onClick={() =>
                    setSelectedAccommodation({ day: segment.day, accommodation: acc })
                  }
                  title={acc.name}
                />
              </Marker>
            ))
          )}
        </Map>
      </div>

      {/* Segment list */}
      {segments.length > 0 && (
        <div className="mt-6 space-y-3">
          <h3 className="text-lg font-semibold">Daily Segments</h3>
          {segments.map((segment) => (
            <div
              key={segment.day}
              className="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{
                      backgroundColor: generateSegmentColor(
                        segment.day,
                        isDarkMode
                      ),
                    }}
                  />
                  <h4 className="font-semibold">Day {segment.day}</h4>
                </div>
                <div className="flex gap-4 text-sm text-gray-600 dark:text-gray-400">
                  <span>{Math.round(segment.route.distance / 1000)} km</span>
                  <span>{Math.round(segment.route.elevation_gain)} m ↑</span>
                </div>
              </div>
              {segment.accommodation_options.length > 0 ? (
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {segment.accommodation_options.length} accommodation{" "}
                  {segment.accommodation_options.length === 1
                    ? "option"
                    : "options"}{" "}
                  available
                </div>
              ) : (
                <div className="text-sm text-amber-600 dark:text-amber-400">
                  No accommodation found
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Selected accommodation info */}
      {selectedAccommodation && (
        <div className="mt-4 rounded-lg bg-white p-4 shadow-md dark:bg-slate-800">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold">
              Day {selectedAccommodation.day} Accommodation
            </h3>
            <button
              onClick={() => setSelectedAccommodation(null)}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          <div className="mt-2">
            <p className="font-semibold">
              {selectedAccommodation.accommodation.name}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {selectedAccommodation.accommodation.address}
            </p>
            {selectedAccommodation.accommodation.rating && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Rating: ⭐ {selectedAccommodation.accommodation.rating}
              </p>
            )}
            <a
              href={selectedAccommodation.accommodation.map_link}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-sm mt-2 inline-block"
            >
              View on Google Maps →
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoutePlannerMap;