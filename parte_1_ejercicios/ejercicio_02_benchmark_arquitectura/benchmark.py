import time
import psutil
import math
import random
import numpy as np
import gc
from pathlib import Path
import matplotlib.pyplot as plt


# ============================================================
# Configuración de tamaños
# ============================================================

# CPU (N-body): N partículas. Trabajo real = N*(N-1)/2 pares de cálculos.
# Produce aprox. 1.1M, 2.0M, 3.9M, 8.0M, 15.1M cálculos de pares.
N_PARTICULAS = [1500, 2000, 2800, 4000, 5500]

# Memoria (acceso secuencial y aleatorio): número de elementos float64.
LADOS_MATRIZ = [500, 1200, 2800, 6000, 11000]

# Disco (escritura/lectura): tamaño del archivo en MB.
SIZES_DISK_MB = [2500,4000,6000,8000]

# Disco - solo subconjunto chico para CSV (serialización es muy lenta)
SIZES_CSV_MB = [200, 400,600,800]

def medir(func, *args, **kwargs):
    """
    Ejecuta func(*args, **kwargs) midiendo tiempo y memoria.

    Devuelve un dict con:
      - tiempo_s: segundos transcurridos
      - memoria_delta_mb: cambio de memoria residente (RSS) en MB
      - resultado: lo que devolvió func
    """
    proceso = psutil.Process()

    mem_antes = proceso.memory_info().rss
    t_antes = time.perf_counter()

    resultado = func(*args, **kwargs)

    t_despues = time.perf_counter()
    mem_despues = proceso.memory_info().rss

    return {
        "tiempo_s": t_despues - t_antes,
        "memoria_delta_mb": (mem_despues - mem_antes) / 1024**2,
        "resultado": resultado,
    }


def crear_particulas(n, semilla=42):
    """Genera n partículas con posición, velocidad y masa aleatoria.
    La semilla fija hace que cada corrida arranque desde el mismo estado
    (reproducibilidad)."""
    rng = random.Random(semilla)
    return [
        {
            "x":    rng.uniform(-1, 1),
            "y":    rng.uniform(-1, 1),
            "vx":   0.0,
            "vy":   0.0,
            "masa": rng.uniform(0.5, 2.0),
        }
        for _ in range(n)
    ]


def paso_nbody(particulas, dt=0.01, softening=0.001):
    """Un paso de simulación gravitacional 2D. Modifica `particulas` in-place.

    `softening` evita la singularidad cuando dos partículas están muy
    cerca (sin esto, r² → 0 dispara la fuerza al infinito y truena la sim).
    """
    n = len(particulas)
    fuerzas = [(0.0, 0.0)] * n

    # Cálculo de fuerzas: O(N²)
    for i in range(n):
        fx, fy = 0.0, 0.0
        for j in range(n):
            if i == j:
                continue
            dx = particulas[j]["x"] - particulas[i]["x"]
            dy = particulas[j]["y"] - particulas[i]["y"]
            r2 = dx*dx + dy*dy + softening
            f  = particulas[j]["masa"] / (r2 * math.sqrt(r2))
            fx += f * dx
            fy += f * dy
        fuerzas[i] = (fx, fy)

    # Integración: actualizar velocidades y posiciones (O(N))
    for i, (fx, fy) in enumerate(fuerzas):
        particulas[i]["vx"] += fx * dt
        particulas[i]["vy"] += fy * dt
        particulas[i]["x"]  += particulas[i]["vx"] * dt
        particulas[i]["y"]  += particulas[i]["vy"] * dt


def simulacion_nbody(num_particulas, num_pasos=1):
    """Corre `num_pasos` pasos de simulación con `num_particulas` partículas.
    El trabajo total es aprox. num_pasos × num_particulas × (num_particulas - 1) / 2
    cálculos de pares."""
    particulas = crear_particulas(num_particulas)
    for _ in range(num_pasos):
        paso_nbody(particulas)
    return particulas

# ============================================================
# Orquestador del escenario CPU
# ============================================================
def benchmark_cpu(verbose=True):
    """
    Corre el escenario CPU completo: 8 reps × 5 tamaños de N_PARTICULAS,
    con cooldown de 10 s entre repeticiones para evitar thermal throttling.

    El resultado de la simulación se descarta (no lo guardamos, solo nos
    interesa el tiempo y la memoria).

    Devuelve una lista de dicts; cada dict es una medición.
    """
    registros = []
    n_reps = 8
    cooldown_s = 10

    for idx_n, n in enumerate(N_PARTICULAS):
        pares = n * (n - 1) // 2

        if verbose:
            print(f"\n[CPU] N = {n} partículas ({pares:,} pares de cálculos)")

        for rep in range(1, n_reps + 1):
            m = medir(simulacion_nbody, n)
            # m["resultado"] (la lista de partículas) se descarta acá:
            # no la guardamos en el registro.

            registros.append({
                "escenario":           "cpu_nbody",
                "tamano_n":            n,
                "tamano_pares":        pares,
                "repeticion":          rep,
                "tiempo_s":            m["tiempo_s"],
                "memoria_delta_mb":    m["memoria_delta_mb"],
                "throughput_pares_s":  pares / m["tiempo_s"],
            })

            if verbose:
                print(f"  rep {rep}/{n_reps}: {m['tiempo_s']:.3f} s")

            # Cooldown entre mediciones (no después de la última de todas)
            es_ultima = (idx_n == len(N_PARTICULAS) - 1) and (rep == n_reps)
            if not es_ultima:
                time.sleep(cooldown_s)

    return registros

# ============================================================
# Escenarios B y C: Memoria (secuencial vs strided vs aleatorio)
# El enunciado pide (b) acceso secuencial y (c) acceso aleatorio.
# Se añade además 'strided' (columnas) como caso intermedio ilustrativo.
# ============================================================

def sumar_con_indices(arr, indices):
    """Suma arr[indices] de forma vectorizada (NumPy fancy indexing).

    Esta es la ÚNICA primitiva de acceso usada por los tres patrones de
    memoria (secuencial, strided y aleatorio). Lo único que cambia entre
    ellos es el ORDEN del vector 'indices'; el método de acceso es idéntico.
    Así la comparación es justa: la diferencia de tiempo se debe al patrón
    de localidad y no a usar bucles de Python en un caso y NumPy en otro."""
    return arr[indices].sum()


def benchmark_memoria(verbose=True):
    """
    Corre el escenario memoria completo. Para cada tamaño de arreglo se
    miden TRES patrones de acceso, cada uno con 8 repeticiones:

      - memoria_secuencial : índices en orden 0,1,2,...  (localidad perfecta)
      - memoria_strided    : índices a paso fijo N (equivale a recorrer por
                             columnas una matriz row-major: predecible pero
                             rompe la línea de caché)
      - memoria_aleatorio  : índices BARAJADOS (orden impredecible que
                             derrota al prefetcher: peor caso de localidad)

    Los tres usan la misma primitiva (sumar_con_indices) sobre el MISMO
    arreglo 1D, creado una sola vez por tamaño. Los vectores de índices se
    construyen también una sola vez (fuera de la medición), de modo que lo
    único cronometrado es el patrón de acceso.
    """
    registros = []
    n_reps = 8
    cooldown_s = 10
    rng = np.random.default_rng(42)  # reproducibilidad del barajado

    patrones = ["memoria_secuencial", "memoria_strided", "memoria_aleatorio"]
    total_mediciones = len(LADOS_MATRIZ) * len(patrones) * n_reps
    contador = 0

    for n in LADOS_MATRIZ:
        elementos = n * n
        size_mb = elementos * 8 / (1024**2)

        if verbose:
            print(f"\n[MEM] Arreglo {elementos:,} elementos ({size_mb:.1f} MB)")

        # Arreglo de datos: UNA sola vez por tamaño
        gc.collect()
        arr = np.arange(elementos, dtype=np.float64)

        # Vectores de índices: UNA sola vez por tamaño (fuera de medir)
        idx_secuencial = np.arange(elementos)
        # 'strided': recorre como si fueran columnas de una matriz n×n
        #   (col 0 completa, luego col 1, ...) -> saltos regulares de n
        idx_strided = np.arange(elementos).reshape(n, n).T.reshape(-1).copy()
        # 'aleatorio': permutación barajada de todas las posiciones
        idx_aleatorio = rng.permutation(elementos)

        indices_por_patron = {
            "memoria_secuencial": idx_secuencial,
            "memoria_strided":    idx_strided,
            "memoria_aleatorio":  idx_aleatorio,
        }

        etiquetas = {
            "memoria_secuencial": "Acceso secuencial (orden contiguo)",
            "memoria_strided":    "Acceso strided (saltos regulares = columnas)",
            "memoria_aleatorio":  "Acceso aleatorio (índices barajados)",
        }

        for patron in patrones:
            indices = indices_por_patron[patron]
            if verbose:
                print(f"  {etiquetas[patron]}:")
            for rep in range(1, n_reps + 1):
                m = medir(sumar_con_indices, arr, indices)
                registros.append({
                    "escenario":         patron,
                    "tamano_n":          n,
                    "tamano_elementos":  elementos,
                    "tamano_mb":         size_mb,
                    "repeticion":        rep,
                    "tiempo_s":          m["tiempo_s"],
                    "memoria_delta_mb":  m["memoria_delta_mb"],
                    "throughput_mb_s":   size_mb / m["tiempo_s"],
                })
                contador += 1
                if verbose:
                    print(f"    rep {rep}/{n_reps}: {m['tiempo_s']:.4f} s")
                if contador < total_mediciones:
                    time.sleep(cooldown_s)

        # Liberar antes del siguiente tamaño
        del arr, idx_secuencial, idx_strided, idx_aleatorio
        gc.collect()

    return registros

# ============================================================
# Escenario D: Disco I/O (binario vs CSV)
# ============================================================

def escribir_binario(arr, path):
    """Escribe un array a disco en formato .npy (binario crudo)."""
    np.save(str(path), arr)


def leer_binario(path):
    """Lee un array desde disco en formato .npy."""
    return np.load(str(path))


def escribir_csv(arr, path):
    """Escribe un array a disco en formato CSV (texto plano)."""
    np.savetxt(str(path), arr, delimiter=",")


def leer_csv(path):
    """Lee un array desde disco en formato CSV."""
    return np.loadtxt(str(path), delimiter=",")

def benchmark_disco(verbose=True):
    """
    Corre el escenario disco completo:
      - Binario (.npy) en los 5 tamaños de SIZES_DISK_MB
      - CSV en los 2 tamaños chicos de SIZES_CSV_MB
      - Para cada combinación: 8 reps de escritura + 8 reps de lectura
      - Cooldown de 10 s entre mediciones
    
    Los archivos temporales se crean en ./temp_benchmark_disco/ y se borran al final.
    """
    registros = []
    n_reps = 8
    cooldown_s = 10
    
    # Plan completo: lista de (formato, size_mb)
    plan = [("binario", s) for s in SIZES_DISK_MB] + \
           [("csv",     s) for s in SIZES_CSV_MB]
    
    total_mediciones = len(plan) * 2 * n_reps   # × 2 ops (escr/lect) × n_reps
    contador = 0
    
    # Carpeta temporal
    dir_temp = Path("temp_benchmark_disco")
    dir_temp.mkdir(exist_ok=True)
    
    try:
        for formato, size_mb in plan:
            n_elementos = int(size_mb * 1024**2 / 8)
            arr = np.random.rand(n_elementos)
            extension = "npy" if formato == "binario" else "csv"
            path = dir_temp / f"test_{formato}_{size_mb}MB.{extension}"
            
            if verbose:
                print(f"\n[DISCO-{formato.upper()}] {size_mb} MB ({n_elementos:,} float64)")
            
            # Elegir las funciones según el formato
            fn_escribir = escribir_binario if formato == "binario" else escribir_csv
            fn_leer     = leer_binario     if formato == "binario" else leer_csv
            
            # --- Escritura ---
            if verbose:
                print("  Escritura:")
            for rep in range(1, n_reps + 1):
                if path.exists():
                    path.unlink()           # arrancar siempre desde cero
                m = medir(fn_escribir, arr, path)
                registros.append({
                    "escenario":         f"disco_escritura_{formato}",
                    "tamano_mb":         size_mb,
                    "repeticion":        rep,
                    "tiempo_s":          m["tiempo_s"],
                    "memoria_delta_mb":  m["memoria_delta_mb"],
                    "throughput_mb_s":   size_mb / m["tiempo_s"],
                })
                contador += 1
                if verbose:
                    print(f"    rep {rep}/{n_reps}: {m['tiempo_s']:.3f} s")
                if contador < total_mediciones:
                    time.sleep(cooldown_s)
            
            # --- Lectura ---
            if verbose:
                print("  Lectura:")
            for rep in range(1, n_reps + 1):
                m = medir(fn_leer, path)
                registros.append({
                    "escenario":         f"disco_lectura_{formato}",
                    "tamano_mb":         size_mb,
                    "repeticion":        rep,
                    "tiempo_s":          m["tiempo_s"],
                    "memoria_delta_mb":  m["memoria_delta_mb"],
                    "throughput_mb_s":   size_mb / m["tiempo_s"],
                })
                contador += 1
                if verbose:
                    print(f"    rep {rep}/{n_reps}: {m['tiempo_s']:.3f} s")
                if contador < total_mediciones:
                    time.sleep(cooldown_s)
            
            # Liberar el archivo y el array de esta iteración
            if path.exists():
                path.unlink()
            del arr
            gc.collect()
    
    finally:
        # LIMPIEZA: pase lo que pase, eliminar todo lo creado
        for f in dir_temp.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            dir_temp.rmdir()
        except OSError:
            pass
    
    return registros

# ============================================================
# Visualizaciones
# ============================================================



def graficar_cpu(df_cpu, output_dir="visualizaciones"):
    """Dos gráficos del escenario CPU: throughput constante + escalado O(N²)."""
    Path(output_dir).mkdir(exist_ok=True)
    
    resumen = df_cpu.groupby('tamano_n').agg(
        tiempo_mean=('tiempo_s', 'mean'),
        tiempo_std=('tiempo_s', 'std'),
        throughput_mean=('throughput_pares_s', 'mean'),
        throughput_std=('throughput_pares_s', 'std'),
        pares=('tamano_pares', 'first'),
    ).reset_index()
    
    # Gráfico 1: throughput vs trabajo 
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(resumen['pares'], resumen['throughput_mean'] / 1e6,
                yerr=resumen['throughput_std'] / 1e6,
                marker='o', capsize=4, linewidth=2)
    ax.set_xscale('log')
    ax.set_xlabel('Pares calculados (trabajo total)')
    ax.set_ylabel('Throughput (millones de pares/s)')
    ax.set_title('CPU (N-body): throughput vs trabajo\n'
                 'Throughput constante → tarea CPU-bound confirmada')
    ax.set_ylim(0, max(resumen['throughput_mean'] / 1e6) * 1.3)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/01_cpu_throughput.png", dpi=120, bbox_inches='tight')
    plt.show()
    
    # Gráfico 2: tiempo vs N 
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(resumen['tamano_n'], resumen['tiempo_mean'],
                yerr=resumen['tiempo_std'],
                marker='o', capsize=4, linewidth=2, label='Medido')
    
    # Línea de referencia O(N²)
    n_ref = resumen['tamano_n'].iloc[0]
    t_ref = resumen['tiempo_mean'].iloc[0]
    import numpy as np
    n_range = np.linspace(resumen['tamano_n'].min(), resumen['tamano_n'].max(), 100)
    t_pred = t_ref * (n_range / n_ref) ** 2
    ax.plot(n_range, t_pred, '--', alpha=0.5, label='Referencia O(N²)')
    
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('N partículas')
    ax.set_ylabel('Tiempo (s)')
    ax.set_title('CPU (N-body): tiempo vs N\n'
                 'Crecimiento cuadrático confirma O(N²)')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')
    fig.tight_layout()
    fig.savefig(f"{output_dir}/02_cpu_escalado.png", dpi=120, bbox_inches='tight')
    plt.show()


def graficar_memoria(df_mem, output_dir="visualizaciones"):
    """Tres patrones de acceso a memoria: secuencial vs strided vs aleatorio."""
    Path(output_dir).mkdir(exist_ok=True)

    resumen = df_mem.groupby(['escenario', 'tamano_mb']).agg(
        throughput_mean=('throughput_mb_s', 'mean'),
        throughput_std=('throughput_mb_s', 'std'),
    ).reset_index()

    estilos = {
        'memoria_secuencial': ('C2', 'o', '-',  'Secuencial (contiguo)'),
        'memoria_strided':    ('C1', 's', '--', 'Strided (columnas)'),
        'memoria_aleatorio':  ('C3', '^', ':',  'Aleatorio (barajado)'),
    }

    fig, ax = plt.subplots(figsize=(9, 6))
    for esc, grp in resumen.groupby('escenario'):
        color, marker, linestyle, label = estilos.get(esc, ('gray', '.', '-', esc))
        ax.errorbar(grp['tamano_mb'], grp['throughput_mean'],
                    yerr=grp['throughput_std'],
                    marker=marker, linestyle=linestyle, color=color,
                    capsize=4, linewidth=2, label=label)

    # Línea de referencia en L2 cache (~16 MB)
    ax.axvline(x=16, color='gray', linestyle=':', alpha=0.5, label='Caché L2 (~16 MB)')

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Tamaño del arreglo (MB)')
    ax.set_ylabel('Throughput (MB/s)')
    ax.set_title('Memoria: secuencial vs strided vs aleatorio\n'
                 'El acceso aleatorio derrota al prefetcher → peor caso de localidad')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')
    fig.tight_layout()
    fig.savefig(f"{output_dir}/03_memoria_acceso.png", dpi=120, bbox_inches='tight')
    plt.show()


def graficar_disco(df_disco, output_dir="visualizaciones"):
    """Cuatro curvas: lectura/escritura × binario/CSV."""
    Path(output_dir).mkdir(exist_ok=True)
    
    resumen = df_disco.groupby(['escenario', 'tamano_mb']).agg(
        throughput_mean=('throughput_mb_s', 'mean'),
        throughput_std=('throughput_mb_s', 'std'),
    ).reset_index()
    
    fig, ax = plt.subplots(figsize=(9, 6))
    
    estilos = {
        'disco_escritura_binario': ('C0', 'o', '-',  'Escritura binaria'),
        'disco_lectura_binario':   ('C0', 's', '--', 'Lectura binaria'),
        'disco_escritura_csv':     ('C1', 'o', '-',  'Escritura CSV'),
        'disco_lectura_csv':       ('C1', 's', '--', 'Lectura CSV'),
    }
    
    for esc, grp in resumen.groupby('escenario'):
        color, marker, linestyle, label = estilos.get(esc, ('gray', '.', '-', esc))
        ax.errorbar(grp['tamano_mb'], grp['throughput_mean'],
                    yerr=grp['throughput_std'],
                    marker=marker, linestyle=linestyle, color=color,
                    capsize=4, linewidth=2, label=label)
    
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Tamaño de archivo (MB)')
    ax.set_ylabel('Throughput (MB/s)')
    ax.set_title('Disco: binario vs CSV (escritura y lectura)\n'
                 'Binario limitado por SSD (~1.6 GB/s); CSV limitado por CPU (constante)')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')
    fig.tight_layout()
    fig.savefig(f"{output_dir}/04_disco_formatos.png", dpi=120, bbox_inches='tight')
    plt.show()