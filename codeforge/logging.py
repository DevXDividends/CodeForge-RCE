import logging


def configure_logging(
    level: int = logging.INFO,
):
    logging.basicConfig(
        level=level,
        format="[CodeForge] %(levelname)s: %(message)s",
    )