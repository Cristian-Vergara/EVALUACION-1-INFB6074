# Evaluación Integradora 1 — INFB6074

**Fundamentos de Arquitectura Computacional, Big Data y Ambientes Reproducibles**

Repositorio de la **Evaluación Integradora 1** de la asignatura *Infraestructura para Ciencia de Datos* (**INFB6074**) de la UTEM. Reúne dos bloques de trabajo: una **Parte 1** con seis ejercicios aplicados que cubren los contenidos de las semanas 1 a 5 (desde un bootloader en ensamblador hasta una mini infraestructura conteinerizada), y una **Parte 2** con el **anteproyecto integrador** que articula esos fundamentos en una propuesta de infraestructura de datos.

---

## Contexto académico

| Campo       | Detalle                                                                 |
| ----------- | ----------------------------------------------------------------------- |
| Universidad | Universidad Tecnológica Metropolitana (UTEM)                            |
| Facultad    | Facultad de Ingeniería — Depto. de Informática y Computación            |
| Carrera     | Ingeniería Civil en Ciencia de Datos                                    |
| Asignatura  | Infraestructura para Ciencia de Datos (**INFB6074**)                    |
| Evaluación  | Evaluación Integradora 1                                                 |
| Semestre    | Primer Semestre 2026                                                     |
| Profesor    | Dr. Ing. Michael Miranda Sandoval                                        |
| Integrantes | Ignacio Ramírez ([@altairBASIC](https://github.com/altairBASIC))<br>Cristian Vergara ([@Cristian-Vergara](https://github.com/Cristian-Vergara))<br>Francisco Provoste ([@fprovoste0](https://github.com/fprovoste0)) |

---

## Estructura del repositorio

```
EVALUACION-1-INFB6074/
├── informe/
│   └── herramientas_evaluación.pdf          # Informe técnico completo de la evaluación
├── parte_1_ejercicios/                       # Bloque experimental (6 ejercicios)
│   ├── ejercicio_01_bootloader_qemu/         # Bootloader x86 de dos etapas en QEMU
│   ├── ejercicio_02_benchmark_arquitectura/  # Microbenchmark CPU / memoria / disco / I/O
│   ├── ejercicio_03_paralelismo_local/       # Paralelismo local y medición de speedup
│   ├── ejercicio_04_pipeline_bigdata_docker/ # Pipeline Big Data (Bronze→Silver→Gold + Parquet)
│   ├── ejercicio_05_docker_compose_infraestructura/  # Data lake local con MinIO + Docker Compose
│   ├── ejercicio_06_evaluacion_arquitectonica/       # Evaluación comparativa de arquitecturas
│   └── requirements_ej2_3_6.txt              # Dependencias compartidas (ejercicios 2, 3 y 6)
└── parte_2_anteproyecto/                     # Anteproyecto integrador
    ├── anteproyecto.pptx                     # Presentación del anteproyecto
    ├── herramientas_anteproyecto_integrador .pdf   # Documento escrito del anteproyecto
    └── diagrama_anteproyecto.png             # Diagrama de la arquitectura propuesta
```

---

## Parte 1 — Ejercicios aplicados

Seis ejercicios que recorren la pila de infraestructura de abajo hacia arriba: del arranque del hardware hasta la orquestación de servicios. Cada carpeta incluye su propio `README.md` con instrucciones detalladas de reproducción.

| # | Ejercicio | Tema | Herramientas clave |
|---|-----------|------|--------------------|
| 1 | [Bootloader en QEMU](parte_1_ejercicios/ejercicio_01_bootloader_qemu) | Mini sistema booteable de dos etapas que escribe directo al framebuffer VGA (`0xB8000`) | NASM · QEMU · Ensamblador x86 (modo real) |
| 2 | [Benchmark de arquitectura](parte_1_ejercicios/ejercicio_02_benchmark_arquitectura) | Diagnóstico experimental de CPU, memoria, disco e I/O con firmas características de cada recurso | Python · NumPy · Pandas · Matplotlib · psutil |
| 3 | [Paralelismo local](parte_1_ejercicios/ejercicio_03_paralelismo_local) | Comparación secuencial vs. paralelo sobre 500.000 registros, midiendo speedup, eficiencia y overhead | Python · multiprocessing · Jupyter |
| 4 | [Pipeline Big Data + Docker](parte_1_ejercicios/ejercicio_04_pipeline_bigdata_docker) | Pipeline reproducible con arquitectura medallón (Bronze→Silver→Gold), reglas de calidad, catálogo y linaje | Docker · Polars · PyArrow · DuckDB · Parquet |
| 5 | [Infraestructura con Docker Compose](parte_1_ejercicios/ejercicio_05_docker_compose_infraestructura) | Data lake local S3-compatible con consultas SQL directas sobre el object storage (patrón *lakehouse*) | Docker Compose · MinIO · DuckDB · Python |
| 6 | [Evaluación arquitectónica](parte_1_ejercicios/ejercicio_06_evaluacion_arquitectonica) | Matriz multicriterio que compara cinco alternativas Big Data a partir de la evidencia de los ejercicios previos | Python · Pandas · Jupyter |

> **Hilo conductor.** Los ejercicios están encadenados: el Ejercicio 2 justifica empíricamente el uso de formatos columnares (Parquet) que adopta el Ejercicio 4; los datos *Silver* del Ejercicio 4 alimentan el data lake del Ejercicio 5; y el Ejercicio 6 sintetiza todo en una comparación arquitectónica.

---

## Parte 2 — Anteproyecto integrador

**Infraestructura de datos personal para priorización contextual en flujos de trabajo técnico multi-dominio.**

Propuesta de diseño de una **infraestructura de datos personal, conteinerizada y reproducible**, orientada a soportar la priorización contextual de señales generadas por un trabajador del conocimiento técnico que opera en múltiples sistemas heterogéneos (correo, calendario, mensajería corporativa, repositorios de código, plataformas académicas).

El foco es la **capa de datos** —ingesta, normalización, calidad, almacenamiento mixto columnar/vectorial/clave-valor, linaje y observabilidad—, no la construcción de un asistente conversacional. Un eventual agente de lenguaje aparece únicamente como *consumidor* que demuestra el valor de la infraestructura, lo que permite defender la propuesta como un trabajo de infraestructura y no de aplicación. La arquitectura propuesta es un **lakehouse local conteinerizado** con zonas bronze/silver/gold sobre object storage, DuckDB para analítica y un vector store dedicado para embeddings, todo orquestado vía Docker Compose.

Contenido de la carpeta:

- **`anteproyecto.pptx`** — presentación del anteproyecto.
- **`herramientas_anteproyecto_integrador .pdf`** — documento escrito completo (contexto, necesidad de datos, propósito técnico, arquitectura preliminar y alternativas consideradas).
- **`diagrama_anteproyecto.png`** — diagrama de la arquitectura propuesta.

---

## Informe

La carpeta [`informe/`](informe) contiene **`herramientas_evaluación.pdf`**, el informe técnico que documenta de forma integrada la Parte 1 (los seis ejercicios y sus resultados) y enlaza con el anteproyecto de la Parte 2.

---

## Requisitos generales

Las herramientas varían según el ejercicio; los requisitos transversales más habituales son:

- **Python 3.12+** — para los ejercicios 2, 3, 4, 5 y 6 (ver `parte_1_ejercicios/requirements_ej2_3_6.txt` y los `requirements.txt` de cada ejercicio).
- **Docker / Docker Compose** — para los ejercicios 4 y 5.
- **NASM y QEMU** — para el ejercicio 1.

Cada ejercicio detalla sus dependencias exactas y su procedimiento de reproducción en el `README.md` correspondiente.

```bash
# Clonar el repositorio
git clone https://github.com/Cristian-Vergara/EVALUACION-1-INFB6074.git
cd EVALUACION-1-INFB6074

# Entrar al ejercicio deseado y seguir su README
cd parte_1_ejercicios/ejercicio_04_pipeline_bigdata_docker
cat README.md
```

---

## Declaración de uso de herramientas de apoyo

Conforme a la sección de integridad académica del enunciado, algunos ejercicios fueron desarrollados con apoyo de herramientas de IA (Claude, de Anthropic) como ayuda para la generación y revisión de código. La asistencia no reemplazó el criterio del grupo: todas las decisiones de diseño fueron tomadas, y el código fue revisado, ejecutado y validado por los integrantes. Cada ejercicio incluye su propia declaración detallada cuando corresponde.