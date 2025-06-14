import logging
import threading
from contextlib import contextmanager

_indent_storage = threading.local()

def _get_level():
    return getattr(_indent_storage, 'level', 0)

def increase_indent():
    _indent_storage.level = _get_level() + 1

def decrease_indent():
    _indent_storage.level = max(0, _get_level() - 1)

def get_indent_str():
    return "    " * _get_level()

class ColoredIndentedFormatter(logging.Formatter):
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"
    
    BASE_FORMAT = "%(message)s"

    FORMATS = {
        logging.DEBUG: GREY + BASE_FORMAT + RESET,
        logging.INFO: GREEN + BASE_FORMAT + RESET,
        logging.WARNING: YELLOW + BASE_FORMAT + RESET,
        logging.ERROR: RED + BASE_FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + BASE_FORMAT + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.BASE_FORMAT)
        formatter = logging.Formatter(log_fmt)
        indent_str = get_indent_str()
        original_message = formatter.format(record)
        indented_message = "\n".join(
            f"{indent_str}{line}" for line in original_message.splitlines()
        )
        return indented_message

def setup_custom_logging(logger_name="AppLogger", level=logging.INFO) -> logging.Logger:
    logger_instance = logging.getLogger(logger_name)
    logger_instance.setLevel(level)
    
    if not any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, ColoredIndentedFormatter) for h in logger_instance.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(ColoredIndentedFormatter())
        logger_instance.addHandler(handler)
        logger_instance.propagate = False
    return logger_instance

@contextmanager
def log_node_ctx(logger_instance: logging.Logger, node_name: str):
    logger_instance.info(f"-> Entering Node: {node_name}")
    increase_indent()
    try:
        yield
    finally:
        decrease_indent()
        logger_instance.info(f"<- Exiting Node: {node_name}")