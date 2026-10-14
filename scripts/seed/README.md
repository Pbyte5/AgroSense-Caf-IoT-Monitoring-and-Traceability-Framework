# Seed de datos agronómicos

Este paquete puede ejecutarse dentro del monorepo o copiarse como directorio
`seed/` al repositorio que administra PostgreSQL. No importa el código Python de
la API ni altera modelos o migraciones.

## Ejecución en este repositorio

```powershell
uv run python -m scripts.seed --mode dev --seed 42
```

Sin `--write-postgres`, se generan SQL UPSERT y se comprueba idempotencia en
memoria; **no se conecta ni escribe en PostgreSQL**.

## Migración a un repositorio de base de datos

1. Copia el contenido completo de `scripts/seed/` a `<repositorio-db>/seed/`,
   incluyendo `pyproject.toml`, `README.md` y los módulos auxiliares. No copies
   solamente `run_seed.py`.
2. Desde la raíz del repositorio destino, instala/ejecuta con:

   ```powershell
   uv run --project seed python -m seed --mode dev --seed 42
   ```

3. Para escribir datos, configura `AGROSENSE_DATABASE_URL` con la URL de
   PostgreSQL y opta por la conexión de forma explícita:

   ```powershell
   $env:AGROSENSE_DATABASE_URL = "postgresql://usuario:clave@host:5432/base"
   uv run --project seed python -m seed --mode dev --seed 42 --write-postgres
   ```

4. Aplica primero las migraciones que definen el esquema ORM de AgroSense.
   El escritor verifica tablas y columnas antes de insertar y ejecuta todos
   los UPSERT en una transacción. Un error de esquema o de inserción aborta la
   transacción y se reporta; no existe una escritura silenciosa de respaldo.

`--reset` solo limpia el simulador en memoria. Para truncar en PostgreSQL se
requiere la opción separada `--write-postgres --reset-database`; esta trunca
solamente las tablas incluidas en el dataset, sin `CASCADE`. Si existen tablas
dependientes ajenas al dataset, PostgreSQL rechazará el reset en vez de
eliminarlas indirectamente.

## Contrato de tablas

La proyección `database_dataset.py` envía solo tablas y columnas declaradas por
los modelos/migraciones actuales. En particular, la tabla del esquema es
`soil_lab_analyses` (no `soil_analyses`). `international_buyers.company_name` se
proyecta como `buyer_name`. Los generadores de departamentos, reservas, sensores
y cruces geométricos se excluyen porque no corresponden al contrato destino
actual; las geometrías de solapamiento sintéticas no se insertan en
`farm_reserve_overlaps`.

Los análisis F6 conservan los valores originales y N/P/K normalizados a mg/kg.
El generador produce una recomendación RN-07 por análisis, buscando la
referencia F1 por variedad y etapa fenológica. La dosis de un nutriente
deficiente usa `(mínimo de referencia - valor medido) * 0.5`; `0.5` es un
supuesto del prototipo que requiere calibración agronómica antes de su uso en
campo. El ahorro es una estimación contra `200 kg/ha`, ajustable con
`AGROSENSE_FERTILIZER_BASELINE_KG_HA`.

Las alertas RN-03/RN-04/RN-05 son deterministas para semilla y fecha objetivo.
Se pueden forzar mediante `SEED_FORCE_ROYA_FARMS`,
`SEED_FORCE_DEFICIT_FARMS` y `SEED_FORCE_EXTREME_RAIN_FARMS`, listas de
`farm_code` separadas por comas. Un código que no exista aborta explícitamente.
Recomendaciones y alertas usan UUIDv5 como clave UPSERT; el estado operacional
existente se conserva al repetir la carga.

## Dependencias y validación

Las dependencias mínimas del paquete están declaradas en este directorio en
`pyproject.toml` (`faker` para generación y `psycopg` para el escritor). En el
monorepo, las pruebas están en `tests/scripts/`; una base PostgreSQL accesible
no es necesaria para las pruebas unitarias del escritor simulado.
