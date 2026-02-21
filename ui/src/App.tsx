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

const incidentTypeByCategory: Record<string, Incident["type"]> = {
  medical: "medical",
  rescue: "rescue",
  disaster: "disaster",
  fire: "fire",
  fuel: "emergency",
  shelter: "emergency",
  food_water: "emergency",
  other: "emergency",
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
    type: incidentTypeByCategory[event.case_category ?? "other"] ?? "emergency",
    description: event.description || event.case_title || "Emergency event",
    region: event.case_title || "Unknown region",
    severity: toIncidentSeverity(event.case_severity),
    status: toIncidentStatus(event.case_status),
    timestamp: Number.isNaN(parsedTimestamp.getTime())
      ? new Date()
      : parsedTimestamp,
    lat: event.latitude,
    lng: event.longitude,
  };
}

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
  },
  {
    id: "r2",
    name: "Johan Bergström",
    role: "Emergency Medical Technician",
    distance: 3.7,
    availability: "available" as const,
    verificationLevel: "verified" as const,
    skills: ["BLS", "CPR", "First Aid"],
  },
  {
    id: "r3",
    name: "Sofia Lindqvist",
    role: "Critical Care Specialist",
    distance: 4.1,
    availability: "on-call" as const,
    verificationLevel: "verified" as const,
    skills: ["ALS", "Pediatric", "ICU"],
  },
  {
    id: "r4",
    name: "Marcus Johansson",
    role: "Paramedic Unit Lead",
    distance: 5.2,
    availability: "available" as const,
    verificationLevel: "verified" as const,
    skills: ["ALS", "Command", "Triage"],
  },
  {
    id: "r5",
    name: "Anna Karlsson",
    role: "Emergency Medical Technician",
    distance: 6.8,
    availability: "busy" as const,
    verificationLevel: "verified" as const,
    skills: ["BLS", "Transport"],
  },
  {
    id: "r6",
    name: "Erik Nilsson",
    role: "Advanced Paramedic",
    distance: 7.3,
    availability: "available" as const,
    verificationLevel: "pending" as const,
    skills: ["ALS", "Airway", "Cardiac"],
  },
];

export default function App() {
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    null,
  );
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
  const queueRef = useRef<IncidentQueueHandle>(null);

  const handleMapSelect = (id: string) => {
    setSelectedIncidentId(id);
    queueRef.current?.scrollTo(id);
  };

  const handleDispatch = (responderId: string, incidentId: string) => {
    // TODO: trigger API call to dispatch responder to incident - update state in BE
    console.log(
      `Dispatching responder ${responderId} to incident ${incidentId}`,
    );
  };

  useEffect(() => {
    if (incidents.length === 0) {
      setSelectedIncidentId(null);
      return;
    }

    const hasSelectedIncident = selectedIncidentId
      ? incidents.some((incident) => incident.id === selectedIncidentId)
      : false;
    if (hasSelectedIncident) return;

    const severityRank: Record<Incident["severity"], number> = {
      critical: 4,
      high: 3,
      moderate: 2,
      low: 1,
    };
    const fallback = [...incidents].sort((a, b) => {
      const severityDiff = severityRank[b.severity] - severityRank[a.severity];
      if (severityDiff !== 0) return severityDiff;
      return b.timestamp.getTime() - a.timestamp.getTime();
    })[0];

    setSelectedIncidentId(fallback?.id ?? null);
  }, [incidents, selectedIncidentId]);

  const selectedIncident =
    incidents.find((incident) => incident.id === selectedIncidentId) || null;

  return (
    <div className="size-full flex flex-col bg-[#0a0e1a] text-[#e8eaed]">
      <TopBar
        activeIncidents={incidents.length}
        activeResponders={
          mockResponders.filter((r) => r.availability === "available").length
        }
        regionsMonitored={1}
      />

      <div className="flex-1 flex overflow-hidden">
        <IncidentQueue
          incidents={incidents}
          selectedId={selectedIncidentId}
          onSelectIncident={setSelectedIncidentId}
        />

        <MapView
          incidents={incidents}
          selectedId={selectedIncidentId}
          onSelectIncident={handleMapSelect}
        />

        <IntelligencePanel
          selectedIncident={selectedIncident}
          responders={mockResponders}
          onDispatch={handleDispatch}
        />
      </div>
    </div>
  );
}
