import logging


def configure_logging(level: int = logging.INFO):
    fmt = '%(asctime)s %(levelname)-5s [%(name)s] %(message)s'
    logging.basicConfig(level=level, format=fmt)


configure_logging()
import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = None):
    level = getattr(logging, (log_level or os.getenv('LOG_LEVEL') or 'INFO').upper(), logging.INFO)

    # ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        log_dir = os.path.dirname(__file__)

    logger = logging.getLogger()
    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    fmt = logging.Formatter('%(asctime)s %(levelname)-7s [%(name)s] %(message)s')
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler with rotation
    fh_path = os.path.join(log_dir, 'app.log')
    fh = RotatingFileHandler(fh_path, maxBytes=5_000_000, backupCount=3)
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)


setup_logging()
