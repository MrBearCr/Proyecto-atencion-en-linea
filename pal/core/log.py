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

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"}

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
        try:
            print(self._format(level, message, caller_offset=3))
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
        self.log("SUCCESS", message)

def get_logger(component: Optional[str] = None) -> Logger:
    return Logger(component or "APP")
