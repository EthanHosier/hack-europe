import { useEffect, useMemo, useRef, useState } from "react";
import { TopBar } from "@/components/ui/TopBar";
import { IncidentQueue } from "@/components/ui/IncidentQueue";
import type {
  Incident,
  IncidentQueueHandle,
} from "@/components/ui/IncidentQueue";
import { MapView } from "@/components/ui/MapView";
import { IntelligencePanel } from "@/components/ui/IntelligencePanel";
import { useGetLiveEventsEventsLiveGet } from "@/api/generated/endpoints";
import type { LiveEventResponse } from "@/api/generated/schemas";
import { useCompleteCase } from "@/lib/useCompleteCase";
// import { generateTestIncidents } from "./test/generatePoints";

const ALL_INCIDENT_TYPES: Incident["type"][] = [
  "fire",
  "medical",
  "rescue",
  "disaster",
  "emergency",
  "other",
];

const incidentTypeByCategory: Record<string, Incident["type"]> = {
  medical: "medical",
  rescue: "rescue",
  disaster: "disaster",
  fire: "fire",
  fuel: "emergency",
  shelter: "emergency",
  food_water: "emergency",
  other: "other",
};

function toIncidentSeverity(caseSeverity: number): Incident["severity"] {
  if (caseSeverity >= 5) return "critical";
  if (caseSeverity >= 4) return "high";
  if (caseSeverity >= 3) return "moderate";
  return "low";
}

function toIncidentStatus(caseStatus: string): Incident["status"] {
  const normalized = caseStatus.toLowerCase();
  if (normalized.includes("progress")) return "matching";
  if (normalized.includes("resolved") || normalized.includes("closed")) {
    return "assigned";
  }
  return "unassigned";
}

function toIncident(event: LiveEventResponse): Incident {
  const parsedTimestamp = new Date(event.timestamp);
  return {
    id: event.event_id,
    type: incidentTypeByCategory[event.case_category ?? "other"] ?? "other",
    description: event.description || event.case_title || "Emergency event",
    region: event.case_title || "Unknown region",
    severity: toIncidentSeverity(event.case_severity),
    status: toIncidentStatus(event.case_status),
    timestamp: Number.isNaN(parsedTimestamp.getTime())
      ? new Date()
      : parsedTimestamp,
    lat: event.latitude,
    lng: event.longitude,
    completedAt: event.completed_at ? new Date(event.completed_at) : null,
    p2p: event.p2p ?? false,
    confidence: event.confidence ?? null,
    requiredCapability: event.required_capability ?? null,
    parsedNeedType: event.parsed_need_type ?? null,
    recommendedAction: event.recommended_action ?? null,
  };
}

// const mockIncidents = generateTestIncidents(800);

// Mock responder data
const mockResponders = [
  {
    id: "r1",
    name: "Dr. Emma Andersson",
    role: "Advanced Life Support Paramedic",
    distance: 2.3,
    availability: "available" as const,
    verificationLevel: "verified" as const,
    skills: ["ALS", "Cardiac", "Trauma"],
    lat: 59.342,
    lng: 18.045,
  },
  {
    id: "r2",
    name: "Johan Bergström",
    role: "Emergency Medical Technician",
    distance: 3.7,
    availability: "available" as const,
    verificationLevel: "verified" as const,
    skills: ["BLS", "CPR", "First Aid"],
    lat: 59.318,
    lng: 18.092,
  },
  {
    id: "r3",
    name: "Sofia Lindqvist",
    role: "Critical Care Specialist",
    distance: 4.1,
    availability: "on-call" as const,
    verificationLevel: "verified" as const,
    skills: ["ALS", "Pediatric", "ICU"],
    lat: 59.305,
    lng: 18.068,
  },
  {
    id: "r4",
    name: "Marcus Johansson",
    role: "Paramedic Unit Lead",
    distance: 5.2,
    availability: "available" as const,
    verificationLevel: "verified" as const,
    skills: ["ALS", "Command", "Triage"],
    lat: 59.337,
    lng: 18.022,
  },
  {
    id: "r5",
    name: "Anna Karlsson",
    role: "Emergency Medical Technician",
    distance: 6.8,
    availability: "busy" as const,
    verificationLevel: "verified" as const,
    skills: ["BLS", "Transport"],
    lat: 59.35,
    lng: 18.11,
  },
  {
    id: "r6",
    name: "Erik Nilsson",
    role: "Advanced Paramedic",
    distance: 7.3,
    availability: "available" as const,
    verificationLevel: "pending" as const,
    skills: ["ALS", "Airway", "Cardiac"],
    lat: 59.298,
    lng: 18.075,
  },
];

export default function App() {
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    null,
  );
  const [selectedTypes, setSelectedTypes] = useState<Incident["type"][]>([]);
  const [queueViewMode, setQueueViewMode] = useState<"active" | "historical">(
    "active",
  );
  const [dispatchedByIncident, setDispatchedByIncident] = useState<
    Record<string, string[]>
  >({});

  const { completeCase, isResolving } = useCompleteCase();

  const { data: liveEventsResponse } = useGetLiveEventsEventsLiveGet(
    { limit: 300 },
    {
      query: {
        refetchInterval: 5000,
        refetchIntervalInBackground: true,
      },
    },
  );
  const liveEvents = liveEventsResponse?.data ?? [];
  const incidents = useMemo<Incident[]>(
    () => liveEvents.map(toIncident),
    [liveEvents],
  );
  // const incidents = mockIncidents;
  const filteredIncidents = useMemo(
    () =>
      selectedTypes.length === 0
        ? incidents
        : incidents.filter((incident) => selectedTypes.includes(incident.type)),
    [incidents, selectedTypes],
  );
  const mapIncidents = useMemo(
    () =>
      queueViewMode === "active"
        ? filteredIncidents.filter(
            (i) => i.completedAt === null && i.status !== "assigned",
          )
        : filteredIncidents.filter(
            (i) => i.completedAt !== null || i.status === "assigned",
          ),
    [filteredIncidents, queueViewMode],
  );

  const incidentTypeCounts = useMemo<Record<Incident["type"], number>>(
    () =>
      incidents.reduce(
        (acc, incident) => {
          acc[incident.type] += 1;
          return acc;
        },
        {
          fire: 0,
          medical: 0,
          rescue: 0,
          disaster: 0,
          emergency: 0,
          other: 0,
        },
      ),
    [incidents],
  );
  const queueRef = useRef<IncidentQueueHandle>(null);

  const handleMapSelect = (id: string) => {
    setSelectedIncidentId(id);
    queueRef.current?.scrollTo(id);
  };

  const handleMarkResolved = (incidentId: string) => {
    const caseId = liveEvents.find((ev) => ev.event_id === incidentId)?.case_id;
    if (!caseId) return;
    completeCase({ caseId });
  };

  const handleDispatch = (responderId: string, incidentId: string) => {
    // Match the 1500ms animation delay in IntelligencePanel
    setTimeout(() => {
      setDispatchedByIncident((prev) => ({
        ...prev,
        [incidentId]: [...(prev[incidentId] ?? []), responderId],
      }));
    }, 1500);
  };

  const dispatchedResponders = useMemo(() => {
    if (!selectedIncidentId) return [];
    const ids = dispatchedByIncident[selectedIncidentId] ?? [];
    return mockResponders
      .filter((r) => ids.includes(r.id))
      .map((r) => ({ id: r.id, lat: r.lat, lng: r.lng }));
  }, [selectedIncidentId, dispatchedByIncident]);

  const handleToggleType = (type: Incident["type"]) => {
    setSelectedTypes((prev) =>
      prev.includes(type)
        ? prev.filter((item) => item !== type)
        : [...prev, type],
    );
  };

  const handleClearAllTypes = () => {
    setSelectedTypes([]);
  };

  useEffect(() => {
    if (filteredIncidents.length === 0) {
      setSelectedIncidentId(null);
      return;
    }

    const hasSelectedIncident = selectedIncidentId
      ? filteredIncidents.some((incident) => incident.id === selectedIncidentId)
      : false;
    if (hasSelectedIncident) return;

    const severityRank: Record<Incident["severity"], number> = {
      critical: 4,
      high: 3,
      moderate: 2,
      low: 1,
    };
    const fallback = [...filteredIncidents].sort((a, b) => {
      const severityDiff = severityRank[b.severity] - severityRank[a.severity];
      if (severityDiff !== 0) return severityDiff;
      return b.timestamp.getTime() - a.timestamp.getTime();
    })[0];

    setSelectedIncidentId(fallback?.id ?? null);
  }, [filteredIncidents, selectedIncidentId]);

  const selectedIncident =
    filteredIncidents.find((incident) => incident.id === selectedIncidentId) ||
    null;

  return (
    <div className="size-full flex flex-col bg-[#0a0e1a] text-[#e8eaed]">
      <TopBar
        activeIncidents={
          filteredIncidents.filter((i) => i.completedAt === null).length
        }
        activeResponders={
          mockResponders.filter((r) => r.availability === "available").length
        }
      />

      <div className="flex-1 flex overflow-hidden">
        <IncidentQueue
          ref={queueRef}
          incidents={filteredIncidents}
          selectedId={selectedIncidentId}
          onSelectIncident={setSelectedIncidentId}
          incidentTypes={ALL_INCIDENT_TYPES}
          selectedTypes={selectedTypes}
          incidentTypeCounts={incidentTypeCounts}
          onToggleType={handleToggleType}
          onClearAllTypes={handleClearAllTypes}
          viewMode={queueViewMode}
          onViewModeChange={setQueueViewMode}
        />

        <MapView
          incidents={mapIncidents}
          selectedId={selectedIncidentId}
          onSelectIncident={handleMapSelect}
          dispatchedResponders={dispatchedResponders}
        />

        <IntelligencePanel
          selectedIncident={selectedIncident}
          responders={mockResponders}
          onDispatch={handleDispatch}
          onMarkResolved={handleMarkResolved}
          isResolving={isResolving}
        />
      </div>
    </div>
  );
}
