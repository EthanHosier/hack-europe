#!/usr/bin/env python3
"""
Seed geospatial emergency cases/events around a fixed center point.

Creates:
- deterministic "fixed" points within 200m
- dispersed points within 3km

Each point creates both:
- one row in "case"
- one row in event
"""

import argparse
import math
import os
import random
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

sys.path.append(os.path.dirname(__file__))
from env import SUPABASE_POSTGRES_URL


CENTER_LAT = 46.314625411042
CENTER_LNG = 8.259776396555727
EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Scenario:
    title: str
    summary: str
    category: str
    severity: int
    p2p: bool = False
    confidence: int = 80
    required_capability: str | None = None
    parsed_need_type: str | None = None
    recommended_action: str | None = None
    stress_level: str | None = None


SCENARIOS = [
    Scenario(
        title="EpiPen needed for allergic reaction",
        summary="Adult showing severe allergic reaction symptoms; needs EpiPen support immediately.",
        category="medical",
        severity=5,
        p2p=False,
        confidence=92,
        required_capability="Epinephrine auto-injector and airway management",
        parsed_need_type="Immediate anaphylaxis intervention",
        recommended_action="Dispatch nearest ALS unit with epinephrine supply",
        stress_level="High",
    ),
    Scenario(
        title="Suspected broken leg after fall",
        summary="Person unable to move after a fall; possible leg fracture and pain escalation.",
        category="rescue",
        severity=4,
        p2p=False,
        confidence=85,
        required_capability="Splinting equipment and pain management",
        parsed_need_type="Fracture stabilisation and extraction",
        recommended_action="Send rescue team with stretcher and splints",
        stress_level="High",
    ),
    Scenario(
        title="Family needs drinking water",
        summary="Group reports depleted water supply and dehydration risk in current conditions.",
        category="food_water",
        severity=3,
        p2p=True,
        confidence=88,
        required_capability="Potable water supply",
        parsed_need_type="Clean drinking water for group",
        recommended_action="Deliver water rations from nearest supply point",
        stress_level="Medium",
    ),
    Scenario(
        title="Vehicle needs fuel for evacuation",
        summary="Evacuation vehicle stranded with no fuel; movement blocked until refuel support.",
        category="fuel",
        severity=3,
        p2p=True,
        confidence=95,
        required_capability="Portable fuel canister",
        parsed_need_type="Vehicle refuelling to resume evacuation",
        recommended_action="Dispatch fuel resupply to vehicle location",
        stress_level="Medium",
    ),
    Scenario(
        title="Minor injury needs assessment",
        summary="Individual with non-life-threatening injury requesting first response assessment.",
        category="medical",
        severity=2,
        p2p=True,
        confidence=78,
        required_capability="Basic first aid kit",
        parsed_need_type="Wound assessment and dressing",
        recommended_action="Send nearby peer volunteer with first aid supplies",
        stress_level="Low",
    ),
    Scenario(
        title="Temporary shelter requested",
        summary="People exposed to weather conditions need short-term shelter and blankets.",
        category="shelter",
        severity=3,
        p2p=True,
        confidence=82,
        required_capability="Emergency blankets and temporary cover",
        parsed_need_type="Weather protection for exposed group",
        recommended_action="Direct group to nearest shelter or deploy tent kit",
        stress_level="Medium",
    ),
]

# Deterministic radial offsets for fixed 200m cluster (distance_m, bearing_deg)
FIXED_OFFSETS = [
    (20, 15),
    (35, 70),
    (55, 130),
    (75, 195),
    (95, 250),
    (115, 315),
    (140, 40),
    (165, 110),
    (180, 175),
    (190, 240),
    (198, 300),
    (200, 350),
]


def destination_point(
    lat_deg: float, lng_deg: float, bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """Project a point from origin by bearing+distance using spherical earth."""
    lat1 = math.radians(lat_deg)
    lng1 = math.radians(lng_deg)
    bearing = math.radians(bearing_deg)
    angular_distance = distance_m / EARTH_RADIUS_M

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lng2 = lng1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )

    return math.degrees(lat2), math.degrees(lng2)


def build_fixed_points(count: int) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for i in range(count):
        distance_m, bearing_deg = FIXED_OFFSETS[i % len(FIXED_OFFSETS)]
        lat, lng = destination_point(CENTER_LAT, CENTER_LNG, bearing_deg, distance_m)
        points.append((lat, lng))
    return points


def build_dispersed_points(
    count: int, seed: int, min_radius_m: float = 200.0, max_radius_m: float = 3000.0
) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    points: list[tuple[float, float]] = []
    for _ in range(count):
        bearing_deg = rng.uniform(0, 360)
        # sqrt(random) for area-uniform distribution across ring.
        u = rng.random()
        radius_m = math.sqrt(
            u * (max_radius_m * max_radius_m - min_radius_m * min_radius_m)
            + min_radius_m * min_radius_m
        )
        lat, lng = destination_point(CENTER_LAT, CENTER_LNG, bearing_deg, radius_m)
        points.append((lat, lng))
    return points


def build_incidents(total: int, seed: int) -> list[Scenario]:
    rng = random.Random(seed)
    incidents: list[Scenario] = []
    for i in range(total):
        # Ensure requested emergency examples are always represented.
        if i < 4:
            incidents.append(SCENARIOS[i])
            continue
        incidents.append(rng.choice(SCENARIOS))
    return incidents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed emergency geospatial cases/events.")
    parser.add_argument("--fixed-count", type=int, default=12)
    parser.add_argument("--dispersed-count", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rows to be inserted without writing to DB.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.fixed_count < 0 or args.dispersed_count < 0:
        raise ValueError("Counts must be >= 0.")
    if args.fixed_count == 0 and args.dispersed_count == 0:
        raise ValueError("At least one of --fixed-count or --dispersed-count must be > 0.")


def insert_case_and_event(
    cur: psycopg.Cursor, scenario: Scenario, lat: float, lng: float, timestamp: datetime
) -> tuple[str, str]:
    case_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())

    cur.execute(
        """
        INSERT INTO "case" (id, title, summary, severity, status, category,
            stress_level, p2p, confidence, required_capability, parsed_need_type,
            recommended_action, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            case_id,
            scenario.title,
            scenario.summary,
            scenario.severity,
            "Open",
            scenario.category,
            scenario.stress_level,
            scenario.p2p,
            scenario.confidence,
            scenario.required_capability,
            scenario.parsed_need_type,
            scenario.recommended_action,
            timestamp,
            timestamp,
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
            timestamp,
            f"{scenario.title}. {scenario.summary}",
            lat,
            lng,
        ),
    )

    return case_id, event_id


def print_summary(
    inserted_count: int,
    category_counter: Counter,
    points: list[tuple[float, float]],
) -> None:
    min_lat = min(lat for lat, _ in points)
    max_lat = max(lat for lat, _ in points)
    min_lng = min(lng for _, lng in points)
    max_lng = max(lng for _, lng in points)

    print("\n=== Seed Summary ===")
    print(f"Total inserted: {inserted_count}")
    print("By category:")
    for category, count in sorted(category_counter.items()):
        print(f"  - {category}: {count}")
    print("Coordinate bounds:")
    print(f"  - latitude:  {min_lat:.7f} .. {max_lat:.7f}")
    print(f"  - longitude: {min_lng:.7f} .. {max_lng:.7f}")


def main() -> None:
    args = parse_args()
    validate_args(args)

    fixed_points = build_fixed_points(args.fixed_count)
    dispersed_points = build_dispersed_points(args.dispersed_count, seed=args.seed)
    all_points = fixed_points + dispersed_points

    scenarios = build_incidents(len(all_points), seed=args.seed)
    now = datetime.now(UTC)
    category_counter: Counter = Counter()

    print("Center:", f"{CENTER_LAT}, {CENTER_LNG}")
    print(f"Fixed points (<=200m): {args.fixed_count}")
    print(f"Dispersed points (0.2km-3km): {args.dispersed_count}")
    print(f"Total points: {len(all_points)}")

    if args.dry_run:
        print("\nDry-run preview:")
        for i, ((lat, lng), scenario) in enumerate(zip(all_points, scenarios), start=1):
            print(
                f"{i:03d} | {scenario.category:10s} | sev {scenario.severity} | "
                f"{lat:.7f}, {lng:.7f} | {scenario.title}"
            )
            category_counter[scenario.category] += 1
        print_summary(len(all_points), category_counter, all_points)
        return

    # Disable auto-prepared statements for compatibility with transaction poolers
    # (e.g. Supabase PgBouncer), which can raise DuplicatePreparedStatement errors.
    with psycopg.connect(
        SUPABASE_POSTGRES_URL,
        row_factory=dict_row,
        prepare_threshold=None,
    ) as conn:
        with conn.cursor() as cur:
            for idx, ((lat, lng), scenario) in enumerate(zip(all_points, scenarios)):
                timestamp = now - timedelta(minutes=idx)
                insert_case_and_event(cur, scenario, lat, lng, timestamp)
                category_counter[scenario.category] += 1

        conn.commit()

    print_summary(len(all_points), category_counter, all_points)
    print("\nSeed complete.")


if __name__ == "__main__":
    main()
