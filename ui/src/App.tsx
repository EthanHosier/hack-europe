import { useState } from "react";
import { TopBar } from "@/components/ui/TopBar";
import { IncidentQueue } from "@/components/ui/IncidentQueue";
import type { Incident } from "@/components/ui/IncidentQueue";
import { MapView } from "@/components/ui/MapView";
import { IntelligencePanel } from "@/components/ui/IntelligencePanel";
import { SimpleChat } from "@/components/SimpleChat";

// Mock incident data
const mockIncidents: Incident[] = [
  {
    id: "1",
    type: "medical",
    description: "Cardiac arrest reported, patient unconscious",
    region: "Stockholm Central",
    severity: "critical",
    timestamp: new Date(Date.now() - 5 * 60000),
    status: "matching",
    lat: 59.3293,
    lng: 18.0686,
  },
  {
    id: "2",
    type: "fire",
    description: "Structure fire in residential building",
    region: "Södermalm",
    severity: "critical",
    timestamp: new Date(Date.now() - 12 * 60000),
    status: "assigned",
    lat: 59.3167,
    lng: 18.0667,
  },
  {
    id: "3",
    type: "rescue",
    description: "Vehicle accident, multiple casualties",
    region: "E4 Highway North",
    severity: "high",
    timestamp: new Date(Date.now() - 18 * 60000),
    status: "matching",
    lat: 59.35,
    lng: 18.05,
  },
  {
    id: "4",
    type: "medical",
    description: "Respiratory distress, elderly patient",
    region: "Kungsholmen",
    severity: "high",
    timestamp: new Date(Date.now() - 25 * 60000),
    status: "unassigned",
    lat: 59.33,
    lng: 18.04,
  },
  {
    id: "5",
    type: "emergency",
    description: "Severe allergic reaction, anaphylaxis",
    region: "Östermalm",
    severity: "critical",
    timestamp: new Date(Date.now() - 8 * 60000),
    status: "matching",
    lat: 59.34,
    lng: 18.085,
  },
  {
    id: "6",
    type: "rescue",
    description: "Water rescue needed, person in distress",
    region: "Djurgården",
    severity: "high",
    timestamp: new Date(Date.now() - 15 * 60000),
    status: "assigned",
    lat: 59.325,
    lng: 18.115,
  },
  {
    id: "7",
    type: "medical",
    description: "Fall injury, possible fracture",
    region: "Vasastan",
    severity: "moderate",
    timestamp: new Date(Date.now() - 30 * 60000),
    status: "unassigned",
    lat: 59.345,
    lng: 18.055,
  },
  {
    id: "8",
    type: "fire",
    description: "Small kitchen fire, smoke reported",
    region: "Solna",
    severity: "moderate",
    timestamp: new Date(Date.now() - 35 * 60000),
    status: "assigned",
    lat: 59.36,
    lng: 18.0,
  },
  {
    id: "9",
    type: "emergency",
    description: "Gas leak reported in apartment complex",
    region: "Hägersten",
    severity: "high",
    timestamp: new Date(Date.now() - 20 * 60000),
    status: "matching",
    lat: 59.3,
    lng: 18.0,
  },
  {
    id: "10",
    type: "medical",
    description: "Diabetic emergency, low blood sugar",
    region: "Bromma",
    severity: "moderate",
    timestamp: new Date(Date.now() - 40 * 60000),
    status: "unassigned",
    lat: 59.34,
    lng: 17.95,
  },
  {
    id: "11",
    type: "disaster",
    description: "Building evacuation, structural concern",
    region: "Lidingö",
    severity: "high",
    timestamp: new Date(Date.now() - 28 * 60000),
    status: "matching",
    lat: 59.3667,
    lng: 18.1333,
  },
  {
    id: "12",
    type: "rescue",
    description: "Person trapped in elevator",
    region: "Huddinge",
    severity: "low",
    timestamp: new Date(Date.now() - 45 * 60000),
    status: "assigned",
    lat: 59.2369,
    lng: 17.9819,
  },
];

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
    mockIncidents[0].id
  );

  const handleDispatch = (responderId: string, incidentId: string) => {
    // TODO: trigger API call to dispatch responder to incident - update state in BE
    console.log(
      `Dispatching responder ${responderId} to incident ${incidentId}`
    );
  };

  const selectedIncident =
    mockIncidents.find((i) => i.id === selectedIncidentId) || null;

  return (
    <div className="size-full flex flex-col bg-[#0a0e1a] text-[#e8eaed]">
      <TopBar
        activeIncidents={mockIncidents.length}
        activeResponders={
          mockResponders.filter((r) => r.availability === "available").length
        }
        regionsMonitored={12}
      />

      <div className="flex-1 flex overflow-hidden">
        <IncidentQueue
          incidents={mockIncidents}
          selectedId={selectedIncidentId}
          onSelectIncident={setSelectedIncidentId}
        />

        <MapView
          incidents={mockIncidents}
          selectedId={selectedIncidentId}
          onSelectIncident={setSelectedIncidentId}
        />

        <IntelligencePanel
          selectedIncident={selectedIncident}
          responders={mockResponders}
          onDispatch={handleDispatch}
        />
      </div>
      <SimpleChat />
    </div>
  );
}
