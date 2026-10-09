"""AgroSense Café — PostGIS Spatial Polygon Generator for Farms and Reserves.

Implements EPSG:4326 deterministic polygon generation for farm perimeters and protected
forest reserves within Colombia's coffee region bounding box.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from typing import Any

# Bounding box oficial para la región cafetera colombiana
# (Huila, Cauca, Eje Cafetero, Antioquia, Tolima)
COFFEE_REGION_BOUNDS = {
    "min_lat": 1.0,
    "max_lat": 7.5,
    "min_lon": -77.5,
    "max_lon": -74.5,
}

# Límites absolutos de coordenadas geográficas permitidas por el modelo relacional (Colombia)
COLOMBIA_VALID_BOUNDS = {
    "min_lat": -4.23,
    "max_lat": 13.50,
    "min_lon": -81.73,
    "max_lon": -66.85,
}

# Namespace oficial para UUIDv5 determinista
AGROSENSE_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass(frozen=True)
class SpatialPolygonResult:
    """Resultado estructurado de una entidad espacial generada."""

    entity_id: str
    entity_code: str
    name: str
    center_lat: float
    center_lon: float
    area_ha: float
    points: list[tuple[float, float]]
    wkt: str
    geojson: dict[str, Any]
    is_valid_coords: bool
    overlaps_reserve: bool = False
    srid: int = 4326

    @property
    def ewkt(self) -> str:
        """Return EWKT accepted by PostGIS ``ST_GeomFromEWKT``."""
        return f"SRID={self.srid};{self.wkt}"


class PostGISSpatialGenerator:
    """Generador determinista de polígonos espaciales EPSG:4326 para fincas y reservas."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed) if seed is not None else random.Random()

    @staticmethod
    def meters_to_lat_deg(meters: float) -> float:
        """Convierte distancia métrica a grados de latitud."""
        return meters / 111139.0

    @staticmethod
    def meters_to_lon_deg(meters: float, lat_deg: float) -> float:
        """Convierte distancia métrica a grados de longitud ajustado por latitud."""
        lat_rad = math.radians(lat_deg)
        cos_lat = max(math.cos(lat_rad), 0.0001)
        return meters / (111139.0 * cos_lat)

    @staticmethod
    def is_within_bounds(lat: float, lon: float, bounds: dict[str, float]) -> bool:
        """Valida si un punto geográfico se encuentra dentro de los límites dados."""
        return (
            bounds["min_lat"] <= lat <= bounds["max_lat"]
            and bounds["min_lon"] <= lon <= bounds["max_lon"]
        )

    def generate_irregular_polygon(
        self,
        center_lat: float,
        center_lon: float,
        area_ha: float,
        sides: int = 6,
    ) -> list[tuple[float, float]]:
        """Genera un anillo poligonal cerrado no auto-intersecante en coordenadas (lon, lat).

        Args:
            center_lat: Latitud centroide.
            center_lon: Longitud centroide.
            area_ha: Área objetivo en hectáreas (> 0).
            sides: Número de lados/vértices del polígono (mínimo 3).

        Returns:
            list[tuple[float, float]]: Vértices (lon, lat) con el anillo cerrado.

        Raises:
            ValueError: Si los lados son menores a 3 o el área no es positiva.
        """
        if not isinstance(sides, int) or isinstance(sides, bool) or sides < 3:
            raise ValueError(f"Un polígono requiere al menos 3 lados, recibido: {sides}")
        if (
            not isinstance(area_ha, int | float)
            or isinstance(area_ha, bool)
            or not math.isfinite(area_ha)
            or area_ha <= 0
        ):
            raise ValueError(f"El área en hectáreas debe ser positiva, recibido: {area_ha}")
        if (
            not isinstance(center_lat, int | float)
            or not isinstance(center_lon, int | float)
            or isinstance(center_lat, bool)
            or isinstance(center_lon, bool)
            or not math.isfinite(center_lat)
            or not math.isfinite(center_lon)
        ):
            raise ValueError("El centro del polígono debe usar coordenadas finitas.")
        if not -90 <= center_lat <= 90 or not -180 <= center_lon <= 180:
            raise ValueError("El centro debe estar dentro del rango geográfico válido.")

        target_area_m2 = area_ha * 10000.0
        if not math.isfinite(target_area_m2):
            raise ValueError("El área es demasiado grande para generar un polígono.")
        avg_radius_m = math.sqrt(target_area_m2 / math.pi)

        # Angles sorted by bearing produce a simple, non-self-intersecting outline.
        angles = sorted(self.rng.uniform(0, 2 * math.pi) for _ in range(sides))

        offsets: list[tuple[float, float]] = []
        for angle in angles:
            r = avg_radius_m * self.rng.uniform(0.75, 1.25)
            dx_m = r * math.cos(angle)
            dy_m = r * math.sin(angle)
            offsets.append((dx_m, dy_m))

        # Rescale the irregular outline so its local projected area matches area_ha.
        planar_area_m2 = abs(
            sum(
                x1 * y2 - x2 * y1
                for (x1, y1), (x2, y2) in zip(offsets, offsets[1:] + offsets[:1], strict=True)
            )
            / 2
        )
        if planar_area_m2 <= 0:
            raise ValueError("No se pudo generar un polígono con área positiva.")
        scale = math.sqrt(target_area_m2 / planar_area_m2)

        points: list[tuple[float, float]] = []
        for dx_m, dy_m in offsets:
            dx_m *= scale
            dy_m *= scale
            lat = center_lat + self.meters_to_lat_deg(dy_m)
            lon = center_lon + self.meters_to_lon_deg(dx_m, center_lat)
            points.append((round(lon, 6), round(lat, 6)))

        # Cerrar el anillo según el estándar OGC / PostGIS
        points.append(points[0])
        self._validate_ring(points)
        return points

    @staticmethod
    def _validate_ring(points: list[tuple[float, float]]) -> None:
        """Validate a closed WGS84 polygon exterior ring before serialization."""
        if not isinstance(points, list) or len(points) < 4:
            raise ValueError("Un anillo poligonal cerrado requiere al menos 4 puntos.")
        if any(not isinstance(point, tuple | list) or len(point) != 2 for point in points):
            raise ValueError("Cada vértice debe ser un par de coordenadas.")
        for point in points:
            if (
                not all(isinstance(value, int | float) for value in point)
                or any(isinstance(value, bool) for value in point)
                or not all(math.isfinite(value) for value in point)
            ):
                raise ValueError("Cada vértice debe contener longitud y latitud finitas.")
            lon, lat = point
            if not -180 <= lon <= 180 or not -90 <= lat <= 90:
                raise ValueError("Los vértices deben estar dentro del rango geográfico válido.")
        if tuple(points[0]) != tuple(points[-1]):
            raise ValueError("El primer y el último vértice deben coincidir para cerrar el anillo.")
        if len({tuple(point) for point in points[:-1]}) < 3:
            raise ValueError("Un polígono requiere al menos 3 vértices distintos.")

    @staticmethod
    def polygon_to_wkt(points: list[tuple[float, float]]) -> str:
        """Convierte vértices (lon, lat) a formato Well-Known Text (WKT)."""
        PostGISSpatialGenerator._validate_ring(points)
        coords_str = ", ".join(f"{lon} {lat}" for lon, lat in points)
        return f"POLYGON(({coords_str}))"

    @staticmethod
    def polygon_to_geojson(points: list[tuple[float, float]]) -> dict[str, Any]:
        """Convierte vértices (lon, lat) a diccionario GeoJSON Polygon."""
        PostGISSpatialGenerator._validate_ring(points)
        return {
            "type": "Polygon",
            "coordinates": [[list(pt) for pt in points]],
        }

    @staticmethod
    def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
        """Determina si un punto (lon, lat) está dentro de un polígono usando Ray Casting."""
        px, py = point
        inside = False
        n = len(polygon)
        if n < 4:
            return False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if PostGISSpatialGenerator._point_on_segment(point, (xi, yi), (xj, yj)):
                return True
            intersect = ((yi > py) != (yj > py)) and (
                px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi
            )
            if intersect:
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _point_on_segment(
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
        epsilon: float = 1e-12,
    ) -> bool:
        """Return whether a point lies on a segment, including its endpoints."""
        px, py = point
        sx, sy = start
        ex, ey = end
        cross = (px - sx) * (ey - sy) - (py - sy) * (ex - sx)
        if abs(cross) > epsilon:
            return False
        return (
            min(sx, ex) - epsilon <= px <= max(sx, ex) + epsilon
            and min(sy, ey) - epsilon <= py <= max(sy, ey) + epsilon
        )

    @classmethod
    def _segments_intersect(
        cls,
        a1: tuple[float, float],
        a2: tuple[float, float],
        b1: tuple[float, float],
        b2: tuple[float, float],
    ) -> bool:
        """Return whether two planar segments cross or touch."""

        def orientation(
            p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]
        ) -> float:
            return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

        o1 = orientation(a1, a2, b1)
        o2 = orientation(a1, a2, b2)
        o3 = orientation(b1, b2, a1)
        o4 = orientation(b1, b2, a2)
        epsilon = 1e-12

        if ((o1 > epsilon and o2 < -epsilon) or (o1 < -epsilon and o2 > epsilon)) and (
            (o3 > epsilon and o4 < -epsilon) or (o3 < -epsilon and o4 > epsilon)
        ):
            return True

        return (
            (abs(o1) <= epsilon and cls._point_on_segment(b1, a1, a2, epsilon))
            or (abs(o2) <= epsilon and cls._point_on_segment(b2, a1, a2, epsilon))
            or (abs(o3) <= epsilon and cls._point_on_segment(a1, b1, b2, epsilon))
            or (abs(o4) <= epsilon and cls._point_on_segment(a2, b1, b2, epsilon))
        )

    @staticmethod
    def _validate_bounds(bounds: dict[str, float]) -> None:
        """Validate the geographic bounding-box shape and finite coordinates."""
        if not isinstance(bounds, dict):
            raise ValueError("Los límites deben proporcionarse como un diccionario.")
        required = {"min_lat", "max_lat", "min_lon", "max_lon"}
        if not required.issubset(bounds):
            missing = ", ".join(sorted(required - bounds.keys()))
            raise ValueError(f"Faltan límites geográficos: {missing}")
        if not all(
            isinstance(bounds[key], int | float)
            and not isinstance(bounds[key], bool)
            and math.isfinite(bounds[key])
            for key in required
        ):
            raise ValueError("Los límites geográficos deben ser finitos.")
        if bounds["min_lat"] >= bounds["max_lat"] or bounds["min_lon"] >= bounds["max_lon"]:
            raise ValueError("Los límites mínimos deben ser menores que los máximos.")
        if not (-90 <= bounds["min_lat"] < bounds["max_lat"] <= 90):
            raise ValueError("Los límites de latitud deben estar entre -90 y 90 grados.")
        if not (-180 <= bounds["min_lon"] < bounds["max_lon"] <= 180):
            raise ValueError("Los límites de longitud deben estar entre -180 y 180 grados.")

    @classmethod
    def _validate_coffee_region_bounds(cls, bounds: dict[str, float]) -> None:
        """Require a custom generation box to stay inside the project coffee-region box."""
        cls._validate_bounds(bounds)
        if (
            bounds["min_lat"] < COFFEE_REGION_BOUNDS["min_lat"]
            or bounds["max_lat"] > COFFEE_REGION_BOUNDS["max_lat"]
            or bounds["min_lon"] < COFFEE_REGION_BOUNDS["min_lon"]
            or bounds["max_lon"] > COFFEE_REGION_BOUNDS["max_lon"]
        ):
            raise ValueError(
                "Los límites personalizados deben quedar dentro de la región cafetera."
            )

    def _generate_polygon_inside_bounds(
        self,
        area_ha: float,
        sides: int,
        bounds: dict[str, float],
        max_attempts: int = 100,
    ) -> tuple[float, float, list[tuple[float, float]]]:
        """Generate a polygon whose every vertex remains inside the supplied bounds."""
        self._validate_coffee_region_bounds(bounds)
        if (
            not isinstance(area_ha, int | float)
            or isinstance(area_ha, bool)
            or not math.isfinite(area_ha)
            or area_ha <= 0
        ):
            raise ValueError("El área del polígono debe ser un número finito mayor que cero.")
        if not isinstance(sides, int) or isinstance(sides, bool) or sides < 3:
            raise ValueError("Un polígono requiere al menos 3 lados.")
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts < 1:
            raise ValueError("max_attempts debe ser un entero positivo.")
        max_radius_m = 1.25 * math.sqrt(area_ha * 10000.0 / math.pi)
        if not math.isfinite(max_radius_m):
            raise ValueError("El área es demasiado grande para el bounding box indicado.")
        lat_margin = self.meters_to_lat_deg(max_radius_m) + 0.000001
        max_abs_lat = max(abs(bounds["min_lat"]), abs(bounds["max_lat"]))
        min_cos = max(math.cos(math.radians(max_abs_lat)), 0.0001)
        lon_margin = max_radius_m / (111139.0 * min_cos) + 0.000001

        min_lat = bounds["min_lat"] + lat_margin
        max_lat = bounds["max_lat"] - lat_margin
        min_lon = bounds["min_lon"] + lon_margin
        max_lon = bounds["max_lon"] - lon_margin
        if min_lat >= max_lat or min_lon >= max_lon:
            raise ValueError("El polígono es demasiado grande para el bounding box indicado.")

        for _ in range(max_attempts):
            center_lat = round(self.rng.uniform(min_lat, max_lat), 6)
            center_lon = round(self.rng.uniform(min_lon, max_lon), 6)
            points = self.generate_irregular_polygon(center_lat, center_lon, area_ha, sides)
            if all(self.is_within_bounds(lat, lon, bounds) for lon, lat in points):
                return center_lat, center_lon, points

        raise ValueError("No fue posible generar un polígono dentro de los límites indicados.")

    @classmethod
    def polygons_intersect(
        cls,
        poly_a: list[tuple[float, float]],
        poly_b: list[tuple[float, float]],
    ) -> bool:
        """Determina si dos polígonos simples se intersectan o solapan.

        Evalúa inclusión de vértices y cruces de segmentos para polígonos simples; incluye
        el contacto entre bordes, como ST_Intersects.
        """
        try:
            cls._validate_ring(poly_a)
            cls._validate_ring(poly_b)
        except (TypeError, ValueError):
            return False
        # Descarte rápido por bounding box envolvente
        a_lons = [p[0] for p in poly_a]
        a_lats = [p[1] for p in poly_a]
        b_lons = [p[0] for p in poly_b]
        b_lats = [p[1] for p in poly_b]

        if (
            max(a_lons) < min(b_lons)
            or min(a_lons) > max(b_lons)
            or max(a_lats) < min(b_lats)
            or min(a_lats) > max(b_lats)
        ):
            return False

        # Comprobar si algún vértice de A está dentro de B
        for pt in poly_a[:-1]:
            if cls.point_in_polygon(pt, poly_b):
                return True

        # Comprobar si algún vértice de B está dentro de A
        for pt in poly_b[:-1]:
            if cls.point_in_polygon(pt, poly_a):
                return True

        for a_start, a_end in zip(poly_a, poly_a[1:], strict=False):
            for b_start, b_end in zip(poly_b, poly_b[1:], strict=False):
                if cls._segments_intersect(a_start, a_end, b_start, b_end):
                    return True

        return False

    def generate_forest_reserves(
        self,
        count: int = 5,
        bounds: dict[str, float] | None = None,
    ) -> list[SpatialPolygonResult]:
        """Genera reservas forestales protegidas en la región cafetera."""
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("La cantidad de reservas debe ser un entero no negativo.")
        active_bounds = COFFEE_REGION_BOUNDS if bounds is None else bounds
        self._validate_coffee_region_bounds(active_bounds)
        reserves: list[SpatialPolygonResult] = []

        for i in range(1, count + 1):
            code = f"RES-{i:03d}"
            res_id = str(uuid.uuid5(AGROSENSE_NAMESPACE, code))
            # These geometries are synthetic and must not imply real reserve boundaries.
            name = f"Reserva forestal sintética {i:03d}"

            area_ha = round(self.rng.uniform(200.0, 1500.0), 2)
            center_lat, center_lon, points = self._generate_polygon_inside_bounds(
                area_ha, sides=8, bounds=active_bounds
            )

            reserves.append(
                SpatialPolygonResult(
                    entity_id=res_id,
                    entity_code=code,
                    name=name,
                    center_lat=center_lat,
                    center_lon=center_lon,
                    area_ha=area_ha,
                    points=points,
                    wkt=self.polygon_to_wkt(points),
                    geojson=self.polygon_to_geojson(points),
                    is_valid_coords=True,
                    overlaps_reserve=False,
                )
            )

        return reserves

    def generate_farm_polygon(
        self,
        farm_code: str,
        name: str,
        area_ha: float | None = None,
        sides: int = 6,
        force_out_of_bounds: bool = False,
        force_swap_coords: bool = False,
        force_reserve_overlap: SpatialPolygonResult | None = None,
        bounds: dict[str, float] | None = None,
    ) -> SpatialPolygonResult:
        """Genera el polígono perimetral de una finca con soporte para defectos espaciales.

        Args:
            farm_code: Código de la finca (e.g. 'FIN-0001').
            name: Nombre de la finca.
            area_ha: Área total en hectáreas (aleatoria entre 2.0 y 25.0 si es None).
            sides: Cantidad de vértices del polígono (por defecto 6).
            force_out_of_bounds: Inyecta DEF-04 (coordenadas fuera del bounding box).
            force_swap_coords: Inyecta DEF-04 (latitud y longitud invertidas).
            force_reserve_overlap: Inyecta DEF-07/RN-09 sobre una reserva sintética.
            bounds: Límites de búsqueda para la generación nominal.
        """
        active_bounds = COFFEE_REGION_BOUNDS if bounds is None else bounds
        self._validate_coffee_region_bounds(active_bounds)
        if not isinstance(farm_code, str) or not farm_code.strip():
            raise ValueError("farm_code debe ser un texto no vacío.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name debe ser un texto no vacío.")
        if area_ha is not None and (
            not isinstance(area_ha, int | float)
            or isinstance(area_ha, bool)
            or not math.isfinite(area_ha)
            or area_ha <= 0
        ):
            raise ValueError("area_ha debe ser un número finito mayor que cero.")
        if not isinstance(sides, int) or isinstance(sides, bool) or sides < 3:
            raise ValueError("Un polígono requiere al menos 3 lados.")
        if not isinstance(force_out_of_bounds, bool) or not isinstance(force_swap_coords, bool):
            raise ValueError("Los indicadores de inyección deben ser booleanos.")
        if force_reserve_overlap is not None and not isinstance(
            force_reserve_overlap, SpatialPolygonResult
        ):
            raise ValueError("force_reserve_overlap debe ser una reserva espacial generada.")
        forced_scenarios = sum(
            (force_out_of_bounds, force_swap_coords, force_reserve_overlap is not None)
        )
        if forced_scenarios > 1:
            raise ValueError("Solo se puede activar un escenario espacial forzado por finca.")
        farm_id = str(uuid.uuid5(AGROSENSE_NAMESPACE, farm_code))
        target_area = (
            round(self.rng.uniform(2.5, 30.0), 2) if area_ha is None else round(area_ha, 2)
        )
        if target_area <= 0:
            raise ValueError("area_ha debe ser al menos 0.01 ha con la precisión actual.")

        if force_reserve_overlap is not None:
            # Coloca la finca sobre la reserva sintética para simular RN-09.
            self._validate_ring(force_reserve_overlap.points)
            if force_reserve_overlap.srid != 4326 or not all(
                self.is_within_bounds(lat, lon, active_bounds)
                for lon, lat in force_reserve_overlap.points
            ):
                raise ValueError("La reserva debe estar dentro de la región y usar SRID 4326.")
            center_lat = force_reserve_overlap.center_lat
            center_lon = force_reserve_overlap.center_lon
            is_valid = True
            points = []
            for _ in range(100):
                points = self.generate_irregular_polygon(
                    center_lat, center_lon, target_area, sides=sides
                )
                if all(
                    self.is_within_bounds(lat, lon, active_bounds) for lon, lat in points
                ) and self.polygons_intersect(points, force_reserve_overlap.points):
                    break
            else:
                raise ValueError("No fue posible generar una finca que interseque la reserva.")
            overlaps = True
        elif force_out_of_bounds:
            # DEF-04: Coordenadas claramente fuera de Colombia
            center_lat = round(self.rng.uniform(25.0, 45.0), 6)
            center_lon = round(self.rng.uniform(-10.0, 15.0), 6)
            is_valid = False
            overlaps = False
        else:
            center_lat, center_lon, points = self._generate_polygon_inside_bounds(
                target_area, sides=sides, bounds=active_bounds
            )
            is_valid = True
            overlaps = False

        if force_swap_coords:
            # DEF-04: Latitud y longitud intercambiadas
            center_lat, center_lon = center_lon, center_lat
            is_valid = False

        if force_out_of_bounds or force_swap_coords:
            points = self.generate_irregular_polygon(
                center_lat, center_lon, target_area, sides=sides
            )

        return SpatialPolygonResult(
            entity_id=farm_id,
            entity_code=farm_code,
            name=name,
            center_lat=center_lat,
            center_lon=center_lon,
            area_ha=target_area,
            points=points,
            wkt=self.polygon_to_wkt(points),
            geojson=self.polygon_to_geojson(points),
            is_valid_coords=is_valid,
            overlaps_reserve=overlaps,
        )
