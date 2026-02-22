import type { Incident } from "../components/ui/IncidentQueue";

// Stockholm region bounding boxes for realistic spread
const REGIONS: Record<
  string,
  { lat: [number, number]; lng: [number, number] }
> = {
  Södermalm: { lat: [59.3, 59.32], lng: [18.04, 18.09] },
  "Gamla Stan": { lat: [59.32, 59.332], lng: [18.06, 18.08] },
  Östermalm: { lat: [59.33, 59.355], lng: [18.07, 18.11] },
  Vasastan: { lat: [59.338, 59.358], lng: [18.03, 18.07] },
  Kungsholmen: { lat: [59.326, 59.343], lng: [18.01, 18.055] },
  Lidingö: { lat: [59.34, 59.38], lng: [18.11, 18.18] },
  Nacka: { lat: [59.29, 59.33], lng: [18.09, 18.18] },
  Solna: { lat: [59.355, 59.38], lng: [17.99, 18.04] },
  Sundbyberg: { lat: [59.358, 59.38], lng: [17.95, 17.995] },
  Bromma: { lat: [59.32, 59.355], lng: [17.93, 17.99] },
  Hägersten: { lat: [59.295, 59.32], lng: [17.98, 18.03] },
  Farsta: { lat: [59.24, 59.28], lng: [18.06, 18.12] },
  Spånga: { lat: [59.37, 59.4], lng: [17.88, 17.95] },
  Hässelby: { lat: [59.355, 59.385], lng: [17.82, 17.89] },
  Täby: { lat: [59.42, 59.46], lng: [18.04, 18.11] },
  Huddinge: { lat: [59.22, 59.265], lng: [17.95, 18.04] },
  Tyresö: { lat: [59.22, 59.255], lng: [18.18, 18.27] },
  "Upplands Väsby": { lat: [59.49, 59.53], lng: [17.89, 17.98] },
};

const TYPES: Incident["type"][] = [
  "fire",
  "medical",
  "rescue",
  "disaster",
  "emergency",
  "other",
];
const SEVERITIES: Incident["severity"][] = [
  "critical",
  "high",
  "moderate",
  "low",
];
const STATUSES: Incident["status"][] = ["unassigned", "matching", "assigned"];

// Weighted severity so critical is rarer
const SEVERITY_WEIGHTS = [0.1, 0.25, 0.4, 0.25]; // critical, high, moderate, low

const DESCRIPTIONS: Record<Incident["type"], string[]> = {
  fire: [
    "Structure fire reported on residential building",
    "Vehicle fire blocking intersection",
    "Grass fire spreading toward residential area",
    "Electrical fire in commercial building",
    "Fire alarm triggered in high-rise, smoke confirmed",
  ],
  medical: [
    "Cardiac arrest, bystander CPR in progress",
    "Multiple casualties from road traffic collision",
    "Unresponsive adult, unknown cause",
    "Suspected overdose at public location",
    "Severe allergic reaction reported",
  ],
  rescue: [
    "Person trapped in elevator",
    "Water rescue — individual in distress",
    "Person reported trapped in vehicle after collision",
    "Cliff rescue, hiker stranded on slope",
    "Building collapse, occupants unaccounted for",
  ],
  disaster: [
    "Flooding in low-lying residential streets",
    "Gas main rupture, area evacuation in progress",
    "Major power outage affecting critical infrastructure",
    "Bridge structural damage reported",
    "Chemical spill at industrial facility",
  ],
  emergency: [
    "Unattended package reported at transit hub",
    "Large crowd disturbance with injuries",
    "Missing child — last seen near waterfront",
    "Suspicious device reported in public area",
    "Hazmat leak from overturned vehicle",
  ],
  other: [
    "Non-categorized assistance request reported",
    "Public safety incident under assessment",
    "Unknown incident type awaiting triage",
    "General emergency support requested",
    "Unclassified field report submitted",
  ],
};

// Per-type analysis data aligned to the descriptions above
// Each array index corresponds to the matching description index
const ANALYSIS: Record<
  Incident["type"],
  Array<{
    parsedNeedType: string;
    requiredCapability: string;
    recommendedAction: string;
  }>
> = {
  fire: [
    {
      parsedNeedType: "Structure fire — residential",
      requiredCapability: "Fire suppression / Ladder unit",
      recommendedAction:
        "Deploy ladder truck and two pumper units. Evacuate adjacent floors. Establish water supply from nearest hydrant.",
    },
    {
      parsedNeedType: "Vehicle fire — road obstruction",
      requiredCapability: "Fire suppression / Traffic management",
      recommendedAction:
        "Dispatch one pumper unit. Coordinate with traffic control to reroute vehicles. Check for fuel leak before approach.",
    },
    {
      parsedNeedType: "Wildland-urban interface fire",
      requiredCapability: "Fire suppression / Evacuation coordination",
      recommendedAction:
        "Issue precautionary evacuation notice for adjacent streets. Deploy brush unit. Monitor wind direction for spread assessment.",
    },
    {
      parsedNeedType: "Electrical fire — commercial",
      requiredCapability: "Fire suppression / Electrical hazard",
      recommendedAction:
        "Request utility company to isolate power feed. Do not use water; deploy CO₂ units. Establish 50 m exclusion zone.",
    },
    {
      parsedNeedType: "High-rise smoke — alarm confirmed",
      requiredCapability: "Fire suppression / High-rise ops",
      recommendedAction:
        "Stage in lobby, do not use lifts. Send advance team to floor below alarm origin. Initiate partial building evacuation.",
    },
  ],
  medical: [
    {
      parsedNeedType: "Cardiac arrest — CPR in progress",
      requiredCapability: "Advanced Life Support (ALS)",
      recommendedAction:
        "Dispatch ALS unit immediately. Confirm bystander CPR quality via call handler. Nearest defibrillator location sent to responder.",
    },
    {
      parsedNeedType: "Mass casualty — road traffic collision",
      requiredCapability: "Mass casualty triage / ALS",
      recommendedAction:
        "Activate MCI protocol. Dispatch two ALS units and one BLS transport. Request trauma centre pre-alert. Establish triage area away from traffic.",
    },
    {
      parsedNeedType: "Unconscious patient — unknown cause",
      requiredCapability: "Basic Life Support (BLS)",
      recommendedAction:
        "Dispatch BLS unit with ALS backup. Collect medication history if available. Monitor airway; place in recovery position if breathing.",
    },
    {
      parsedNeedType: "Suspected substance overdose",
      requiredCapability: "ALS / Naloxone administration",
      recommendedAction:
        "Dispatch ALS-capable responder with naloxone. Ensure scene safety before approach. Notify nearest emergency department.",
    },
    {
      parsedNeedType: "Anaphylaxis — severe allergic reaction",
      requiredCapability: "ALS / Epinephrine administration",
      recommendedAction:
        "Deploy ALS unit. Administer epinephrine if prescribed auto-injector present. Prepare for airway management. Transport to hospital urgently.",
    },
  ],
  rescue: [
    {
      parsedNeedType: "Entrapment — elevator",
      requiredCapability: "Technical rescue / Lift engineer",
      recommendedAction:
        "Dispatch technical rescue unit and contact building management for lift engineer. Confirm occupant is not injured before manual release.",
    },
    {
      parsedNeedType: "Water rescue — person in distress",
      requiredCapability: "Swift water rescue / Boat unit",
      recommendedAction:
        "Deploy swift-water rescue team. Do not allow untrained bystanders to enter water. Notify coast guard if open water.",
    },
    {
      parsedNeedType: "Vehicle entrapment — collision",
      requiredCapability: "Extrication / Hydraulic tools",
      recommendedAction:
        "Send heavy rescue with hydraulic spreaders. Stabilise vehicle before extrication. ALS unit on standby for trauma management.",
    },
    {
      parsedNeedType: "Cliff rescue — stranded hiker",
      requiredCapability: "High-angle rope rescue",
      recommendedAction:
        "Deploy mountain rescue team with rope equipment. Identify safe approach route. Request helicopter standby if ground access not possible.",
    },
    {
      parsedNeedType: "Structural collapse — persons unaccounted",
      requiredCapability: "Urban search and rescue (USAR)",
      recommendedAction:
        "Activate USAR team. Establish collapse zone perimeter. Deploy search dogs and acoustic detection equipment. Do not disturb debris.",
    },
  ],
  disaster: [
    {
      parsedNeedType: "Flooding — residential streets",
      requiredCapability: "Flood response / Boat evacuation",
      recommendedAction:
        "Deploy flood response boats for resident evacuation. Coordinate with municipality for temporary shelter. Alert utility providers to isolate electricity in affected area.",
    },
    {
      parsedNeedType: "Gas main rupture — evacuation active",
      requiredCapability: "Hazmat — gas / Utility coordination",
      recommendedAction:
        "Establish 200 m exclusion zone. No ignition sources. Coordinate with gas utility for emergency shut-off. Account for all evacuated residents.",
    },
    {
      parsedNeedType: "Power outage — critical infrastructure",
      requiredCapability: "Infrastructure liaison / Generator deployment",
      recommendedAction:
        "Identify affected hospitals and care homes. Coordinate backup generator deployment. Liaise with grid operator for estimated restoration time.",
    },
    {
      parsedNeedType: "Structural damage — bridge",
      requiredCapability: "Structural engineering assessment",
      recommendedAction:
        "Close bridge to all traffic immediately. Request structural engineer for rapid assessment. Divert emergency routes via alternatives.",
    },
    {
      parsedNeedType: "Hazmat spill — industrial facility",
      requiredCapability: "Hazmat Level B / CBRN",
      recommendedAction:
        "Deploy Hazmat Level B team. Identify substance via MSDS if available. Establish hot, warm, and cold zones. Notify environmental agency.",
    },
  ],
  emergency: [
    {
      parsedNeedType: "Unattended package — possible IED",
      requiredCapability: "EOD / Evacuation coordination",
      recommendedAction:
        "Do not touch or move package. Evacuate 100 m radius. Request EOD team. Suspend transit operations in immediate area.",
    },
    {
      parsedNeedType: "Civil disturbance with injuries",
      requiredCapability: "Public order / Medical support",
      recommendedAction:
        "Deploy public order unit with medical support. Establish triage point away from crowd. Identify instigators for de-escalation.",
    },
    {
      parsedNeedType: "Missing child — waterfront",
      requiredCapability: "Search coordination / Water rescue standby",
      recommendedAction:
        "Initiate immediate grid search of waterfront. Activate water rescue standby. Issue description to all units in sector.",
    },
    {
      parsedNeedType: "Suspicious device — public area",
      requiredCapability: "EOD / Cordon management",
      recommendedAction:
        "Establish 150 m cordon. Do not use radio transmitters within cordon. Request EOD and notify counter-terrorism liaison.",
    },
    {
      parsedNeedType: "Hazmat leak — overturned vehicle",
      requiredCapability: "Hazmat / Extrication",
      recommendedAction:
        "Identify substance before approach. Deploy Hazmat unit with extrication capability. Downwind evacuation. Alert hospitals to potential chemical casualties.",
    },
  ],
  other: [
    {
      parsedNeedType: "Unclassified assistance request",
      requiredCapability: "General response",
      recommendedAction:
        "Dispatch nearest available unit for scene assessment. Classify incident on arrival and escalate if required.",
    },
    {
      parsedNeedType: "Public safety incident — under assessment",
      requiredCapability: "General response",
      recommendedAction:
        "Send patrol unit to assess. Gather further information from caller. Upgrade resource level once nature confirmed.",
    },
    {
      parsedNeedType: "Unknown incident — awaiting triage",
      requiredCapability: "General response / Triage",
      recommendedAction:
        "Assign triage officer. Do not commit specialist resources until incident type confirmed. Keep channel open with caller.",
    },
    {
      parsedNeedType: "General emergency support",
      requiredCapability: "General response",
      recommendedAction:
        "Dispatch multi-capability unit. Await scene report before further escalation.",
    },
    {
      parsedNeedType: "Unclassified field report",
      requiredCapability: "General response",
      recommendedAction:
        "Treat as unknown risk until confirmed. Approach with caution. Provide scene update within 5 minutes of arrival.",
    },
  ],
};

function randomBetween(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

function weightedRandom<T>(items: T[], weights: number[]): T {
  const total = weights.reduce((a, b) => a + b, 0);
  let threshold = Math.random() * total;
  for (let i = 0; i < items.length; i++) {
    threshold -= weights[i];
    if (threshold <= 0) return items[i];
  }
  return items[items.length - 1];
}

function randomFrom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomTimestamp(maxAgeMinutes = 90): Date {
  const now = Date.now();
  return new Date(now - Math.random() * maxAgeMinutes * 60 * 1000);
}

/**
 * Generates `count` realistic test incidents spread across Stockholm regions.
 * Optionally seed with `hotspotBias` to cluster more incidents in central areas.
 *
 * @param count      Total number of incidents to generate (default: 120)
 * @param hotspotBias  0–1, probability that an incident is placed in a central region (default: 0.4)
 */
export function generateTestIncidents(
  count = 120,
  hotspotBias = 0.4
): Incident[] {
  const regionNames = Object.keys(REGIONS);
  const centralRegions = [
    "Södermalm",
    "Gamla Stan",
    "Östermalm",
    "Vasastan",
    "Kungsholmen",
  ];
  const outerRegions = regionNames.filter((r) => !centralRegions.includes(r));

  const incidents: Incident[] = [];

  for (let i = 0; i < count; i++) {
    const isCentral = Math.random() < hotspotBias;
    const regionName = isCentral
      ? randomFrom(centralRegions)
      : randomFrom(outerRegions);

    const bounds = REGIONS[regionName];
    const lat = randomBetween(bounds.lat[0], bounds.lat[1]);
    const lng = randomBetween(bounds.lng[0], bounds.lng[1]);

    const type = randomFrom(TYPES);
    const severity = weightedRandom(SEVERITIES, SEVERITY_WEIGHTS);
    const status = weightedRandom(
      STATUSES,
      severity === "critical" ? [0.5, 0.3, 0.2] : [0.3, 0.35, 0.35]
    );

    const descIdx = Math.floor(Math.random() * DESCRIPTIONS[type].length);
    const analysis = ANALYSIS[type][descIdx];

    incidents.push({
      id: `test-${i.toString().padStart(4, "0")}`,
      caseId: `test-case-${i.toString().padStart(4, "0")}`,
      type,
      description: DESCRIPTIONS[type][descIdx],
      region: regionName,
      severity,
      timestamp: randomTimestamp(90),
      status,
      lat,
      lng,
      completedAt: null,
      p2p: Math.random() > 0.5,
      confidence: Math.floor(randomBetween(60, 99)),
      requiredCapability: analysis.requiredCapability,
      parsedNeedType: analysis.parsedNeedType,
      recommendedAction: analysis.recommendedAction,
    });
  }

  return incidents;
}
