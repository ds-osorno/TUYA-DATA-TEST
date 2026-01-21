-- DDL: Tablas para Ejercicio 3 (Rachas)

DROP TABLE IF EXISTS historia_saldos;
DROP TABLE IF EXISTS retiros;

CREATE TABLE historia_saldos (
  identificacion TEXT NOT NULL,
  corte_mes     TEXT NOT NULL, -- 'YYYY-MM-DD' (fin de mes)
  saldo         INTEGER NOT NULL,
  PRIMARY KEY (identificacion, corte_mes)
);

CREATE TABLE retiros (
  identificacion TEXT PRIMARY KEY,
  fecha_retiro   TEXT -- 'YYYY-MM-DD' o NULL
);

CREATE INDEX IF NOT EXISTS idx_historia_id ON historia_saldos(identificacion);
CREATE INDEX IF NOT EXISTS idx_historia_mes ON historia_saldos(corte_mes);
