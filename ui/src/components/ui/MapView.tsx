import { useEffect, useMemo, useRef, useState } from "react";
import mapboxgl, { type GeoJSONSource } from "mapbox-gl";
import type { Incident } from "./IncidentQueue";

interface MapViewProps {
  incidents: Incident[];
  selectedId: string | null;
  onSelectIncident: (id: string) => void;
}

const severityColors = {
  critical: "#8B2835",
  high: "#B8741A",
  moderate: "#3B5B8C",
  low: "#4A4A5A",
} as const;

const SEVERITY_HEATMAP_WEIGHT: Record<string, number> = {
  critical: 1.0,
  high: 0.7,
  moderate: 0.4,
  low: 0.2,
};

const MAPBOX_ACCESS_TOKEN =
  "pk.eyJ1IjoidG9tLXNtYWlsIiwiYSI6ImNsdGFyem" +
  "UxazFmcDgybG03bW56ZTc0d3gifQ.iWzQyehvRTR5inI5Q4tp9g";
const CLUSTERED_SOURCE_ID = "incidents-clustered";
const HEATMAP_SOURCE_ID = "incidents-heatmap-src";
const STOCKHOLM_CENTER: [number, number] = [18.0686, 59.3293];

const HEAT_FADE_START = 11;
const HEAT_FADE_END = 13;

const LABEL_LAYER_CANDIDATES = [
  "settlement-subdivision-label",
  "settlement-minor-label",
  "settlement-major-label",
  "poi-label",
  "place-city",
  "place-town",
];

function getFirstExistingLabelLayer(map: mapboxgl.Map): string | undefined {
  const styleLayers = map.getStyle().layers ?? [];
  for (const candidate of LABEL_LAYER_CANDIDATES) {
    if (styleLayers.some((l) => l.id === candidate)) return candidate;
  }
  return styleLayers.find((l) => l.type === "symbol")?.id;
}

function toIncidentGeoJson(
  incidents: Incident[],
): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: "FeatureCollection",
    features: incidents.map((incident) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [incident.lng, incident.lat] },
      properties: {
        id: incident.id,
        severity: incident.severity,
        heatWeight: SEVERITY_HEATMAP_WEIGHT[incident.severity] ?? 0.2,
        resolved:
          incident.completedAt !== null || incident.status === "assigned",
      },
    })),
  };
}

// ── Donut chart SVG marker ─────────────────────────────────────────────────────
// Based on the official Mapbox HTML cluster example, adapted for severity categories.

function donutSegment(
  start: number,
  end: number,
  r: number,
  r0: number,
  color: string,
): string {
  if (end - start === 1) end -= 0.00001;
  const a0 = 2 * Math.PI * (start - 0.25);
  const a1 = 2 * Math.PI * (end - 0.25);
  const x0 = Math.cos(a0),
    y0 = Math.sin(a0);
  const x1 = Math.cos(a1),
    y1 = Math.sin(a1);
  const largeArc = end - start > 0.5 ? 1 : 0;
  return [
    `<path d="M ${r + r0 * x0} ${r + r0 * y0}`,
    `L ${r + r * x0} ${r + r * y0}`,
    `A ${r} ${r} 0 ${largeArc} 1 ${r + r * x1} ${r + r * y1}`,
    `L ${r + r0 * x1} ${r + r0 * y1}`,
    `A ${r0} ${r0} 0 ${largeArc} 0 ${r + r0 * x0} ${r + r0 * y0}`,
    `" fill="${color}" />`,
  ].join(" ");
}

function createDonutMarkerElement(props: {
  critical: number;
  high: number;
  moderate: number;
  low: number;
  point_count: number;
}): HTMLElement {
  const counts = [props.critical, props.high, props.moderate, props.low];
  const colors = [
    severityColors.critical,
    severityColors.high,
    severityColors.moderate,
    severityColors.low,
  ];
  const total = props.point_count;

  // Scale ring size with count
  const r = total >= 500 ? 36 : total >= 100 ? 30 : total >= 20 ? 24 : 18;
  const r0 = Math.round(r * 0.58); // inner radius (hole size)
  const w = r * 2;
  const fontSize = total >= 1000 ? 13 : total >= 100 ? 12 : 11;

  // Build cumulative offsets
  const offsets: number[] = [];
  let running = 0;
  for (const c of counts) {
    offsets.push(running);
    running += c;
  }

  // Dominant severity for the glow ring color
  const dominantIdx = counts.indexOf(Math.max(...counts));
  const glowColor = colors[dominantIdx];

  let segments = "";
  for (let i = 0; i < counts.length; i++) {
    if (counts[i] === 0) continue;
    segments += donutSegment(
      offsets[i] / total,
      (offsets[i] + counts[i]) / total,
      r,
      r0,
      colors[i],
    );
  }

  const html = `
    <div style="
      cursor: pointer;
      filter: drop-shadow(0 0 6px ${glowColor}88);
      transition: filter 0.15s ease;
    ">
      <svg
        width="${w}" height="${w}"
        viewBox="0 0 ${w} ${w}"
        text-anchor="middle"
        style="display:block; overflow:visible"
      >
        ${segments}
        <!-- inner fill -->
        <circle cx="${r}" cy="${r}" r="${r0}" fill="#0f1724" />
        <!-- count label -->
        <text
          x="${r}" y="${r}"
          dominant-baseline="central"
          text-anchor="middle"
          fill="#e8eaed"
          font-size="${fontSize}"
          font-family="'DIN Offc Pro Medium', 'Arial Unicode MS Bold', sans-serif"
          font-weight="600"
        >${total >= 1000 ? `${(total / 1000).toFixed(1)}k` : total}</text>
      </svg>
    </div>`;

  const el = document.createElement("div");
  el.innerHTML = html.trim();
  const node = el.firstChild as HTMLElement;

  // Hover glow boost
  node.addEventListener("mouseenter", () => {
    (node as HTMLElement).style.filter = `drop-shadow(0 0 10px ${glowColor}cc)`;
  });
  node.addEventListener("mouseleave", () => {
    (node as HTMLElement).style.filter = `drop-shadow(0 0 6px ${glowColor}88)`;
  });

  return node;
}

// ── Layer setup ───────────────────────────────────────────────────────────────

function addNonClusterLayers(map: mapboxgl.Map, selectedId: string | null) {
  const beforeLabelLayer = getFirstExistingLabelLayer(map);

  // Heatmap — below city labels
  map.addLayer(
    {
      id: "incident-heatmap",
      type: "heatmap",
      source: HEATMAP_SOURCE_ID,
      paint: {
        "heatmap-weight": [
          "interpolate",
          ["linear"],
          ["get", "heatWeight"],
          0,
          0,
          1,
          1,
        ],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 9, 3],
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0,0,0,0)",
          0.1,
          "rgba(43,60,110,0.5)",
          0.3,
          "rgba(90,100,180,0.7)",
          0.5,
          "rgba(184,116,26,0.8)",
          0.75,
          "rgba(180,60,40,0.9)",
          1,
          "rgba(139,40,53,1)",
        ],
        "heatmap-radius": [
          "interpolate",
          ["linear"],
          ["zoom"],
          0,
          8,
          9,
          20,
          11,
          40,
          13,
          60,
        ],
        "heatmap-opacity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          HEAT_FADE_START,
          0.9,
          HEAT_FADE_END,
          0.0,
        ],
      },
    },
    beforeLabelLayer,
  );

  // Individual points in heatmap mode
  map.addLayer({
    id: "heatmap-points",
    type: "circle",
    source: HEATMAP_SOURCE_ID,
    minzoom: HEAT_FADE_START,
    paint: {
      "circle-color": [
        "case",
        ["==", ["get", "resolved"], true],
        "#22c55e",
        [
          "match",
          ["get", "severity"],
          "critical",
          severityColors.critical,
          "high",
          severityColors.high,
          "moderate",
          severityColors.moderate,
          "low",
          severityColors.low,
          severityColors.low,
        ],
      ],
      "circle-radius": 7,
      "circle-opacity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        HEAT_FADE_START,
        0,
        HEAT_FADE_END,
        0.95,
      ],
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#0A0E1A",
      "circle-stroke-opacity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        HEAT_FADE_START,
        0,
        HEAT_FADE_END,
        1,
      ],
    },
  });

  map.addLayer({
    id: "heatmap-critical-pulse",
    type: "circle",
    source: HEATMAP_SOURCE_ID,
    minzoom: HEAT_FADE_START,
    filter: [
      "all",
      ["==", ["get", "severity"], "critical"],
      ["!=", ["get", "resolved"], true],
    ],
    paint: {
      "circle-color": severityColors.critical,
      "circle-radius": 12,
      "circle-opacity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        HEAT_FADE_START,
        0,
        HEAT_FADE_END,
        0.4,
      ],
    },
  });

  // Cluster mode — unclustered single points (no donut needed for lone points)
  map.addLayer({
    id: "cluster-single-points",
    type: "circle",
    source: CLUSTERED_SOURCE_ID,
    filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-color": [
        "case",
        ["==", ["get", "resolved"], true],
        "#22c55e",
        [
          "match",
          ["get", "severity"],
          "critical",
          severityColors.critical,
          "high",
          severityColors.high,
          "moderate",
          severityColors.moderate,
          "low",
          severityColors.low,
          severityColors.low,
        ],
      ],
      "circle-radius": 7,
      "circle-opacity": 0.95,
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#0A0E1A",
    },
  });

  // Selection rings
  map.addLayer({
    id: "cluster-selected",
    type: "circle",
    source: CLUSTERED_SOURCE_ID,
    filter: [
      "all",
      ["!", ["has", "point_count"]],
      ["==", ["get", "id"], selectedId ?? ""],
    ],
    paint: {
      "circle-color": "transparent",
      "circle-radius": 14,
      "circle-stroke-color": "#5B8DBF",
      "circle-stroke-width": 2,
      "circle-opacity": 0,
    },
  });

  map.addLayer({
    id: "heatmap-selected",
    type: "circle",
    source: HEATMAP_SOURCE_ID,
    minzoom: HEAT_FADE_START,
    filter: ["==", ["get", "id"], selectedId ?? ""],
    paint: {
      "circle-color": "transparent",
      "circle-radius": 14,
      "circle-stroke-color": "#5B8DBF",
      "circle-stroke-width": 2,
      "circle-opacity": 0,
    },
  });
}

type ViewMode = "cluster" | "heatmap";

// Layers controlled by visibility toggle (HTML markers are shown/hidden separately)
const HEATMAP_LAYERS = [
  "incident-heatmap",
  "heatmap-points",
  "heatmap-critical-pulse",
  "heatmap-selected",
];
const CLUSTER_POINT_LAYERS = ["cluster-single-points", "cluster-selected"];

function applyViewMode(
  map: mapboxgl.Map,
  mode: ViewMode,
  markersOnScreen: Record<number, mapboxgl.Marker>,
) {
  const showCluster = mode === "cluster";

  for (const id of HEATMAP_LAYERS) {
    if (map.getLayer(id))
      map.setLayoutProperty(id, "visibility", showCluster ? "none" : "visible");
  }
  for (const id of CLUSTER_POINT_LAYERS) {
    if (map.getLayer(id))
      map.setLayoutProperty(id, "visibility", showCluster ? "visible" : "none");
  }

  // Show/hide HTML donut markers
  for (const marker of Object.values(markersOnScreen)) {
    const el = marker.getElement();
    el.style.display = showCluster ? "block" : "none";
  }
}

function applySeeingStoneTechTheme(map: mapboxgl.Map) {
  map.setFog({
    range: [0.9, 9],
    color: "#EAF4FF",
    "high-color": "#CFE3F7",
    "space-color": "#F3F9FF",
    "horizon-blend": 0.08,
    "star-intensity": 0,
  });

  if (!map.getSource("mapbox-dem")) {
    map.addSource("mapbox-dem", {
      type: "raster-dem",
      url: "mapbox://mapbox.terrain-rgb",
      tileSize: 512,
      maxzoom: 14,
    });
  }
  map.setTerrain({ source: "mapbox-dem", exaggeration: 1.15 });

  const labelLayerId = map
    .getStyle()
    .layers?.find((l) => l.type === "symbol")?.id;

  if (!map.getLayer("terrain-hillshade")) {
    map.addLayer(
      {
        id: "terrain-hillshade",
        type: "hillshade",
        source: "mapbox-dem",
        paint: {
          "hillshade-shadow-color": "#2F3B4A",
          "hillshade-highlight-color": "#F7FAFF",
          "hillshade-accent-color": "#76859B",
          "hillshade-exaggeration": 0.8,
          "hillshade-illumination-anchor": "map",
          "hillshade-illumination-direction": 315,
        },
      },
      labelLayerId,
    );
  }

  if (map.getLayer("water")) {
    map.setPaintProperty("water", "fill-color", "#9FD3FF");
    map.setPaintProperty("water", "fill-opacity", 0.45);
  }
  if (map.getLayer("water-shadow")) {
    map.setPaintProperty("water-shadow", "fill-color", "#7CB7E8");
  }
  if (map.getLayer("landuse")) {
    map.setPaintProperty("landuse", "fill-color", "#AAB4C2");
    map.setPaintProperty("landuse", "fill-opacity", 0.25);
  }

  if (!map.getLayer("3d-buildings")) {
    map.addLayer(
      {
        id: "3d-buildings",
        source: "composite",
        "source-layer": "building",
        filter: ["==", "extrude", "true"],
        type: "fill-extrusion",
        minzoom: 13,
        paint: {
          "fill-extrusion-color": [
            "interpolate",
            ["linear"],
            ["get", "height"],
            0,
            "#FFE7C2",
            80,
            "#D2E6FF",
            200,
            "#CBBEFF",
          ],
          "fill-extrusion-height": [
            "interpolate",
            ["linear"],
            ["zoom"],
            13,
            0,
            14,
            ["get", "height"],
          ],
          "fill-extrusion-base": [
            "interpolate",
            ["linear"],
            ["zoom"],
            13,
            0,
            14,
            ["get", "min_height"],
          ],
          "fill-extrusion-opacity": 0.82,
        },
      },
      labelLayerId,
    );
  }
}

export function MapView({
  incidents,
  selectedId,
  onSelectIncident,
}: MapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  const selectedIdRef = useRef(selectedId);
  const onSelectIncidentRef = useRef(onSelectIncident);
  const incidentsRef = useRef(incidents);

  // Marker pools for donut clusters
  const markersRef = useRef<Record<number, mapboxgl.Marker>>({});
  const markersOnScreenRef = useRef<Record<number, mapboxgl.Marker>>({});
  const viewModeRef = useRef<ViewMode>("heatmap");

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);
  useEffect(() => {
    onSelectIncidentRef.current = onSelectIncident;
  }, [onSelectIncident]);
  useEffect(() => {
    incidentsRef.current = incidents;
  }, [incidents]);

  const incidentGeoJson = useMemo(
    () => toIncidentGeoJson(incidents),
    [incidents],
  );

  const [pitch, setPitch] = useState(60);
  const [bearing, setBearing] = useState(-18);
  const [viewMode, setViewMode] = useState<ViewMode>("heatmap");

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current || !MAPBOX_ACCESS_TOKEN)
      return;

    mapboxgl.accessToken = MAPBOX_ACCESS_TOKEN;
    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: STOCKHOLM_CENTER,
      zoom: 10.8,
      pitch: 60,
      bearing: -18,
      antialias: true,
      dragPan: true,
      pitchWithRotate: true,
    });

    mapRef.current = map;
    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.dragRotate.enable();
    map.keyboard.enable();
    setPitch(Math.round(map.getPitch()));
    setBearing(Math.round(map.getBearing()));
    map.on("move", () => {
      setPitch(Math.round(map.getPitch()));
      setBearing(Math.round(map.getBearing()));
    });

    const resizeObserver = new ResizeObserver(() => map.resize());
    resizeObserver.observe(mapContainerRef.current!);

    map.on("load", () => {
      const initialGeoJson = toIncidentGeoJson(incidentsRef.current);

      map.addSource(CLUSTERED_SOURCE_ID, {
        type: "geojson",
        data: initialGeoJson,
        cluster: true,
        clusterRadius: 50,
        clusterMaxZoom: 14,
        clusterProperties: {
          critical: [
            "+",
            ["case", ["==", ["get", "severity"], "critical"], 1, 0],
          ],
          high: ["+", ["case", ["==", ["get", "severity"], "high"], 1, 0]],
          moderate: [
            "+",
            ["case", ["==", ["get", "severity"], "moderate"], 1, 0],
          ],
          low: ["+", ["case", ["==", ["get", "severity"], "low"], 1, 0]],
        },
      });

      map.addSource(HEATMAP_SOURCE_ID, {
        type: "geojson",
        data: initialGeoJson,
        cluster: false,
      });

      addNonClusterLayers(map, selectedIdRef.current);
      applySeeingStoneTechTheme(map);
      applyViewMode(map, "heatmap", markersOnScreenRef.current);

      // ── Donut HTML marker management ──────────────────────────────────────
      function updateDonutMarkers() {
        if (viewModeRef.current !== "cluster") return;

        const newMarkers: Record<number, mapboxgl.Marker> = {};
        const features = map.querySourceFeatures(CLUSTERED_SOURCE_ID);

        for (const feature of features) {
          const props = feature.properties as {
            cluster: boolean;
            cluster_id: number;
            point_count: number;
            critical: number;
            high: number;
            moderate: number;
            low: number;
          };
          if (!props.cluster) continue;

          const id = props.cluster_id;
          const coords = (feature.geometry as GeoJSON.Point).coordinates as [
            number,
            number,
          ];

          let marker = markersRef.current[id];
          if (!marker) {
            const el = createDonutMarkerElement(props);
            marker = new mapboxgl.Marker({ element: el }).setLngLat(coords);

            // Click → expand cluster
            el.addEventListener("click", () => {
              const source = map.getSource(
                CLUSTERED_SOURCE_ID,
              ) as GeoJSONSource;
              source.getClusterExpansionZoom(id, (err, zoom) => {
                if (err || typeof zoom !== "number") return;
                map.easeTo({ center: coords, zoom: zoom + 0.5, duration: 800 });
              });
            });

            markersRef.current[id] = marker;
          }

          newMarkers[id] = marker;
          if (!markersOnScreenRef.current[id]) marker.addTo(map);
        }

        // Remove markers no longer on screen
        for (const id in markersOnScreenRef.current) {
          const numId = Number(id);
          if (!newMarkers[numId]) markersOnScreenRef.current[numId].remove();
        }
        markersOnScreenRef.current = newMarkers;
      }

      map.on("render", () => {
        if (!map.isSourceLoaded(CLUSTERED_SOURCE_ID)) return;
        updateDonutMarkers();
      });

      // ── Individual point clicks ───────────────────────────────────────────
      const handlePointClick = (
        event: mapboxgl.MapMouseEvent & {
          features?: mapboxgl.MapboxGeoJSONFeature[];
        },
      ) => {
        const incidentId = event.features?.[0]?.properties?.id;
        if (typeof incidentId === "string")
          onSelectIncidentRef.current(incidentId);
      };

      map.on("click", "cluster-single-points", handlePointClick);
      map.on("click", "heatmap-points", handlePointClick);

      for (const layerId of ["cluster-single-points", "heatmap-points"]) {
        map.on("mouseenter", layerId, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layerId, () => {
          map.getCanvas().style.cursor = "";
        });
      }
    });

    return () => {
      resizeObserver.disconnect();
      // Clean up all markers
      for (const m of Object.values(markersRef.current)) m.remove();
      markersRef.current = {};
      markersOnScreenRef.current = {};
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync both sources
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    for (const sourceId of [CLUSTERED_SOURCE_ID, HEATMAP_SOURCE_ID]) {
      const source = map.getSource(sourceId);
      if (source && "setData" in source)
        (source as GeoJSONSource).setData(incidentGeoJson);
    }
    // Invalidate marker cache so donuts are rebuilt with fresh data
    for (const m of Object.values(markersRef.current)) m.remove();
    markersRef.current = {};
    markersOnScreenRef.current = {};
  }, [incidentGeoJson]);

  // Selection ring + zoom
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (map.getLayer("cluster-selected")) {
      map.setFilter("cluster-selected", [
        "all",
        ["!", ["has", "point_count"]],
        ["==", ["get", "id"], selectedId ?? ""],
      ]);
    }
    if (map.getLayer("heatmap-selected")) {
      map.setFilter("heatmap-selected", [
        "==",
        ["get", "id"],
        selectedId ?? "",
      ]);
    }

    if (selectedId) {
      const incident = incidents.find((i) => i.id === selectedId);
      if (incident) {
        map.easeTo({
          center: [incident.lng, incident.lat],
          zoom: Math.max(map.getZoom(), 14),
          duration: 700,
          pitch: 50,
        });
      }
    }
  }, [selectedId, incidents]);

  // View mode switch
  useEffect(() => {
    viewModeRef.current = viewMode;
    const map = mapRef.current;
    if (!map || !map.getLayer("heatmap-points")) return;
    applyViewMode(map, viewMode, markersOnScreenRef.current);

    // When switching away from cluster mode, remove all donut markers
    if (viewMode !== "cluster") {
      for (const m of Object.values(markersOnScreenRef.current)) m.remove();
      markersOnScreenRef.current = {};
    }
  }, [viewMode]);

  if (!MAPBOX_ACCESS_TOKEN) {
    return (
      <div className="flex-1 bg-[#0a0e1a] border-r border-[#1e2530] flex items-center justify-center p-6">
        <div className="max-w-md bg-[#1a2332]/90 border border-[#2a3441] rounded p-4 text-sm text-[#9ca3af]">
          <p className="text-[#e8eaed] font-medium mb-1">Map unavailable</p>
          <p>
            Set <code>VITE_MAPBOX_ACCESS_TOKEN</code> in the project root{" "}
            <code>.env</code> and restart the UI dev server.
          </p>
        </div>
      </div>
    );
  }

  const handlePitchChange = (nextPitch: number) => {
    const map = mapRef.current;
    setPitch(nextPitch);
    map?.easeTo({ pitch: nextPitch, duration: 200 });
  };

  const handleBearingChange = (nextBearing: number) => {
    const map = mapRef.current;
    setBearing(nextBearing);
    map?.easeTo({ bearing: nextBearing, duration: 200 });
  };

  return (
    <div className="flex-1 bg-[#0a0e1a] relative overflow-hidden [&_.mapboxgl-ctrl]:!hidden">
      <div ref={mapContainerRef} className="w-full h-full" />

      <div className="absolute top-4 right-4 z-10 bg-[#1a2332]/90 border border-[#2a3441] rounded backdrop-blur-sm p-3 w-[230px]">
        <div className="text-[10px] text-[#9ca3af] uppercase tracking-wider mb-2">
          View Controls
        </div>
        <div className="space-y-2">
          <label className="block text-[11px] text-[#9ca3af]">
            Perspective ({pitch}°)
          </label>
          <input
            type="range"
            min={0}
            max={80}
            step={1}
            value={pitch}
            onChange={(e) => handlePitchChange(Number(e.target.value))}
            className="w-full accent-[#5b8dbf]"
          />
          <label className="block text-[11px] text-[#9ca3af]">
            Rotation ({bearing}°)
          </label>
          <input
            type="range"
            min={-180}
            max={180}
            step={1}
            value={bearing}
            onChange={(e) => handleBearingChange(Number(e.target.value))}
            className="w-full accent-[#5b8dbf]"
          />
          <div className="pt-1 border-t border-[#2a3441]">
            <div className="text-[10px] text-[#9ca3af] uppercase tracking-wider mb-1.5">
              Display Mode
            </div>
            <div className="flex rounded overflow-hidden border border-[#2a3441]">
              <button
                onClick={() => setViewMode("heatmap")}
                className={`flex-1 py-1 text-[11px] transition-colors duration-150 ${viewMode === "heatmap" ? "bg-[#5b8dbf] text-white" : "bg-transparent text-[#9ca3af] hover:bg-[#2a3441]"}`}
              >
                Heatmap
              </button>
              <button
                onClick={() => setViewMode("cluster")}
                className={`flex-1 py-1 text-[11px] transition-colors duration-150 ${viewMode === "cluster" ? "bg-[#5b8dbf] text-white" : "bg-transparent text-[#9ca3af] hover:bg-[#2a3441]"}`}
              >
                Clusters
              </button>
            </div>
          </div>
          <p className="text-[10px] text-[#6b7280] leading-snug">
            Drag to pan. Right-click + drag (or Ctrl + drag) to tilt/rotate.
          </p>
        </div>
      </div>

      <div className="absolute bottom-4 left-4 z-10 bg-[#1a2332]/90 border border-[#2a3441] rounded backdrop-blur-sm p-3">
        <div className="text-[10px] text-[#9ca3af] uppercase tracking-wider mb-2">
          Severity
        </div>
        <div className="flex flex-col gap-1.5">
          {Object.entries(severityColors).map(([severity, color]) => (
            <div key={severity} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-[11px] text-[#9ca3af] capitalize">
                {severity}
              </span>
            </div>
          ))}
        </div>
        {viewMode === "heatmap" && (
          <div className="mt-3 pt-2 border-t border-[#2a3441]">
            <div className="text-[10px] text-[#9ca3af] uppercase tracking-wider mb-1.5">
              Density
            </div>
            <div
              className="h-2 w-full rounded-sm"
              style={{
                background:
                  "linear-gradient(to right, rgba(43,60,110,0.5), rgba(90,100,180,0.7), rgba(184,116,26,0.8), rgba(139,40,53,1))",
              }}
            />
            <div className="flex justify-between mt-0.5">
              <span className="text-[9px] text-[#6b7280]">Low</span>
              <span className="text-[9px] text-[#6b7280]">High</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
