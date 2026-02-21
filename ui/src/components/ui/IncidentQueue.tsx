import { AlertTriangle, Flame, Heart, Home, Zap, Clock } from "lucide-react";

export interface Incident {
  id: string;
  type: "fire" | "medical" | "rescue" | "disaster" | "emergency";
  description: string;
  region: string;
  severity: "critical" | "high" | "moderate" | "low";
  timestamp: Date;
  status: "unassigned" | "matching" | "assigned";
  lat: number;
  lng: number;
}

interface IncidentQueueProps {
  incidents: Incident[];
  selectedId: string | null;
  onSelectIncident: (id: string) => void;
}

const severityColors = {
  critical: "#8B2835",
  high: "#B8741A",
  moderate: "#3B5B8C",
  low: "#4A4A5A",
};

const severityLabels = {
  critical: "CRITICAL",
  high: "HIGH",
  moderate: "MODERATE",
  low: "LOW",
};

const statusLabels = {
  unassigned: "UNASSIGNED",
  matching: "MATCHING",
  assigned: "ASSIGNED",
};

const typeIcons = {
  fire: Flame,
  medical: Heart,
  rescue: AlertTriangle,
  disaster: Home,
  emergency: Zap,
};

export function IncidentQueue({
  incidents,
  selectedId,
  onSelectIncident,
}: IncidentQueueProps) {
  const getTimeSince = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  return (
    <div className="w-[340px] bg-[#0f1419] border-r border-[#1e2530] flex flex-col">
      <div className="h-12 border-b border-[#1e2530] flex items-center px-4">
        <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500]">
          Live Incidents
        </span>
        <span className="ml-auto text-[12px] text-[#5b8dbf] tabular-nums font-[500]">
          {incidents.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {incidents.map((incident) => {
          const Icon = typeIcons[incident.type];
          const isSelected = incident.id === selectedId;

          return (
            <div
              key={incident.id}
              onClick={() => onSelectIncident(incident.id)}
              className={`
                px-4 py-3 border-b border-[#1e2530] cursor-pointer transition-colors
                ${
                  isSelected
                    ? "bg-[#1a2332] border-l-2 border-l-[#5b8dbf]"
                    : "hover:bg-[#141825]"
                }
              `}
            >
              <div className="flex items-start gap-3">
                <div
                  className="w-8 h-8 rounded flex items-center justify-center mt-0.5"
                  style={{
                    backgroundColor: `${severityColors[incident.severity]}15`,
                  }}
                >
                  <Icon
                    className="w-4 h-4"
                    style={{ color: severityColors[incident.severity] }}
                  />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="text-[13px] text-[#e8eaed] leading-tight">
                      {incident.description}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[11px] text-[#6b7280]">
                      {incident.region}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider font-[500]"
                      style={{
                        backgroundColor: `${
                          severityColors[incident.severity]
                        }20`,
                        color: severityColors[incident.severity],
                      }}
                    >
                      {severityLabels[incident.severity]}
                    </span>

                    <span className="text-[10px] text-[#6b7280] uppercase tracking-wider">
                      {statusLabels[incident.status]}
                    </span>

                    <span className="ml-auto flex items-center gap-1 text-[10px] text-[#6b7280]">
                      <Clock className="w-3 h-3" />
                      {getTimeSince(incident.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
