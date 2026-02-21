import type { Incident } from "../components/ui/IncidentQueue";

// Stockholm region bounding boxes for realistic spread
const REGIONS: Record<string, { lat: [number, number]; lng: [number, number] }> = {
  "Södermalm":        { lat: [59.300, 59.320], lng: [18.040, 18.090] },
  "Gamla Stan":       { lat: [59.320, 59.332], lng: [18.060, 18.080] },
  "Östermalm":        { lat: [59.330, 59.355], lng: [18.070, 18.110] },
  "Vasastan":         { lat: [59.338, 59.358], lng: [18.030, 18.070] },
  "Kungsholmen":      { lat: [59.326, 59.343], lng: [18.010, 18.055] },
  "Lidingö":          { lat: [59.340, 59.380], lng: [18.110, 18.180] },
  "Nacka":            { lat: [59.290, 59.330], lng: [18.090, 18.180] },
  "Solna":            { lat: [59.355, 59.380], lng: [17.990, 18.040] },
  "Sundbyberg":       { lat: [59.358, 59.380], lng: [17.950, 17.995] },
  "Bromma":           { lat: [59.320, 59.355], lng: [17.930, 17.990] },
  "Hägersten":        { lat: [59.295, 59.320], lng: [17.980, 18.030] },
  "Farsta":           { lat: [59.240, 59.280], lng: [18.060, 18.120] },
  "Spånga":           { lat: [59.370, 59.400], lng: [17.880, 17.950] },
  "Hässelby":         { lat: [59.355, 59.385], lng: [17.820, 17.890] },
  "Täby":             { lat: [59.420, 59.460], lng: [18.040, 18.110] },
  "Huddinge":         { lat: [59.220, 59.265], lng: [17.950, 18.040] },
  "Tyresö":           { lat: [59.220, 59.255], lng: [18.180, 18.270] },
  "Upplands Väsby":   { lat: [59.490, 59.530], lng: [17.890, 17.980] },
};

const TYPES: Incident["type"][] = [
  "fire",
  "medical",
  "rescue",
  "disaster",
  "emergency",
  "other",
];
const SEVERITIES: Incident["severity"][] = ["critical", "high", "moderate", "low"];
const STATUSES: Incident["status"][] = ["unassigned", "matching", "assigned"];

// Weighted severity so critical is rarer
const SEVERITY_WEIGHTS = [0.10, 0.25, 0.40, 0.25]; // critical, high, moderate, low

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
  hotspotBias = 0.4,
): Incident[] {
  const regionNames = Object.keys(REGIONS);
  const centralRegions = ["Södermalm", "Gamla Stan", "Östermalm", "Vasastan", "Kungsholmen"];
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
      severity === "critical" ? [0.5, 0.3, 0.2] : [0.3, 0.35, 0.35],
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
    });
  }

  return incidents;
}