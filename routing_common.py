"""Shared constants and data model for the location and routing optimization tool.

Used by generate_data.py, validate_data.py, and analyze_routes.py so all
three scripts agree on what a valid location record looks like.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Bounding box of the demo service area (greater Athens, Greece).
LAT_RANGE = (37.90, 38.10)
LON_RANGE = (23.60, 23.90)

RAW_DATA_PATH = "data/locations_raw.csv"
VALIDATED_DATA_PATH = "data/locations_validated.csv"
VALIDATION_REPORT_PATH = "data/validation_report.txt"
OUTPUT_WORKBOOK_PATH = "output/routing_analysis.xlsx"
OUTPUT_MAP_PATH = "output/route_map.png"

CSV_FIELDS = [
    "location_id",
    "location_type",
    "name",
    "lat",
    "lon",
    "demand_units",
    "service_min",
    "fixed_annual_cost",
]


class Location(BaseModel):
    """Either a delivery stop (customer) or a candidate site for a new depot.

    Customers need demand_units > 0 (units delivered per day) and a service time;
    candidate sites need fixed_annual_cost > 0 (rent, staff, utilities for running the site).
    """

    model_config = ConfigDict(extra="ignore")

    location_id: str = Field(min_length=1)
    location_type: Literal["customer", "candidate_site"]
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    demand_units: float = Field(ge=0)
    service_min: float = Field(ge=0)
    fixed_annual_cost: float = Field(ge=0)

    @model_validator(mode="after")
    def check_type_fields(self):
        if self.location_type == "customer" and self.demand_units <= 0:
            raise ValueError("customers need demand_units > 0")
        if self.location_type == "candidate_site" and self.fixed_annual_cost <= 0:
            raise ValueError("candidate sites need fixed_annual_cost > 0")
        return self
