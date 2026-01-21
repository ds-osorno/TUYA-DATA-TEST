# Ejercicio 1 — Diseño de dataset confiable de teléfonos (Azure + Databricks)

## Objetivo

Creacion de un dataset de teléfonos de clientes que sea confiable y listo para usar por negocio. Los teléfonos son PII, así que el pipeline debe tener controles fuertes sobre calidad, acceso y auditabilidad. Todo automatizado con CI/CD para evitar sorpresas en producción.

## Por qué este diseño

**PII y seguridad:** Los teléfonos son datos sensibles. Usamos Unity Catalog para controlar quién ve qué y, cuando aplica, encriptación en ADLS.

**Medallion (Bronze/Silver/Gold):** Separamos capas porque si cambian las reglas de validación podemos reprocesar desde Bronze sin re-ingerir todo. Bronze es nuestra red de seguridad.

**Delta Lake:** ACID transactions y time travel. Si algo se rompe en Gold, podemos hacer rollback a una versión anterior en minutos.

**SCD2 en Gold:** El negocio suele pedir "qué teléfono tenía el cliente X en la fecha Y"; por eso guardamos historia (valid_from/valid_to).

## Arquitectura

Fuentes (CRM/KYC/Canales)
  ↓ batch o streaming
ADLS Gen2 + Delta Lake:
  /bronze/phone_raw/     → todo crudo, append-only
  /silver/phone_valid/   → validado con flags (is_valid, invalid_reason)
  /gold/phone_trusted/   → golden record, listo para BI
  ↓
Databricks (notebooks/jobs)
Unity Catalog (permisos + lineage)
Storage: ADLS Gen2
Formato: Delta (ACID + time travel gratis)
Gobierno: Unity Catalog por tabla/columna

## Escalabilidad y Rendimiento

A medida que el dataset crece, vamos a necesitar pensar en cómo mantener las queries rápidas y los costos manejables.

**Particionamiento:** En Bronze y Silver particionamos por `ingestion_date` para acelerar queries que filtran por rango de fechas (típico en reprocesos). Si pasamos 50M registros, añadimos particionamiento adicional por `country_code` en Silver/Gold para queries geográficas.

**Z-ordering:** En Gold aplicamos Z-ordering por `customer_id` (la columna más consultada en joins). Esto mejora las queries tipo "dame todos los teléfonos del cliente X" de forma considerable.

**Mantenimiento:** Cada 7 días ejecutamos `VACUUM dq_metrics_phone RETAIN 7 DAYS` (limpia versiones antiguas y archivos huérfanos). Ojo con PII: antes de vacuum en Gold, nos aseguramos de que no haya copias de datos sensibles sin encriptar.

## Dónde se almacena cada capa

- Bronze: ADLS Gen2 (Delta) — path `/bronze/phone_raw/` (append-only). Mantener raw tal cual.
- Silver: ADLS Gen2 (Delta) — path `/silver/phone_valid/` (normalización, flags y correcciones temporales).
- Gold: ADLS Gen2 (Delta) — path `/gold/phone_trusted/` (tabla consumible y versionada en Unity Catalog).

## Gobierno y entornos

- Unity Catalog para control de acceso y lineage por tabla/columna.
- RBAC en storage/Databricks: separar permisos para `dev`/`stg`/`prod`.
- Entornos: `dev` (experimentos), `stg` (pre-prod) y `prod`.

## Reglas de validación (ejemplos)

- Formato E.164: regex `^\\+[1-9]\\d{6,14}$`. Ejemplo Colombia: `+573001234567`.
- Completitud: `customer_id` y `phone_e164` no nulos.
- Unicidad: `(customer_id, phone_e164)` sin duplicados en Silver; en Gold aplicar la clave lógica.
- Consistencia: `country_code` debería coincidir con el prefijo de `phone_e164`.
- Placeholders comunes (`0000000`, `1234567`, `NA`, `DESCONOCIDO`) → marcar `status = invalid` usando una lista negra configurable.

## Problemas que vamos a encontrar (y cómo los resolvemos)

**Teléfonos compartidos:**
En Colombia es común que varios familiares usen el mismo número. Si vemos un teléfono asociado a más de 3 `customer_id`, lo marcamos `suspect` y lo enviamos a revisión manual; permitimos una whitelist para casos legítimos.

**Prefijos mal formateados:**
Llegan formatos como `57-300-1234567`, `(57) 300 1234567` o `300 1234 567`. En Silver limpiamos (quitar espacios, paréntesis, guiones) y luego validamos contra E.164.

**Placeholders comunes:**
Valores como `0000000`, `9999999`, `NA` o `SIN TELEFONO` están en una blacklist en configuración (no hardcodeada). Los marcamos `invalid`.

**Clientes sin teléfono:**
Preguntamos al negocio si es aceptable. Por ahora permitimos `NULL` pero medimos el % missing; si pasa 5% se dispara una alerta en CI.

**Tipo de teléfono (mobile/landline):**
Para fase 1 inferimos por prefijo cuando sea claro; el enriquecimiento con APIs (Twilio Lookup) queda para Fase 2.

## Versionamiento y auditoría

**Bronze:** append-only, nunca borramos. Si metemos la pata, reprocesamos desde aquí.

**Silver:** añadimos flags útiles para debug:
- `is_valid`, `invalid_reason`, `normalized_phone`
- `source_system`, `ingestion_ts`, `run_id`

Esto nos permite responder preguntas como "¿qué pasó con este teléfono en la corrida X?".

**Gold:** SCD2 con `valid_from`/`valid_to`. Ejemplo: cliente A tuvo `+573001111111` del `2024-01-01` al `2024-06-15`, y cambió a `+573002222222` desde `2024-06-16`.

Alternativa sencilla: snapshots diarios si solo necesitamos "estado al día X".

**Rollback:** Delta time travel. Si Gold quedó corrupto en `run_id=XYZ` hacemos:

```sql
RESTORE TABLE phone_trusted TO VERSION AS OF 123;
```

Y luego volver a ejecutar el job tras corregir la fuente.

## CI/CD (Azure DevOps Pipelines + Databricks)

Usamos **Azure DevOps Pipelines** para automatizar validaciones y despliegues, y **Databricks Jobs** para la ejecución del pipeline productivo.

**Herramientas específicas:**
- `databricks-cli` para desplegar notebooks y configurar Databricks Assets (DABs).
- `pytest` para unit tests de transformaciones (tests en Python antes de correr en Databricks).
- `great_expectations` para validar el contrato YAML contra datos reales en staging.

**En PR (Pull Request):**
1. Validar contrato YAML (sintaxis y schema básico).
2. Ejecutar tests unitarios con pytest.
3. Ejecutar great_expectations en muestra de staging:
   - `valid_rate >= 98%`
   - `missing_rate <= 5%`
   - `duplicate_pairs = 0`

Si falla alguno, bloqueamos el merge.

**En merge a `main`:**
1. Deploy a `stg` (databricks-cli + DABs).
2. Ejecutar Databricks Job "phone_pipeline_stg" de forma manual o automática.
3. Validar métricas en tabla `dq_metrics_phone`.
4. Si todo OK → promoción manual a `prod` (trigger manual en Azure DevOps).

**Métricas que trackeamos:**
- `total_records`, `valid_count`, `invalid_count`, `suspect_count`
- `duplicate_pairs`, `missing_phones`, `format_errors`
- `processing_time_seconds`

Todo en Delta table `quality_metrics` con `run_id`, `layer`, `timestamp`.

## Monitoreo Operacional

**Alertas en Databricks Jobs:**
Cada Databricks Job tiene configurado un webhook a nuestro canal #data-alerts de Microsoft Teams. Si el job falla o el `valid_rate` cae por debajo de 95%, se dispara un mensaje automático con:
- run_id del job
- error message si aplica
- link directo al notebook en ejecución

**Dashboard de observabilidad (Databricks SQL):**
Tenemos un dashboard que se refresca cada 30 minutos durante horario laboral mostrando:
- Duración de cada run en minutos (target: <15min para Bronze→Silver→Gold).
- Conteo de registros procesados vs fallidos por capa (para detectar caídas en volumen).
- Uso estimado de DBUs y costos acumulados del mes (importante para showback a negocio).
- Última ejecución exitosa y tiempo hasta próxima (para verificar que el job está corriendo).

**Logs centralizados (Azure Log Analytics):**
Todos los logs de Databricks Jobs se envían a Azure Log Analytics (via Azure Diagnostic Settings). Esto nos permite:
- Queries ad-hoc tipo "dame todos los errores de Silver en la última hora".
- Alertas automáticas si ven excepciones de memoria o timeout.
- Retención a largo plazo para auditoría (2 años).

## Quién hace qué

- **Product Owner (negocio):** define qué teléfono es primario y reglas de negocio.
- **Data lead:** umbrales de calidad y whitelist/blacklist.
- **Data Engineering (nosotros):** pipeline, CI/CD y observabilidad.

**Lineage:** Unity Catalog trackea la mayoría del lineage; además guardamos por registro `source_system`, `run_id`, `ingestion_ts` y una tabla `lineage_logs` con `upstream_table`, `downstream_table`, `transformation_applied`, `run_id`.

## Roadmap

**Fase 1 (MVP):**
- Pipeline Bronze → Silver → Gold básico.
- Validaciones core (E.164, duplicados, placeholders).
- CI con quality gates mínimos.

**Fase 2 (mejoras):**
- Detección automática de teléfonos compartidos (con whitelist).
- Enriquecimiento de tipo (mobile/landline) vía API.
- Dashboard en Power BI con métricas de calidad.

**Optimizaciones futuras:**
- Z-ordering en Delta por `customer_id` para consultas más rápidas.
- Particionamiento por `country_code` si el volumen crece.
- Retención y housekeeping de versiones (ej. retener 90 días).

## Data Retention Policy

**Bronze (`/bronze/phone_raw/`):**
- Retener 1 año (compliance con regulaciones PII en LATAM).
- Después de 1 año, ejecutar `VACUUM` para limpiar histórico.

**Silver (`/silver/phone_valid/`):**
- Retener 6 meses (suficiente para reprocesar si necesitamos ajustar reglas de validación).
- Si necesitamos auditoría más antigua, referenciar Bronze.

**Gold (`/gold/phone_trusted/`):**
- Retener indefinidamente (consumible por negocio, potencial valor legal/compliance).
- Guardar snapshots mensuales en path separado para repaso histórico.

**Delta time travel:**
- Mantener últimas 30 versiones por defecto (Delta las guarda automáticamente).
- Para datasets críticos, considerar retención de 60+ versiones si el costo de storage lo permite.
- Usar time travel para rollback en caso de errores: `RESTORE TABLE phone_trusted TO VERSION AS OF 123`.

## Notas prácticas

- Implementar transformaciones en Databricks Notebooks o Jobs idempotentes (mismo run_id no debe insertar duplicados).
- Validar contract YAML (ver `1_dataset_design/contracts/phone_trusted.contract.yaml`) como parte del pipeline de CI, usando `great_expectations`.
- Evitar exponer `phone_e164` en logs sin enmascarar cuando no sea necesario.
- Si la empresa usa Azure DevOps en lugar de otro CI/CD, los templates de pipeline están en `.azuredevops/azure-pipelines-*.yml`.
