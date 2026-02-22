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

    incidents.push({
      id: `test-${i.toString().padStart(4, "0")}`,
      type,
      description: randomFrom(DESCRIPTIONS[type]),
      region: regionName,
      severity,
      timestamp: randomTimestamp(90),
      status,
      lat,
      lng,
      completedAt: null,
      p2p: Math.random() > 0.5,
      confidence: Math.floor(randomBetween(60, 99)),
      requiredCapability: null,
      parsedNeedType: null,
      recommendedAction: null,
    });
  }

  return incidents;
}
