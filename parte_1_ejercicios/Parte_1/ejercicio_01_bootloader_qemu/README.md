# Ejercicio 1 - Mini sistema operativo booteable en ensamblador y QEMU

Bootloader **de dos etapas** en ensamblador x86 (modo real, 16 bits) que arranca en QEMU y dibuja una pantalla institucional UTEM escribiendo **directamente al framebuffer de texto VGA (`0xB8000`)**. Desarrollado para la **Evaluación Integradora 1** de la asignatura *Infraestructura para Ciencia de Datos* (INFB6074) de la UTEM.

---

## Contexto académico

| Campo       | Detalle                                                                 |
| ----------- | ----------------------------------------------------------------------- |
| Universidad | Universidad Tecnológica Metropolitana (UTEM)                            |
| Carrera     | Ingeniería Civil en Ciencia de Datos                                    |
| Asignatura  | Infraestructura para Ciencia de Datos (**INFB6074**)                     |
| Evaluación  | Evaluación Integradora 1 - Ejercicio 1                                   |
| Semestre    | Primer Semestre 2026                                                     |
| Profesor    | Dr. Ing. Michael Miranda Sandoval                                        |
| Integrantes | Ignacio Ramírez ([@altairBASIC](https://github.com/altairBASIC))<br>Cristian Vergara ([@Cristian-Vergara](https://github.com/Cristian-Vergara))<br>Francisco Provoste ([@fprovoste0](https://github.com/fprovoste0)) |

---

## Por qué dos etapas (decisión técnica central)

Un sector de arranque mide **exactamente 512 bytes**: 510 útiles más 2 de firma. La pantalla institucional requerida por el enunciado (banner ASCII de UTEM, identificación del curso, varias líneas explicativas y separadores) **no cabe** junto con el código en ese espacio.

En lugar de recortar el contenido, este proyecto adopta el patrón real de los bootloaders de producción (GRUB, el cargador de Windows): **arranque en dos etapas**.

- **Etapa 1 — `stage1.asm` (512 bytes):** es el único sector que el BIOS carga en `0x7C00`. Su única responsabilidad es leer la etapa 2 desde el disco usando el servicio de disco del BIOS (`int 0x13`) y saltar a ella. Lleva la firma `0xAA55`.
- **Etapa 2 — `stage2.asm` (2048 bytes):** ya sin la restricción de 512 bytes, dibuja la pantalla institucional completa escribiendo directo a `0xB8000`.

La imagen de disco final es la concatenación `stage1 + stage2` = **2560 bytes**.

---

## Descripción funcional

Al ejecutarse en QEMU:

1. El BIOS carga `stage1` (512 B) en `0x7C00` y verifica la firma `0xAA55`.
2. `stage1` inicializa segmentos y pila, y usa `int 0x13` para leer 4 sectores (la etapa 2) en `0x0000:0x7E00`.
3. `stage1` salta a `stage2`.
4. `stage2` apunta `ES` al segmento `0xB800`, limpia las 2000 celdas de pantalla y recorre una **tabla de descriptores** `(fila, columna, color, puntero)` imprimiendo cada cadena directamente en memoria de video.
5. Se dibuja el banner **UTEM**, la identificación del curso, 5 líneas explicativas sobre arquitectura y el estado de arranque.
6. La CPU se detiene con `cli` + `hlt`.

---

## Requisitos

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y nasm qemu-system-x86 make
```

### Fedora

```bash
sudo dnf install -y nasm qemu-system-x86 make
```

### macOS (Homebrew)

```bash
brew install nasm qemu make
```

---

## Uso rápido

```bash
make build     # Ensambla ambas etapas y construye build/disk.img
make run       # Ejecuta la imagen en QEMU
make verify    # Comprueba tamaños (512 / 2048 / 2560) y firma 0xAA55
make all       # build + run
make clean     # Elimina binarios e imagen
```

---

## Estructura del repositorio

```
ejercicio_01_bootloader_qemu/
├── src/
│   ├── stage1.asm      # Etapa 1: boot sector de 512 B (carga la etapa 2)
│   └── stage2.asm      # Etapa 2: pantalla institucional (escribe a 0xB8000)
├── build/
│   ├── stage1.bin      # Binario etapa 1 (no versionado)
│   ├── stage2.bin      # Binario etapa 2 (no versionado)
│   ├── disk.img        # Imagen de disco concatenada (no versionado)
│   └── .gitkeep
├── docs/
│   ├── informe.md      # Informe técnico del ejercicio
│   └── capturas/
│       └── qemu-boot.png   # Captura de la ejecución en QEMU
├── Makefile
└── README.md
```

---

## Comandos de referencia (manuales)

```bash
# Compilación
nasm -f bin -o build/stage1.bin src/stage1.asm
nasm -f bin -o build/stage2.bin src/stage2.asm
cat build/stage1.bin build/stage2.bin > build/disk.img

# Verificación de tamaños
wc -c < build/stage1.bin   # 512
wc -c < build/disk.img     # 2560

# Verificación de firma (offset 0x1FE debe ser 55 aa)
od -A x -t x1 -j 0x1FE -N 2 build/disk.img

# Ejecución
qemu-system-x86_64 -drive format=raw,file=build/disk.img
```

---

## Conceptos clave

- **Boot sector y firma `0xAA55`:** el BIOS solo reconoce como arrancable un primer sector de 512 bytes que termine en los bytes `0x55 0xAA` (little-endian).
- **Modo real x86:** la CPU arranca en modo de 16 bits con segmentación; dirección física = `segmento × 16 + offset`.
- **Framebuffer de texto VGA (`0xB8000`):** memoria de video de 80×25 celdas, 2 bytes por celda (`[carácter][atributo de color]`). Escribir aquí es como un SO real gestiona la consola.
- **Bootloader de dos etapas:** patrón estándar para superar el límite de 512 bytes del primer sector.

---

## Declaración de uso de herramientas de apoyo

Conforme a la sección de integridad académica del enunciado: este ejercicio parte de un bootloader previo del grupo (asignatura INFB6052) que fue **rediseñado críticamente** para esta evaluación. Los cambios sustantivos —migración de `int 0x10` a escritura directa en `0xB8000`, arquitectura de dos etapas con carga vía `int 0x13`, banner institucional y líneas explicativas— fueron implementados, compilados y verificados en QEMU por el grupo. Se utilizó asistencia de IA como apoyo para la reestructuración y la generación de la tabla de descriptores; todo el código fue revisado, ejecutado y validado por el grupo.

---

## Referencias

- QEMU Project. *QEMU Documentation*. <https://www.qemu.org/docs/master/>
- NASM Project. *NASM Manual*. <https://www.nasm.us/docs.php>
- OSDev Wiki. *Boot Sequence*. <https://wiki.osdev.org/Boot_Sequence>
- OSDev Wiki. *Rolling Your Own Bootloader*. <https://wiki.osdev.org/Rolling_Your_Own_Bootloader>
