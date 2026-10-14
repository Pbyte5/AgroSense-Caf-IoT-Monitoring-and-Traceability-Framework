"""AgroSense Café — Deterministic synthetic dataset generator using Faker.

Generates realistic, localized synthetic records for all operational entities
with fixed PRNG seeding and deterministic UUIDv5 primary keys derived from
natural business keys (Deliverable E-03, CT-06).
"""

from __future__ import annotations

import hashlib
import os
import random
import uuid
from datetime import date
from typing import Any

from faker import Faker

from .agronomy import (
    evaluate_fertilizer_recommendation,
    normalize_soil_lab_values,
)
from .spatial import PostGISSpatialGenerator
from .spatial_models import AGROSENSE_NAMESPACE

DEFAULT_DEPARTMENTS: list[dict[str, str]] = [
    {"dane_code": "05", "name": "Antioquia"},
    {"dane_code": "17", "name": "Caldas"},
    {"dane_code": "41", "name": "Huila"},
    {"dane_code": "73", "name": "Tolima"},
    {"dane_code": "19", "name": "Cauca"},
    {"dane_code": "52", "name": "Nariño"},
    {"dane_code": "63", "name": "Quindío"},
    {"dane_code": "66", "name": "Risaralda"},
    {"dane_code": "68", "name": "Santander"},
    {"dane_code": "20", "name": "Cesar"},
]

DEFAULT_MUNICIPALITIES: list[dict[str, Any]] = [
    {"dane_code": "05045", "name": "Andes", "department_dane": "05", "altitude_avg_masl": 1350},
    {"dane_code": "05368", "name": "Jericó", "department_dane": "05", "altitude_avg_masl": 1967},
    {"dane_code": "05282", "name": "Fredonia", "department_dane": "05", "altitude_avg_masl": 1800},
    {
        "dane_code": "05101",
        "name": "Ciudad Bolívar",
        "department_dane": "05",
        "altitude_avg_masl": 1400,
    },
    {"dane_code": "17174", "name": "Chinchiná", "department_dane": "17", "altitude_avg_masl": 1378},
    {"dane_code": "17001", "name": "Manizales", "department_dane": "17", "altitude_avg_masl": 2150},
    {"dane_code": "17524", "name": "Palestina", "department_dane": "17", "altitude_avg_masl": 1630},
    {"dane_code": "41551", "name": "Pitalito", "department_dane": "41", "altitude_avg_masl": 1318},
    {"dane_code": "41298", "name": "Garzón", "department_dane": "41", "altitude_avg_masl": 1400},
    {"dane_code": "41006", "name": "Acevedo", "department_dane": "41", "altitude_avg_masl": 1348},
    {
        "dane_code": "41668",
        "name": "San Agustín",
        "department_dane": "41",
        "altitude_avg_masl": 1730,
    },
    {"dane_code": "73001", "name": "Ibagué", "department_dane": "73", "altitude_avg_masl": 1285},
    {"dane_code": "73411", "name": "Líbano", "department_dane": "73", "altitude_avg_masl": 1565},
    {"dane_code": "73555", "name": "Planadas", "department_dane": "73", "altitude_avg_masl": 1450},
    {"dane_code": "63001", "name": "Armenia", "department_dane": "63", "altitude_avg_masl": 1480},
    {"dane_code": "63130", "name": "Calarcá", "department_dane": "63", "altitude_avg_masl": 1573},
    {"dane_code": "63190", "name": "Circasia", "department_dane": "63", "altitude_avg_masl": 1772},
    {"dane_code": "66001", "name": "Pereira", "department_dane": "66", "altitude_avg_masl": 1411},
    {
        "dane_code": "66682",
        "name": "Santa Rosa de Cabal",
        "department_dane": "66",
        "altitude_avg_masl": 1715,
    },
    {"dane_code": "19001", "name": "Popayán", "department_dane": "19", "altitude_avg_masl": 1760},
    {"dane_code": "19355", "name": "Inzá", "department_dane": "19", "altitude_avg_masl": 1800},
    {"dane_code": "52001", "name": "Pasto", "department_dane": "52", "altitude_avg_masl": 2527},
    {"dane_code": "52399", "name": "La Unión", "department_dane": "52", "altitude_avg_masl": 1745},
]

DEFAULT_COFFEE_VARIETIES: list[dict[str, Any]] = [
    {
        "variety_id": 1,
        "name": "Castillo",
        "rust_resistance_level": "HIGH",
        "optimal_temp_min_c": 17.0,
        "optimal_temp_max_c": 24.0,
    },
    {
        "variety_id": 2,
        "name": "Caturra",
        "rust_resistance_level": "LOW",
        "optimal_temp_min_c": 16.0,
        "optimal_temp_max_c": 23.0,
    },
    {
        "variety_id": 3,
        "name": "Colombia",
        "rust_resistance_level": "HIGH",
        "optimal_temp_min_c": 17.5,
        "optimal_temp_max_c": 24.5,
    },
    {
        "variety_id": 4,
        "name": "Geisha",
        "rust_resistance_level": "LOW",
        "optimal_temp_min_c": 15.0,
        "optimal_temp_max_c": 21.0,
    },
    {
        "variety_id": 5,
        "name": "Tabi",
        "rust_resistance_level": "HIGH",
        "optimal_temp_min_c": 16.5,
        "optimal_temp_max_c": 23.5,
    },
    {
        "variety_id": 6,
        "name": "Bourbon",
        "rust_resistance_level": "LOW",
        "optimal_temp_min_c": 16.0,
        "optimal_temp_max_c": 22.0,
    },
    {
        "variety_id": 7,
        "name": "Typica",
        "rust_resistance_level": "LOW",
        "optimal_temp_min_c": 15.5,
        "optimal_temp_max_c": 22.5,
    },
    {
        "variety_id": 8,
        "name": "Cenicafé 1",
        "rust_resistance_level": "HIGH",
        "optimal_temp_min_c": 17.0,
        "optimal_temp_max_c": 24.0,
    },
]

DEFAULT_SENSOR_TYPES: list[dict[str, str]] = [
    {
        "type_code": "SOIL_MOISTURE",
        "name": "Sensor de Humedad del Suelo",
        "unit": "%",
    },
    {
        "type_code": "TEMPERATURE",
        "name": "Sensor de Temperatura y Humedad Ambiente",
        "unit": "°C",
    },
    {
        "type_code": "PLUVIOMETER",
        "name": "Pluviómetro de Precipitación",
        "unit": "mm",
    },
    {
        "type_code": "MULTI_AGRO",
        "name": "Estación Agroclimática Multiparámetro",
        "unit": "multi",
    },
]

FARM_NAME_PREFIXES = [
    "Finca",
    "Hacienda",
    "Villa",
    "Granja",
    "El Paraíso de",
    "La Esperanza de",
    "San José de",
    "Santa Rita de",
    "El Porvenir de",
    "La Primavera de",
]


class AgroSenseFakerGenerator:
    """Generador determinista de datos sintéticos con integración de Faker.

    Asegura reproducibilidad e idempotencia estricta (CT-06) generando claves primarias
    UUIDv5 derivadas de claves naturales de negocio y sembrando Faker con semilla fija.
    """

    def __init__(self, seed: int = 42) -> None:
        """Inicializa el generador con semilla reproducible y localizaciones.

        Args:
            seed: Entero fijo para el estado pseudoaleatorio.
        """
        self.seed = seed
        self.rng = random.Random(seed)
        self.faker_es = Faker("es_CO")
        self.faker_en = Faker("en_US")
        self.faker_es.seed_instance(seed)
        self.faker_en.seed_instance(seed)
        self.spatial_gen = PostGISSpatialGenerator(seed=seed)

    @staticmethod
    def get_uuid5(natural_key: str) -> str:
        """Genera un UUIDv5 determinista en el namespace de AgroSense.

        Args:
            natural_key: Cadena con la clave natural de negocio.

        Returns:
            str: Representación canónica en cadena del UUIDv5 determinista.
        """
        return str(uuid.uuid5(AGROSENSE_NAMESPACE, natural_key))

    def generate_departments(self) -> list[dict[str, Any]]:
        """Genera catálogo estático de departamentos cafeteros de Colombia."""
        departments: list[dict[str, Any]] = []
        for idx, item in enumerate(DEFAULT_DEPARTMENTS, start=1):
            departments.append(
                {
                    "department_id": idx,
                    "dane_code": item["dane_code"],
                    "name": item["name"],
                    "created_at": "2026-01-01T00:00:00Z",
                }
            )
        return departments

    def generate_municipalities(
        self, departments: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Genera catálogo de municipios cafeteros vinculados a departamentos."""
        deps = departments or self.generate_departments()
        dep_map = {d["dane_code"]: d["department_id"] for d in deps}

        municipalities: list[dict[str, Any]] = []
        for idx, item in enumerate(DEFAULT_MUNICIPALITIES, start=1):
            department_id = dep_map.get(item["department_dane"], 1)
            municipalities.append(
                {
                    "municipality_id": idx,
                    "department_id": department_id,
                    "dane_code": item["dane_code"],
                    "name": item["name"],
                    "altitude_avg_masl": item["altitude_avg_masl"],
                    "created_at": "2026-01-01T00:00:00Z",
                }
            )
        return municipalities

    def generate_coffee_varieties(self) -> list[dict[str, Any]]:
        """Genera catálogo estático de variedades de café."""
        varieties: list[dict[str, Any]] = []
        for var in DEFAULT_COFFEE_VARIETIES:
            record = dict(var)
            record["rust_susceptibility"] = var["rust_resistance_level"]
            varieties.append(record)
        return varieties

    def generate_sensor_types(self) -> list[dict[str, Any]]:
        """Genera catálogo de tipos de hardware IoT."""
        types: list[dict[str, Any]] = []
        for idx, st in enumerate(DEFAULT_SENSOR_TYPES, start=1):
            types.append(
                {
                    "sensor_type_id": idx,
                    "type_code": st["type_code"],
                    "name": st["name"],
                    "unit": st["unit"],
                    "canonical_unit": st["unit"],
                    "expected_interval_min": 10,
                }
            )
        return types

    def generate_crop_nutrient_references(
        self, varieties: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Genera referencias nutricionales por variedad y etapa fenológica."""
        vars_list = varieties or self.generate_coffee_varieties()
        stages = ["VEGETATIVE", "FLOWERING", "GRAIN_FILLING", "POST_HARVEST"]
        references: list[dict[str, Any]] = []
        ref_id = 1

        for var in vars_list:
            var_id = var["variety_id"]
            for stage in stages:
                req_n = 150.0 + (ref_id % 5) * 10.0
                req_p = 30.0 + (ref_id % 3) * 5.0
                req_k = 120.0 + (ref_id % 4) * 8.0
                references.append(
                    {
                        "reference_id": ref_id,
                        "variety_id": var_id,
                        "crop_label": "coffee",
                        "growth_stage": stage,
                        "target_ph_min": 5.00,
                        "target_ph_max": 5.80,
                        "ph_min": 5.00,
                        "ph_max": 5.80,
                        "req_nitrogen_kg_ha": req_n,
                        "n_min_mg_kg": req_n,
                        "n_max_mg_kg": req_n + 50.0,
                        "req_phosphorus_kg_ha": req_p,
                        "p_min_mg_kg": req_p,
                        "p_max_mg_kg": req_p + 15.0,
                        "req_potassium_kg_ha": req_k,
                        "k_min_mg_kg": req_k,
                        "k_max_mg_kg": req_k + 40.0,
                    }
                )
                ref_id += 1
        return references

    def generate_users(self, count: int = 15) -> list[dict[str, Any]]:
        """Genera usuarios del sistema con Faker colombiano."""
        roles = ["ADMIN", "AGRONOMIST", "PRODUCER", "AUDITOR"]
        users: list[dict[str, Any]] = []

        for i in range(1, count + 1):
            full_name = self.faker_es.name()
            email_prefix = f"user_{i:03d}_{self.faker_es.user_name()}"
            email = f"{email_prefix}@agrosense.co"
            role = roles[(i - 1) % len(roles)]
            raw_pwd = f"AgroSense2026_{i}"
            password_hash = hashlib.sha256(raw_pwd.encode("utf-8")).hexdigest()

            users.append(
                {
                    "user_id": self.get_uuid5(email),
                    "full_name": full_name,
                    "email": email,
                    "role": role,
                    "password_hash": password_hash,
                    "is_active": True,
                }
            )
        return users

    def generate_producers(self, count: int = 30) -> list[dict[str, Any]]:
        """Genera caficultores con Faker colombiano y cédulas únicas."""
        producers: list[dict[str, Any]] = []

        for i in range(1, count + 1):
            doc_number = f"CC-109{i:05d}"
            producer_id = self.get_uuid5(doc_number)
            full_name = self.faker_es.name()
            phone = f"+57 3{self.rng.randint(10, 24)} {self.rng.randint(1000000, 9999999)}"
            email = f"productor_{i:04d}@cafetero.co"

            producers.append(
                {
                    "producer_id": producer_id,
                    "document_number": doc_number,
                    "full_name": full_name,
                    "phone_number": phone,
                    "email": email,
                    "cooperative_join_date": "2021-03-15",
                    "is_active": True,
                }
            )
        return producers

    def generate_international_buyers(self, count: int = 10) -> list[dict[str, Any]]:
        """Genera compradores internacionales con Faker inglés."""
        country_info = [
            ("Germany", "DE"),
            ("United States", "US"),
            ("Japan", "JP"),
            ("Netherlands", "NL"),
            ("Italy", "IT"),
            ("Canada", "CA"),
            ("South Korea", "KR"),
            ("France", "FR"),
        ]
        buyers: list[dict[str, Any]] = []

        for i in range(1, count + 1):
            client_id = f"BUY-INT-{i:03d}"
            buyer_id = self.get_uuid5(client_id)
            company_base = self.faker_en.company().replace(",", "").replace("'", "")
            company_name = f"{company_base} Coffee Traders"
            country, country_iso = country_info[(i - 1) % len(country_info)]
            raw_key = f"ak_live_{client_id}_{self.seed}"
            api_key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

            buyers.append(
                {
                    "buyer_id": buyer_id,
                    "client_id": client_id,
                    "api_client_id": client_id,
                    "company_name": company_name,
                    "country": country,
                    "country_iso_code": country_iso,
                    "api_key_hash": api_key_hash,
                    "rate_limit_per_min": 60,
                    "is_active": True,
                }
            )
        return buyers

    def generate_forest_reserves(self, count: int = 5) -> list[dict[str, Any]]:
        """Genera reservas forestales PostGIS en la región cafetera."""
        raw_reserves = self.spatial_gen.generate_forest_reserves(count=count)
        return [
            {
                "reserve_id": r.entity_id,
                "reserve_code": r.entity_code,
                "official_code": r.entity_code,
                "municipality_id": 1,
                "name": r.name,
                "protection_category": "Parque Nacional Natural",
                "area_ha": r.area_ha,
                "srid": r.srid,
                "geom_ewkt": r.ewkt,
                "polygon_geojson": r.geojson,
                "boundary_geojson": r.geojson,
                "created_at": "2026-01-01T00:00:00Z",
            }
            for r in raw_reserves
        ]

    def generate_farms(
        self,
        count: int = 30,
        pilot_count: int = 10,
        producers: list[dict[str, Any]] | None = None,
        municipalities: list[dict[str, Any]] | None = None,
        forest_reserves: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Genera fincas cafeteras con polígonos PostGIS, productores y municipios."""
        prods = producers or self.generate_producers(count=max(count // 2, 5))
        munis = municipalities or self.generate_municipalities()
        reserves = forest_reserves or self.generate_forest_reserves(count=3)

        raw_reserves = [
            self.spatial_gen.generate_forest_reserves(count=1)[0] if not reserves else None
        ]  # dummy fallback
        _ = raw_reserves  # reserve for overlap checking

        farms: list[dict[str, Any]] = []

        for i in range(1, count + 1):
            farm_code = f"FIN-{i:04d}"
            farm_id = self.get_uuid5(farm_code)
            producer = prods[(i - 1) % len(prods)]
            municipality = munis[(i - 1) % len(munis)]

            prefix = FARM_NAME_PREFIXES[(i - 1) % len(FARM_NAME_PREFIXES)]
            last_name = self.faker_es.last_name()
            farm_name = f"{prefix} {last_name}"

            total_area_ha = round(self.rng.uniform(3.0, 35.0), 2)
            cultivated_area_ha = round(total_area_ha * 0.75, 2)
            altitude_msl = self.rng.randint(1200, 1950)
            has_pilot_sensors = i <= pilot_count
            water_usage = round(self.rng.uniform(3.0, 5.0), 2)

            # Generación espacial de polígono
            polygon = self.spatial_gen.generate_farm_polygon(
                farm_code=farm_code,
                name=farm_name,
                area_ha=total_area_ha,
            )

            # Evaluar solapamiento con reservas
            overlaps_reserve = False
            for res in reserves:
                res_ewkt = res.get("geom_ewkt", "")
                if "POLYGON" in res_ewkt and hasattr(self.spatial_gen, "polygons_intersect"):
                    # Comprobación segura
                    overlaps_reserve = i % 10 == 0  # inyección determinista 10%

            farms.append(
                {
                    "farm_id": farm_id,
                    "farm_code": farm_code,
                    "municipality_id": municipality["municipality_id"],
                    "producer_id": producer["producer_id"],
                    "name": farm_name,
                    "producer_name": producer["full_name"],
                    "latitude": polygon.center_lat,
                    "longitude": polygon.center_lon,
                    "altitude_msl": altitude_msl,
                    "altitude_masl": altitude_msl,
                    "total_area_ha": total_area_ha,
                    "cultivated_area_ha": cultivated_area_ha,
                    "has_pilot_sensors": has_pilot_sensors,
                    "is_pilot_sensor_farm": has_pilot_sensors,
                    "water_usage_m3_ton": water_usage,
                    "is_active": True,
                    "overlaps_reserve": overlaps_reserve,
                    "has_valid_coords": True,
                    "srid": polygon.srid,
                    "geom_ewkt": polygon.ewkt,
                    "polygon_geojson": polygon.geojson,
                }
            )
        return farms

    def generate_farm_plots(
        self,
        farms: list[dict[str, Any]],
        plots_per_farm: int = 2,
        varieties: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Genera lotes productivos internos para cada finca."""
        vars_list = varieties or self.generate_coffee_varieties()
        plots: list[dict[str, Any]] = []

        for farm in farms:
            farm_code = farm["farm_code"]
            farm_id = farm["farm_id"]
            farm_area = farm["total_area_ha"]

            for plot_num in range(1, plots_per_farm + 1):
                natural_key = f"{farm_code}:PLOT-{plot_num}"
                plot_id = self.get_uuid5(natural_key)
                variety = vars_list[(plot_num - 1) % len(vars_list)]
                cultivated_area = round(farm_area / (plots_per_farm + 0.5), 2)
                tree_density = self.rng.randint(4500, 6500)
                crop_age = self.rng.randint(2, 7)

                plots.append(
                    {
                        "plot_id": plot_id,
                        "farm_id": farm_id,
                        "variety_id": variety["variety_id"],
                        "plot_number": plot_num,
                        "plot_name": f"Lote {plot_num}",
                        "cultivated_area_ha": cultivated_area,
                        "plot_area_ha": cultivated_area,
                        "tree_density_per_ha": tree_density,
                        "crop_age_years": crop_age,
                        "polygon_geojson": None,
                    }
                )
        return plots

    def generate_farm_reserve_overlaps(
        self,
        farms: list[dict[str, Any]],
        forest_reserves: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Genera vínculos de solapamiento entre fincas y reservas protegidas."""
        overlaps: list[dict[str, Any]] = []
        if not forest_reserves:
            return overlaps

        for farm in farms:
            if farm.get("overlaps_reserve", False):
                reserve = forest_reserves[0]
                natural_key = f"{farm['farm_code']}:{reserve['reserve_code']}"
                overlaps.append(
                    {
                        "overlap_id": self.get_uuid5(natural_key),
                        "farm_id": farm["farm_id"],
                        "reserve_id": reserve["reserve_id"],
                        "overlap_area_ha": round(self.rng.uniform(0.5, 3.5), 2),
                        "deforestation_free_status": "NON_COMPLIANT",
                        "verified_at": "2026-10-13T05:00:00Z",
                    }
                )
        return overlaps

    def generate_iot_sensors(
        self,
        farms: list[dict[str, Any]],
        sensor_types: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Genera 3 sensores por finca piloto (SOIL_MOISTURE, TEMPERATURE, PLUVIOMETER)."""
        pilot_farms = [f for f in farms if f.get("has_pilot_sensors", False)]
        stypes = ["SOIL_MOISTURE", "TEMPERATURE", "PLUVIOMETER"]
        sensors: list[dict[str, Any]] = []

        sensor_counter = 1
        for farm in pilot_farms:
            plot_id = self.get_uuid5(f"{farm['farm_code']}:PLOT-1")
            for stype in stypes:
                serial_number = f"SN-AGRO-{stype[:4]}-{sensor_counter:05d}"
                sensor_id = self.get_uuid5(serial_number)
                battery_level = round(self.rng.uniform(85.0, 100.0), 1)

                sensors.append(
                    {
                        "sensor_id": sensor_id,
                        "serial_number": serial_number,
                        "farm_id": farm["farm_id"],
                        "plot_id": plot_id,
                        "sensor_type": stype,
                        "sensor_type_id": stypes.index(stype) + 1,
                        "status": "ACTIVE",
                        "health_status": "ACTIVE",
                        "battery_level": battery_level,
                        "battery_level_pct": battery_level,
                        "clock_drift_seconds": 0,
                        "firmware_version": "v2.1.0",
                        "last_seen_at": "2026-10-13T05:00:00Z",
                        "last_transmission_at": "2026-10-13T05:00:00Z",
                        "installed_at": "2025-06-01",
                    }
                )
                sensor_counter += 1
        return sensors

    def generate_soil_lab_analyses(
        self,
        farms: list[dict[str, Any]],
        count: int = 30,
    ) -> list[dict[str, Any]]:
        """Genera análisis químicos de suelos por finca y fecha determinista."""
        textures = ["LOAM", "CLAY_LOAM", "SANDY_LOAM", "CLAY"]
        analyses: list[dict[str, Any]] = []

        for i in range(1, count + 1):
            farm = farms[(i - 1) % len(farms)]
            farm_code = farm["farm_code"]
            plot_id = self.get_uuid5(f"{farm_code}:PLOT-1")
            month = ((i - 1) % 12) + 1
            sample_date = f"2026-{month:02d}-15"
            natural_key = f"{farm_code}:{sample_date}"
            analysis_id = self.get_uuid5(natural_key)

            ph_level = round(self.rng.uniform(4.8, 6.2), 2)
            om_pct = round(self.rng.uniform(3.5, 8.5), 2)
            n_ppm = round(self.rng.uniform(20.0, 75.0), 2)
            p_ppm = round(self.rng.uniform(12.0, 48.0), 2)
            k_cmol = round(self.rng.uniform(0.35, 0.95), 2)
            texture = textures[(i - 1) % len(textures)]
            normalized_values = normalize_soil_lab_values(
                nitrogen_value=n_ppm,
                nitrogen_unit="ppm",
                phosphorus_value=p_ppm,
                phosphorus_unit="ppm",
                potassium_value=k_cmol,
                potassium_unit="cmol/kg",
            )

            analyses.append(
                {
                    "analysis_id": analysis_id,
                    "farm_id": farm["farm_id"],
                    "plot_id": plot_id,
                    "sample_date": sample_date,
                    "raw_unit_reported": "N=ppm;P=ppm;K=cmol/kg",
                    "ph_level": ph_level,
                    "ph_value": ph_level,
                    "organic_matter_pct": om_pct,
                    "nitrogen_ppm": n_ppm,
                    "nitrogen_mg_kg": float(normalized_values["nitrogen_mg_kg"]),
                    "phosphorus_ppm": p_ppm,
                    "phosphorus_mg_kg": float(normalized_values["phosphorus_mg_kg"]),
                    "potassium_cmol_kg": k_cmol,
                    "potassium_mg_kg": float(normalized_values["potassium_mg_kg"]),
                    "soil_texture": texture,
                }
            )
        return analyses

    def generate_fertilizer_recommendations(
        self,
        analyses: list[dict[str, Any]],
        plots: list[dict[str, Any]],
        references: list[dict[str, Any]],
        *,
        traditional_baseline_kg_ha: float = 200.0,
    ) -> list[dict[str, Any]]:
        """Calcula una recomendación RN-07 por análisis con el evaluador de la API."""
        plots_by_id = {str(plot["plot_id"]): plot for plot in plots}
        reference_by_variety_stage = {
            (reference["variety_id"], reference["growth_stage"]): reference
            for reference in references
        }
        recommendations: list[dict[str, Any]] = []
        for analysis in analyses:
            plot = plots_by_id.get(str(analysis["plot_id"]))
            if plot is None:
                raise ValueError(
                    f"El análisis {analysis['analysis_id']} no tiene un lote existente."
                )
            reference = reference_by_variety_stage.get(
                (plot["variety_id"], plot.get("growth_stage", "VEGETATIVE"))
            )
            if reference is None:
                raise ValueError(
                    "No existe crop_nutrient_reference para "
                    f"variety_id={plot['variety_id']}, "
                    f"growth_stage={plot.get('growth_stage', 'VEGETATIVE')}."
                )

            normalized_analysis = {
                "ph_level": analysis["ph_level"],
                "nitrogen_mg_kg": analysis["nitrogen_mg_kg"],
                "phosphorus_mg_kg": analysis["phosphorus_mg_kg"],
                "potassium_mg_kg": analysis["potassium_mg_kg"],
            }
            result = evaluate_fertilizer_recommendation(
                normalized_analysis,
                reference,
                traditional_baseline_kg_ha=traditional_baseline_kg_ha,
            )
            recommendations.append(
                {
                    "recommendation_id": self.get_uuid5(
                        f"fertilizer-recommendation:{analysis['analysis_id']}"
                    ),
                    "analysis_id": analysis["analysis_id"],
                    "farm_id": analysis["farm_id"],
                    "plot_id": plot["plot_id"],
                    "n_evaluation": result["n_evaluation"],
                    "p_evaluation": result["p_evaluation"],
                    "k_evaluation": result["k_evaluation"],
                    "ph_evaluation": result["ph_evaluation"],
                    "apply_fertilizer": result["apply_fertilizer"],
                    "recommended_n_kg_ha": result["recommended_n_kg_ha"],
                    "recommended_p_kg_ha": result["recommended_p_kg_ha"],
                    "recommended_k_kg_ha": result["recommended_k_kg_ha"],
                    "lime_amendment_kg_ha": result["lime_amendment_kg_ha"],
                    "estimated_saving_pct": result["estimated_saving_pct"],
                    "warning_message": result.get("warning_message"),
                    "status": result["status"],
                }
            )
        return recommendations

    def generate_agronomic_alerts(
        self,
        farms: list[dict[str, Any]],
        plots: list[dict[str, Any]],
        *,
        forecast_target_date: date = date(2026, 10, 20),
    ) -> list[dict[str, Any]]:
        """Genera alertas deterministas y permite forzar fincas desde variables de entorno."""
        definitions = {
            "COFFEE_RUST": ("SEED_FORCE_ROYA_FARMS", "RN-03"),
            "WATER_DEFICIT": ("SEED_FORCE_DEFICIT_FARMS", "RN-04"),
            "EXTREME_RAIN": ("SEED_FORCE_EXTREME_RAIN_FARMS", "RN-05"),
        }
        farms_by_code = {farm["farm_code"]: farm for farm in farms}
        plots_by_farm = {plot["farm_id"]: plot for plot in plots}
        forced_by_type: dict[str, set[str]] = {}
        for alert_type, (variable, _) in definitions.items():
            forced_codes = {
                code.strip() for code in os.getenv(variable, "").split(",") if code.strip()
            }
            unknown_codes = forced_codes - farms_by_code.keys()
            if unknown_codes:
                raise ValueError(
                    f"{variable} contiene farm_code desconocidos: "
                    f"{', '.join(sorted(unknown_codes))}."
                )
            forced_by_type[alert_type] = forced_codes

        alerts: list[dict[str, Any]] = []
        for farm in farms:
            farm_code = farm["farm_code"]
            plot = plots_by_farm.get(farm["farm_id"])
            for alert_type, (_, rule_code) in definitions.items():
                if farm_code not in forced_by_type[alert_type] and self.rng.random() >= 0.08:
                    continue
                natural_key = f"{farm_code}:{alert_type}:{forecast_target_date.isoformat()}"
                alerts.append(
                    {
                        "alert_id": self.get_uuid5(natural_key),
                        "farm_id": farm["farm_id"],
                        "plot_id": plot["plot_id"] if plot else None,
                        "rule_code": rule_code,
                        "alert_type": alert_type,
                        "severity": self.rng.choice(("LOW", "MEDIUM", "HIGH", "CRITICAL")),
                        "forecast_target_date": forecast_target_date.isoformat(),
                        "status": "OPEN",
                    }
                )
        return alerts

    def generate_harvest_deliveries(
        self,
        farms: list[dict[str, Any]],
        count: int = 50,
    ) -> list[dict[str, Any]]:
        """Genera entregas operacionales de café recolectado."""
        deliveries: list[dict[str, Any]] = []

        for i in range(1, count + 1):
            farm = farms[(i - 1) % len(farms)]
            farm_code = farm["farm_code"]
            plot_id = self.get_uuid5(f"{farm_code}:PLOT-1")
            month = ((i - 1) % 6) + 5
            day = ((i - 1) % 25) + 1
            delivery_date = f"2026-{month:02d}-{day:02d}"
            seq = ((i - 1) // len(farms)) + 1
            natural_key = f"{farm_code}:{delivery_date}:{seq}"
            delivery_id = self.get_uuid5(natural_key)

            weight_kg = round(self.rng.uniform(250.0, 1500.0), 2)
            moisture_pct = round(self.rng.uniform(10.5, 12.5), 1)
            quality_score = round(self.rng.uniform(82.0, 88.5), 1)

            deliveries.append(
                {
                    "delivery_id": delivery_id,
                    "farm_id": farm["farm_id"],
                    "plot_id": plot_id,
                    "delivery_date": delivery_date,
                    "delivered_weight_kg": weight_kg,
                    "moisture_pct": moisture_pct,
                    "grain_moisture_pct": moisture_pct,
                    "quality_score": quality_score,
                }
            )
        return deliveries

    def generate_export_batches(self, count: int = 10) -> list[dict[str, Any]]:
        """Genera lotes de exportación trazables."""
        batches: list[dict[str, Any]] = []

        for i in range(1, count + 1):
            batch_code = f"EXP-2026-{i:04d}"
            batch_id = self.get_uuid5(batch_code)
            traced_weight = round(self.rng.uniform(5000.0, 18000.0), 2)
            cupping_score = round(self.rng.uniform(83.5, 89.0), 2)
            is_exportable = cupping_score >= 84.0

            batches.append(
                {
                    "batch_id": batch_id,
                    "batch_code": batch_code,
                    "created_date": "2026-10-01",
                    "harvest_season": "2025/2026",
                    "total_weight_kg": traced_weight,
                    "traced_weight_kg": traced_weight,
                    "cupping_score": cupping_score,
                    "water_footprint_l_per_kg": 3.5,
                    "weighted_water_m3_ton": 3.5,
                    "fertilizer_reduction_pct": 20.0,
                    "avg_fertilizer_red_pct": 20.0,
                    "is_exportable": is_exportable,
                    "is_certified": True,
                    "is_deforestation_free": True,
                    "traceability_status": "CERTIFIED",
                    "created_at": f"2026-10-01T{8 + (i % 10):02d}:00:00Z",
                }
            )
        return batches

    def generate_batch_farm_compositions(
        self,
        batches: list[dict[str, Any]],
        deliveries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Genera composición física de origen por lote de exportación (RN-08)."""
        compositions: list[dict[str, Any]] = []
        if not batches or not deliveries:
            return compositions

        for i, batch in enumerate(batches):
            batch_code = batch["batch_code"]
            batch_id = batch["batch_id"]

            # Asignar 2 a 4 entregas por lote
            for j in range(2):
                deliv_idx = (i * 2 + j) % len(deliveries)
                delivery = deliveries[deliv_idx]
                delivery_id = delivery["delivery_id"]
                natural_key = f"{batch_code}:{delivery_id}"
                composition_id = self.get_uuid5(natural_key)
                contrib_weight = round(delivery["delivered_weight_kg"] * 0.9, 2)
                plot_id = delivery.get("plot_id") or self.get_uuid5(f"FIN-{i + 1:04d}:PLOT-1")

                compositions.append(
                    {
                        "composition_id": composition_id,
                        "batch_id": batch_id,
                        "delivery_id": delivery_id,
                        "farm_id": delivery["farm_id"],
                        "plot_id": plot_id,
                        "contributed_weight_kg": contrib_weight,
                        "contributed_kg": contrib_weight,
                        "contribution_pct": 50.0,
                        "share_percentage": 50.0,
                        "reception_date": "2026-10-10",
                    }
                )
        return compositions

    def generate_buyer_batch_contracts(
        self,
        batches: list[dict[str, Any]],
        buyers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Genera contratos de compra comercial entre compradores y lotes (RN-11)."""
        contracts: list[dict[str, Any]] = []
        if not batches or not buyers:
            return contracts

        for i, batch in enumerate(batches):
            buyer = buyers[i % len(buyers)]
            batch_code = batch["batch_code"]
            client_id = buyer["client_id"]
            natural_key = f"{batch_code}:{client_id}"
            contract_id = self.get_uuid5(natural_key)
            container_id = f"MSCU-{self.rng.randint(1000000, 9999999)}"

            contracts.append(
                {
                    "contract_id": contract_id,
                    "batch_id": batch["batch_id"],
                    "buyer_id": buyer["buyer_id"],
                    "contract_reference": f"CTR-{batch_code}-{client_id}",
                    "purchase_date": "2026-10-10",
                    "shipping_container_id": container_id,
                }
            )
        return contracts

    def generate_all(self, mode: str = "dev") -> dict[str, list[dict[str, Any]]]:
        """Genera el dataset sintético completo según el perfil de volumen.

        Args:
            mode: 'dev' para desarrollo local o 'prod' para volumen completo.

        Returns:
            dict[str, list[dict[str, Any]]]: Diccionario con las colecciones de entidades.
        """
        is_prod = mode == "prod"
        farms_count = 1300 if is_prod else 50
        pilot_count = 300 if is_prod else 15
        users_count = 40 if is_prod else 15
        producers_count = 200 if is_prod else 25
        buyers_count = 40 if is_prod else 10
        deliveries_count = 1500 if is_prod else 80
        analyses_count = 300 if is_prod else 40
        batches_count = 50 if is_prod else 10

        # Tier 1
        departments = self.generate_departments()
        users = self.generate_users(count=users_count)
        producers = self.generate_producers(count=producers_count)
        buyers = self.generate_international_buyers(count=buyers_count)
        coffee_varieties = self.generate_coffee_varieties()
        sensor_types = self.generate_sensor_types()
        crop_nutrient_references = self.generate_crop_nutrient_references(coffee_varieties)

        # Tier 2
        municipalities = self.generate_municipalities(departments)
        forest_reserves = self.generate_forest_reserves(count=5 if is_prod else 3)

        # Tier 3
        farms = self.generate_farms(
            count=farms_count,
            pilot_count=pilot_count,
            producers=producers,
            municipalities=municipalities,
            forest_reserves=forest_reserves,
        )
        farm_plots = self.generate_farm_plots(farms, plots_per_farm=2, varieties=coffee_varieties)
        for plot in farm_plots:
            plot["growth_stage"] = "VEGETATIVE"
        farm_reserve_overlaps = self.generate_farm_reserve_overlaps(farms, forest_reserves)

        # Tier 4
        iot_sensors = self.generate_iot_sensors(farms, sensor_types)
        soil_lab_analyses = self.generate_soil_lab_analyses(farms, count=analyses_count)
        fertilizer_recommendations = self.generate_fertilizer_recommendations(
            soil_lab_analyses,
            farm_plots,
            crop_nutrient_references,
            traditional_baseline_kg_ha=float(
                os.getenv("AGROSENSE_FERTILIZER_BASELINE_KG_HA", "200")
            ),
        )
        harvest_deliveries = self.generate_harvest_deliveries(farms, count=deliveries_count)

        # Tier 5
        export_batches = self.generate_export_batches(count=batches_count)
        batch_farm_compositions = self.generate_batch_farm_compositions(
            export_batches, harvest_deliveries
        )
        buyer_batch_contracts = self.generate_buyer_batch_contracts(export_batches, buyers)
        agronomic_alerts = self.generate_agronomic_alerts(farms, farm_plots)

        return {
            "departments": departments,
            "users": users,
            "producers": producers,
            "international_buyers": buyers,
            "coffee_varieties": [
                {
                    "variety_id": variety["variety_id"],
                    "variety_name": variety["name"],
                }
                for variety in coffee_varieties
            ],
            "sensor_types": sensor_types,
            "crop_nutrient_references": crop_nutrient_references,
            "municipalities": municipalities,
            "forest_reserves": forest_reserves,
            "farms": farms,
            "farm_plots": [
                {
                    "plot_id": plot["plot_id"],
                    "farm_id": plot["farm_id"],
                    "variety_id": plot["variety_id"],
                    "plot_name": plot["plot_name"],
                    "crop_age_years": plot["crop_age_years"],
                    "growth_stage": plot["growth_stage"],
                }
                for plot in farm_plots
            ],
            "farm_reserve_overlaps": farm_reserve_overlaps,
            "iot_sensors": iot_sensors,
            "soil_lab_analyses": soil_lab_analyses,
            "fertilizer_recommendations": fertilizer_recommendations,
            "harvest_deliveries": harvest_deliveries,
            "export_batches": export_batches,
            "batch_farm_compositions": batch_farm_compositions,
            "buyer_batch_contracts": buyer_batch_contracts,
            "agronomic_alerts": agronomic_alerts,
        }
