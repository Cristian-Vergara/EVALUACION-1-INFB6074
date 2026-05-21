# =============================================================================
# Makefile - Ejercicio 1: Bootloader de 2 etapas
# Evaluacion Integradora 1 - INFB6074 - Infraestructura para C. de Datos
# UTEM - Ingenieria Civil en Ciencia de Datos
# Grupo: I.Ramirez, C.Vergara, F.Provoste
# =============================================================================

ASM    = nasm
QEMU   = qemu-system-x86_64

SRC1   = src/stage1.asm
SRC2   = src/stage2.asm
BIN1   = build/stage1.bin
BIN2   = build/stage2.bin
IMG    = build/disk.img

.PHONY: all build run clean verify

# Target por defecto: compila la imagen y la ejecuta en QEMU
all: build run

# -----------------------------------------------------------------------------
# build: ensambla ambas etapas y concatena en una imagen de disco unica.
# La imagen final es: [stage1: 512 B][stage2: 2048 B] = 2560 bytes.
# El BIOS lee el primer sector (stage1) y stage1 lee el resto (stage2).
# -----------------------------------------------------------------------------
build:
	@echo "==> Ensamblando etapa 1 (boot sector, 512 B)..."
	$(ASM) -f bin -o $(BIN1) $(SRC1)
	@echo "==> Ensamblando etapa 2 (contenido institucional, 2048 B)..."
	$(ASM) -f bin -o $(BIN2) $(SRC2)
	@echo "==> Construyendo imagen de disco $(IMG)..."
	cat $(BIN1) $(BIN2) > $(IMG)
	@echo "Listo: $(IMG)"

# Ejecuta la imagen en QEMU como disco de arranque crudo
run:
	$(QEMU) -drive format=raw,file=$(IMG)

# Elimina los binarios y la imagen generados
clean:
	rm -f $(BIN1) $(BIN2) $(IMG)
	@echo "Limpieza completada."

# -----------------------------------------------------------------------------
# verify: comprueba tamanos y la firma 0xAA55 del boot sector.
# Usa od (POSIX) para no depender de xxd.
# -----------------------------------------------------------------------------
verify: build
	@echo "=== Verificacion de la imagen ==="
	@echo "Tamano stage1 (debe ser 512):"
	@wc -c < $(BIN1)
	@echo "Tamano stage2 (debe ser 2048):"
	@wc -c < $(BIN2)
	@echo "Tamano imagen total (debe ser 2560):"
	@wc -c < $(IMG)
	@echo "Firma del boot sector en offset 0x1FE (debe ser 55 aa):"
	@od -A x -t x1 -j 0x1FE -N 2 $(IMG)
