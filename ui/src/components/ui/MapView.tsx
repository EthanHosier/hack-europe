import { useState } from "react";
import type { Incident } from "./IncidentQueue";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

interface MapViewProps {
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

export function MapView({
  incidents,
  selectedId,
  onSelectIncident,
}: MapViewProps) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const severityPriority = {
    critical: 4,
    high: 3,
    moderate: 2,
    low: 1,
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 0.25, 2));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 0.25, 0.5));
  };

  // Group incidents by proximity for clustering
  const clusterRadius = 40;
  const clusters: Array<{
    incidents: Incident[];
    x: number;
    y: number;
    severity: Incident["severity"];
  }> = [];

  incidents.forEach((incident) => {
    // Convert lat/lng to x/y coordinates (simplified)
    const x = ((incident.lng + 180) / 360) * 800;
    const y = ((90 - incident.lat) / 180) * 600;

    let addedToCluster = false;
    for (const cluster of clusters) {
      const distance = Math.sqrt(
        Math.pow(cluster.x - x, 2) + Math.pow(cluster.y - y, 2),
      );

      if (distance < clusterRadius) {
        cluster.incidents.push(incident);
        // Update severity to highest in cluster
        if (
          severityPriority[incident.severity] >
          severityPriority[cluster.severity]
        ) {
          cluster.severity = incident.severity;
        }
        addedToCluster = true;
        break;
      }
    }

    if (!addedToCluster) {
      clusters.push({
        incidents: [incident],
        x,
        y,
        severity: incident.severity,
      });
    }
  });

  return (
    <div className="flex-1 bg-[#0a0e1a] relative overflow-hidden">
      {/* Map controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <button
          onClick={handleZoomIn}
          className="w-8 h-8 bg-[#1a2332] border border-[#2a3441] rounded flex items-center justify-center hover:bg-[#1e2530] transition-colors"
        >
          <ZoomIn className="w-4 h-4 text-[#9ca3af]" />
        </button>
        <button
          onClick={handleZoomOut}
          className="w-8 h-8 bg-[#1a2332] border border-[#2a3441] rounded flex items-center justify-center hover:bg-[#1e2530] transition-colors"
        >
          <ZoomOut className="w-4 h-4 text-[#9ca3af]" />
        </button>
        <button className="w-8 h-8 bg-[#1a2332] border border-[#2a3441] rounded flex items-center justify-center hover:bg-[#1e2530] transition-colors">
          <Maximize2 className="w-4 h-4 text-[#9ca3af]" />
        </button>
      </div>

      {/* Map location label */}
      <div className="absolute top-4 left-4 z-10 px-3 py-1.5 bg-[#1a2332]/90 border border-[#2a3441] rounded backdrop-blur-sm">
        <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider">
          Stockholm Region • Sweden
        </span>
      </div>

      {/* Map container */}
      <div
        className="w-full h-full cursor-move"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg
          className="w-full h-full"
          viewBox="0 0 1200 800"
          style={{
            transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
            transition: isDragging ? "none" : "transform 0.2s ease-out",
          }}
        >
          {/* Background grid */}
          <defs>
            <pattern
              id="grid"
              width="40"
              height="40"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="#1e2530"
                strokeWidth="0.5"
              />
            </pattern>
          </defs>
          <rect width="1200" height="800" fill="#0a0e1a" />
          <rect width="1200" height="800" fill="url(#grid)" />

          {/* Stylized map regions */}
          {/* Main Stockholm area */}
          <path
            d="M 500,300 Q 520,280 550,290 L 580,310 Q 600,330 590,360 L 570,390 Q 550,410 520,400 L 490,380 Q 470,350 500,300 Z"
            fill="#141825"
            stroke="#2a3441"
            strokeWidth="1.5"
          />

          {/* Surrounding municipalities */}
          <path
            d="M 350,250 L 380,240 L 420,260 L 430,290 L 410,310 L 370,300 Z"
            fill="#0f1419"
            stroke="#2a3441"
            strokeWidth="1"
          />

          <path
            d="M 620,270 L 660,260 L 690,280 L 700,320 L 680,350 L 640,340 Z"
            fill="#0f1419"
            stroke="#2a3441"
            strokeWidth="1"
          />

          <path
            d="M 480,450 L 520,440 L 550,460 L 560,500 L 530,520 L 490,510 Z"
            fill="#0f1419"
            stroke="#2a3441"
            strokeWidth="1"
          />

          <path
            d="M 320,360 L 360,350 L 390,370 L 400,410 L 370,430 L 330,420 Z"
            fill="#0f1419"
            stroke="#2a3441"
            strokeWidth="1"
          />

          {/* Roads/connections */}
          <line
            x1="400"
            y1="275"
            x2="500"
            y2="330"
            stroke="#2a3441"
            strokeWidth="2"
            strokeDasharray="5,5"
          />
          <line
            x1="590"
            y1="340"
            x2="660"
            y2="300"
            stroke="#2a3441"
            strokeWidth="2"
            strokeDasharray="5,5"
          />
          <line
            x1="520"
            y1="400"
            x2="520"
            y2="460"
            stroke="#2a3441"
            strokeWidth="2"
            strokeDasharray="5,5"
          />

          {/* Water bodies */}
          <ellipse
            cx="750"
            cy="400"
            rx="80"
            ry="120"
            fill="#0d1520"
            stroke="#1e2530"
            strokeWidth="1"
          />

          {/* Incident markers and clusters */}
          {clusters.map((cluster, index) => {
            const isMultiple = cluster.incidents.length > 1;
            // const hasSelected = cluster.incidents.some(
            //   (i) => i.id === selectedId,
            // );

            if (isMultiple) {
              // Cluster marker
              return (
                <g key={index}>
                  {/* Outer glow */}
                  <circle
                    cx={cluster.x}
                    cy={cluster.y}
                    r="24"
                    fill={`${severityColors[cluster.severity]}15`}
                    className="animate-pulse"
                  />
                  {/* Cluster circle */}
                  <circle
                    cx={cluster.x}
                    cy={cluster.y}
                    r="16"
                    fill={severityColors[cluster.severity]}
                    stroke="#0a0e1a"
                    strokeWidth="2"
                    className="cursor-pointer hover:opacity-80 transition-opacity"
                  />
                  {/* Count */}
                  <text
                    x={cluster.x}
                    y={cluster.y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="text-[12px] font-[600] fill-white pointer-events-none"
                  >
                    {cluster.incidents.length}
                  </text>
                </g>
              );
            } else {
              // Single incident marker
              const incident = cluster.incidents[0];
              const isSelected = incident.id === selectedId;

              return (
                <g
                  key={incident.id}
                  onClick={() => onSelectIncident(incident.id)}
                  className="cursor-pointer"
                >
                  {/* Selected ring */}
                  {isSelected && (
                    <circle
                      cx={cluster.x}
                      cy={cluster.y}
                      r="14"
                      fill="none"
                      stroke="#5b8dbf"
                      strokeWidth="2"
                      className="animate-pulse"
                    />
                  )}
                  {/* Outer glow */}
                  <circle
                    cx={cluster.x}
                    cy={cluster.y}
                    r="12"
                    fill={`${severityColors[incident.severity]}20`}
                  />
                  {/* Pin */}
                  <circle
                    cx={cluster.x}
                    cy={cluster.y}
                    r="6"
                    fill={severityColors[incident.severity]}
                    stroke="#0a0e1a"
                    strokeWidth="1.5"
                    className="hover:opacity-80 transition-opacity"
                  />
                </g>
              );
            }
          })}

          {/* Region labels */}
          <text
            x="540"
            y="350"
            className="text-[11px] fill-[#6b7280] uppercase tracking-wider pointer-events-none"
            textAnchor="middle"
          >
            STOCKHOLM
          </text>
          <text
            x="390"
            y="280"
            className="text-[9px] fill-[#4b5563] uppercase tracking-wider pointer-events-none"
            textAnchor="middle"
          >
            SOLNA
          </text>
          <text
            x="665"
            y="300"
            className="text-[9px] fill-[#4b5563] uppercase tracking-wider pointer-events-none"
            textAnchor="middle"
          >
            LIDINGÖ
          </text>
          <text
            x="520"
            y="485"
            className="text-[9px] fill-[#4b5563] uppercase tracking-wider pointer-events-none"
            textAnchor="middle"
          >
            HUDDINGE
          </text>
        </svg>
      </div>

      {/* Map legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-[#1a2332]/90 border border-[#2a3441] rounded backdrop-blur-sm p-3">
        <div className="text-[10px] text-[#9ca3af] uppercase tracking-wider mb-2">
          Severity
        </div>
        <div className="flex flex-col gap-1.5">
          {Object.entries(severityColors).map(([severity, color]) => (
            <div key={severity} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-[11px] text-[#9ca3af] capitalize">
                {severity}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
