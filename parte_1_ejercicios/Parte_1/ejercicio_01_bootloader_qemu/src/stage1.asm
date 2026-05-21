; =============================================================================
; stage1.asm - Etapa 1 del bootloader (Boot Sector, 512 bytes)
; Evaluacion Integradora 1 - INFB6074 - Infraestructura para C. de Datos
; Universidad Tecnologica Metropolitana (UTEM)
; Autores: Ignacio Ramirez, Cristian Vergara y Francisco Provoste
;
; PROPOSITO DE ESTA ETAPA:
; El sector de arranque solo dispone de 512 bytes (510 utiles + 2 de firma).
; Ese espacio es insuficiente para una pantalla institucional completa con
; banner ASCII art y texto explicativo. Por eso este sector NO dibuja nada:
; su unica responsabilidad es leer la ETAPA 2 desde el disco a memoria y
; saltar a ella. Este es exactamente el patron de arranque en dos etapas que
; usan GRUB, el bootloader de Linux y Windows: stage1 minimo -> stage2 rico.
; =============================================================================

BITS 16                 ; Modo real x86 (16 bits)
ORG  0x7C00             ; El BIOS carga este sector en 0x7C00

STAGE2_SEG   equ 0x0000 ; Segmento donde cargaremos la etapa 2
STAGE2_OFF   equ 0x7E00 ; Offset destino: justo despues de este sector
STAGE2_SECTS equ 4      ; Cuantos sectores de 512 B leer para la etapa 2

start:
    ; -------------------------------------------------------------------------
    ; Inicializacion de segmentos y pila. La direccion fisica en modo real
    ; es segmento*16 + offset; ponemos los segmentos de datos a 0.
    ; -------------------------------------------------------------------------
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00      ; Pila crece hacia abajo desde justo bajo el codigo
    sti

    mov [boot_drive], dl ; El BIOS deja en DL el numero de la unidad de arranque

    ; -------------------------------------------------------------------------
    ; Leer la etapa 2 desde el disco usando el servicio de disco del BIOS
    ; (int 0x13, funcion 0x02 = leer sectores en modo CHS).
    ;   AH=0x02  AL=numero de sectores  CH=cilindro  CL=sector inicial
    ;   DH=cabeza  DL=unidad  ES:BX=buffer destino
    ; La etapa 2 esta inmediatamente despues del boot sector, es decir en
    ; el sector logico 2 (CHS: cilindro 0, cabeza 0, sector 2).
    ; -------------------------------------------------------------------------
    mov ah, 0x02            ; Funcion: leer sectores
    mov al, STAGE2_SECTS    ; Cantidad de sectores a leer
    mov ch, 0x00            ; Cilindro 0
    mov dh, 0x00            ; Cabeza 0
    mov cl, 0x02            ; Sector 2 (el 1 es este boot sector)
    mov dl, [boot_drive]    ; Misma unidad desde la que arrancamos
    mov bx, STAGE2_OFF      ; ES:BX -> 0x0000:0x7E00 (destino en memoria)
    int 0x13                ; Llamada al servicio de disco del BIOS
    jc  disk_error          ; CF=1 indica error de lectura

    ; -------------------------------------------------------------------------
    ; Salto a la etapa 2 ya cargada en memoria. A partir de aqui el control
    ; lo tiene el codigo de stage2.
    ; -------------------------------------------------------------------------
    jmp STAGE2_SEG:STAGE2_OFF

; -----------------------------------------------------------------------------
; Manejo de error de disco: imprime una letra y detiene la CPU.
; Se usa int 0x10/0x0E (teletype) porque aqui aun no montamos el framebuffer.
; -----------------------------------------------------------------------------
disk_error:
    mov ah, 0x0E
    mov al, 'E'             ; 'E' de Error de lectura de disco
    int 0x10
.hang:
    cli
    hlt
    jmp .hang

boot_drive db 0             ; Almacena el numero de unidad de arranque

; =============================================================================
; RELLENO Y FIRMA DE ARRANQUE
; El sector debe medir exactamente 512 bytes y terminar con 0xAA55, o el
; BIOS no lo reconocera como dispositivo de arranque valido.
; =============================================================================
times 510-($-$$) db 0       ; Relleno con ceros hasta el byte 510
dw 0xAA55                   ; Firma magica (0x55 en 0x1FE, 0xAA en 0x1FF)
