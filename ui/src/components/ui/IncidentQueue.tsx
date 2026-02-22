import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
} from "react";
import {
  AlertTriangle,
  BarChart2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  ClipboardList,
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
  completedAt: Date | null;
  p2p: boolean;
  confidence: number | null;
  requiredCapability: string | null;
  parsedNeedType: string | null;
  recommendedAction: string | null;
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
  viewMode: "active" | "historical" | "analytics";
  onViewModeChange: (mode: "active" | "historical" | "analytics") => void;
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

function formatMins(mins: number): string {
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
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
    viewMode,
    onViewModeChange,
  },
  ref,
) {
  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const filterRef = useRef<HTMLDivElement | null>(null);

  const [showPriority, setShowPriority] = useState(true);
  const [showP2P, setShowP2P] = useState(false);
  const [recentExpanded, setRecentExpanded] = useState(false);
  const [flashId, setFlashId] = useState<string | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);

  useEffect(() => {
    function handleClickOutside(e: globalThis.MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useImperativeHandle(ref, () => ({
    scrollTo(id: string) {
      // Determine which collapsed section the incident lives in and expand it
      const isInPriority = unassigned.some((i) => i.id === id);
      const isInP2P = p2pIncidents.some((i) => i.id === id);

      let needsExpansion = false;
      if (isInPriority && !showPriority) {
        setShowPriority(true);
        needsExpansion = true;
      } else if (isInP2P && !showP2P) {
        setShowP2P(true);
        needsExpansion = true;
      }

      const doScroll = () =>
        itemRefs.current[id]?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });

      if (needsExpansion) {
        // Wait two animation frames for React to re-render and mount the card
        requestAnimationFrame(() => requestAnimationFrame(doScroll));
      } else {
        doScroll();
      }
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

  // Active = not yet completed (unassigned or currently being matched)
  const unassigned = useMemo(
    () =>
      sortBySeverityThenTime(
        filtered.filter(
          (i) =>
            i.completedAt === null &&
            (i.status === "unassigned" || i.status === "matching") &&
            !i.p2p,
        ),
      ),
    [filtered],
  );

  const p2pIncidents = useMemo(
    () =>
      sortBySeverityThenTime(
        filtered.filter(
          (i) =>
            i.completedAt === null &&
            (i.status === "unassigned" || i.status === "matching") &&
            i.p2p,
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

  const analytics = useMemo(() => {
    const withTime = historical.filter((i) => i.completedAt !== null);

    const avgMttrMins = (list: Incident[]) => {
      if (list.length === 0) return null;
      const ms =
        list.reduce(
          (s, i) => s + (i.completedAt!.getTime() - i.timestamp.getTime()),
          0,
        ) / list.length;
      return Math.round(ms / 60_000);
    };

    const overallMttr = avgMttrMins(withTime);

    const mttrByType = (
      [
        "medical",
        "fire",
        "rescue",
        "disaster",
        "emergency",
        "other",
      ] as Incident["type"][]
    )
      .map((type) => ({
        type,
        mttr: avgMttrMins(withTime.filter((i) => i.type === type)),
        count: historical.filter((i) => i.type === type).length,
      }))
      .filter((x) => x.mttr !== null)
      .sort((a, b) => b.mttr! - a.mttr!);

    const p2pMttr = avgMttrMins(withTime.filter((i) => i.p2p));
    const specialistMttr = avgMttrMins(withTime.filter((i) => !i.p2p));
    const p2pRate =
      historical.length > 0
        ? Math.round(
            (historical.filter((i) => i.p2p).length / historical.length) * 100,
          )
        : 0;

    const now = Date.now();
    const lastHour = historical.filter(
      (i) => i.completedAt && now - i.completedAt.getTime() < 3_600_000,
    ).length;
    const last24h = historical.filter(
      (i) => i.completedAt && now - i.completedAt.getTime() < 86_400_000,
    ).length;
    const avgPerHour = Math.round((last24h / 24) * 10) / 10;

    const sev = (["critical", "high", "moderate", "low"] as const).map(
      (s) => ({
        key: s,
        count: historical.filter((i) => i.severity === s).length,
      }),
    );
    const sevTotal = sev.reduce((a, b) => a + b.count, 0);

    const regionMap: Record<string, number> = {};
    historical.forEach((i) => {
      regionMap[i.region] = (regionMap[i.region] ?? 0) + 1;
    });
    const topRegions = Object.entries(regionMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    const hourBuckets = Array.from({ length: 24 }, (_, h) =>
      historical.filter((i) => i.timestamp.getHours() === h).length,
    );

    return {
      overallMttr,
      mttrByType,
      p2pMttr,
      specialistMttr,
      p2pRate,
      lastHour,
      avgPerHour,
      sev,
      sevTotal,
      topRegions,
      hourBuckets,
    };
  }, [historical]);

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
          {viewMode === "active"
            ? "Live Incidents"
            : viewMode === "historical"
              ? "Resolved Cases"
              : "Analytics"}
        </span>
        <span className="text-[12px] text-[#5b8dbf] tabular-nums font-[500]">
          {viewMode === "active" ? activeCount : historical.length}
        </span>
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() =>
              onViewModeChange(viewMode === "historical" ? "active" : "historical")
            }
            className={[
              "flex items-center gap-1.5 text-[10px] px-2 py-1 rounded",
              "uppercase tracking-wider font-[500] transition-colors border",
              viewMode === "historical"
                ? "bg-[#3B5B8C20] text-[#5b8dbf] border-[#3B5B8C60]"
                : "text-[#6b7280] hover:text-[#9ca3af] border-[#1e2530] hover:border-[#2e3540]",
            ].join(" ")}
          >
            <History className="w-3 h-3" />
            {viewMode === "historical" ? "Live" : "History"}
          </button>
          <button
            onClick={() =>
              onViewModeChange(viewMode === "analytics" ? "active" : "analytics")
            }
            className={[
              "flex items-center gap-1.5 text-[10px] px-2 py-1 rounded",
              "uppercase tracking-wider font-[500] transition-colors border",
              viewMode === "analytics"
                ? "bg-[#3B5B8C20] text-[#5b8dbf] border-[#3B5B8C60]"
                : "text-[#6b7280] hover:text-[#9ca3af] border-[#1e2530] hover:border-[#2e3540]",
            ].join(" ")}
          >
            <BarChart2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* ── Type filter ── */}
      <div className="border-b border-[#1e2530] px-4 py-3 space-y-2 shrink-0">
        <span className="text-[10px] text-[#6b7280] uppercase tracking-wider">
          Filter
        </span>
        <div ref={filterRef} className="relative">
          <div
            role="button"
            tabIndex={0}
            onClick={() => setFilterOpen((o) => !o)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setFilterOpen((o) => !o); }}
            className="w-full cursor-pointer rounded border border-[#2a3340] bg-[#141825] px-2 py-2 text-[11px] text-[#c5cad3]"
          >
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
              <ChevronDown
                className={`h-3.5 w-3.5 text-[#7b8798] transition-transform ${filterOpen ? "rotate-180" : ""}`}
              />
            </div>
          </div>
          {filterOpen && (
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
          )}
        </div>
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
      <div className="flex-1 overflow-hidden">
        {/* ACTIVE VIEW */}
        {viewMode === "active" && (
          <div className="h-full flex flex-col">
            <button
              className="w-full px-4 pt-3 pb-1.5 flex items-center gap-2 shrink-0 bg-[#0f1419] z-10 border-b border-[#1e2530] hover:bg-[#141825] transition-colors"
              onClick={() => setShowPriority((s) => !s)}
            >
              <ClipboardList className="w-3 h-3 text-[#6b7280]" />
              <span className="text-[10px] text-[#9ca3af] uppercase tracking-wider font-[500]">
                Priority Tasks
              </span>
              <span className="text-[10px] text-[#5b8dbf] tabular-nums">
                {unassigned.length}
              </span>
              <span className="ml-auto text-[#6b7280]">
                {showPriority ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
              </span>
            </button>

            {showPriority && (
              <div className="flex-1 overflow-y-auto min-h-0">
                {unassigned.length === 0 ? (
                  <div className="px-4 py-10 text-center text-[12px] text-[#4a4a5a]">
                    No active incidents requiring action
                  </div>
                ) : (
                  unassigned.map((i) => renderCard(i))
                )}
              </div>
            )}

            <button
              className="shrink-0 w-full px-4 py-2.5 flex items-center gap-2 border-t border-[#1e2530] hover:bg-[#141825] transition-colors"
              onClick={() => setShowP2P((s) => !s)}
            >
              <Users className="w-3 h-3 text-[#6b7280]" />
              <span className="text-[10px] text-[#9ca3af] uppercase tracking-wider font-[500]">
                Peer Coordinating
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

            {showP2P && (
              <div className="flex-1 overflow-y-auto min-h-0">
                {p2pIncidents.length === 0 ? (
                  <div className="px-4 py-4 text-center text-[12px] text-[#4a4a5a]">
                    No active incidents in peer-to-peer coordination
                  </div>
                ) : (
                  p2pIncidents.map((i) => renderCard(i))
                )}
              </div>
            )}
          </div>
        )}

        {/* HISTORICAL VIEW — uses completed=true for green RESOLVED styling */}
        {viewMode === "historical" && (
          <div className="h-full overflow-y-auto">
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
          </div>
        )}

        {/* ANALYTICS VIEW */}
        {viewMode === "analytics" && (
          <div className="h-full overflow-y-auto">
            {historical.length === 0 ? (
              <div className="px-4 py-12 text-center text-[12px] text-[#4a4a5a]">
                No resolved cases to analyse yet
              </div>
            ) : (
              <div className="p-4 space-y-6">

                {/* ── Summary cards 2×2 ── */}
                <div className="grid grid-cols-2 gap-2">
                  {[
                    {
                      label: "Resolved",
                      value: historical.length.toString(),
                      sub: "total cases",
                    },
                    {
                      label: "Avg MTTR",
                      value:
                        analytics.overallMttr != null
                          ? formatMins(analytics.overallMttr)
                          : "—",
                      sub: "mean time to resolve",
                    },
                    {
                      label: "Last Hour",
                      value: analytics.lastHour.toString(),
                      sub: `${analytics.avgPerHour}/h 24h avg`,
                    },
                    {
                      label: "P2P Rate",
                      value: `${analytics.p2pRate}%`,
                      sub: "peer-coordinated",
                    },
                  ].map(({ label, value, sub }) => (
                    <div
                      key={label}
                      className="bg-[#141825] border border-[#1e2530] rounded-md p-3"
                    >
                      <div className="text-[9px] text-[#6b7280] uppercase tracking-wider mb-1.5">
                        {label}
                      </div>
                      <div className="text-[22px] text-[#e8eaed] font-[600] tabular-nums leading-none mb-1">
                        {value}
                      </div>
                      <div className="text-[9px] text-[#4a5c6e] leading-tight">
                        {sub}
                      </div>
                    </div>
                  ))}
                </div>

                {/* ── Response time by type ── */}
                <div>
                  <p className="text-[10px] text-[#5b7a9a] uppercase tracking-wider font-[500] mb-3">
                    Response Time by Type
                  </p>
                  {analytics.mttrByType.length === 0 ? (
                    <p className="text-[11px] text-[#4a4a5a]">
                      Insufficient data
                    </p>
                  ) : (
                    (() => {
                      const maxMttr = Math.max(
                        ...analytics.mttrByType.map((x) => x.mttr!),
                        1,
                      );
                      return analytics.mttrByType.map(
                        ({ type, mttr, count }) => {
                          const Icon = typeIcons[type];
                          return (
                            <div key={type} className="mb-3">
                              <div className="flex items-center justify-between mb-1.5">
                                <div className="flex items-center gap-1.5">
                                  <Icon
                                    className="w-3 h-3"
                                    style={{
                                      color: severityColors.moderate,
                                    }}
                                  />
                                  <span className="text-[11px] text-[#c5cad3] capitalize">
                                    {type}
                                  </span>
                                  <span className="text-[9px] text-[#4a5c6e]">
                                    ({count})
                                  </span>
                                </div>
                                <span className="text-[11px] text-[#9ca3af] tabular-nums font-[500]">
                                  {formatMins(mttr!)}
                                </span>
                              </div>
                              <div className="w-full h-1.5 bg-[#1a2332] rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full"
                                  style={{
                                    width: `${(mttr! / maxMttr) * 100}%`,
                                    backgroundColor: "#5b8dbf",
                                  }}
                                />
                              </div>
                            </div>
                          );
                        },
                      );
                    })()
                  )}
                </div>

                {/* ── Peer vs Specialist MTTR ── */}
                <div>
                  <p className="text-[10px] text-[#5b7a9a] uppercase tracking-wider font-[500] mb-3">
                    Peer vs Specialist MTTR
                  </p>
                  <div className="flex gap-2">
                    {[
                      {
                        label: "Peer",
                        value: analytics.p2pMttr,
                        color: "#3d7a5e",
                      },
                      {
                        label: "Specialist",
                        value: analytics.specialistMttr,
                        color: "#5b8dbf",
                      },
                    ].map(({ label, value, color }) => (
                      <div
                        key={label}
                        className="flex-1 bg-[#141825] border border-[#1e2530] rounded-md p-3"
                      >
                        <div className="text-[9px] text-[#6b7280] uppercase tracking-wider mb-1.5">
                          {label}
                        </div>
                        <div
                          className="text-[18px] font-[600] tabular-nums leading-none"
                          style={{ color }}
                        >
                          {value != null ? formatMins(value) : "—"}
                        </div>
                      </div>
                    ))}
                  </div>
                  {analytics.p2pMttr != null &&
                    analytics.specialistMttr != null && (
                      <p className="text-[10px] text-[#4a5c6e] mt-2 leading-snug">
                        {analytics.p2pMttr < analytics.specialistMttr
                          ? `Peer coordination resolves ${formatMins(analytics.specialistMttr - analytics.p2pMttr)} faster on average`
                          : `Specialist dispatch resolves ${formatMins(analytics.p2pMttr - analytics.specialistMttr)} faster on average`}
                      </p>
                    )}
                </div>

                {/* ── Severity breakdown ── */}
                <div>
                  <p className="text-[10px] text-[#5b7a9a] uppercase tracking-wider font-[500] mb-3">
                    Severity Breakdown
                  </p>
                  {analytics.sev.map(({ key, count }) => {
                    const pct =
                      analytics.sevTotal > 0
                        ? Math.round((count / analytics.sevTotal) * 100)
                        : 0;
                    return (
                      <div key={key} className="mb-2.5">
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className="text-[10px] uppercase tracking-wider font-[500]"
                            style={{ color: severityColors[key] }}
                          >
                            {key}
                          </span>
                          <span className="text-[10px] text-[#6b7280] tabular-nums">
                            {count} · {pct}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-[#1a2332] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: severityColors[key],
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* ── Regional hotspots ── */}
                {analytics.topRegions.length > 0 && (
                  <div>
                    <p className="text-[10px] text-[#5b7a9a] uppercase tracking-wider font-[500] mb-3">
                      Hotspot Regions
                    </p>
                    {(() => {
                      const maxCount = analytics.topRegions[0][1];
                      return analytics.topRegions.map(
                        ([region, count], idx) => (
                          <div key={region} className="mb-2.5">
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <span className="text-[9px] text-[#4a5c6e] tabular-nums w-3 text-right">
                                  {idx + 1}
                                </span>
                                <span className="text-[11px] text-[#c5cad3]">
                                  {region}
                                </span>
                              </div>
                              <span className="text-[10px] text-[#9ca3af] tabular-nums">
                                {count}
                              </span>
                            </div>
                            <div className="w-full h-1 bg-[#1a2332] rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${(count / maxCount) * 100}%`,
                                  backgroundColor:
                                    idx === 0 ? "#8B2835" : "#5b8dbf",
                                }}
                              />
                            </div>
                          </div>
                        ),
                      );
                    })()}
                  </div>
                )}

                {/* ── Peak hours ── */}
                <div>
                  <p className="text-[10px] text-[#5b7a9a] uppercase tracking-wider font-[500] mb-3">
                    Incident Volume by Hour
                  </p>
                  <div
                    className="flex items-end gap-px"
                    style={{ height: "48px" }}
                  >
                    {analytics.hourBuckets.map((count, h) => {
                      const max = Math.max(...analytics.hourBuckets, 1);
                      const pct = (count / max) * 100;
                      return (
                        <div
                          key={h}
                          className="flex-1 rounded-sm"
                          title={`${h.toString().padStart(2, "0")}:00 — ${count}`}
                          style={{
                            height: `${Math.max(pct, count > 0 ? 6 : 0)}%`,
                            backgroundColor:
                              pct > 70
                                ? severityColors.critical
                                : pct > 40
                                  ? severityColors.high
                                  : "#3B5B8C",
                            opacity: 0.85,
                          }}
                        />
                      );
                    })}
                  </div>
                  <div className="flex justify-between mt-1.5">
                    <span className="text-[9px] text-[#4a5c6e]">00:00</span>
                    <span className="text-[9px] text-[#4a5c6e]">12:00</span>
                    <span className="text-[9px] text-[#4a5c6e]">23:00</span>
                  </div>
                </div>

              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
});
