import { Activity, Shield, CheckCircle2 } from "lucide-react";

interface TopBarProps {
  activeIncidents: number;
  activeResponders: number;
}

export function TopBar({
  activeIncidents,
  activeResponders,
}: TopBarProps) {
  return (
    <div className="h-14 bg-[#0f1419] border-b border-[#1e2530] flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-[#5b8dbf]" />
          <span className="text-[15px] tracking-wide text-[#e8eaed] font-[500]">
            HERMESOS
          </span>
        </div>
        <div className="h-4 w-px bg-[#2a3441]" />
        <span className="text-[13px] text-[#9ca3af] tracking-wide">
          CONSOLE
        </span>
      </div>

      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#c94f5a]" />
          <div className="flex flex-col">
            <span className="text-[11px] text-[#6b7280] uppercase tracking-wider">
              Active Incidents
            </span>
            <span className="text-[15px] text-[#e8eaed] font-[500] tabular-nums">
              {activeIncidents}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#3d7a5e]" />
          <div className="flex flex-col">
            <span className="text-[11px] text-[#6b7280] uppercase tracking-wider">
              Active Responders
            </span>
            <span className="text-[15px] text-[#e8eaed] font-[500] tabular-nums">
              {activeResponders}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 bg-[#1a2332] rounded border border-[#2a3441]">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#3d7a5e]" />
          <span className="text-[12px] text-[#3d7a5e] uppercase tracking-wide font-[500]">
            Operational
          </span>
        </div>
      </div>
    </div>
  );
}
