import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Clock,
  Flame,
  Heart,
  History,
  Home,
  Users,
  Zap,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

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

export interface IncidentQueueHandle {
  /** Scroll the main priority list to this incident id */
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
  disaster: Home,
  emergency: Zap,
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

// ─── Component ────────────────────────────────────────────────────────────────

export const IncidentQueue = forwardRef<IncidentQueueHandle, IncidentQueueProps>(
  function IncidentQueue({ incidents, selectedId, onSelectIncident }, ref) {
    // Refs: one per main-list row so we can scroll to them
    const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});

    const [showP2P, setShowP2P] = useState(false);
    const [viewMode, setViewMode] = useState<"active" | "historical">("active");
    const [recentExpanded, setRecentExpanded] = useState(false);
    // Transient: id that should briefly flash in the main list after recent-click
    const [flashId, setFlashId] = useState<string | null>(null);

    // Expose scrollTo so App can drive scroll from map clicks
    useImperativeHandle(ref, () => ({
      scrollTo(id: string) {
        itemRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      },
    }));

    // ── Derived data (all memoised) ──────────────────────────────────────────

    const unassigned = useMemo(
      () => sortBySeverityThenTime(incidents.filter((i) => i.status === "unassigned")),
      [incidents],
    );

    const p2pIncidents = useMemo(
      () => sortBySeverityThenTime(incidents.filter((i) => i.status === "matching")),
      [incidents],
    );

    const historical = useMemo(
      () =>
        [...incidents.filter((i) => i.status === "assigned")].sort(
          (a, b) => b.timestamp.getTime() - a.timestamp.getTime(),
        ),
      [incidents],
    );

    // Recent = all active (unassigned + matching) sorted purely by arrival time.
    // This is a navigation aid only – items also live in the main priority list.
    const recentByTime = useMemo(
      () =>
        [...incidents.filter((i) => i.status !== "assigned")].sort(
          (a, b) => b.timestamp.getTime() - a.timestamp.getTime(),
        ),
      [incidents],
    );

    const visibleRecent = recentExpanded
      ? recentByTime
      : recentByTime.slice(0, RECENT_DEFAULT_LIMIT);
    const hiddenRecentCount = recentByTime.length - RECENT_DEFAULT_LIMIT;

    // ── Handlers ────────────────────────────────────────────────────────────

    const handleRecentClick = useCallback(
      (id: string) => {
        onSelectIncident(id);

        // If this incident lives in the collapsed P2P section, expand it first
        // so the DOM element exists before we try to scroll to it
        const isP2P = p2pIncidents.some((i) => i.id === id);
        if (isP2P) setShowP2P(true);

        setFlashId(id);

        // Two rAFs: first waits for React state flush, second for DOM paint
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            itemRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
          });
        });

        // Clear flash after highlight window
        setTimeout(() => setFlashId(null), 1000);
      },
      [onSelectIncident, p2pIncidents],
    );

    // ── Render helpers ───────────────────────────────────────────────────────

    /**
     * Full incident card rendered in the main priority / historical list.
     * Assigns a ref so it can be scroll-targeted.
     */
    const renderCard = (incident: Incident) => {
      const Icon = typeIcons[incident.type];
      const isSelected = incident.id === selectedId;
      const isFlashing = incident.id === flashId;

      let bgClass: string;
      if (isSelected) bgClass = "bg-[#1a2332] border-l-2 border-l-[#5b8dbf]";
      else if (isFlashing) bgClass = "bg-[#1d3148]";
      else bgClass = "hover:bg-[#141825]";

      return (
        <div
          key={incident.id}
          ref={(el) => {
            itemRefs.current[incident.id] = el;
          }}
          onClick={() => onSelectIncident(incident.id)}
          className={`px-4 py-3 border-b border-[#1e2530] cursor-pointer transition-colors duration-500 ${bgClass}`}
        >
          <div className="flex items-start gap-3">
            <div
              className="w-8 h-8 rounded flex items-center justify-center mt-0.5 shrink-0"
              style={{ backgroundColor: `${severityColors[incident.severity]}18` }}
            >
              <Icon
                className="w-4 h-4"
                style={{ color: severityColors[incident.severity] }}
              />
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-[#e8eaed] leading-tight line-clamp-2 mb-1">
                {incident.description}
              </p>
              <p className="text-[11px] text-[#6b7280] truncate mb-2">{incident.region}</p>

              <div className="flex items-center gap-2 flex-wrap">
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

                <span className="ml-auto flex items-center gap-1 text-[10px] text-[#6b7280]">
                  <Clock className="w-3 h-3" />
                  {getTimeSince(incident.timestamp)}
                </span>
              </div>
            </div>
          </div>
        </div>
      );
    };

    /**
     * Compact row used only in the Recent section.
     * No ref assignment – this is purely a navigation shortcut.
     * Clicking navigates + scrolls to the item in the main priority list.
     */
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
          {/* Severity dot */}
          <span
            className="w-1.5 h-1.5 rounded-full shrink-0 mt-px"
            style={{ backgroundColor: severityColors[incident.severity] }}
          />

          {/* Description */}
          <span className="flex-1 text-[11px] text-[#6e808f] truncate leading-tight">
            {incident.description}
          </span>

          {/* Time */}
          <span className="text-[10px] text-[#3d5470] tabular-nums shrink-0">
            {getTimeSince(incident.timestamp)}
          </span>
        </button>
      );
    };

    const activeCount = unassigned.length + p2pIncidents.length;

    // ── Layout ───────────────────────────────────────────────────────────────
    // Structure:
    //   [header]          – fixed, no scroll
    //   [recent section]  – fixed, no scroll (active view only)
    //   [main list]       – flex-1, overflow-y-auto (scrolls independently)
    //
    // The recent section is intentionally outside the scroll container so it
    // stays visible as the operator scrolls through the priority queue.

    return (
      <div className="w-[340px] bg-[#0f1419] border-r border-[#1e2530] flex flex-col overflow-hidden">

        {/* ── Header ── */}
        <div className="h-12 border-b border-[#1e2530] flex items-center px-4 gap-2 shrink-0">
          <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500]">
            {viewMode === "active" ? "Live Incidents" : "Resolved Cases"}
          </span>
          <span className="text-[12px] text-[#5b8dbf] tabular-nums font-[500]">
            {viewMode === "active" ? activeCount : historical.length}
          </span>

          <button
            onClick={() => setViewMode((m) => (m === "active" ? "historical" : "active"))}
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

        {/* ── Recent section (fixed, outside scroll) ── */}
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

            {/* Compact rows – capped height when expanded */}
            <div className={recentExpanded ? "max-h-[196px] overflow-y-auto" : ""}>
              {visibleRecent.map(renderRecentRow)}
            </div>

            {/* Expand / collapse toggle */}
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

          {/* ACTIVE VIEW ─────────────────────────────────────────────────── */}
          {viewMode === "active" && (
            <>
              {/* Priority queue section header (sticky while scrolling) */}
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
                unassigned.map(renderCard)
              )}

              {/* P2P section (collapsible, hidden by default) */}
              <button
                className="w-full px-4 py-2.5 flex items-center gap-2 border-t border-[#1e2530]
                           hover:bg-[#141825] transition-colors"
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
                  p2pIncidents.map(renderCard)
                ))}
            </>
          )}

          {/* HISTORICAL VIEW ──────────────────────────────────────────────── */}
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
                historical.map(renderCard)
              )}
            </>
          )}
        </div>
      </div>
    );
  },
);
