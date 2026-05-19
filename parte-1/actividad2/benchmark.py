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
# Escenarios B y C: Memoria (matriz 2D, filas vs columnas)
# ============================================================

def sumar_por_filas(mat):
    """Suma todos los elementos recorriendo fila por fila.
    Cada fila es contigua en memoria (numpy guarda matrices row-major),
    así que el acceso es secuencial y la caché lo predice perfectamente."""
    total = 0.0
    for i in range(mat.shape[0]):
        total += mat[i].sum()
    return total


def sumar_por_columnas(mat):
    """Suma todos los elementos recorriendo columna por columna.
    Cada columna NO es contigua en memoria: hay un salto de N*8 bytes
    entre cada elemento. Eso fuerza cache misses constantes."""
    total = 0.0
    for j in range(mat.shape[1]):
        total += mat[:, j].sum()
    return total

def benchmark_memoria(verbose=True):
    """
    Corre el escenario memoria completo: para cada tamaño de matriz,
    8 repeticiones de acceso por filas + 8 repeticiones por columnas.
    
    La matriz se crea UNA VEZ por tamaño (afuera de medir) y se reusa
    para ambos patrones, garantizando que la única diferencia entre
    secuencial y aleatorio es el patrón de acceso.
    """
    registros = []
    n_reps = 8
    cooldown_s = 10
    
    # Calculamos cuántas mediciones totales para saber cuándo es la última
    total_mediciones = len(LADOS_MATRIZ) * 2 * n_reps
    contador = 0
    
    for n in LADOS_MATRIZ:
        elementos = n * n
        size_mb = elementos * 8 / (1024**2)
        
        if verbose:
            print(f"\n[MEM] Matriz {n}×{n}  ({elementos:,} elementos, {size_mb:.1f} MB)")
        
        # Asignar la matriz UNA VEZ (afuera de medir)
        gc.collect()
        mat = np.arange(elementos, dtype=np.float64).reshape(n, n)
        
        # --- 8 reps acceso por filas ---
        if verbose:
            print("  Acceso por filas (secuencial en memoria):")
        for rep in range(1, n_reps + 1):
            m = medir(sumar_por_filas, mat)
            registros.append({
                "escenario":         "memoria_filas",
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
        
        # --- 8 reps acceso por columnas ---
        if verbose:
            print("  Acceso por columnas (con saltos en memoria):")
        for rep in range(1, n_reps + 1):
            m = medir(sumar_por_columnas, mat)
            registros.append({
                "escenario":         "memoria_columnas",
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
        
        # Liberar matriz antes de pasar al siguiente tamaño
        del mat
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
    """Acceso secuencial (filas) vs no-secuencial (columnas)."""
    Path(output_dir).mkdir(exist_ok=True)
    
    resumen = df_mem.groupby(['escenario', 'tamano_mb']).agg(
        throughput_mean=('throughput_mb_s', 'mean'),
        throughput_std=('throughput_mb_s', 'std'),
    ).reset_index()
    
    fig, ax = plt.subplots(figsize=(9, 6))
    for esc, grp in resumen.groupby('escenario'):
        nombre = esc.replace('memoria_', '').capitalize()
        ax.errorbar(grp['tamano_mb'], grp['throughput_mean'],
                    yerr=grp['throughput_std'],
                    marker='o', capsize=4, linewidth=2, label=nombre)
    
    # Línea de referencia en L2 cache (~16 MB)
    ax.axvline(x=16, color='red', linestyle=':', alpha=0.5, label='Caché L2 (~16 MB)')
    
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Tamaño de matriz (MB)')
    ax.set_ylabel('Throughput (MB/s)')
    ax.set_title('Memoria: acceso secuencial (filas) vs no-secuencial (columnas)\n'
                 'Gap entre curvas crece más allá de L2 → jerarquía de memoria visible')
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