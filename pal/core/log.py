"""
Logging helper for PAL with standardized console prefixes.
Usage:
    from pal.core.log import get_logger
    logger = get_logger("STOCK")
    logger.info("Mensaje")
    logger.debug("Debug")
    logger.error("Error")
    logger.success("OK")
"""
import time
import threading
import inspect
from typing import Optional

# Niveles y umbrales
_LEVEL_ORDER = {"DEBUG": 10, "INFO": 20, "SUCCESS": 25, "WARNING": 30, "ERROR": 40}
_LEVELS = set(_LEVEL_ORDER.keys())

# Configuración global de niveles por componente
_default_level = "INFO"
_component_levels = {}
_log_callback = None


def set_log_callback(callback):
    """Establece una función callback para redirigir los logs (ej: a la UI)."""
    global _log_callback
    _log_callback = callback


def set_level(level: str):
    global _default_level
    level = (level or "INFO").upper()
    if level in _LEVELS:
        _default_level = level


def set_component_level(component: str, level: str):
    if not component:
        return
    lvl = (level or "INFO").upper()
    if lvl in _LEVELS:
        _component_levels[component.upper()] = lvl


def _should_emit(component: str, level: str) -> bool:
    comp = (component or "APP").upper()
    lvl = (level or "INFO").upper()
    if lvl not in _LEVELS:
        lvl = "INFO"
    min_level = _component_levels.get(comp, _default_level)
    return _LEVEL_ORDER[lvl] >= _LEVEL_ORDER[min_level]


class Logger:
    def __init__(self, component: str):
        self.component = component.upper() if component else "APP"

    def _format(self, level: str, message: str, caller_offset: int = 2) -> str:
        level = level.upper()
        if level not in _LEVELS:
            level = "INFO"
        try:
            frame_info = inspect.stack()[caller_offset]
            module = inspect.getmodule(frame_info.frame)
            mod_name = getattr(module, "__name__", "unknown")
            func_name = frame_info.function
            line_no = frame_info.lineno
        except Exception:
            mod_name, func_name, line_no = "unknown", "unknown", 0
        thread_name = threading.current_thread().name
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[PAL][{self.component}][{level}][{thread_name}][{mod_name}.{func_name}:{line_no}]"
        return f"{prefix} {message}"

    def log(self, level: str, message: str):
        # Filtrar por nivel efectivo
        if not _should_emit(self.component, level):
            return
        
        formatted_msg = self._format(level, message, caller_offset=3)
        
        # Redirigir al callback si existe (ej: para mostrar en UI)
        if _log_callback:
            try:
                # El callback suele ser app.log(message, level)
                _log_callback(message, level)
            except Exception:
                pass

        try:
            print(formatted_msg)
        except Exception:
            try:
                print(message)
            except Exception:
                pass

    def debug(self, message: str):
        self.log("DEBUG", message)

    def info(self, message: str):
        self.log("INFO", message)

    def warning(self, message: str):
        self.log("WARNING", message)

    def error(self, message: str):
        self.log("ERROR", message)

    def success(self, message: str):
        # Tratar SUCCESS entre INFO y WARNING
        self.log("SUCCESS", message)


def get_logger(component: Optional[str] = None) -> Logger:
    return Logger(component or "APP")
