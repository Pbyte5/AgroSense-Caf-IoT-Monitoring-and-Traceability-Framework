"""Synthetic farm and spatial record generation for the seed workflow."""

from __future__ import annotations

import random
import uuid
from typing import Any

from scripts.seed.spatial import PostGISSpatialGenerator
from scripts.seed.spatial_models import AGROSENSE_NAMESPACE


def generate_sample_seed_records(count: int = 5) -> list[dict[str, Any]]:
    """Generate deterministic sample farm records using the current PRNG state."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count debe ser un entero no negativo.")

    sample_records: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        farm_code = f"FIN-{i:04d}"
        sample_records.append(
            {
                "farm_id": str(uuid.uuid5(AGROSENSE_NAMESPACE, farm_code)),
                "farm_code": farm_code,
                "name": f"Hacienda Cafetera {i}",
                "altitude_msl": random.randint(1200, 1950),
                "total_area_ha": round(random.uniform(2.5, 25.0), 2),
                "has_pilot_sensors": random.random() < 0.3,
            }
        )
    return sample_records


def generate_spatial_seed_records(
    farms: list[dict[str, Any]], seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Attach PostGIS-ready geometries to farms and generate forest reserves.

    Returns EWKT for PostGIS and GeoJSON for the project's JSONB columns. This
    function generates records only; it does not connect to or write to a database.
    """
    if not isinstance(farms, list) or any(not isinstance(farm, dict) for farm in farms):
        raise ValueError("farms debe ser una lista de registros tipo diccionario.")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed debe ser un entero.")
    required_fields = {"farm_code", "name", "total_area_ha"}
    for index, farm in enumerate(farms):
        missing_fields = required_fields - farm.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"El registro de finca {index} no contiene: {missing}.")

    generator = PostGISSpatialGenerator(seed=seed)
    reserves = generator.generate_forest_reserves(count=min(len(farms), 5))
    reserve_records = [
        {
            "reserve_id": reserve.entity_id,
            "reserve_code": reserve.entity_code,
            "name": reserve.name,
            "area_ha": reserve.area_ha,
            "srid": reserve.srid,
            "geom_ewkt": reserve.ewkt,
            "polygon_geojson": reserve.geojson,
        }
        for reserve in reserves
    ]

    farm_records: list[dict[str, Any]] = []
    for farm in farms:
        polygon = generator.generate_farm_polygon(
            farm_code=farm["farm_code"],
            name=farm["name"],
            area_ha=farm["total_area_ha"],
        )
        overlaps_reserve = any(
            generator.polygons_intersect(polygon.points, reserve.points) for reserve in reserves
        )
        farm_records.append(
            {
                **farm,
                "latitude": polygon.center_lat,
                "longitude": polygon.center_lon,
                "has_valid_coords": polygon.is_valid_coords,
                "overlaps_reserve": overlaps_reserve,
                "srid": polygon.srid,
                "geom_ewkt": polygon.ewkt,
                "polygon_geojson": polygon.geojson,
            }
        )
    return farm_records, reserve_records
