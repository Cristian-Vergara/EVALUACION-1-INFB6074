"""
generar_datos.py
Ejercicio 4 - INFB6074 Infraestructura para C. de Datos

Genera datos sintéticos de sensores astronómicos basados en rangos reales
del Observatorio Cerro Paranal (ESO, Chile, 2635m de altitud).

Fuentes de referencia:
  - ESO Paranal DIMM Seeing: archive.eso.org/wdb/wdb/asm/dimm_paranal/form
  - ESO Paranal Meteo: archive.eso.org/wdb/wdb/asm/meteo_paranal/form
  Datos reales descargados: marzo 2024. Rangos calibrados con estadísticas reales.

Archivos generados:
  - datos/lecturas_sensores.csv     → 10.000 filas (Fuente A)
  - datos/eventos_observacion.jsonl → ~1.100 líneas (Fuente B, con duplicados)

Uso:
  python generar_datos.py
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ── Semilla fija para reproducibilidad ──────────────────────────────────────
np.random.seed(42)
random.seed(42)

# ── Configuración principal ───────────────────────────────────────────────────
N_LECTURAS   = 10_000          # filas del CSV
N_EVENTOS    = 1_000           # eventos JSONL (antes de duplicados)
TASA_ERROR   = 0.10            # 10 % de filas con errores inyectados
RUTA_SALIDA  = Path("datos")
RUTA_SALIDA.mkdir(exist_ok=True)

# ── Metadatos de sensores (5 sensores, posiciones cardinales del observatorio) ─
SENSORES = {
    "SENS-001": "Norte",
    "SENS-002": "Sur",
    "SENS-003": "Este",
    "SENS-004": "Oeste",
    "SENS-005": "Centro",
}

# ── Telescopios e instrumentos ────────────────────────────────────────────────
TELESCOPIOS          = ["TEL-CCD01", "TEL-ESP01", "TEL-FOT01"]
INSTRUMENTOS_VALIDOS = ["CCD", "Espectrógrafo", "Fotómetro"]
INSTRUMENTOS_INVALIDOS = ["RADAR", "LIDAR", "SONAR", "ULTRASONIDO"]  # categorías no permitidas
ESTADOS_VALIDOS      = ["completada", "fallida", "cancelada"]

# Objetos celestes reales del hemisferio sur visible desde Chile
OBJETOS_CELESTES = [
    "NGC 224", "M42", "NGC 1977", "Alpha Centauri", "NGC 5128 (Cen A)",
    "M87",     "NGC 4472", "M31 (Andrómeda)", "NGC 253", "M83",
    "NGC 3372 (Eta Carinae)", "Omega Centauri", "NGC 6397", "47 Tucanae",
    "NGC 104", "Carina Nebula", "Large Magellanic Cloud", "SMC",
    "NGC 6752", "NGC 362",
]

# ── Rangos reales calibrados con datos ESO Paranal (marzo 2024) ───────────────
# temperatura_c:     media 16.8°C, std 1.5°C  → rango nocturno 14-20°C
# humedad_pct:       media 10.5%, muy seco     → 3-20%
# velocidad_viento:  media 5.3 m/s             → 0.1-12 m/s
# presion_hpa:       media 745 hPa (altitud 2635m) → 740-810 hPa
# seeing_arcsec:     media 0.64", excellent    → 0.30-2.00"
# transparencia:     alta en desierto          → 0.65-1.00


# ─────────────────────────────────────────────────────────────────────────────
# FUENTE A: lecturas_sensores.csv
# ─────────────────────────────────────────────────────────────────────────────

def generar_lecturas(n_total: int, tasa_error: float) -> pd.DataFrame:
    """
    Genera n_total filas de lecturas de sensores ambientales.
    Cada sensor produce n_total // len(SENSORES) lecturas con intervalo de 5 minutos.
    Después inyecta 8 tipos de error para alcanzar la tasa indicada.
    """
    filas = []
    n_por_sensor = n_total // len(SENSORES)
    fecha_inicio = datetime(2024, 3, 1, 0, 0, 0)

    for sensor_id, ubicacion in SENSORES.items():
        for i in range(n_por_sensor):
            ts = fecha_inicio + timedelta(minutes=5 * i)

            # Añadir leve variación temporal: temperatura baja a las 3-4 AM
            hora = ts.hour
            ajuste_temp = -1.5 if 2 <= hora <= 5 else 0.0   # más frío de madrugada

            fila = {
                "sensor_id":          sensor_id,
                "timestamp":          ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "ubicacion":          ubicacion,
                "temperatura_c":      round(np.random.normal(16.8 + ajuste_temp, 1.5), 2),
                "humedad_pct":        round(float(np.random.uniform(3.0, 20.0)), 1),
                "velocidad_viento_ms": round(float(abs(np.random.normal(5.3, 2.1))), 2),
                "presion_hpa":        round(np.random.normal(745.0, 2.5), 2),
                "seeing_arcsec":      round(float(abs(np.random.normal(0.64, 0.25))), 3),
                "transparencia":      round(float(np.random.uniform(0.65, 1.00)), 3),
            }
            filas.append(fila)

    df = pd.DataFrame(filas)

    # ── Inyección de errores (10 % distribuido en 8 tipos) ──────────────────
    n_err = max(1, int(len(df) * tasa_error / 8))   # errores por tipo

    # Error 1 — temperatura con valor de sensor roto (-999)
    idx = np.random.choice(df.index, n_err, replace=False)
    df.loc[idx, "temperatura_c"] = -999.0

    # Error 2 — humedad imposible (> 100 %)
    idx = np.random.choice(df.index, n_err, replace=False)
    df.loc[idx, "humedad_pct"] = [round(random.uniform(105, 200), 1)
                                   for _ in range(n_err)]

    # Error 3 — sensor_id nulo (campo obligatorio)
    idx = np.random.choice(df.index, n_err, replace=False)
    df.loc[idx, "sensor_id"] = None

    # Error 4 — timestamp en el futuro (año 2027)
    fechas_futuras = [
        (datetime(2027, random.randint(1, 12), random.randint(1, 28),
                  random.randint(0, 23), random.randint(0, 59))
         .strftime("%Y-%m-%dT%H:%M:%S"))
        for _ in range(n_err)
    ]
    idx = np.random.choice(df.index, n_err, replace=False)
    df.loc[idx, "timestamp"] = fechas_futuras

    # Error 5 — seeing negativo (valor físicamente imposible)
    idx = np.random.choice(df.index, n_err, replace=False)
    df.loc[idx, "seeing_arcsec"] = [round(random.uniform(-2.0, -0.1), 3)
                                     for _ in range(n_err)]

    # Error 6 — presión de nivel del mar (sensor descalibrado, valor ~1013 hPa)
    idx = np.random.choice(df.index, n_err, replace=False)
    df.loc[idx, "presion_hpa"] = [round(random.uniform(1010, 1020), 2)
                                   for _ in range(n_err)]

    # Error 7 — transparencia fuera de rango (> 1.0, físicamente imposible)
    idx = np.random.choice(df.index, n_err, replace=False)
    df.loc[idx, "transparencia"] = [round(random.uniform(1.5, 3.0), 3)
                                     for _ in range(n_err)]

    # Error 8 — filas duplicadas (mismo registro repetido)
    duplicados = df.sample(n=n_err, random_state=42)
    df = pd.concat([df, duplicados], ignore_index=True)

    # Mezclar para que los errores no queden agrupados al final
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# FUENTE B: eventos_observacion.jsonl
# ─────────────────────────────────────────────────────────────────────────────

def generar_eventos(n_total: int, tasa_error: float) -> list[dict]:
    """
    Genera n_total eventos de observación telescópica.
    Cada evento representa una sesión de observación completada, fallida o cancelada.
    Después inyecta 5 tipos de error.
    """
    eventos = []
    fecha_inicio = datetime(2024, 3, 1, 20, 0, 0)   # 20:00 hs (oscurece en desierto)

    for i in range(n_total):
        # Los telescopios observan de noche: timestamp aleatorio entre 20:00 y 06:00
        offset_h = random.uniform(0, 10) + random.randint(0, 6) * 24
        ts = fecha_inicio + timedelta(hours=offset_h)

        evento = {
            "obs_id":           f"OBS-2024-{i+1:04d}",
            "sensor_id":        random.choice(list(SENSORES.keys())),
            "timestamp":        ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "objeto_observado": random.choice(OBJETOS_CELESTES),
            "magnitud":         round(random.uniform(-1.5, 15.0), 2),
            "ascension_recta":  round(random.uniform(0.0, 360.0), 4),
            "declinacion":      round(random.uniform(-90.0, 0.0), 4),   # hemisferio sur
            "duracion_min":     random.randint(15, 120),
            "instrumento":      random.choice(INSTRUMENTOS_VALIDOS),
            "estado":           random.choices(
                                    ESTADOS_VALIDOS,
                                    weights=[0.70, 0.20, 0.10]
                                )[0],
        }
        eventos.append(evento)

    # ── Inyección de errores (10 % distribuido en 5 tipos) ──────────────────
    n_err = max(1, int(len(eventos) * tasa_error / 5))

    # Error 1 — instrumento con categoría no permitida
    for idx in np.random.choice(len(eventos), n_err, replace=False):
        eventos[idx]["instrumento"] = random.choice(INSTRUMENTOS_INVALIDOS)

    # Error 2 — declinación fuera de rango (-90 a +90)
    for idx in np.random.choice(len(eventos), n_err, replace=False):
        eventos[idx]["declinacion"] = round(random.uniform(91.0, 180.0), 4)

    # Error 3 — timestamp en el futuro
    for idx in np.random.choice(len(eventos), n_err, replace=False):
        eventos[idx]["timestamp"] = (
            datetime(2027, random.randint(1, 12), random.randint(1, 28),
                     21, 0, 0).strftime("%Y-%m-%dT%H:%M:%S")
        )

    # Error 4 — obs_id duplicado (mismo ID, dos filas distintas)
    ids_originales = [e["obs_id"] for e in eventos[:n_err]]
    for i, idx in enumerate(np.random.choice(len(eventos), n_err, replace=False)):
        copia = dict(eventos[idx])
        copia["obs_id"] = ids_originales[i]     # reutiliza un ID ya existente
        eventos.append(copia)

    # Error 5 — sensor_id nulo (campo obligatorio)
    for idx in np.random.choice(len(eventos), n_err, replace=False):
        eventos[idx]["sensor_id"] = None

    random.shuffle(eventos)
    return eventos


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Generador de datos sintéticos — Observatorio Astronómico")
    print("Rangos calibrados con datos reales ESO Paranal, Chile")
    print("=" * 60)

    # ── Fuente A: CSV ────────────────────────────────────────────────────────
    print(f"\n[1/2] Generando lecturas_sensores.csv ({N_LECTURAS:,} filas base)...")
    df_lecturas = generar_lecturas(N_LECTURAS, TASA_ERROR)
    ruta_csv = RUTA_SALIDA / "lecturas_sensores.csv"
    df_lecturas.to_csv(ruta_csv, index=False)

    # Resumen de errores inyectados en CSV
    n_temp   = (pd.to_numeric(df_lecturas["temperatura_c"],  errors="coerce") == -999).sum()
    n_hum    = (pd.to_numeric(df_lecturas["humedad_pct"],    errors="coerce") > 100).sum()
    n_null   = df_lecturas["sensor_id"].isna().sum()
    n_futuro = df_lecturas["timestamp"].str.startswith("2027").sum()
    n_seeing = (pd.to_numeric(df_lecturas["seeing_arcsec"], errors="coerce") < 0).sum()
    n_pres   = (pd.to_numeric(df_lecturas["presion_hpa"],   errors="coerce") > 900).sum()
    n_trans  = (pd.to_numeric(df_lecturas["transparencia"], errors="coerce") > 1).sum()

    print(f"  → {len(df_lecturas):,} filas guardadas en {ruta_csv}")
    print(f"  Errores inyectados:")
    print(f"    Temperatura -999:      {n_temp:4d} filas")
    print(f"    Humedad > 100%:        {n_hum:4d} filas")
    print(f"    sensor_id nulo:        {n_null:4d} filas")
    print(f"    Timestamp futuro:      {n_futuro:4d} filas")
    print(f"    Seeing negativo:       {n_seeing:4d} filas")
    print(f"    Presión nivel del mar: {n_pres:4d} filas")
    print(f"    Transparencia > 1:     {n_trans:4d} filas")
    print(f"    Duplicados agregados:  incluidos en total")
    total_err = n_temp + n_hum + n_null + n_futuro + n_seeing + n_pres + n_trans
    print(f"    TOTAL filas con error: {total_err:4d} / {len(df_lecturas):,} "
          f"({total_err/len(df_lecturas)*100:.1f}%)")

    # ── Fuente B: JSONL ──────────────────────────────────────────────────────
    print(f"\n[2/2] Generando eventos_observacion.jsonl ({N_EVENTOS:,} eventos base)...")
    eventos = generar_eventos(N_EVENTOS, TASA_ERROR)
    ruta_jsonl = RUTA_SALIDA / "eventos_observacion.jsonl"
    with open(ruta_jsonl, "w", encoding="utf-8") as f:
        for ev in eventos:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    n_err_jsonl = int(N_EVENTOS * TASA_ERROR)
    print(f"  → {len(eventos):,} eventos guardados en {ruta_jsonl}")
    print(f"  Errores inyectados: ~{n_err_jsonl * 5} instancias "
          f"(instrumento inválido, declinación, futuro, duplicados, null)")

    print("\n" + "=" * 60)
    print("¡Datos generados correctamente!")
    print(f"  {ruta_csv}:   {len(df_lecturas):,} filas")
    print(f"  {ruta_jsonl}: {len(eventos):,} eventos")
    print("=" * 60)


if __name__ == "__main__":
    main()
