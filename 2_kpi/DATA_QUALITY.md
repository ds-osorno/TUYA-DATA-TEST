# Ejercicio 2 — KPI, Calidad y Trazabilidad (Dataset de teléfonos)

## Objetivo

Monitorear de forma continua la calidad del dataset `phone_trusted` y transformar las validaciones técnicas en KPIs claros para negocio, con histórico por corrida y trazabilidad por `run_id`.

Este diseño asume un lakehouse en Azure Databricks + Delta y el pipeline con capas:
- Bronze: `phone_raw`
- Silver: `phone_valid`
- Gold: `phone_trusted`

## KPIs principales

- `valid_rate`: % registros con `status = 'valid'` (o `is_valid = true` en Silver).
- `missing_rate`: % clientes sin teléfono usable / % registros con `phone_e164` NULL.
- `duplicates_rate`: duplicados por cliente `(customer_id, phone_e164)` y duplicados globales (`phone_e164` en varios `customer_id`).
- `freshness`: tiempo desde la última ingestión (`now - max(ingestion_ts)`).
- `invalid_rate`: % registros con `invalid_reason` en Silver.
- `top_invalid_reasons`: razones más frecuentes de invalidez (para priorizar acciones).

Todos los KPIs se calculan por `run_id` y se guardan en histórico para poder comparar tendencias.

## Mecanismo de monitoreo

1) Tabla histórica `dq_metrics_phone` (Delta)
- Grano: 1 fila por `run_id` + `metric_name` + dimensión (ej. `source_system`).
- Campos mínimos: `run_id`, `run_ts`, `layer` (silver/gold), `metric_name`, `metric_value`, `source_system` (nullable), `notes` (nullable).

2) Artefacto por corrida
- Guardar un `report.json` por corrida en ADLS: `dq_reports/phones/run_id=<...>/report.json`.
- Debe incluir conteos, KPIs principales, top invalid reasons y el estado de umbrales.

3) Alertas y acción
- Umbrales por KPI (warning / error). Ejemplos:
  - `valid_rate` warning < 98%, error < 95%
  - `missing_rate` warning > 3%, error > 5%
- Acción práctica:
  - **Error**: bloquear publicación a Gold (no promovemos datos malos).
  - **Warning**: publicar pero generar alerta (Teams/Email) y marcar run con `warning`.

## Cómo se calculan los KPIs (en práctica)

Los KPIs se calculan en un Databricks Notebook llamado `calculate_dq_metrics.py` que se ejecuta después de cada corrida de Silver→Gold. El notebook se dispara automáticamente como tarea dependiente en Databricks Jobs (job orchestration).

El flujo es: ingerir → validar en Silver → publicar a Gold → **ejecutar calculate_dq_metrics.py** → insertar resultados en `dq_metrics_phone`.

Si algún KPI cae fuera de umbral (ej. `valid_rate < 95%`), el notebook falla con `exit(1)` y Databricks Job automáticamente envía una notificación.

**Queries SQL de ejemplo:**

a) Calcular `valid_rate` desde `phone_trusted`:
```sql
WITH metrics AS (
  SELECT 
    COUNT(*) as total_records,
    SUM(CASE WHEN status = 'valid' THEN 1 ELSE 0 END) as valid_count,
    current_timestamp() as run_ts
  FROM phone_trusted
  WHERE run_id = '${run_id}'  -- parámetro inyectado desde el notebook
)
INSERT INTO dq_metrics_phone
SELECT
  '${run_id}' as run_id,
  run_ts,
  'gold' as layer,
  'valid_rate' as metric_name,
  ROUND(valid_count / total_records, 4) as metric_value,
  NULL as source_system,
  NULL as notes
FROM metrics;
```

b) Calcular `missing_rate` (clientes sin teléfono válido):
```sql
-- Asume que existe tabla customers con todos los customer_id
WITH customer_coverage AS (
  SELECT
    COUNT(DISTINCT c.customer_id) as total_customers,
    COUNT(DISTINCT p.customer_id) as customers_with_phone
  FROM customers c
  LEFT JOIN phone_trusted p 
    ON c.customer_id = p.customer_id 
    AND p.status = 'valid'
    AND p.run_id = '${run_id}'
)
INSERT INTO dq_metrics_phone
SELECT
  '${run_id}',
  current_timestamp(),
  'gold',
  'missing_rate',
  ROUND((total_customers - customers_with_phone) / total_customers, 4),
  NULL,
  NULL
FROM customer_coverage;
```

c) Top 5 `invalid_reasons` desde Silver (para debugging):
```sql
INSERT INTO dq_metrics_phone
SELECT
  '${run_id}',
  current_timestamp(),
  'silver',
  CONCAT('top_invalid_reason_', ROW_NUMBER() OVER (ORDER BY cnt DESC)),
  cnt,
  NULL,
  invalid_reason  -- guardamos el reason en notas para ver qué falló
FROM (
  SELECT invalid_reason, COUNT(*) as cnt
  FROM phone_valid
  WHERE run_id = '${run_id}' AND is_valid = false
  GROUP BY invalid_reason
  ORDER BY cnt DESC
  LIMIT 5
);
```

## Trazabilidad

Mantener en registros y metadatos:
- `run_id`, `ingestion_ts`, `source_system` en Bronze/Silver/Gold.
- En Silver: `is_valid`, `invalid_reason`, `normalized_phone`.
- En Gold: `status`, `valid_from`, `valid_to` (o `snapshot_date`).

Esto permite responder: ¿qué fuente introdujo este teléfono? ¿en qué corrida se publicó? ¿por qué fue marcado inválido?

## Cómo funcionan las alertas

Un Databricks Job programado cada 24 horas (cron: `0 8 * * *`) ejecuta el notebook `check_alerts.py` que:
1. Lee la tabla `dq_metrics_phone` del último run.
2. Compara cada métrica contra umbrales definidos en un archivo JSON de configuración.
3. Si encuentra problemas, envía notificaciones.

**Flujo de alertas:**
- **Error** (ej. `valid_rate < 95%`): webhook a Teams canal #data-alerts + email a dataDB@tuya.com
- **Warning** (ej. `valid_rate 95-98%`): solo mensaje en Teams (sin email).

**Payload del webhook a Teams:**
```json
{
  "run_id": "20260121_0800",
  "metric": "valid_rate",
  "current_value": 0.94,
  "threshold": 0.95,
  "severity": "error",
  "dashboard_link": "https://databricks.com/.../phone_quality_dashboard"
}
```

**Configuración de umbrales (archivo JSON, no hardcodeada):**
```json
{
  "valid_rate": {"warning": 0.98, "error": 0.95},
  "missing_rate": {"warning": 0.03, "error": 0.05},
  "duplicates_rate": {"warning": 0.01, "error": 0.02},
  "freshness_hours": {"warning": 24, "error": 48}
}
```

**Responsables de alertas:**
- **Error**: Data DB + Data Engineering Lead (ambos reciben email + Teams).
- **Warning**: Solo Data Engineering en canal #data-alerts (Teams).

## Dashboard para Negocio

El dashboard se implementa en **Databricks SQL** (MVP) sin dependencias de Power BI. Se refresca automáticamente cada hora durante horario laboral (6am-8pm).

**Vista principal:**
- Semáforo grande arriba: verde si `valid_rate >= 98%`, amarillo si 95-98%, rojo si < 95%.
- Gráfica de línea: tendencia de `valid_rate` últimos 30 días (identifica si hay deterioro).
- Tabla: top 10 `invalid_reasons` con conteo y % del total (para que negocio sepa qué corregir en la fuente).

**Vista secundaria:**
- Frescura: "última ingesta hace X horas" (target: < 12 hrs).
- Comparativa: `valid_rate` hoy vs promedio de últimos 7 días (para detectar cambios anómalos).
- Tabla de `source_system` breakdown: `valid_rate` por fuente (para identificar si un sistema está malo).

El link del dashboard se incluye automáticamente en las alertas de Teams.

## Ownership

- **Product Owner (negocio):** define umbrales y prioridades.
- **Data DB:** mantiene reglas de calidad y excepciones (whitelist/blacklist).
- **Data Engineering:** opera el pipeline, escribe métricas y configura alertas.

## Cómo usa negocio los KPIs

- Dashboard en Power BI o Databricks SQL con tendencia de `valid_rate`, `missing_rate`, `duplicates_rate` y `freshness`.
- Semáforo diario (verde/amarillo/rojo) y reportes de top invalid reasons para corregir fuentes.

## Resultado esperado

- KPIs comparables en el tiempo (por `run_id`).
- Alertas accionables que eviten publicar datos malos en Gold.
- Trazabilidad por registro para auditoría e incidentes.

## Service Level Objectives (SLO)

**Freshness:** Datos en Gold actualizados <24 horas desde ingesta (target: 12 horas). Si pasa 24h sin actualización, alerta automática.

**Disponibilidad:** Dashboard accesible 99% del tiempo durante horario laboral (6am-8pm, lunes-viernes). Se excluyen mantenimientos programados comunicados.

**Latencia:** Queries en `phone_trusted` responden en <5 segundos (p95). Usar Z-ordering para asegurar esto.

**Calidad:** `valid_rate >= 98%` en promedio mensual. Permitimos picos temporales mientras estemos en 95%+; si caemos <95%, es un incidente.


