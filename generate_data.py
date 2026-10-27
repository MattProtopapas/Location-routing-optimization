"""Generate a fake delivery network dataset with Faker.

Produces a CSV of locations: delivery stops (customers with a daily demand and
service time) clustered around a few neighbourhoods, and candidate sites for a
new depot (with a yearly fixed cost, higher near the centre). The rest of the
pipeline (validate_data.py, analyze_routes.py) consumes it. A small percentage
of rows are deliberately corrupted (out-of-range coordinates, negative demand,
unknown location types, blanks, duplicate IDs) so validate_data.py has real
work to do - pass --error-rate 0 for a perfectly clean dataset.
"""

import argparse
import csv
import os
import random

from faker import Faker

from routing_common import CSV_FIELDS, LAT_RANGE, LON_RANGE, RAW_DATA_PATH


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def generate_customers(fake: Faker, count: int, clusters: int) -> list[dict]:
    # Neighbourhood centres that the customers cluster around.
    centres = [(random.uniform(*LAT_RANGE), random.uniform(*LON_RANGE)) for _ in range(clusters)]
    rows = []
    for i in range(1, count + 1):
        lat_c, lon_c = random.choice(centres)
        rows.append(
            {
                "location_id": f"C-{i:03d}",
                "location_type": "customer",
                "name": fake.company(),
                "lat": round(clamp(random.gauss(lat_c, 0.025), *LAT_RANGE), 5),
                "lon": round(clamp(random.gauss(lon_c, 0.035), *LON_RANGE), 5),
                "demand_units": random.randint(3, 25),
                "service_min": random.choice([5, 10, 10, 15, 20]),
                "fixed_annual_cost": 0,
            }
        )
    return rows


def generate_sites(fake: Faker, count: int) -> list[dict]:
    mid_lat, mid_lon = sum(LAT_RANGE) / 2, sum(LON_RANGE) / 2
    rows = []
    for i in range(1, count + 1):
        lat = random.uniform(*LAT_RANGE)
        lon = random.uniform(*LON_RANGE)
        # Central sites cost more to rent than peripheral ones: a genuine trade-off with proximity.
        centrality = 1 - min(1.0, (abs(lat - mid_lat) / 0.1 + abs(lon - mid_lon) / 0.15) / 2)
        rows.append(
            {
                "location_id": f"S-{i:02d}",
                "location_type": "candidate_site",
                "name": f"{fake.city()} Depot",
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "demand_units": 0,
                "service_min": 0,
                "fixed_annual_cost": round(random.uniform(30_000, 40_000) * (1 + 0.4 * centrality), -2),
            }
        )
    return rows


def corrupt_row(row: dict) -> dict:
    """Introduce one realistic data-quality issue into a row, in place."""
    issue = random.choice(["bad_latitude", "negative_demand", "bad_type", "blank_name", "missing_cost"])
    if issue == "bad_latitude":
        row["lat"] = 95.2
    elif issue == "negative_demand":
        row["location_type"], row["demand_units"] = "customer", -abs(row["demand_units"] or 10)
    elif issue == "bad_type":
        row["location_type"] = "warehouse"
    elif issue == "blank_name":
        row["name"] = ""
    elif issue == "missing_cost":
        row["location_type"], row["fixed_annual_cost"] = "candidate_site", 0
    return row


def generate_dataset(customers: int, sites: int, clusters: int, error_rate: float, seed: int | None) -> list[dict]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)
    fake = Faker()

    rows = generate_customers(fake, customers, clusters) + generate_sites(fake, sites)

    n_errors = round(len(rows) * error_rate)
    for row in random.sample(rows, k=min(n_errors, len(rows))):
        corrupt_row(row)

    # Inject a duplicate location ID to exercise the validator's duplicate check.
    if error_rate > 0 and len(rows) > 1:
        dup = dict(rows[0])
        dup["location_id"] = rows[-1]["location_id"]
        rows.append(dup)

    return rows


def write_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a fake delivery network for the location/routing pipeline.")
    parser.add_argument("--customers", type=int, default=40, help="Number of delivery stops (default: 40)")
    parser.add_argument("--sites", type=int, default=8, help="Number of candidate depot sites (default: 8)")
    parser.add_argument("--clusters", type=int, default=4, help="Number of neighbourhood clusters customers form (default: 4)")
    parser.add_argument(
        "--error-rate",
        type=float,
        default=0.05,
        help="Fraction of rows (0-1) to deliberately corrupt, to exercise validate_data.py (default: 0.05)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible output")
    parser.add_argument("--output", type=str, default=RAW_DATA_PATH, help="Path to write the raw CSV to")
    args = parser.parse_args()

    rows = generate_dataset(args.customers, args.sites, args.clusters, args.error_rate, args.seed)
    write_csv(rows, args.output)
    print(f"Generated {len(rows)} rows ({round(args.error_rate * 100)}% target error rate) -> {args.output}")


if __name__ == "__main__":
    main()
