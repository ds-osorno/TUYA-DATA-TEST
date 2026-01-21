-- Rachas: devuelve la racha más larga (y más reciente en empate) por cliente
WITH RECURSIVE
params AS (SELECT date(:fecha_base) AS fecha_base, CAST(:n AS INTEGER) AS n),
base_cut AS (
  SELECT CASE
    WHEN date(p.fecha_base, 'start of month', '+1 month', '-1 day') <= p.fecha_base
      THEN date(p.fecha_base, 'start of month', '+1 month', '-1 day')
    ELSE date(p.fecha_base, 'start of month', '-1 day') END AS base_month_end, p.n AS n
  FROM params p
),
historia_niveles AS (
  SELECT identificacion, date(corte_mes) AS corte_mes,
    CASE WHEN saldo < 300000 THEN 'N0'
         WHEN saldo < 1000000 THEN 'N1'
         WHEN saldo < 3000000 THEN 'N2'
         WHEN saldo < 5000000 THEN 'N3' ELSE 'N4' END AS nivel, saldo
  FROM historia_saldos
),
primera_aparicion AS (
  SELECT identificacion, MIN(corte_mes) AS primer_corte FROM historia_niveles GROUP BY identificacion
),
retiro_cutoff AS (
  SELECT identificacion,
    CASE WHEN fecha_retiro IS NULL OR TRIM(fecha_retiro) = '' THEN NULL
         ELSE date(fecha_retiro, 'start of month', '-1 day') END AS retiro_month_end
  FROM retiros
),
cliente_rango AS (
  SELECT p.identificacion, p.primer_corte,
    CASE WHEN rc.retiro_month_end IS NULL THEN bc.base_month_end
         WHEN rc.retiro_month_end < bc.base_month_end THEN rc.retiro_month_end
         ELSE bc.base_month_end END AS end_corte, bc.n AS n
  FROM primera_aparicion p CROSS JOIN base_cut bc LEFT JOIN retiro_cutoff rc USING(identificacion)
  WHERE p.primer_corte <= CASE WHEN rc.retiro_month_end IS NULL THEN bc.base_month_end
                               WHEN rc.retiro_month_end < bc.base_month_end THEN rc.retiro_month_end
                               ELSE bc.base_month_end END
),
meses AS (
  SELECT identificacion, primer_corte AS corte_mes, end_corte, n FROM cliente_rango
  UNION ALL
  SELECT identificacion, date(corte_mes, 'start of month', '+2 months', '-1 day'), end_corte, n FROM meses
  WHERE date(corte_mes, 'start of month', '+2 months', '-1 day') <= end_corte
),
timeline AS (
  SELECT m.identificacion, m.corte_mes, COALESCE(hn.nivel, 'N0') AS nivel
  FROM meses m LEFT JOIN historia_niveles hn ON hn.identificacion = m.identificacion AND hn.corte_mes = m.corte_mes
),
marcas AS (
  SELECT t.*, CASE WHEN LAG(nivel) OVER (PARTITION BY identificacion ORDER BY corte_mes) IS NULL THEN 1
                   WHEN nivel <> LAG(nivel) OVER (PARTITION BY identificacion ORDER BY corte_mes) THEN 1 ELSE 0 END AS inicia_racha
  FROM timeline t
),
rachas_id AS (SELECT m.*, SUM(inicia_racha) OVER (PARTITION BY identificacion ORDER BY corte_mes) AS racha_id FROM marcas m),
rachas_agg AS (SELECT identificacion, nivel, racha_id, COUNT(*) AS racha, MAX(corte_mes) AS fecha_fin FROM rachas_id GROUP BY identificacion, nivel, racha_id),
filtradas AS (SELECT ra.identificacion, ra.nivel, ra.racha, ra.fecha_fin FROM rachas_agg ra JOIN cliente_rango cr ON cr.identificacion = ra.identificacion WHERE ra.racha >= cr.n),
ranked AS (SELECT f.*, ROW_NUMBER() OVER (PARTITION BY identificacion ORDER BY racha DESC, date(fecha_fin) DESC) AS rn FROM filtradas f)
SELECT identificacion, racha, fecha_fin, nivel FROM ranked WHERE rn = 1 ORDER BY identificacion;
