#!/usr/bin/env python3
"""
Seed geospatial emergency cases/events across Stockholm regions.

Generates incidents in the same style as ui/src/test/generatePoints.ts:
- Stockholm-regional spread with hotspot bias toward central areas
- Types: fire, medical, rescue, disaster, emergency, other
- Severity-weighted distribution (critical rarer)
- Rich analysis fields per description index

Each incident creates both:
- one row in "case"
- one row in event
"""

import argparse
import os
import random
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

sys.path.append(os.path.dirname(__file__))
from env import SUPABASE_POSTGRES_URL


# ─── Regions ─────────────────────────────────────────────────────────────────

REGIONS: dict[str, dict[str, tuple[float, float]]] = {
    "Södermalm":      {"lat": (59.300, 59.320),  "lng": (18.040, 18.090)},
    "Gamla Stan":     {"lat": (59.320, 59.332),  "lng": (18.060, 18.080)},
    "Östermalm":      {"lat": (59.330, 59.355),  "lng": (18.070, 18.110)},
    "Vasastan":       {"lat": (59.338, 59.358),  "lng": (18.030, 18.070)},
    "Kungsholmen":    {"lat": (59.326, 59.343),  "lng": (18.010, 18.055)},
    "Lidingö":        {"lat": (59.340, 59.380),  "lng": (18.110, 18.180)},
    "Nacka":          {"lat": (59.290, 59.330),  "lng": (18.090, 18.180)},
    "Solna":          {"lat": (59.355, 59.380),  "lng": (17.990, 18.040)},
    "Sundbyberg":     {"lat": (59.358, 59.380),  "lng": (17.950, 17.995)},
    "Bromma":         {"lat": (59.320, 59.355),  "lng": (17.930, 17.990)},
    "Hägersten":      {"lat": (59.295, 59.320),  "lng": (17.980, 18.030)},
    "Farsta":         {"lat": (59.240, 59.280),  "lng": (18.060, 18.120)},
    "Spånga":         {"lat": (59.370, 59.400),  "lng": (17.880, 17.950)},
    "Hässelby":       {"lat": (59.355, 59.385),  "lng": (17.820, 17.890)},
    "Täby":           {"lat": (59.420, 59.460),  "lng": (18.040, 18.110)},
    "Huddinge":       {"lat": (59.220, 59.265),  "lng": (17.950, 18.040)},
    "Tyresö":         {"lat": (59.220, 59.255),  "lng": (18.180, 18.270)},
    "Upplands Väsby": {"lat": (59.490, 59.530),  "lng": (17.890, 17.980)},
}

CENTRAL_REGIONS = {"Södermalm", "Gamla Stan", "Östermalm", "Vasastan", "Kungsholmen"}

# ─── Types / severities / statuses ───────────────────────────────────────────

TYPES = ["fire", "medical", "rescue", "disaster", "emergency", "other"]

SEVERITIES = ["critical", "high", "moderate", "low"]
SEVERITY_WEIGHTS = [0.10, 0.25, 0.40, 0.25]

# Values understood by the frontend's toIncidentStatus() in App.tsx:
#   "In Progress" → matching | "Resolved" → assigned | anything else → unassigned
STATUSES = ["Open", "In Progress", "Resolved"]
STATUS_WEIGHTS_NORMAL   = [0.30, 0.35, 0.35]
STATUS_WEIGHTS_CRITICAL = [0.50, 0.30, 0.20]

SEVERITY_TO_INT: dict[str, int] = {
    "critical": 5, "high": 4, "moderate": 3, "low": 2,
}
SEVERITY_TO_STRESS: dict[str, str] = {
    "critical": "High", "high": "High", "moderate": "Medium", "low": "Low",
}

# ─── Descriptions & analysis (mirrors generatePoints.ts exactly) ─────────────

DESCRIPTIONS: dict[str, list[str]] = {
    "fire": [
        "Structure fire reported on residential building",
        "Vehicle fire blocking intersection",
        "Grass fire spreading toward residential area",
        "Electrical fire in commercial building",
        "Fire alarm triggered in high-rise, smoke confirmed",
    ],
    "medical": [
        "Cardiac arrest, bystander CPR in progress",
        "Multiple casualties from road traffic collision",
        "Unresponsive adult, unknown cause",
        "Suspected overdose at public location",
        "Severe allergic reaction reported",
    ],
    "rescue": [
        "Person trapped in elevator",
        "Water rescue — individual in distress",
        "Person reported trapped in vehicle after collision",
        "Cliff rescue, hiker stranded on slope",
        "Building collapse, occupants unaccounted for",
    ],
    "disaster": [
        "Flooding in low-lying residential streets",
        "Gas main rupture, area evacuation in progress",
        "Major power outage affecting critical infrastructure",
        "Bridge structural damage reported",
        "Chemical spill at industrial facility",
    ],
    "emergency": [
        "Unattended package reported at transit hub",
        "Large crowd disturbance with injuries",
        "Missing child — last seen near waterfront",
        "Suspicious device reported in public area",
        "Hazmat leak from overturned vehicle",
    ],
    "other": [
        "Non-categorized assistance request reported",
        "Public safety incident under assessment",
        "Unknown incident type awaiting triage",
        "General emergency support requested",
        "Unclassified field report submitted",
    ],
}

ANALYSIS: dict[str, list[dict[str, str]]] = {
    "fire": [
        {
            "parsed_need_type": "Structure fire — residential",
            "required_capability": "Fire suppression / Ladder unit",
            "recommended_action": (
                "Deploy ladder truck and two pumper units. Evacuate adjacent floors. "
                "Establish water supply from nearest hydrant."
            ),
        },
        {
            "parsed_need_type": "Vehicle fire — road obstruction",
            "required_capability": "Fire suppression / Traffic management",
            "recommended_action": (
                "Dispatch one pumper unit. Coordinate with traffic control to reroute vehicles. "
                "Check for fuel leak before approach."
            ),
        },
        {
            "parsed_need_type": "Wildland-urban interface fire",
            "required_capability": "Fire suppression / Evacuation coordination",
            "recommended_action": (
                "Issue precautionary evacuation notice for adjacent streets. Deploy brush unit. "
                "Monitor wind direction for spread assessment."
            ),
        },
        {
            "parsed_need_type": "Electrical fire — commercial",
            "required_capability": "Fire suppression / Electrical hazard",
            "recommended_action": (
                "Request utility company to isolate power feed. Do not use water; deploy CO2 units. "
                "Establish 50 m exclusion zone."
            ),
        },
        {
            "parsed_need_type": "High-rise smoke — alarm confirmed",
            "required_capability": "Fire suppression / High-rise ops",
            "recommended_action": (
                "Stage in lobby, do not use lifts. Send advance team to floor below alarm origin. "
                "Initiate partial building evacuation."
            ),
        },
    ],
    "medical": [
        {
            "parsed_need_type": "Cardiac arrest — CPR in progress",
            "required_capability": "Advanced Life Support (ALS)",
            "recommended_action": (
                "Dispatch ALS unit immediately. Confirm bystander CPR quality via call handler. "
                "Nearest defibrillator location sent to responder."
            ),
        },
        {
            "parsed_need_type": "Mass casualty — road traffic collision",
            "required_capability": "Mass casualty triage / ALS",
            "recommended_action": (
                "Activate MCI protocol. Dispatch two ALS units and one BLS transport. "
                "Request trauma centre pre-alert. Establish triage area away from traffic."
            ),
        },
        {
            "parsed_need_type": "Unconscious patient — unknown cause",
            "required_capability": "Basic Life Support (BLS)",
            "recommended_action": (
                "Dispatch BLS unit with ALS backup. Collect medication history if available. "
                "Monitor airway; place in recovery position if breathing."
            ),
        },
        {
            "parsed_need_type": "Suspected substance overdose",
            "required_capability": "ALS / Naloxone administration",
            "recommended_action": (
                "Dispatch ALS-capable responder with naloxone. Ensure scene safety before approach. "
                "Notify nearest emergency department."
            ),
        },
        {
            "parsed_need_type": "Anaphylaxis — severe allergic reaction",
            "required_capability": "ALS / Epinephrine administration",
            "recommended_action": (
                "Deploy ALS unit. Administer epinephrine if prescribed auto-injector present. "
                "Prepare for airway management. Transport to hospital urgently."
            ),
        },
    ],
    "rescue": [
        {
            "parsed_need_type": "Entrapment — elevator",
            "required_capability": "Technical rescue / Lift engineer",
            "recommended_action": (
                "Dispatch technical rescue unit and contact building management for lift engineer. "
                "Confirm occupant is not injured before manual release."
            ),
        },
        {
            "parsed_need_type": "Water rescue — person in distress",
            "required_capability": "Swift water rescue / Boat unit",
            "recommended_action": (
                "Deploy swift-water rescue team. Do not allow untrained bystanders to enter water. "
                "Notify coast guard if open water."
            ),
        },
        {
            "parsed_need_type": "Vehicle entrapment — collision",
            "required_capability": "Extrication / Hydraulic tools",
            "recommended_action": (
                "Send heavy rescue with hydraulic spreaders. Stabilise vehicle before extrication. "
                "ALS unit on standby for trauma management."
            ),
        },
        {
            "parsed_need_type": "Cliff rescue — stranded hiker",
            "required_capability": "High-angle rope rescue",
            "recommended_action": (
                "Deploy mountain rescue team with rope equipment. Identify safe approach route. "
                "Request helicopter standby if ground access not possible."
            ),
        },
        {
            "parsed_need_type": "Structural collapse — persons unaccounted",
            "required_capability": "Urban search and rescue (USAR)",
            "recommended_action": (
                "Activate USAR team. Establish collapse zone perimeter. "
                "Deploy search dogs and acoustic detection equipment. Do not disturb debris."
            ),
        },
    ],
    "disaster": [
        {
            "parsed_need_type": "Flooding — residential streets",
            "required_capability": "Flood response / Boat evacuation",
            "recommended_action": (
                "Deploy flood response boats for resident evacuation. Coordinate with municipality "
                "for temporary shelter. Alert utility providers to isolate electricity in affected area."
            ),
        },
        {
            "parsed_need_type": "Gas main rupture — evacuation active",
            "required_capability": "Hazmat — gas / Utility coordination",
            "recommended_action": (
                "Establish 200 m exclusion zone. No ignition sources. "
                "Coordinate with gas utility for emergency shut-off. Account for all evacuated residents."
            ),
        },
        {
            "parsed_need_type": "Power outage — critical infrastructure",
            "required_capability": "Infrastructure liaison / Generator deployment",
            "recommended_action": (
                "Identify affected hospitals and care homes. Coordinate backup generator deployment. "
                "Liaise with grid operator for estimated restoration time."
            ),
        },
        {
            "parsed_need_type": "Structural damage — bridge",
            "required_capability": "Structural engineering assessment",
            "recommended_action": (
                "Close bridge to all traffic immediately. Request structural engineer for rapid assessment. "
                "Divert emergency routes via alternatives."
            ),
        },
        {
            "parsed_need_type": "Hazmat spill — industrial facility",
            "required_capability": "Hazmat Level B / CBRN",
            "recommended_action": (
                "Deploy Hazmat Level B team. Identify substance via MSDS if available. "
                "Establish hot, warm, and cold zones. Notify environmental agency."
            ),
        },
    ],
    "emergency": [
        {
            "parsed_need_type": "Unattended package — possible IED",
            "required_capability": "EOD / Evacuation coordination",
            "recommended_action": (
                "Do not touch or move package. Evacuate 100 m radius. "
                "Request EOD team. Suspend transit operations in immediate area."
            ),
        },
        {
            "parsed_need_type": "Civil disturbance with injuries",
            "required_capability": "Public order / Medical support",
            "recommended_action": (
                "Deploy public order unit with medical support. Establish triage point away from crowd. "
                "Identify instigators for de-escalation."
            ),
        },
        {
            "parsed_need_type": "Missing child — waterfront",
            "required_capability": "Search coordination / Water rescue standby",
            "recommended_action": (
                "Initiate immediate grid search of waterfront. Activate water rescue standby. "
                "Issue description to all units in sector."
            ),
        },
        {
            "parsed_need_type": "Suspicious device — public area",
            "required_capability": "EOD / Cordon management",
            "recommended_action": (
                "Establish 150 m cordon. Do not use radio transmitters within cordon. "
                "Request EOD and notify counter-terrorism liaison."
            ),
        },
        {
            "parsed_need_type": "Hazmat leak — overturned vehicle",
            "required_capability": "Hazmat / Extrication",
            "recommended_action": (
                "Identify substance before approach. Deploy Hazmat unit with extrication capability. "
                "Downwind evacuation. Alert hospitals to potential chemical casualties."
            ),
        },
    ],
    "other": [
        {
            "parsed_need_type": "Unclassified assistance request",
            "required_capability": "General response",
            "recommended_action": (
                "Dispatch nearest available unit for scene assessment. "
                "Classify incident on arrival and escalate if required."
            ),
        },
        {
            "parsed_need_type": "Public safety incident — under assessment",
            "required_capability": "General response",
            "recommended_action": (
                "Send patrol unit to assess. Gather further information from caller. "
                "Upgrade resource level once nature confirmed."
            ),
        },
        {
            "parsed_need_type": "Unknown incident — awaiting triage",
            "required_capability": "General response / Triage",
            "recommended_action": (
                "Assign triage officer. Do not commit specialist resources until incident type confirmed. "
                "Keep channel open with caller."
            ),
        },
        {
            "parsed_need_type": "General emergency support",
            "required_capability": "General response",
            "recommended_action": (
                "Dispatch multi-capability unit. Await scene report before further escalation."
            ),
        },
        {
            "parsed_need_type": "Unclassified field report",
            "required_capability": "General response",
            "recommended_action": (
                "Treat as unknown risk until confirmed. Approach with caution. "
                "Provide scene update within 5 minutes of arrival."
            ),
        },
    ],
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _weighted_choice(rng: random.Random, items: list, weights: list):
    threshold = rng.random() * sum(weights)
    for item, weight in zip(items, weights):
        threshold -= weight
        if threshold <= 0:
            return item
    return items[-1]


# ─── Generation ───────────────────────────────────────────────────────────────

def generate_incidents(
    count: int,
    seed: int,
    hotspot_bias: float = 0.4,
    max_age_minutes: float = 90.0,
) -> list[dict]:
    rng = random.Random(seed)
    region_names = list(REGIONS.keys())
    central = [r for r in region_names if r in CENTRAL_REGIONS]
    outer   = [r for r in region_names if r not in CENTRAL_REGIONS]

    now = datetime.now(UTC)
    incidents: list[dict] = []

    for _ in range(count):
        region_name = rng.choice(central) if rng.random() < hotspot_bias else rng.choice(outer)
        bounds = REGIONS[region_name]
        lat = rng.uniform(*bounds["lat"])
        lng = rng.uniform(*bounds["lng"])

        incident_type = rng.choice(TYPES)
        severity      = _weighted_choice(rng, SEVERITIES, SEVERITY_WEIGHTS)
        weights       = STATUS_WEIGHTS_CRITICAL if severity == "critical" else STATUS_WEIGHTS_NORMAL
        status        = _weighted_choice(rng, STATUSES, weights)

        desc_idx    = rng.randint(0, len(DESCRIPTIONS[incident_type]) - 1)
        description = DESCRIPTIONS[incident_type][desc_idx]
        analysis    = ANALYSIS[incident_type][desc_idx]

        age_minutes = rng.random() * max_age_minutes
        timestamp   = now - timedelta(minutes=age_minutes)

        completed_at = None
        if status == "Resolved":
            completed_at = timestamp + timedelta(minutes=rng.randint(10, 60))

        incidents.append({
            "type":                incident_type,
            "title":               description,
            "summary":             f"{description}. {analysis['recommended_action']}",
            "region":              region_name,
            "severity":            severity,
            "status":              status,
            "lat":                 lat,
            "lng":                 lng,
            "timestamp":           timestamp,
            "completed_at":        completed_at,
            "p2p":                 rng.random() > 0.5,
            "confidence":          rng.randint(60, 99),
            "required_capability": analysis["required_capability"],
            "parsed_need_type":    analysis["parsed_need_type"],
            "recommended_action":  analysis["recommended_action"],
            "stress_level":        SEVERITY_TO_STRESS[severity],
        })

    return incidents


# ─── DB insertion ─────────────────────────────────────────────────────────────

def insert_case_and_event(cur: psycopg.Cursor, incident: dict) -> tuple[str, str]:
    case_id  = str(uuid.uuid4())
    event_id = str(uuid.uuid4())

    cur.execute(
        """
        INSERT INTO "case" (
            id, title, summary, severity, status, category,
            stress_level, p2p, confidence, required_capability, parsed_need_type,
            recommended_action, created_at, updated_at, completed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            case_id,
            incident["title"],
            incident["summary"],
            SEVERITY_TO_INT[incident["severity"]],
            incident["status"],
            incident["type"],
            incident["stress_level"],
            incident["p2p"],
            incident["confidence"],
            incident["required_capability"],
            incident["parsed_need_type"],
            incident["recommended_action"],
            incident["timestamp"],
            incident["timestamp"],
            incident["completed_at"],
        ),
    )

    cur.execute(
        """
        INSERT INTO event (id, case_id, timestamp, description, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            event_id,
            case_id,
            incident["timestamp"],
            incident["title"],
            incident["lat"],
            incident["lng"],
        ),
    )

    return case_id, event_id


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Stockholm emergency cases/events.")
    parser.add_argument("--count",        type=int,   default=36,  help="Number of incidents to generate (default: 36).")
    parser.add_argument("--hotspot-bias", type=float, default=0.4, help="Probability 0–1 of placing an incident in central Stockholm (default: 0.4).")
    parser.add_argument("--seed",         type=int,   default=42,  help="Random seed (default: 42).")
    parser.add_argument("--dry-run",      action="store_true",     help="Print rows without writing to DB.")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.count <= 0:
        raise ValueError("--count must be > 0.")
    if not 0.0 <= args.hotspot_bias <= 1.0:
        raise ValueError("--hotspot-bias must be between 0.0 and 1.0.")


def print_summary(
    inserted_count: int,
    type_counter: Counter,
    severity_counter: Counter,
    incidents: list[dict],
) -> None:
    lats = [i["lat"] for i in incidents]
    lngs = [i["lng"] for i in incidents]
    print("\n=== Seed Summary ===")
    print(f"Total inserted: {inserted_count}")
    print("By type:")
    for t in TYPES:
        print(f"  - {t}: {type_counter.get(t, 0)}")
    print("By severity:")
    for s in SEVERITIES:
        print(f"  - {s}: {severity_counter.get(s, 0)}")
    print("Coordinate bounds:")
    print(f"  - latitude:  {min(lats):.7f} .. {max(lats):.7f}")
    print(f"  - longitude: {min(lngs):.7f} .. {max(lngs):.7f}")


def main() -> None:
    args = parse_args()
    validate_args(args)

    incidents = generate_incidents(args.count, seed=args.seed, hotspot_bias=args.hotspot_bias)

    type_counter: Counter     = Counter()
    severity_counter: Counter = Counter()

    print(f"Count: {args.count} | Seed: {args.seed} | Hotspot bias: {args.hotspot_bias}")

    if args.dry_run:
        print("\nDry-run preview:")
        for i, inc in enumerate(incidents, start=1):
            print(
                f"{i:03d} | {inc['type']:10s} | {inc['severity']:8s} | {inc['status']:12s} | "
                f"{inc['lat']:.6f}, {inc['lng']:.6f} | {inc['title']}"
            )
            type_counter[inc["type"]]         += 1
            severity_counter[inc["severity"]] += 1
        print_summary(len(incidents), type_counter, severity_counter, incidents)
        return

    with psycopg.connect(
        SUPABASE_POSTGRES_URL,
        row_factory=dict_row,
        prepare_threshold=None,
    ) as conn:
        with conn.cursor() as cur:
            for inc in incidents:
                insert_case_and_event(cur, inc)
                type_counter[inc["type"]]         += 1
                severity_counter[inc["severity"]] += 1
        conn.commit()

    print_summary(len(incidents), type_counter, severity_counter, incidents)
    print("\nSeed complete.")


if __name__ == "__main__":
    main()
