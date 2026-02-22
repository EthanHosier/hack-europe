import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
} from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Flame,
  Heart,
  History,
  Home,
  Users,
  X,
  Zap,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Incident {
  id: string;
  type: "fire" | "medical" | "rescue" | "disaster" | "emergency" | "other";
  description: string;
  region: string;
  severity: "critical" | "high" | "moderate" | "low";
  timestamp: Date;
  status: "unassigned" | "matching" | "assigned";
  lat: number;
  lng: number;
  completedAt: Date | null; // from doc13
}

interface IncidentQueueProps {
  incidents: Incident[];
  selectedId: string | null;
  onSelectIncident: (id: string) => void;
  incidentTypes: Incident["type"][];
  selectedTypes: Incident["type"][];
  incidentTypeCounts: Record<Incident["type"], number>;
  onToggleType: (type: Incident["type"]) => void;
  onClearAllTypes: () => void;
}

export interface IncidentQueueHandle {
  scrollTo: (id: string) => void;
}

// ─── Constants & lookups ──────────────────────────────────────────────────────

const RECENT_DEFAULT_LIMIT = 3;

const severityRank: Record<Incident["severity"], number> = {
  critical: 4,
  high: 3,
  moderate: 2,
  low: 1,
};

const severityColors: Record<Incident["severity"], string> = {
  critical: "#8B2835",
  high: "#B8741A",
  moderate: "#3B5B8C",
  low: "#4A4A5A",
};

const severityLabels: Record<Incident["severity"], string> = {
  critical: "CRITICAL",
  high: "HIGH",
  moderate: "MODERATE",
  low: "LOW",
};

const statusLabels: Record<Incident["status"], string> = {
  unassigned: "UNASSIGNED",
  matching: "MATCHING",
  assigned: "RESOLVED",
};

const typeIcons: Record<Incident["type"], React.ElementType> = {
  fire: Flame,
  medical: Heart,
  rescue: AlertTriangle,
  disaster: Home, // fixed "di1saster" typo from doc14
  emergency: Zap,
  other: AlertTriangle,
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sortBySeverityThenTime(list: Incident[]): Incident[] {
  return [...list].sort((a, b) => {
    const d = severityRank[b.severity] - severityRank[a.severity];
    return d !== 0 ? d : b.timestamp.getTime() - a.timestamp.getTime();
  });
}

function getTimeSince(ts: Date): string {
  const diff = Date.now() - ts.getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─── IncidentCard (from doc13) ────────────────────────────────────────────────

function IncidentCard({
  incident,
  isSelected,
  isFlashing,
  onClick,
  itemRef,
  completed = false,
}: {
  incident: Incident;
  isSelected: boolean;
  isFlashing?: boolean;
  onClick: () => void;
  itemRef?: (el: HTMLDivElement | null) => void;
  completed?: boolean;
}) {
  const Icon = typeIcons[incident.type];

  let bgClass: string;
  if (isSelected) bgClass = "bg-[#1a2332] border-l-2 border-l-[#5b8dbf]";
  else if (isFlashing) bgClass = "bg-[#1d3148]";
  else bgClass = "hover:bg-[#141825]";

  return (
    <div
      ref={itemRef}
      onClick={onClick}
      className={`px-4 py-3 border-b border-[#1e2530] cursor-pointer transition-colors duration-500 ${completed ? "opacity-60" : ""} ${bgClass}`}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-8 h-8 rounded flex items-center justify-center mt-0.5 shrink-0"
          style={{
            backgroundColor: completed
              ? "#22c55e15"
              : `${severityColors[incident.severity]}18`,
          }}
        >
          {completed ? (
            <CheckCircle2 className="w-4 h-4 text-[#22c55e]" />
          ) : (
            <Icon
              className="w-4 h-4"
              style={{ color: severityColors[incident.severity] }}
            />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-[13px] text-[#e8eaed] leading-tight line-clamp-2 mb-1">
            {incident.description}
          </p>
          <p className="text-[11px] text-[#6b7280] truncate mb-2">
            {incident.region}
          </p>

          <div className="flex items-center gap-2 flex-wrap">
            {completed ? (
              <span className="text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider font-medium bg-[#22c55e20] text-[#22c55e]">
                RESOLVED
              </span>
            ) : (
              <>
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider font-[500]"
                  style={{
                    backgroundColor: `${severityColors[incident.severity]}22`,
                    color: severityColors[incident.severity],
                  }}
                >
                  {severityLabels[incident.severity]}
                </span>
                <span className="text-[10px] text-[#6b7280] uppercase tracking-wider">
                  {statusLabels[incident.status]}
                </span>
              </>
            )}

            <span className="ml-auto flex items-center gap-1 text-[10px] text-[#6b7280]">
              <Clock className="w-3 h-3" />
              {completed && incident.completedAt
                ? getTimeSince(incident.completedAt)
                : getTimeSince(incident.timestamp)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export const IncidentQueue = forwardRef<
  IncidentQueueHandle,
  IncidentQueueProps
>(function IncidentQueue(
  {
    incidents,
    selectedId,
    onSelectIncident,
    incidentTypes,
    selectedTypes,
    incidentTypeCounts,
    onToggleType,
    onClearAllTypes,
  },
  ref,
) {
  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const [showP2P, setShowP2P] = useState(false);
  const [viewMode, setViewMode] = useState<"active" | "historical">("active");
  const [recentExpanded, setRecentExpanded] = useState(false);
  const [flashId, setFlashId] = useState<string | null>(null);

  useImperativeHandle(ref, () => ({
    scrollTo(id: string) {
      itemRefs.current[id]?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    },
  }));

  // ── Derived data ───────────────────────────────────────────────────────

  const filtered = useMemo(
    () =>
      selectedTypes.length === 0
        ? incidents
        : incidents.filter((i) => selectedTypes.includes(i.type)),
    [incidents, selectedTypes],
  );

  // Active = not yet completed
  const unassigned = useMemo(
    () =>
      sortBySeverityThenTime(
        filtered.filter(
          (i) => i.completedAt === null && i.status === "unassigned",
        ),
      ),
    [filtered],
  );

  const p2pIncidents = useMemo(
    () =>
      sortBySeverityThenTime(
        filtered.filter(
          (i) => i.completedAt === null && i.status === "matching",
        ),
      ),
    [filtered],
  );

  // Historical = completedAt set OR status === "assigned"
  const historical = useMemo(
    () =>
      [
        ...filtered.filter(
          (i) => i.completedAt !== null || i.status === "assigned",
        ),
      ].sort((a, b) => {
        const aTime = (a.completedAt ?? a.timestamp).getTime();
        const bTime = (b.completedAt ?? b.timestamp).getTime();
        return bTime - aTime;
      }),
    [filtered],
  );

  const recentByTime = useMemo(
    () =>
      [
        ...filtered.filter(
          (i) => i.completedAt === null && i.status !== "assigned",
        ),
      ].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
    [filtered],
  );

  const visibleRecent = recentExpanded
    ? recentByTime
    : recentByTime.slice(0, RECENT_DEFAULT_LIMIT);
  const hiddenRecentCount = recentByTime.length - RECENT_DEFAULT_LIMIT;
  const activeCount = unassigned.length + p2pIncidents.length;

  // ── Handlers ──────────────────────────────────────────────────────────

  const handleRecentClick = useCallback(
    (id: string) => {
      onSelectIncident(id);
      const isP2P = p2pIncidents.some((i) => i.id === id);
      if (isP2P) setShowP2P(true);
      setFlashId(id);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          itemRefs.current[id]?.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          });
        });
      });
      setTimeout(() => setFlashId(null), 1000);
    },
    [onSelectIncident, p2pIncidents],
  );

  const handleRemoveTag =
    (type: Incident["type"]) => (e: MouseEvent<HTMLButtonElement>) => {
      e.preventDefault();
      e.stopPropagation();
      onToggleType(type);
    };

  const handleClearAll = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    onClearAllTypes();
  };

  // ── Render helpers ─────────────────────────────────────────────────────

  const renderCard = (incident: Incident, completed = false) => (
    <IncidentCard
      key={incident.id}
      incident={incident}
      isSelected={incident.id === selectedId}
      isFlashing={incident.id === flashId}
      onClick={() => onSelectIncident(incident.id)}
      itemRef={(el) => {
        itemRefs.current[incident.id] = el;
      }}
      completed={completed}
    />
  );

  const renderRecentRow = (incident: Incident) => {
    const isSelected = incident.id === selectedId;
    return (
      <button
        key={incident.id}
        onClick={() => handleRecentClick(incident.id)}
        className={`w-full text-left px-4 py-1.5 flex items-center gap-2.5 transition-colors cursor-pointer ${
          isSelected ? "bg-[#141e2b]" : "hover:bg-[#141825]"
        }`}
      >
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0 mt-px"
          style={{ backgroundColor: severityColors[incident.severity] }}
        />
        <span className="flex-1 text-[11px] text-[#6e808f] truncate leading-tight">
          {incident.description}
        </span>
        <span className="text-[10px] text-[#3d5470] tabular-nums shrink-0">
          {getTimeSince(incident.timestamp)}
        </span>
      </button>
    );
  };

  // ── Layout ─────────────────────────────────────────────────────────────

  return (
    <div className="w-[340px] h-full bg-[#0f1419] border-r border-[#1e2530] flex flex-col overflow-hidden">
      {/* ── Header ── */}
      <div className="h-12 border-b border-[#1e2530] flex items-center px-4 gap-2 shrink-0">
        <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500]">
          {viewMode === "active" ? "Live Incidents" : "Resolved Cases"}
        </span>
        <span className="text-[12px] text-[#5b8dbf] tabular-nums font-[500]">
          {viewMode === "active" ? activeCount : historical.length}
        </span>
        <button
          onClick={() =>
            setViewMode((m) => (m === "active" ? "historical" : "active"))
          }
          className={[
            "ml-auto flex items-center gap-1.5 text-[10px] px-2 py-1 rounded",
            "uppercase tracking-wider font-[500] transition-colors border",
            viewMode === "historical"
              ? "bg-[#3B5B8C20] text-[#5b8dbf] border-[#3B5B8C60]"
              : "text-[#6b7280] hover:text-[#9ca3af] border-[#1e2530] hover:border-[#2e3540]",
          ].join(" ")}
        >
          <History className="w-3 h-3" />
          {viewMode === "active" ? "History" : "Live"}
        </button>
      </div>

      {/* ── Type filter ── */}
      <div className="border-b border-[#1e2530] px-4 py-3 space-y-2 shrink-0">
        <span className="text-[10px] text-[#6b7280] uppercase tracking-wider">
          Filter
        </span>
        <details className="group relative">
          <summary className="list-none cursor-pointer rounded border border-[#2a3340] bg-[#141825] px-2 py-2 text-[11px] text-[#c5cad3]">
            <div className="flex items-center gap-2">
              <div className="flex flex-1 flex-wrap gap-1.5">
                {selectedTypes.length === 0 ? (
                  <span className="text-[#6b7280]">All types</span>
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
            <div className="flex flex-wrap gap-1.5">
              {incidentTypes.map((type) => {
                const isSelected = selectedTypes.includes(type);
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => onToggleType(type)}
                    className={`rounded-full border px-2 py-1 text-[10px] capitalize transition-colors ${
                      isSelected
                        ? "border-[#5b8dbf] bg-[#1a2a40] text-[#d6e6f6]"
                        : "border-[#3a4556] bg-[#141d2a] text-[#9ca3af] hover:border-[#5b8dbf] hover:text-[#cfd8e3]"
                    }`}
                  >
                    {type} ({incidentTypeCounts[type] ?? 0})
                  </button>
                );
              })}
            </div>
          </div>
        </details>
      </div>

      {/* ── Recent section (active view only) ── */}
      {viewMode === "active" && recentByTime.length > 0 && (
        <div className="border-b border-[#1e2530] shrink-0">
          <div className="px-4 pt-2.5 pb-1 flex items-center gap-2">
            <span className="text-[10px] text-[#4a5c6e] uppercase tracking-wider font-[500]">
              Recent
            </span>
            <span className="text-[10px] text-[#374a5e] tabular-nums">
              {recentByTime.length}
            </span>
          </div>
          <div
            className={recentExpanded ? "max-h-[196px] overflow-y-auto" : ""}
          >
            {visibleRecent.map(renderRecentRow)}
          </div>
          {(hiddenRecentCount > 0 || recentExpanded) && (
            <button
              onClick={() => setRecentExpanded((e) => !e)}
              className="w-full px-4 py-1.5 text-left text-[10px] text-[#3d5470]
                           hover:text-[#5b8dbf] uppercase tracking-wider transition-colors"
            >
              {recentExpanded ? "Show less" : `${hiddenRecentCount} more…`}
            </button>
          )}
        </div>
      )}

      {/* ── Main scrollable area ── */}
      <div className="flex-1 overflow-y-auto">
        {/* ACTIVE VIEW */}
        {viewMode === "active" && (
          <>
            <div className="px-4 pt-3 pb-1.5 flex items-center gap-2 sticky top-0 bg-[#0f1419] z-10 border-b border-[#1e2530]">
              <span className="text-[10px] text-[#9ca3af] uppercase tracking-wider font-[500]">
                Priority Queue
              </span>
              <span className="text-[10px] text-[#5b8dbf] tabular-nums">
                {unassigned.length}
              </span>
            </div>

            {unassigned.length === 0 ? (
              <div className="px-4 py-10 text-center text-[12px] text-[#4a4a5a]">
                No active incidents
              </div>
            ) : (
              unassigned.map((i) => renderCard(i))
            )}

            <button
              className="w-full px-4 py-2.5 flex items-center gap-2 border-t border-[#1e2530] hover:bg-[#141825] transition-colors"
              onClick={() => setShowP2P((s) => !s)}
            >
              <Users className="w-3 h-3 text-[#6b7280]" />
              <span className="text-[10px] text-[#9ca3af] uppercase tracking-wider font-[500]">
                P2P Coordinating
              </span>
              <span className="text-[10px] text-[#5b8dbf] tabular-nums">
                {p2pIncidents.length}
              </span>
              <span className="ml-auto text-[#6b7280]">
                {showP2P ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
              </span>
            </button>

            {showP2P &&
              (p2pIncidents.length === 0 ? (
                <div className="px-4 py-4 text-center text-[12px] text-[#4a4a5a] border-b border-[#1e2530]">
                  No active P2P coordination
                </div>
              ) : (
                p2pIncidents.map((i) => renderCard(i))
              ))}
          </>
        )}

        {/* HISTORICAL VIEW — uses completed=true for green RESOLVED styling */}
        {viewMode === "historical" && (
          <>
            <div className="px-4 pt-3 pb-1.5 flex items-center gap-2 sticky top-0 bg-[#0f1419] z-10 border-b border-[#1e2530]">
              <span className="text-[10px] text-[#9ca3af] uppercase tracking-wider font-[500]">
                Resolved Cases
              </span>
              <span className="text-[10px] text-[#5b8dbf] tabular-nums">
                {historical.length}
              </span>
            </div>

            {historical.length === 0 ? (
              <div className="px-4 py-12 text-center text-[12px] text-[#4a4a5a]">
                No resolved cases yet
              </div>
            ) : (
              historical.map((i) => renderCard(i, true))
            )}
          </>
        )}
      </div>
    </div>
  );
});
