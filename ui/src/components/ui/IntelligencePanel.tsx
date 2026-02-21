import { Brain, CheckCircle, Navigation, Send, Shield } from "lucide-react";
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
  onDispatch: (responderId: string, incidentId: string) => void;
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
  onDispatch,
}: IntelligencePanelProps) {
  if (!selectedIncident) {
    return (
      <div className="w-[380px] bg-[#0f1419] border-l border-[#1e2530] flex items-center justify-center">
        <div className="text-center px-8">
          <Brain className="w-12 h-12 text-[#2a3441] mx-auto mb-3" />
          <p className="text-[13px] text-[#6b7280]">
            Select an incident to view AI operational analysis
          </p>
        </div>
      </div>
    );
  }

  // Mock AI analysis data
  const analysis = {
    needType: "Immediate medical assistance required",
    capability: "Advanced Life Support (ALS)",
    urgency: "HIGH - Time-critical response needed",
    confidence: 94,
    recommendation:
      "Dispatch nearest ALS-certified unit with cardiac equipment",
  };

  return (
    <div className="w-[380px] bg-[#0f1419] border-l border-[#1e2530] flex flex-col">
      {/* AI Analysis Section */}
      <div className="border-b border-[#1e2530]">
        <div className="h-12 border-b border-[#1e2530] flex items-center px-4 gap-2">
          <Brain className="w-4 h-4 text-[#5b8dbf]" />
          <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500]">
            AI Operational Analysis
          </span>
        </div>

        <div className="p-4 space-y-4">
          {/* Confidence Score */}
          <div className="bg-[#141825] border border-[#2a3441] rounded p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] text-[#6b7280] uppercase tracking-wider">
                Confidence
              </span>
              <span className="text-[14px] text-[#e8eaed] font-[500] tabular-nums">
                {analysis.confidence}%
              </span>
            </div>
            <div className="w-full h-1.5 bg-[#1a2332] rounded overflow-hidden">
              <div
                className="h-full bg-[#3d7a5e] rounded"
                style={{ width: `${analysis.confidence}%` }}
              />
            </div>
          </div>

          {/* Analysis Fields */}
          <div className="space-y-3">
            <div>
              <div className="text-[10px] text-[#6b7280] uppercase tracking-wider mb-1">
                Parsed Need Type
              </div>
              <div className="text-[12px] text-[#e8eaed] leading-relaxed">
                {analysis.needType}
              </div>
            </div>

            <div>
              <div className="text-[10px] text-[#6b7280] uppercase tracking-wider mb-1">
                Required Capability
              </div>
              <div className="text-[12px] text-[#5b8dbf]">
                {analysis.capability}
              </div>
            </div>

            <div>
              <div className="text-[10px] text-[#6b7280] uppercase tracking-wider mb-1">
                Urgency Classification
              </div>
              <div className="text-[12px] text-[#c94f5a]">
                {analysis.urgency}
              </div>
            </div>

            <div className="bg-[#1a2332] border-l-2 border-[#5b8dbf] p-3 rounded">
              <div className="text-[10px] text-[#6b7280] uppercase tracking-wider mb-1">
                Recommended Action
              </div>
              <div className="text-[12px] text-[#e8eaed] leading-relaxed">
                {analysis.recommendation}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Responder Candidates Section */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="h-12 border-b border-[#1e2530] flex items-center px-4">
          <span className="text-[12px] text-[#9ca3af] uppercase tracking-wider font-[500]">
            Responder Candidates
          </span>
          <span className="ml-auto text-[12px] text-[#5b8dbf] tabular-nums font-[500]">
            {responders.length}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto">
          {responders.map((responder) => {
            const VerificationIcon =
              verificationIcons[responder.verificationLevel];

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
                    {responder.skills.slice(0, 2).map((skill, index) => (
                      <span
                        key={index}
                        className="text-[9px] px-1.5 py-0.5 bg-[#1a2332] text-[#6b7280] rounded uppercase tracking-wider"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => onDispatch(responder.id, selectedIncident.id)}
                  disabled={responder.availability === "busy"}
                  className="w-full h-8 bg-[#1a2332] hover:bg-[#5b8dbf] disabled:hover:bg-[#1a2332] border border-[#2a3441] rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
                >
                  <Send className="w-3.5 h-3.5 text-[#9ca3af] group-hover:text-white transition-colors" />
                  <span className="text-[11px] text-[#9ca3af] group-hover:text-white uppercase tracking-wider font-[500] transition-colors">
                    Dispatch
                  </span>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
