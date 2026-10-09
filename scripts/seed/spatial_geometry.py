"""Validation, serialization, and intersection helpers for simple WGS84 polygons."""

from __future__ import annotations

import math
from typing import Any

Point = tuple[float, float]
Ring = list[Point]


def validate_ring(points: Ring) -> None:
    """Validate a closed, non-degenerate, non-self-intersecting WGS84 ring."""
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

    doubled_area = abs(
        sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:], strict=False))
    )
    if doubled_area <= 1e-12:
        raise ValueError("El anillo debe encerrar un área positiva.")

    segments = list(zip(points, points[1:], strict=False))
    for first_index, (start_a, end_a) in enumerate(segments):
        for second_index in range(first_index + 1, len(segments)):
            if second_index == first_index + 1 or (
                first_index == 0 and second_index == len(segments) - 1
            ):
                continue
            start_b, end_b = segments[second_index]
            if segments_intersect(start_a, end_a, start_b, end_b):
                raise ValueError("El anillo no puede auto-intersectarse.")


def polygon_to_wkt(points: Ring) -> str:
    """Serialize a closed ring as a WKT Polygon."""
    validate_ring(points)
    coordinates = ", ".join(f"{longitude} {latitude}" for longitude, latitude in points)
    return f"POLYGON(({coordinates}))"


def polygon_to_geojson(points: Ring) -> dict[str, Any]:
    """Serialize a closed ring as a GeoJSON Polygon geometry."""
    validate_ring(points)
    return {"type": "Polygon", "coordinates": [[list(point) for point in points]]}


def point_on_segment(point: Point, start: Point, end: Point, epsilon: float = 1e-12) -> bool:
    """Return whether a point lies on a segment, including its endpoints."""
    px, py = point
    sx, sy = start
    ex, ey = end
    cross_product = (px - sx) * (ey - sy) - (py - sy) * (ex - sx)
    return abs(cross_product) <= epsilon and (
        min(sx, ex) - epsilon <= px <= max(sx, ex) + epsilon
        and min(sy, ey) - epsilon <= py <= max(sy, ey) + epsilon
    )


def point_in_polygon(point: Point, polygon: Ring) -> bool:
    """Check point inclusion with ray casting, counting boundary points as inside."""
    if len(polygon) < 4:
        return False
    px, py = point
    is_inside = False
    previous_index = len(polygon) - 1
    for index, (current_x, current_y) in enumerate(polygon):
        previous_x, previous_y = polygon[previous_index]
        if point_on_segment(point, (current_x, current_y), (previous_x, previous_y)):
            return True
        crosses_ray = (current_y > py) != (previous_y > py)
        if (
            crosses_ray
            and px
            < (previous_x - current_x) * (py - current_y) / (previous_y - current_y) + current_x
        ):
            is_inside = not is_inside
        previous_index = index
    return is_inside


def segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
    """Return whether two planar segments cross or touch."""

    def orientation(first: Point, second: Point, third: Point) -> float:
        return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (
            third[0] - first[0]
        )

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
        (abs(o1) <= epsilon and point_on_segment(b1, a1, a2, epsilon))
        or (abs(o2) <= epsilon and point_on_segment(b2, a1, a2, epsilon))
        or (abs(o3) <= epsilon and point_on_segment(a1, b1, b2, epsilon))
        or (abs(o4) <= epsilon and point_on_segment(a2, b1, b2, epsilon))
    )


def polygons_intersect(poly_a: Ring, poly_b: Ring) -> bool:
    """Check whether two valid simple polygons intersect, including edge contact."""
    try:
        validate_ring(poly_a)
        validate_ring(poly_b)
    except (TypeError, ValueError):
        return False

    a_longitudes = [point[0] for point in poly_a]
    a_latitudes = [point[1] for point in poly_a]
    b_longitudes = [point[0] for point in poly_b]
    b_latitudes = [point[1] for point in poly_b]
    if (
        max(a_longitudes) < min(b_longitudes)
        or min(a_longitudes) > max(b_longitudes)
        or max(a_latitudes) < min(b_latitudes)
        or min(a_latitudes) > max(b_latitudes)
    ):
        return False

    if any(point_in_polygon(point, poly_b) for point in poly_a[:-1]):
        return True
    if any(point_in_polygon(point, poly_a) for point in poly_b[:-1]):
        return True
    return any(
        segments_intersect(start_a, end_a, start_b, end_b)
        for start_a, end_a in zip(poly_a, poly_a[1:], strict=False)
        for start_b, end_b in zip(poly_b, poly_b[1:], strict=False)
    )
