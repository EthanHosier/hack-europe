import { useEffect, useRef, useState } from "react";
import {
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Navigation,
  Send,
  Shield,
} from "lucide-react";
import type { Incident } from "./IncidentQueue";

interface Responder {
  id: string;
  name: string;
  role: string;
  distance: number;
  availability: "available" | "on-call" | "busy";
  verificationLevel: "verified" | "pending" | "unverified";
  skills: string[];
}

interface IntelligencePanelProps {
  selectedIncident: Incident | null;
  responders: Responder[];
  respondersLoading?: boolean;
  onDispatch: (responderId: string, incidentId: string) => void;
  onMarkResolved?: (incidentId: string) => void;
  isResolving?: boolean;
}

const availabilityColors = {
  available: "#3d7a5e",
  "on-call": "#B8741A",
  busy: "#8B2835",
};

const verificationIcons = {
  verified: CheckCircle,
  pending: Shield,
  unverified: Shield,
};

export function IntelligencePanel({
  selectedIncident,
  responders,
  respondersLoading = false,
  onDispatch,
  onMarkResolved,
  isResolving = false,
}: IntelligencePanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [dispatchStates, setDispatchStates] = useState<
    Record<string, "idle" | "requesting" | "dispatched">
  >({});
  const [candidatesCollapsed, setCandidatesCollapsed] = useState(false);
  const hasAutoCollapsedRef = useRef(false);

  useEffect(() => {
    setDispatchStates({});
    setCandidatesCollapsed(false);
    hasAutoCollapsedRef.current = false;
  }, [selectedIncident?.id]);

  useEffect(() => {
    if (hasAutoCollapsedRef.current) return;
    const hasDispatched = Object.values(dispatchStates).some(
      (s) => s === "dispatched"
    );
    if (hasDispatched) {
      setCandidatesCollapsed(true);
      hasAutoCollapsedRef.current = true;
    }
  }, [dispatchStates]);

  if (collapsed) {
    return (
      <div className="w-10 bg-[#0f1419] border-l border-[#1e2530] flex flex-col items-center pt-3 gap-3">
        <button
          onClick={() => setCollapsed(false)}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-[#1a2332] transition-colors"
          title="Expand panel"
        >
          <ChevronLeft className="w-4 h-4 text-[#9ca3af]" />
        </button>
        <Brain className="w-4 h-4 text-[#2a3441] mt-1" />
      </div>
    );
  }

  if (!selectedIncident) {
    return (
      <div className="w-[380px] bg-[#0f1419] border-l border-[#1e2530] flex flex-col">
        <div className="h-12 border-b border-[#1e2530] flex items-center px-4">
          <Brain className="w-4 h-4 text-[#2a3441] mr-2" />
          <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500] flex-1">
            AI Analysis
          </span>
          <button
            onClick={() => setCollapsed(true)}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-[#1a2332] transition-colors"
            title="Collapse panel"
          >
            <ChevronRight className="w-4 h-4 text-[#9ca3af]" />
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center px-8">
            <Brain className="w-12 h-12 text-[#2a3441] mx-auto mb-3" />
            <p className="text-[13px] text-[#6b7280]">
              Select an incident to view AI operational analysis
            </p>
          </div>
        </div>
      </div>
    );
  }

  const hasAnalysis =
    selectedIncident.confidence != null ||
    selectedIncident.parsedNeedType ||
    selectedIncident.requiredCapability ||
    selectedIncident.recommendedAction;

  const severityLabel =
    selectedIncident.severity === "critical"
      ? "CRITICAL"
      : selectedIncident.severity === "high"
      ? "HIGH"
      : selectedIncident.severity === "moderate"
      ? "MODERATE"
      : "LOW";

  return (
    <div className="w-[380px] bg-[#0f1419] border-l border-[#1e2530] flex flex-col">
      {/* AI Analysis Section */}
      <div className="border-b border-[#1e2530]">
        <div className="h-12 border-b border-[#1e2530] flex items-center px-4 gap-2">
          <Brain className="w-4 h-4 text-[#5b8dbf]" />
          <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500] flex-1">
            Information
          </span>
          <button
            onClick={() => setCollapsed(true)}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-[#1a2332] transition-colors"
            title="Collapse panel"
          >
            <ChevronRight className="w-4 h-4 text-[#9ca3af]" />
          </button>
        </div>

        {hasAnalysis ? (
          <div className="p-4 space-y-4">
            {/* AI Accuracy Confidence Score */}
            {selectedIncident.confidence != null && (
              <div className="bg-[#141825] border border-[#2a3441] rounded p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] text-[#6b7280] uppercase tracking-wider">
                    Accuracy Confidence
                  </span>
                  <span className="text-[14px] text-[#e8eaed] font-[500] tabular-nums">
                    {selectedIncident.confidence}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-[#1a2332] rounded overflow-hidden">
                  <div
                    className="h-full bg-[#3d7a5e] rounded"
                    style={{ width: `${selectedIncident.confidence}%` }}
                  />
                </div>
              </div>
            )}

            {/* P2P Badge */}
            <div className="flex items-center gap-2">
              <span
                className={`text-[10px] px-2 py-1 rounded uppercase tracking-wider font-medium ${
                  selectedIncident.p2p
                    ? "bg-[#3d7a5e20] text-[#3d7a5e]"
                    : "bg-[#8B283520] text-[#c94f5a]"
                }`}
              >
                {selectedIncident.p2p
                  ? "Peer Assistance OK"
                  : "Specialist Required"}
              </span>
              <span className="text-[10px] px-2 py-1 rounded uppercase tracking-wider font-medium bg-[#B8741A20] text-[#B8741A]">
                {severityLabel}
              </span>
            </div>

            {/* Analysis Fields */}
            <div className="space-y-3">
              {selectedIncident.parsedNeedType && (
                <div>
                  <div className="text-[10px] text-[#6b7280] uppercase tracking-wider mb-1">
                    Needs
                  </div>
                  <div className="text-[12px] text-[#e8eaed] leading-relaxed">
                    {selectedIncident.parsedNeedType}
                  </div>
                </div>
              )}

              {selectedIncident.requiredCapability && (
                <div>
                  <div className="text-[10px] text-[#6b7280] uppercase tracking-wider mb-1">
                    Required Skillset
                  </div>
                  <div className="text-[12px] text-[#5b8dbf]">
                    {selectedIncident.requiredCapability}
                  </div>
                </div>
              )}

              {selectedIncident.recommendedAction && (
                <div className="bg-[#1a2332] border-l-2 border-[#5b8dbf] p-3 rounded">
                  <div className="text-[10px] text-[#6b7280] uppercase tracking-wider mb-1">
                    Recommended Action
                  </div>
                  <div className="text-[12px] text-[#e8eaed] leading-relaxed">
                    {selectedIncident.recommendedAction}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-4 flex items-center justify-center py-8">
            <p className="text-[12px] text-[#6b7280]">
              AI analysis not yet available for this incident
            </p>
          </div>
        )}
      </div>

      {/* Dispatched Responders */}
      {responders.some((r) => dispatchStates[r.id] === "dispatched") && (
        <div className="border-b border-[#1e2530] shrink-0">
          <div className="h-10 flex items-center px-4 gap-2">
            <CheckCircle className="w-3.5 h-3.5 text-[#22c55e]" />
            <span className="text-[11px] text-[#22c55e] uppercase tracking-wider font-[500]">
              Dispatched
            </span>
          </div>
          {responders
            .filter((r) => dispatchStates[r.id] === "dispatched")
            .map((responder) => {
              const VerificationIcon =
                verificationIcons[responder.verificationLevel];
              return (
                <div
                  key={responder.id}
                  className="px-4 py-2.5 border-t border-[#22c55e18] bg-[#22c55e08] flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-[12px] text-[#e8eaed] font-[500]">
                        {responder.name}
                      </span>
                      <VerificationIcon
                        className={`w-3 h-3 ${
                          responder.verificationLevel === "verified"
                            ? "text-[#3d7a5e]"
                            : "text-[#6b7280]"
                        }`}
                      />
                    </div>
                    <div className="text-[10px] text-[#6b7280]">
                      {responder.role}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Navigation className="w-3 h-3 text-[#6b7280]" />
                    <span className="text-[10px] text-[#9ca3af] tabular-nums">
                      {responder.distance} km
                    </span>
                  </div>
                </div>
              );
            })}
        </div>
      )}

      {/* Responder Candidates Section */}
      {(() => {
        const hasDispatched = Object.values(dispatchStates).some(
          (s) => s === "dispatched"
        );
        return (
          <div className="flex-1 flex flex-col overflow-hidden">
            <button
              onClick={() => setCandidatesCollapsed((c) => !c)}
              className="h-12 border-b border-[#1e2530] flex items-center px-4 w-full hover:bg-[#141825] transition-colors shrink-0"
            >
              <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500]">
                {hasDispatched
                  ? "Additional Responder Candidates"
                  : "Responder Candidates"}
              </span>
              <span className="ml-2 text-[12px] text-[#5b8dbf] tabular-nums font-[500]">
                {
                  responders.filter(
                    (r) => dispatchStates[r.id] !== "dispatched"
                  ).length
                }
              </span>
              <ChevronDown
                className={`ml-auto w-3.5 h-3.5 text-[#6b7280] transition-transform duration-200 ${
                  candidatesCollapsed ? "-rotate-90" : ""
                }`}
              />
            </button>

            {!candidatesCollapsed && (
              <div className="flex-1 overflow-y-auto pb-16">
                {respondersLoading ? (
                  <div className="flex items-center justify-center gap-2 py-8 text-[12px] text-[#6b7280]">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Loading responder candidates…</span>
                  </div>
                ) : (
                  responders
                    .filter((r) => dispatchStates[r.id] !== "dispatched")
                    .map((responder) => {
                      const VerificationIcon =
                        verificationIcons[responder.verificationLevel];
                      const ds = dispatchStates[responder.id] ?? "idle";
                      const isBusy = responder.availability === "busy";

                      return (
                        <div
                          key={responder.id}
                          className="px-4 py-3 border-b border-[#1e2530] hover:bg-[#141825] transition-colors"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-[13px] text-[#e8eaed] font-[500]">
                                  {responder.name}
                                </span>
                                <VerificationIcon
                                  className={`w-3.5 h-3.5 ${
                                    responder.verificationLevel === "verified"
                                      ? "text-[#3d7a5e]"
                                      : "text-[#6b7280]"
                                  }`}
                                />
                              </div>
                              <div className="text-[11px] text-[#6b7280]">
                                {responder.role}
                              </div>
                            </div>

                            <div className="flex items-center gap-1.5">
                              <Navigation className="w-3 h-3 text-[#6b7280]" />
                              <span className="text-[11px] text-[#9ca3af] tabular-nums">
                                {responder.distance} km
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 mb-3">
                            <div className="flex items-center gap-1.5">
                              <div
                                className="w-2 h-2 rounded-full"
                                style={{
                                  backgroundColor:
                                    availabilityColors[responder.availability],
                                }}
                              />
                              <span className="text-[10px] text-[#9ca3af] capitalize">
                                {responder.availability}
                              </span>
                            </div>

                            <div className="h-3 w-px bg-[#2a3441]" />

                            <div className="flex items-center gap-1 flex-wrap">
                              {responder.skills
                                .slice(0, 2)
                                .map((skill, index) => (
                                  <span
                                    key={index}
                                    className="text-[9px] px-1.5 py-0.5 bg-[#1a2332] text-[#6b7280] rounded uppercase tracking-wider"
                                  >
                                    {skill}
                                  </span>
                                ))}
                            </div>
                          </div>

                          {ds === "requesting" ? (
                            <div className="w-full h-8 bg-[#B8741A18] border border-[#B8741A40] rounded flex items-center justify-center gap-2">
                              <Loader2 className="w-3.5 h-3.5 text-[#B8741A] animate-spin" />
                              <span className="text-[11px] text-[#B8741A] uppercase tracking-wider font-[500]">
                                Requesting…
                              </span>
                            </div>
                          ) : (
                            <button
                              onClick={() => {
                                setDispatchStates((prev) => ({
                                  ...prev,
                                  [responder.id]: "requesting",
                                }));
                                onDispatch(responder.id, selectedIncident.id);
                                setDispatchStates((prev) => ({
                                  ...prev,
                                  [responder.id]: "dispatched",
                                }));
                              }}
                              disabled={isBusy}
                              className="w-full h-8 bg-[#1a2332] hover:bg-[#5b8dbf] disabled:hover:bg-[#1a2332] border border-[#2a3441] rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer group"
                            >
                              <Send className="w-3.5 h-3.5 text-[#9ca3af] group-hover:text-white transition-colors" />
                              <span className="text-[11px] text-[#9ca3af] group-hover:text-white uppercase tracking-wider font-[500] transition-colors">
                                Dispatch
                              </span>
                            </button>
                          )}
                        </div>
                      );
                    })
                )}
              </div>
            )}
          </div>
        );
      })()}

      {/* Resolve button */}
      {!selectedIncident.completedAt && onMarkResolved && (
        <div className="border-t border-[#1e2530] p-4">
          <button
            onClick={() => onMarkResolved(selectedIncident.id)}
            disabled={isResolving}
            className="w-full h-10 bg-[#1a2332] hover:bg-[#253344] border border-[#2a3441] rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <CheckCircle className="w-4 h-4 text-[#5b8dbf] group-hover:text-[#7ea8d1] transition-colors" />
            <span className="text-[12px] text-[#5b8dbf] group-hover:text-[#7ea8d1] uppercase tracking-wider font-medium transition-colors">
              {isResolving ? "Resolving…" : "Mark as Resolved"}
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
