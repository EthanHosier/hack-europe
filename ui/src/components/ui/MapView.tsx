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

const MAPBOX_ACCESS_TOKEN = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN ?? "";
const INCIDENT_SOURCE_ID = "incidents";
const STOCKHOLM_CENTER: [number, number] = [18.0686, 59.3293];

function toIncidentGeoJson(
  incidents: Incident[],
): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: "FeatureCollection",
    features: incidents.map((incident) => ({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [incident.lng, incident.lat],
      },
      properties: {
        id: incident.id,
        severity: incident.severity,
      },
    })),
  };
}

function addIncidentLayers(map: mapboxgl.Map, selectedId: string | null) {
  if (!map.getSource(INCIDENT_SOURCE_ID)) return;

  map.addLayer({
    id: "incident-clusters",
    type: "circle",
    source: INCIDENT_SOURCE_ID,
    filter: ["has", "point_count"],
    paint: {
      "circle-color": [
        "case",
        [">", ["coalesce", ["get", "critical"], 0], 0],
        severityColors.critical,
        [">", ["coalesce", ["get", "high"], 0], 0],
        severityColors.high,
        [">", ["coalesce", ["get", "moderate"], 0], 0],
        severityColors.moderate,
        severityColors.low,
      ],
      "circle-radius": ["step", ["get", "point_count"], 18, 10, 22, 25, 28],
      "circle-opacity": 0.9,
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#0A0E1A",
    },
  });

  map.addLayer({
    id: "incident-cluster-count",
    type: "symbol",
    source: INCIDENT_SOURCE_ID,
    filter: ["has", "point_count"],
    layout: {
      "text-field": ["get", "point_count_abbreviated"],
      "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
      "text-size": 12,
    },
    paint: {
      "text-color": "#E8EAED",
    },
  });

  map.addLayer({
    id: "incident-points",
    type: "circle",
    source: INCIDENT_SOURCE_ID,
    filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-color": [
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
      "circle-radius": 7,
      "circle-opacity": 0.95,
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#0A0E1A",
    },
  });

  map.addLayer({
    id: "incident-selected",
    type: "circle",
    source: INCIDENT_SOURCE_ID,
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
      "circle-opacity": 0.9,
    },
  });
}

function applyPalantirVibe(map: mapboxgl.Map) {
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
    .layers?.find((layer) => layer.type === "symbol")?.id;

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
  const incidentGeoJson = useMemo(
    () => toIncidentGeoJson(incidents),
    [incidents],
  );
  const [pitch, setPitch] = useState(60);
  const [bearing, setBearing] = useState(-18);

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

    map.on("load", () => {
      map.addSource(INCIDENT_SOURCE_ID, {
        type: "geojson",
        data: incidentGeoJson,
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

      addIncidentLayers(map, selectedId);
      applyPalantirVibe(map);

      map.on("click", "incident-clusters", (event) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const source = map.getSource(INCIDENT_SOURCE_ID) as
          | GeoJSONSource
          | undefined;
        const clusterId = feature.properties?.cluster_id;
        if (!source || typeof clusterId !== "number") return;

        source.getClusterExpansionZoom(clusterId, (error, zoom) => {
          if (error || typeof zoom !== "number") return;
          const geometry = feature.geometry as GeoJSON.Point;
          map.easeTo({
            center: geometry.coordinates as [number, number],
            zoom,
          });
        });
      });

      map.on("click", "incident-points", (event) => {
        const feature = event.features?.[0];
        const incidentId = feature?.properties?.id;
        if (typeof incidentId === "string") {
          onSelectIncident(incidentId);
        }
      });

      map.on("mouseenter", "incident-clusters", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "incident-clusters", () => {
        map.getCanvas().style.cursor = "";
      });
      map.on("mouseenter", "incident-points", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "incident-points", () => {
        map.getCanvas().style.cursor = "";
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [incidentGeoJson, onSelectIncident, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const source = map.getSource(INCIDENT_SOURCE_ID);
    if (source && "setData" in source) {
      (source as GeoJSONSource).setData(incidentGeoJson);
    }
  }, [incidentGeoJson]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("incident-selected")) return;

    map.setFilter("incident-selected", [
      "all",
      ["!", ["has", "point_count"]],
      ["==", ["get", "id"], selectedId ?? ""],
    ]);
  }, [selectedId]);

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
    <div className="flex-1 bg-[#0a0e1a] relative overflow-hidden">
      {/* Map location label */}
      <div className="absolute top-4 left-4 z-10 px-3 py-1.5 bg-[#1a2332]/90 border border-[#2a3441] rounded backdrop-blur-sm">
        <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider">
          Stockholm Region • Sweden
        </span>
      </div>

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
            onChange={(event) => handlePitchChange(Number(event.target.value))}
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
            onChange={(event) =>
              handleBearingChange(Number(event.target.value))
            }
            className="w-full accent-[#5b8dbf]"
          />
          <p className="text-[10px] text-[#6b7280] leading-snug">
            Drag to pan. Right-click + drag (or Ctrl + drag) to tilt/rotate.
          </p>
        </div>
      </div>

      {/* Map legend */}
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
      </div>
    </div>
  );
}
