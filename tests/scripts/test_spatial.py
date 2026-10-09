"""Unit tests for PostGISSpatialGenerator and spatial seed routines."""

import pytest

from scripts.seed.spatial import (
    COFFEE_REGION_BOUNDS,
    COLOMBIA_VALID_BOUNDS,
    PostGISSpatialGenerator,
    SpatialPolygonResult,
)


def test_generator_deterministic_reproducibility():
    """Verify that identical seeds produce identical coordinates and WKT strings."""
    gen1 = PostGISSpatialGenerator(seed=42)
    gen2 = PostGISSpatialGenerator(seed=42)

    farm1 = gen1.generate_farm_polygon("FIN-0001", "Hacienda La Palma", area_ha=12.5)
    farm2 = gen2.generate_farm_polygon("FIN-0001", "Hacienda La Palma", area_ha=12.5)

    assert farm1.entity_id == farm2.entity_id
    assert farm1.wkt == farm2.wkt
    assert farm1.points == farm2.points
    assert farm1.center_lat == farm2.center_lat
    assert farm1.center_lon == farm2.center_lon


def test_polygon_closed_ring_and_point_count():
    """Verify that generated polygons close their rings and have expected vertices."""
    gen = PostGISSpatialGenerator(seed=123)
    points = gen.generate_irregular_polygon(center_lat=4.5, center_lon=-75.5, area_ha=5.0, sides=6)

    # 6 lados implica 7 puntos al cerrar el anillo
    assert len(points) == 7
    # El primer punto debe ser idéntico al último (anillo cerrado PostGIS)
    assert points[0] == points[-1]


def test_polygon_validation_errors():
    """Verify that invalid side count or negative area raise ValueError."""
    gen = PostGISSpatialGenerator(seed=10)

    with pytest.raises(ValueError, match="al menos 3 lados"):
        gen.generate_irregular_polygon(center_lat=4.5, center_lon=-75.5, area_ha=5.0, sides=2)

    with pytest.raises(ValueError, match="debe ser positiva"):
        gen.generate_irregular_polygon(center_lat=4.5, center_lon=-75.5, area_ha=-2.0, sides=5)


def test_wkt_and_geojson_conversion():
    """Verify WKT and GeoJSON formats conform to standard OGC specifications."""
    gen = PostGISSpatialGenerator(seed=99)
    farm = gen.generate_farm_polygon("FIN-0010", "Finca El Roble", area_ha=10.0, sides=5)

    assert farm.wkt.startswith("POLYGON((")
    assert farm.wkt.endswith("))")

    geojson = farm.geojson
    assert geojson["type"] == "Polygon"
    assert len(geojson["coordinates"]) == 1
    assert len(geojson["coordinates"][0]) == 6
    assert geojson["coordinates"][0][0] == geojson["coordinates"][0][-1]


def test_wkt_and_geojson_minimum_points_error():
    """Verify that polygon_to_wkt and polygon_to_geojson require at least 4 points."""
    with pytest.raises(ValueError, match="al menos 4 puntos"):
        PostGISSpatialGenerator.polygon_to_wkt([(0.0, 0.0), (1.0, 1.0)])

    with pytest.raises(ValueError, match="al menos 4 puntos"):
        PostGISSpatialGenerator.polygon_to_geojson([(0.0, 0.0), (1.0, 1.0)])


def test_nominal_farm_within_coffee_bounds():
    """Verify nominal farms are placed within Colombia coffee region bounding box."""
    gen = PostGISSpatialGenerator(seed=777)
    farm = gen.generate_farm_polygon("FIN-0020", "Finca Cafetera")

    assert farm.is_valid_coords is True
    assert farm.overlaps_reserve is False
    assert COFFEE_REGION_BOUNDS["min_lat"] <= farm.center_lat <= COFFEE_REGION_BOUNDS["max_lat"]
    assert COFFEE_REGION_BOUNDS["min_lon"] <= farm.center_lon <= COFFEE_REGION_BOUNDS["max_lon"]


def test_defect_injection_def03_out_of_bounds_and_swap():
    """Verify DEF-03 injects out-of-bounds or swapped coordinates."""
    gen = PostGISSpatialGenerator(seed=55)

    # Fuera de bounds
    farm_oob = gen.generate_farm_polygon("FIN-0030", "Finca OOB", force_out_of_bounds=True)
    assert farm_oob.is_valid_coords is False
    assert not PostGISSpatialGenerator.is_within_bounds(
        farm_oob.center_lat, farm_oob.center_lon, COLOMBIA_VALID_BOUNDS
    )

    # Swap de coordenadas
    farm_swap = gen.generate_farm_polygon("FIN-0031", "Finca Swap", force_swap_coords=True)
    assert farm_swap.is_valid_coords is False


def test_forest_reserves_generation_and_overlap():
    """Verify generation of protected reserves and detection of RN-09 overlap."""
    gen = PostGISSpatialGenerator(seed=88)
    reserves = gen.generate_forest_reserves(count=3)

    assert len(reserves) == 3
    for res in reserves:
        assert isinstance(res, SpatialPolygonResult)
        assert res.entity_code.startswith("RES-")
        assert res.area_ha >= 200.0
        assert res.wkt.startswith("POLYGON((")

    # Forzar solapamiento de finca con la primera reserva (RN-09)
    farm_overlap = gen.generate_farm_polygon(
        "FIN-0040",
        "Finca Solapada",
        area_ha=15.0,
        force_reserve_overlap=reserves[0],
    )
    assert farm_overlap.overlaps_reserve is True

    # Validar detección de intersección geométrica
    intersected = PostGISSpatialGenerator.polygons_intersect(
        farm_overlap.points, reserves[0].points
    )
    assert intersected is True


def test_polygons_intersect_disjoint():
    """Verify polygons_intersect returns False for completely disjoint geometries."""
    poly_a = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
    poly_b = [(10.0, 10.0), (11.0, 10.0), (11.0, 11.0), (10.0, 11.0), (10.0, 10.0)]

    assert PostGISSpatialGenerator.polygons_intersect(poly_a, poly_b) is False
    assert PostGISSpatialGenerator.point_in_polygon((5.0, 5.0), [(0.0, 0.0), (1.0, 1.0)]) is False


def test_polygons_intersect_vertex_b_inside_a():
    """Verify intersection when vertices of B fall inside a larger polygon A."""
    poly_outer = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
    poly_inner = [(2.0, 2.0), (4.0, 2.0), (4.0, 4.0), (2.0, 4.0), (2.0, 2.0)]
    assert PostGISSpatialGenerator.polygons_intersect(poly_outer, poly_inner) is True
