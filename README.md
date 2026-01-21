Tuya Data Test

Este repositorio contiene la solución a la prueba técnica de Ingeniería de Datos. A continuación se explica cómo ejecutar cada ejercicio.

Estructura del Repositorio

```
tuya-data-test/
  .venv/
  Prueba Tecnica.xlsx
  requirements.txt
  README.md
  1_dataset_design/          # Ejercicio 1: Diseño conceptual dataset 
  2_kpis_quality/            # Ejercicio 2: KPIs y calidad de datos
  3_rachas_sql/              # Ejercicio 3: Rachas (Python + SQLite)
    rachas_pipeline.py
    sql/
      ddl.sql
      query_rachas.sql
  4_html_processing/         # Ejercicio 4: Procesamiento HTML
```

Configuración Inicial

1. Crear entorno virtual

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ejercicio 3: Rachas

Descripción

Calcula rachas (meses consecutivos) de clientes en un mismo nivel de deuda a partir de datos históricos de saldos.

Ejecución

Desde la raíz del repositorio:
```bash
python 3_rachas_sql/rachas_pipeline.py --fecha-base 2024-12-15 --n 3
```

Parámetros

- `--fecha-base` (requerido): Fecha de corte en formato YYYY-MM-DD
- `--n` (requerido): Número mínimo de meses consecutivos para filtrar rachas
- `--excel` (opcional): Ruta al archivo Excel (default: Prueba Tecnica.xlsx)
- `--out` (opcional): Nombre del CSV de salida (default: resultados_rachas.csv)
- `--db` (opcional): Ruta del archivo SQLite (default: 3_rachas_sql/rachas.db)
- `--verbose`: Mostrar logs detallados

---

## Ejercicio 2: KPI, Calidad y Trazabilidad

Diseño y KPIs propuestos para monitorear el dataset de teléfonos, con histórico por corrida y alertas por umbrales.

Ver: `2_kpi/DATA_QUALITY.md`


Ejercicio 4: Procesamiento HTML

Descripción

Este ejercicio contiene una herramienta simple para "incrustar" imágenes locales en HTML (convertir referencias locales en data URIs) usando solo la biblioteca estándar de Python. Está pensada como una utilidad ligera para generar versiones de páginas HTML autónomas.

Ubicación

- Script: `4_html_processing/html_pipeline.py`
- Ejemplos: `4_html_processing/html/` (contiene `real_page_1.html`, `real_page_2.html` y `assets/` con SVGs de ejemplo)

Cómo ejecutar

Desde la raíz del repositorio, después de activar el `.venv`:

```bash
python 4_html_processing/html_pipeline.py --paths 4_html_processing/html --report 4_html_processing/html/report.json
```

Opciones importantes

- `--paths`: Lista de archivos o carpetas a procesar (requerido). Ej: `4_html_processing/html`.
- `--report`: Ruta opcional para guardar un JSON con el reporte de éxito/errores.
- `--verbose`: Muestra logs más detallados.

Comportamiento y supuestos

- El script procesa archivos `.html` y `.htm` en las rutas dadas (recursivo para carpetas).
- Solo incrusta recursos locales (rutas relativas o absolutas en el sistema de archivos). No descarga recursos remotos (`http(s)://`) ni modifica `data:` URIs existentes.
- Las imágenes locales referenciadas (por ejemplo `assets/red.svg`) se convierten a `data:<mime>;base64,...` y se reemplaza el atributo `src` por el data URI.
- Los archivos resultantes se escriben junto al HTML de origen con el sufijo `_inlined` (por ejemplo `real_page_1_inlined.html`). Si ya existe un archivo con ese nombre, el script añade `_2`, `_3`, ... para evitar sobrescribir.
- El script devuelve por consola un JSON con dos objetos: `success` (archivos procesados y recursos incrustados) y `fail` (errores por archivo).

Limitaciones

- No valida/beautifica el HTML; usa un parser simple y preserva la mayor parte del contenido original.
- No soporta CSS/JS externo (solo procesado de `img[src]`).


Ejemplo con parámetros personalizados
```bash
python 3_rachas_sql/rachas_pipeline.py \
  --fecha-base 2024-12-15 \
  --n 6 \
  --out rachas_6meses.csv \
  --verbose
```

Salida esperada

El script genera:

- Base de datos SQLite: `3_rachas_sql/rachas.db`
- Archivo CSV: `resultados_rachas.csv` (o el especificado en `--out`)
- Consola: Top 20 rachas más largas

Notas técnicas

- No es necesario instalar SQLite por separado (usa sqlite3 incluido en Python)
- El script busca `Prueba Tecnica.xlsx` en el directorio actual por defecto
- Los niveles de deuda son: N0 (< 300k), N1 (300k-1M), N2 (1M-3M), N3 (3M-5M), N4 (≥5M)
- Si un cliente no aparece en un mes (después de su primera aparición), se considera N0
- Los clientes retirados no se consideran después de su fecha de retiro

Ejercicios 1, 2 y 4
[Documentación pendiente - agregar según implementación]
# Tuya Data Test - Ejercicio 3 (Rachas)

Este repositorio contiene varios ejercicios; este documento explica cómo ejecutar el Ejercicio 3 (Rachas) usando Python + SQLite.

Resumen:
- El archivo Excel `Prueba Tecnica.xlsx` está en la raíz del repo.
-- El script para el ejercicio 3 está en `3_rachas_sql/rachas_pipeline.py`.
- Los SQL están en `3_rachas_sql/sql/`.

Entorno y dependencias (recomendado en root):

1) Crear el entorno virtual en la raíz del repo:

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux / macOS (bash):
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2) Ejecutar el Ejercicio 3

Desde la raíz del repo (usando el `.venv` creado arriba):

```bash
python 3_rachas_sql/rachas_pipeline.py --fecha-base 2024-12-15 --n 3
```

Notas importantes:
- No es necesario instalar SQLite por separado; se usa `sqlite3` incluido en Python.
- El script busca `Prueba Tecnica.xlsx` en el directorio actual por defecto. Si está en otra ubicación, usa `--excel ruta/al/archivo.xlsx`
- El archivo SQLite (`rachas.db`) se crea dentro de la carpeta `3_rachas_sql/`
- Los resultados se guardan en `resultados_rachas.csv` por defecto. Personaliza con `--out nombre.csv`

Estructura esperada (parcial):

```
tuya-data-test/
  .venv/
  Prueba Tecnica.xlsx
  requirements.txt
  README.md
  1_dataset_design/
  2_kpis_quality/
  3_rachas_sql/
    rachas_pipeline.py
    sql/
  4_html_processing/
```

## Parámetros

- `--fecha-base` (requerido): Fecha de corte en formato YYYY-MM-DD
- `--n` (requerido): Número mínimo de meses consecutivos para filtrar rachas
- `--excel` (opcional): Ruta al archivo Excel (default: Prueba Tecnica.xlsx)
- `--out` (opcional): Nombre del CSV de salida (default: resultados_rachas.csv)
- `--db` (opcional): Ruta del archivo SQLite (default: 3_rachas_sql/rachas.db)
- `--verbose`: Mostrar logs detallados

---

**Ejercicio 1: Dataset confiable de teléfonos (Azure + Databricks)**

Resumen del enfoque:
- Medallion architecture (Bronze/Silver/Gold) usando ADLS Gen2 + Delta Lake.
- Control de PII y acceso con Unity Catalog y RBAC.
- Validaciones automáticas en Silver (E.164, completitud, duplicados).
- Gold como tabla consumible versionada (SCD2 / snapshots) gobernada por contrato YAML.
- CI/CD con GitHub Actions: validar contrato, métricas y quality gates antes de promover a prod.
- Lineage y auditoría: `run_id`, `ingestion_ts`, `source_system` y tablas de quality_logs.

Documentos:
- Diseño conceptual: [1_dataset_design/PHONE_DATASET_DESIGN.md](1_dataset_design/PHONE_DATASET_DESIGN.md)
- Contract YAML: [1_dataset_design/contracts/phone_trusted.contract.yaml](1_dataset_design/contracts/phone_trusted.contract.yaml)

