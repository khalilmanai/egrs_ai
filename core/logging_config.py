import logging
import sys


def setup_logging(debug: bool = False, log_file: str | None = None):
    """Configure centralized logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )

    # Set third-party loggers to WARNING to reduce noise
    for logger_name in ("httpx", "httpcore", "PIL", "matplotlib", "asyncio"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not debug else logging.INFO)
