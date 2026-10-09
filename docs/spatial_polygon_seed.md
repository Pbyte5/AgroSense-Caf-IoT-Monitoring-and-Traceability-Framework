# Generación espacial de fincas y reservas

El generador crea polígonos sintéticos deterministas en WGS 84 (EPSG:4326),
limitados al bounding box configurado para la región cafetera colombiana: latitud
1.0–7.5 y longitud -77.5–-74.5. No representa linderos reales ni delimitaciones
oficiales de reservas.

El código está dividido por responsabilidad: `spatial.py` genera fincas y reservas,
`spatial_geometry.py` valida, serializa y compara polígonos, y `spatial_models.py`
contiene el resultado espacial y los límites de coordenadas. `records.py` ensambla
las geometrías con los registros del seed; `run_seed.py` conserva la interfaz CLI.

Cada polígono se entrega en:

- `geom_ewkt`: texto `SRID=4326;POLYGON(...)` que PostGIS puede leer con
  `ST_GeomFromEWKT`.
- `polygon_geojson`: objeto GeoJSON Polygon para las columnas JSONB descritas en
  `docs/data_structure.md`.

El generador usa UUIDv5 para códigos estables, valida los parámetros y el bounding
box, cierra los anillos y rechaza anillos con área nula o auto-intersecciones.
Las fincas incluyen un indicador de intersección calculado contra las reservas
generadas, siguiendo la semántica de contacto o solapamiento de `ST_Intersects`.

La función `generate_spatial_seed_records(farms, seed)` del ejecutor enriquece los
registros de fincas y devuelve los registros de reservas. Una carga posterior puede
convertir `geom_ewkt` a una columna `geometry(Polygon, 4326)` con PostGIS. El comando
actual produce los registros y reporta el conteo; no abre conexión ni inserta en
PostgreSQL. Los valores de `polygon_geojson` están listos para las columnas JSONB
documentadas.

```sql
INSERT INTO farms (farm_id, farm_code, polygon_geojson, geom)
VALUES (
    :farm_id,
    :farm_code,
    CAST(:polygon_geojson AS jsonb),
    ST_GeomFromEWKT(:geom_ewkt)
);
```

La columna `geom` del ejemplo requiere existir en el esquema destino y tener tipo
`geometry(Polygon, 4326)`. Este repositorio aún describe `polygon_geojson` como la
representación operacional; habilitar y poblar una columna PostGIS en la base de
datos requiere una migración/schema de persistencia específica.
