# Tuya Data Test — Prueba Técnica (Ingeniería de Datos)

Este repositorio contiene la solución completa a la prueba técnica de Ingeniería de Datos (Tuya), organizada por ejercicios. El enfoque prioriza **claridad, corrección, simplicidad y buenas prácticas**.

---

## Estructura del repositorio

```text
tuya-data-test/
│
├── .git/                                  # Repositorio Git (subido a GitHub)
├── .venv/                                 # Entorno virtual Python
├── Prueba Tecnica.xlsx                    # Datos de entrada (ejercicio 3)
├── Prueba Ingeniería de Datos.pdf         # Especificación de la prueba
├── README.md                              # Documentación principal del proyecto
├── requirements.txt                       # Dependencias (openpyxl)
│
├── 1_dataset_design/                      # Ejercicio 1: Dataset confiable de teléfonos
│   ├── PHONE_DATASET_DESIGN.md            # Diseño conceptual + arquitectura Azure+Databricks
│   ├── phone_trusted.contract.yaml        # Contrato de datos (schema + validaciones esperadas)
│   └── desing_diagram.png                 # Diagrama de arquitectura
│
├── 2_kpi/                                 # Ejercicio 2: KPIs y calidad de datos
│   └── DATA_QUALITY.md                    # Monitoreo, KPIs, alertas, SLOs
│
├── 3_rachas_sql/                          # Ejercicio 3: Pipeline de rachas (Python + SQLite)
│   ├── rachas_pipeline.py                 # Script principal con CLI (--fecha-base, --n, etc)
│   ├── rachas.db                          # Base de datos SQLite (generada)
│   ├── resultados_rachas.csv              # Salida CSV (rachas detectadas)
│   └── sql/
│       ├── ddl.sql                        # Creación de tablas (historia_saldos, retiros)
│       └── query_rachas.sql               # Query para detectar rachas
│
└── 4_html_processing/                     # Ejercicio 4: Procesador HTML (inlining de imágenes)
    ├── html_pipeline.py                   # Script principal (solo standard library)
    ├── report.json                        # Reporte de procesamiento
    └── html/
        ├── test_*.html                    # HTML de prueba
        ├── test_*_ok.html                 # Versiones procesadas (inlined)
        ├── assets/                        # Imágenes (SVG/PNG/JPG)
        └── nested/                        # Subcarpetas para probar recursividad
```

---

## Requisitos

* Python 3.10+ recomendado
* Dependencias: `openpyxl` (solo para el Ejercicio 3, lectura de Excel)

---

## Configuración rápida (una sola vez)

### 1) Crear entorno virtual

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS (bash)**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Resumen por ejercicio

| Ejercicio | Enfoque                                       | Archivos clave                                                                                     |
| --------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **1**     | Diseño dataset teléfonos (Azure + Databricks) | `1_dataset_design/PHONE_DATASET_DESIGN.md`, `1_dataset_design/phone_trusted.contract.yaml`         |
| **2**     | KPIs y monitoreo de calidad                   | `2_kpi/DATA_QUALITY.md`                                                                            |
| **3**     | Pipeline rachas (Python + SQLite)             | `3_rachas_sql/rachas_pipeline.py`, `3_rachas_sql/sql/ddl.sql`, `3_rachas_sql/sql/query_rachas.sql` |
| **4**     | Procesamiento HTML (inlining de imágenes)     | `4_html_processing/html_pipeline.py`, ejemplos en `4_html_processing/html/`                        |

---

# Ejercicio 1 — Dataset confiable de teléfonos

## Objetivo

Diseñar un proceso **auditable, confiable y controlado por CI/CD** para construir y mantener un dataset de teléfonos listo para uso de negocio (alto impacto, sensible).

## Entregables

* Diseño y decisiones: `1_dataset_design/PHONE_DATASET_DESIGN.md`
* Contrato de datos: `1_dataset_design/phone_trusted.contract.yaml`
* Diagrama: `1_dataset_design/desing_diagram.png`

> Nota: este ejercicio es conceptual (no requiere ejecución de código).

---

# Ejercicio 2 — KPI, Calidad y Trazabilidad 

## Objetivo

Definir un mecanismo para monitorear calidad del dataset de teléfonos y exponer indicadores (KPI) útiles para negocio con trazabilidad e histórico.

## Entregable

* Documento: `2_kpi/DATA_QUALITY.md`

> Nota: este ejercicio es conceptual (no requiere ejecución de código).

---

# Ejercicio 3 — Rachas (Python + SQLite)

## Objetivo

Cargar la información del Excel a SQLite y ejecutar una consulta que identifique **rachas de meses consecutivos** por cliente dentro de un **nivel de deuda**, filtrando por longitud mínima `n` y considerando una `fecha_base`.

## Cómo ejecutar

Desde la raíz del repo:

```bash
python 3_rachas_sql/rachas_pipeline.py --fecha-base 2024-12-15 --n 3
```

### Parámetros (CLI)

* `--fecha-base` (requerido): Fecha base `YYYY-MM-DD`
* `--n` (requerido): Longitud mínima de racha
* `--excel` (opcional): Ruta al Excel (default: `Prueba Tecnica.xlsx`)
* `--db` (opcional): Ruta SQLite (default: `3_rachas_sql/rachas.db`)
* `--out` (opcional): CSV salida (default: `3_rachas_sql/resultados_rachas.csv`)
* `--verbose`: logs más detallados

### Salida esperada

* Base SQLite: `3_rachas_sql/rachas.db`
* CSV con resultados: `3_rachas_sql/resultados_rachas.csv`

---

# Ejercicio 4 — Procesamiento HTML

## Objetivo

Procesar HTMLs para **convertir imágenes referenciadas por `<img src="...">` a Base64** y reemplazarlas por **data URIs**, **sin sobrescribir el HTML original**, generando uno nuevo y un reporte con éxitos/fallos.

Requisitos clave:

* Recibir lista de archivos HTML y/o directorios (incluyendo subdirectorios)
* Convertir imágenes a Base64 y reemplazarlas en el HTML
* Generar reporte `{ success: {}, fail: {} }`
* Usar únicamente **standard library**

## Cómo ejecutar

### Ejemplo: procesar la carpeta de pruebas

Desde la raíz del repo:

```bash
python 4_html_processing/html_pipeline.py --paths 4_html_processing/html --report 4_html_processing/report.json
```

### Parámetros (CLI)

* `--paths` (requerido): lista de archivos y/o directorios a procesar
* `--report` (opcional): ruta para guardar el JSON del reporte
* `--verbose`: logs más detallados

## Qué se genera (antes vs después)

**Antes:**

* El HTML apunta a archivos de imagen locales, por ejemplo:
  * `<img src="assets/logo.png">`

**Después:**

* Se crea un HTML nuevo **al lado del original** con sufijo `_ok`:
  * `mi_pagina.html` → `mi_pagina_ok.html`
* Dentro del HTML de salida, el `src` se reemplaza por algo como:
  * `src="data:image/png;base64,...."`

Esto permite que el HTML procesado sea "portable" (embebe la imagen dentro del propio archivo).

## Supuestos y decisiones

* Solo se procesan tags `<img ...>` (según el enunciado).
* El output **no reemplaza** el archivo original: crea un archivo nuevo con sufijo `_ok` y, si existe, agrega sufijos numéricos.
* El reporte final se imprime en consola y opcionalmente se guarda a JSON con `--report`.

