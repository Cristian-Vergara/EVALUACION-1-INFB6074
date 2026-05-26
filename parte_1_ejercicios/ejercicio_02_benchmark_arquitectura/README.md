# Ejercicio 2 — Diagnóstico experimental de CPU, memoria, disco e I/O

---

## Descripción

Microbenchmark local en Python para observar de forma experimental las diferencias
entre operaciones intensivas en **CPU**, **memoria**, **almacenamiento** y **entrada/salida**.
El objetivo es conectar la arquitectura computacional, la jerarquía de memoria y los
cuellos de botella con evidencia medida, no con teoría abstracta.

Cada escenario aísla un recurso distinto y exhibe su "firma" característica:

| Escenario | Recurso bajo prueba | Carga de trabajo |
|-----------|--------------------|------------------|
| **CPU** | Capacidad aritmética del procesador | Simulación gravitacional N-body O(N²) |
| **Memoria** | Jerarquía de caché / prefetcher | Suma de un arreglo con 3 patrones de acceso (secuencial, strided, aleatorio) |
| **Disco** | Almacenamiento (SSD) y serialización | Escritura/lectura binaria (`.npy`) vs. CSV |

Los cuatro escenarios mínimos exigidos por el enunciado quedan cubiertos así: (a) cálculo
intensivo en CPU → N-body; (b) acceso **secuencial** a memoria; (c) acceso **aleatorio**
a memoria; (d) lectura/escritura en disco. El patrón **strided** se añade como caso
intermedio ilustrativo entre el secuencial y el aleatorio.

---

## Estructura de archivos

```
ejercicio_02_benchmark_arquitectura/
├── benchmark.py               # Lógica de los escenarios + funciones de graficado
├── entorno.py                 # Detecta hardware/software y genera entorno_experimental.md
├── actividad2.ipynb           # Notebook orquestador: ejecuta, analiza y discute resultados
├── entorno_experimental.md    # Ficha del entorno experimental (autogenerada)
├── resultados_benchmark.csv   # Mediciones crudas (una fila por repetición)
├── enunciado.md               # Enunciado de la actividad
└── visualizaciones/
    ├── 01_cpu_throughput.png   # Throughput vs. trabajo (firma CPU-bound)
    ├── 02_cpu_escalado.png     # Tiempo vs. N comparado con referencia O(N²)
    ├── 03_memoria_acceso.png   # Secuencial vs. strided vs. aleatorio
    └── 04_disco_formatos.png   # Binario vs. CSV (lectura y escritura)
```

---

## Cómo reproducir

```bash
# 1. Navegar a esta carpeta
cd parte_1_ejercicios/ejercicio_02_benchmark_arquitectura

# 2. Instalar dependencias
pip install numpy pandas matplotlib psutil nbformat

# 3. (Opcional) Regenerar la ficha del entorno para tu propia máquina
python entorno.py

# 4. Abrir y ejecutar el notebook de principio a fin
jupyter notebook actividad2.ipynb
```

> **Advertencia de tiempo de ejecución.** El benchmark aplica un *cooldown* de 10 s
> entre cada repetición para mitigar el *thermal throttling*. Solo el escenario de
> memoria (120 mediciones) tarda **~20 min**; el conjunto completo (288 mediciones)
> ronda **1 h 20 min** en la máquina de referencia. El `resultados_benchmark.csv`
> incluido permite revisar el análisis sin volver a correr todo.

---

## Metodología

- **`medir(func, ...)`** envuelve cada operación midiendo el tiempo con
  `time.perf_counter()` y el delta de memoria residente (RSS) con `psutil`.
- Cada combinación se repite **8 veces** para reportar promedio ± desviación estándar
  (el enunciado pide ≥3).
- Las semillas aleatorias están fijas (reproducibilidad).
- En el escenario de memoria, el arreglo y los vectores de índices se construyen **una
  sola vez** por tamaño, de modo que la única variable medida sea el **patrón de acceso**
  y no la asignación. Los tres patrones usan la misma primitiva (`arr[indices].sum()`),
  variando solo el orden de los índices; así la comparación es justa.
- En el escenario de disco, los archivos temporales se crean en `temp_benchmark_disco/`
  y se eliminan automáticamente mediante un bloque `finally`.

### Parámetros de cada escenario

| Escenario | Tamaños probados | Mediciones |
|-----------|------------------|-----------|
| CPU (N-body) | N = 1500, 2000, 2800, 4000, 5500 partículas | 5 × 8 = 40 |
| Memoria | Lado N = 500, 1200, 2800, 6000, 11000 (× 3 patrones) | 5 × 3 × 8 = 120 |
| Disco binario | 2500, 4000, 6000, 8000 MB (escritura y lectura) | 4 × 2 × 8 = 64 |
| Disco CSV | 200, 400, 600, 800 MB (escritura y lectura) | 4 × 2 × 8 = 64 |

Los tamaños de disco binario (> 4 GB) buscan exceder el *page cache* de una máquina de
16 GB para reflejar la velocidad real del SSD. Los tamaños de CSV se mantienen chicos
porque la serialización a texto es CPU-bound y escala muy mal.

### Patrones de acceso a memoria

- **Secuencial:** índices en orden 0, 1, 2, ... → localidad perfecta, el prefetcher acierta.
- **Strided:** índices a paso fijo (equivale a recorrer una matriz row-major por columnas)
  → saltos predecibles que rompen la línea de caché.
- **Aleatorio:** índices barajados → orden impredecible que derrota al prefetcher; peor
  caso de localidad.

---

## Resultados principales

**CPU (N-body).** El throughput se mantiene aproximadamente constante (~4.5–5.0 millones
de pares/s) pese a que el trabajo crece 13× entre el N menor y el mayor. Esa invariancia
es la firma de una tarea **CPU-bound**. El tiempo escala de forma compatible con O(N²).

**Memoria.** El orden **secuencial > strided > aleatorio** se cumple en los cinco tamaños
sin excepción:

| Tamaño | Secuencial | Strided | Aleatorio | Ratio Sec/Aleat |
|--------|-----------:|--------:|----------:|:---------------:|
| 1.9 MB | 1959 MB/s | 1182 MB/s | 710 MB/s | 2.8× |
| 11 MB | 3725 MB/s | 1470 MB/s | 1005 MB/s | 3.7× |
| 60 MB | 3958 MB/s | 2147 MB/s | 706 MB/s | 5.6× |
| 275 MB | 6108 MB/s | 2559 MB/s | 1340 MB/s | 4.6× |
| 923 MB | 8197 MB/s | 2925 MB/s | 1549 MB/s | 5.3× |

El acceso aleatorio es entre **2.8× y 5.6× más lento** que el secuencial, y la brecha se
acentúa al superar la frontera de la caché L2 (~16 MB), consistente con la jerarquía de
memoria. Detalle metodológico: el patrón secuencial es el de mayor variabilidad en los
tamaños chicos porque sus tiempos (milisegundos) quedan dominados por ruido del sistema;
el aleatorio, al tardar más, mide más estable.

**Disco.** El formato binario (`.npy`) opera entre ~1000–2900 MB/s y decae con el tamaño
del archivo hasta acercarse al throughput sostenido del SSD. El CSV se mantiene plano y
~2 órdenes de magnitud más lento (escritura ~13 MB/s, lectura ~56 MB/s): su límite es el
costo de serialización a texto (CPU-bound), no el dispositivo. Este resultado justifica
de forma empírica la preferencia por formatos binarios columnares (Parquet) en pipelines
Big Data, decisión adoptada en el Ejercicio 4 de esta evaluación.

---

## Entorno experimental

La ficha completa y autogenerada está en
[`entorno_experimental.md`](./entorno_experimental.md). Resumen de la máquina de referencia:

| Componente | Detalle |
|------------|---------|
| Sistema operativo | macOS 26.3.1 |
| Procesador | Apple M4 (10 núcleos físicos / 10 lógicos) |
| RAM | 16 GB |
| Python | 3.12 |
| NumPy / Pandas / Matplotlib / psutil | 2.4 / 3.0 / 3.10 / 7.2 |

> Los valores absolutos dependen del hardware. Al reproducir en otra máquina, las
> tendencias (firma CPU-bound, orden secuencial > strided > aleatorio, brecha
> binario/CSV) deberían mantenerse aunque cambien las cifras.

## Declaración de herramientas de apoyo

Este ejercicio fue desarrollado con apoyo de IA (Claude, de Anthropic) como herramienta
de ayuda para desarrollar codigo, la IA no reemplazo el intelecto humano, toda desicion
fue tomada.