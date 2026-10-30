"""Logging configuration for the stadsdelen package."""

from __future__ import annotations

import logging

LOGGER_NAME = "stadsdelen"


def configure_logging(level: str = "WARNING") -> None:
    """Configure the ``stadsdelen`` logger without altering the root logger."""
    numeric = getattr(logging, level.upper(), None)
    if not isinstance(numeric, int):
        raise ValueError(f"Invalid log level: {level!r}")

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(numeric)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under ``stadsdelen``."""
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)
