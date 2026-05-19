import platform
import psutil
import subprocess
import numpy as np
import pandas as pd
import matplotlib
from pathlib import Path


def get_processor_info():
    """Obtiene nombre comercial del procesador en Mac / Windows / Linux."""
    sistema = platform.system()
    try:
        if sistema == "Darwin":
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True, text=True
            )
            return result.stdout.strip()
        elif sistema == "Windows":
            # `wmic` está deprecado en W11 pero todavía funciona; alternativa: PowerShell.
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'name'],
                capture_output=True, text=True
            )
            lines = [l.strip() for l in result.stdout.split('\n') if l.strip()]
            if len(lines) > 1:
                return lines[1]
        elif sistema == "Linux":
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if 'model name' in line:
                        return line.split(':')[1].strip()
    except Exception:
        pass
    return platform.processor()


def get_so_detallado():
    """Versión amigable del SO."""
    sistema = platform.system()
    try:
        if sistema == "Darwin":
            ver = platform.mac_ver()[0]
            return f"macOS {ver}"
        elif sistema == "Windows":
            return f"Windows {platform.release()} (build {platform.version()})"
        elif sistema == "Linux":
            return f"Linux {platform.release()}"
    except Exception:
        pass
    return f"{sistema} {platform.release()}"


def get_estructura_carpetas():
    """Detecta las subcarpetas reales del directorio actual (1 nivel)."""
    aqui = Path.cwd()
    subdirs = [d.name for d in aqui.iterdir() 
               if d.is_dir() and not d.name.startswith('.') 
               and d.name not in ('__pycache__', '.venv', 'node_modules')]
    return ", ".join(sorted(subdirs)) if subdirs else "(sin subcarpetas)"




def get_gpu_info():
    """Detecta GPU según el sistema operativo."""
    sistema = platform.system()
    try:
        if sistema == "Darwin":
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if 'Chipset Model' in line:
                    return line.split(':')[1].strip()
        elif sistema == "Windows":
            result = subprocess.run(
                ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                capture_output=True, text=True
            )
            lines = [l.strip() for l in result.stdout.split('\n') if l.strip()]
            if len(lines) > 1:
                return lines[1]
        elif sistema == "Linux":
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'VGA' in line or 'Display' in line:
                    return line.split(':')[-1].strip()
    except Exception:
        pass
    return "GPU no detectada"


disk = psutil.disk_usage('/')
freq = psutil.cpu_freq()

env_info = {
    "Sistema operativo": get_so_detallado(),
    "Procesador": get_processor_info(),
    "Núcleos físicos": psutil.cpu_count(logical=False),
    "Núcleos lógicos": psutil.cpu_count(logical=True),
    "Frecuencia CPU (MHz)": f"{freq.current:.0f}" if freq else "no detectada",
    "GPU": get_gpu_info(),
    "RAM total (GB)": round(psutil.virtual_memory().total / (1024**3), 2),
    "Almacenamiento total (GB)": round(disk.total / (1024**3), 2),
    "Almacenamiento disponible (GB)": round(disk.free / (1024**3), 2),
    "Estructura de carpetas": get_estructura_carpetas(),
    "Python": platform.python_version(),
    "NumPy": np.__version__,
    "Pandas": pd.__version__,
    "Matplotlib": matplotlib.__version__,
    "psutil": psutil.__version__,
    "Directorio de trabajo": Path.cwd().name,
}

# Ruta del archivo markdown general
md_path = Path(__file__).parent / "entorno_experimental.md"

md_lines = [
    "# Configuración del Entorno Experimental\n",
    "## Información del sistema\n",
    "| Componente | Detalle |",
    "|------------|---------|"
]

for k, v in env_info.items():
    md_lines.append(f"| {k} | {v} |")

with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"Archivo generado en: {md_path.resolve()}")