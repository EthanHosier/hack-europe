import { forwardRef, useImperativeHandle, useRef, type MouseEvent } from "react";
import { AlertTriangle, ChevronDown, Clock, Flame, Heart, Home, X, Zap } from "lucide-react";

export interface Incident {
  id: string;
  caseId?: string;
  type: "fire" | "medical" | "rescue" | "disaster" | "emergency" | "other";
  description: string;
  region: string;
  severity: "critical" | "high" | "moderate" | "low";
  timestamp: Date;
  status: "unassigned" | "matching" | "assigned" | "completed";
  lat: number;
  lng: number;
}

interface IncidentQueueProps {
  incidents: Incident[];
  selectedId: string | null;
  onSelectIncident: (id: string) => void;
  incidentTypes: Incident["type"][];
  selectedTypes: Incident["type"][];
  incidentTypeCounts: Record<Incident["type"], number>;
  onToggleType: (type: Incident["type"]) => void;
  onSelectAllTypes: () => void;
  onClearAllTypes: () => void;
}

export interface IncidentQueueHandle {
  scrollTo: (id: string) => void;
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
  completed: "COMPLETED",
};

const typeIcons = {
  fire: Flame,
  medical: Heart,
  rescue: AlertTriangle,
  disaster: Home,
  emergency: Zap,
  other: AlertTriangle,
};

export const IncidentQueue = forwardRef<IncidentQueueHandle, IncidentQueueProps>(
  function IncidentQueue({
    incidents,
    selectedId,
    onSelectIncident,
    incidentTypes,
    selectedTypes,
    incidentTypeCounts,
    onToggleType,
    onSelectAllTypes,
    onClearAllTypes,
  }, ref) {
    const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});

    useImperativeHandle(ref, () => ({
      scrollTo(id: string) {
        itemRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      },
    }));

    const getTimeSince = (timestamp: Date) => {
      const now = new Date();
      const diff = now.getTime() - timestamp.getTime();
      const minutes = Math.floor(diff / 60000);
      if (minutes < 1) return "Just now";
      if (minutes < 60) return `${minutes}m ago`;
      const hours = Math.floor(minutes / 60);
      return `${hours}h ago`;
    };

    const handleRemoveTag =
      (type: Incident["type"]) => (event: MouseEvent<HTMLButtonElement>) => {
        event.preventDefault();
        event.stopPropagation();
        onToggleType(type);
      };

    const handleClearAll =
      (event: MouseEvent<HTMLButtonElement>) => {
        event.preventDefault();
        event.stopPropagation();
        onClearAllTypes();
      };

    return (
      <div className="w-[340px] bg-[#0f1419] border-r border-[#1e2530] flex flex-col">
        <div className="h-12 border-b border-[#1e2530] flex items-center px-4">
          <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-medium">
            Live Incidents
          </span>
          <span className="ml-auto text-[12px] text-[#5b8dbf] tabular-nums font-medium">
            {incidents.length}
          </span>
        </div>
        <div className="border-b border-[#1e2530] px-4 py-3 space-y-2">
          <span className="text-[10px] text-[#6b7280] uppercase tracking-wider">
            Filter
          </span>
          <details className="group relative">
            <summary className="list-none cursor-pointer rounded border border-[#2a3340] bg-[#141825] px-2 py-2 text-[11px] text-[#c5cad3]">
              <div className="flex items-center gap-2">
                <div className="flex flex-1 flex-wrap gap-1.5">
                  {selectedTypes.length === 0 ? (
                    <span className="text-[#6b7280]">No types selected</span>
                  ) : (
                    selectedTypes.map((type) => (
                      <span
                        key={type}
                        className="inline-flex items-center gap-1 rounded-full border border-[#3a4556] bg-[#1a2332] pl-2 pr-1 py-0.5 text-[10px] capitalize text-[#cfd8e3]"
                      >
                        {type}
                        <button
                          type="button"
                          onClick={handleRemoveTag(type)}
                          className="rounded-full p-0.5 text-[#9aa6b5] hover:bg-[#273449] hover:text-[#d9e2ec]"
                          aria-label={`Remove ${type} filter`}
                        >
                          <X className="h-2.5 w-2.5" />
                        </button>
                      </span>
                    ))
                  )}
                </div>
                {selectedTypes.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClearAll}
                    className="rounded-full p-1 text-[#8e9bad] hover:bg-[#273449] hover:text-[#d9e2ec]"
                    aria-label="Clear all selected types"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
                <ChevronDown className="h-3.5 w-3.5 text-[#7b8798] transition-transform group-open:rotate-180" />
              </div>
            </summary>
            <div className="absolute left-0 top-[calc(100%+6px)] z-20 w-full rounded border border-[#2a3340] bg-[#101723] p-2 shadow-lg">
              <div className="mb-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onSelectAllTypes}
                  className="text-[10px] uppercase tracking-wider text-[#5b8dbf] hover:text-[#7ea8d1]"
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={onClearAllTypes}
                  className="text-[10px] uppercase tracking-wider text-[#6b7280] hover:text-[#9ca3af]"
                >
                  None
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {incidentTypes.map((type) => {
                  const isSelected = selectedTypes.includes(type);
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => onToggleType(type)}
                      className={`
                      rounded-full border px-2 py-1 text-[10px] capitalize transition-colors
                      ${isSelected
                          ? "border-[#5b8dbf] bg-[#1a2a40] text-[#d6e6f6]"
                          : "border-[#3a4556] bg-[#141d2a] text-[#9ca3af] hover:border-[#5b8dbf] hover:text-[#cfd8e3]"
                        }
                    `}
                    >
                      {type} ({incidentTypeCounts[type] ?? 0})
                    </button>
                  );
                })}
              </div>
            </div>
          </details>
        </div>

        <div className="flex-1 overflow-y-auto">
          {incidents.map((incident) => {
            const Icon = typeIcons[incident.type];
            const isSelected = incident.id === selectedId;
            const isCompleted = incident.status === "completed";

            return (
              <div
                key={incident.id}
                ref={(el) => { itemRefs.current[incident.id] = el; }}
                onClick={() => onSelectIncident(incident.id)}
                className={`
                px-4 py-3 border-b border-[#1e2530] cursor-pointer transition-colors
                ${isSelected
                    ? "bg-[#1a2332] border-l-2 border-l-[#5b8dbf]"
                    : "hover:bg-[#141825]"
                  }
                ${isCompleted ? "opacity-60" : ""}
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
                      <p className={`text-[13px] leading-tight ${isCompleted ? "text-[#9ca3af]" : "text-[#e8eaed]"}`}>
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
                        className="text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider font-medium"
                        style={{
                          backgroundColor: `${severityColors[incident.severity]
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
  });
