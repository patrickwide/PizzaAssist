import logging
import logging.handlers
import os

def setup_logger(
    logger_name: str = None,
    log_file: str = "app.log",
    log_dir: str = "logs",
    level=logging.DEBUG,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
    console: bool = True,
) -> logging.Logger:
    """
    Setup and return a logger with RotatingFileHandler.

    Args:
        logger_name: Name of the logger (usually __name__)
        log_file: Filename for the log file
        log_dir: Directory where the log files are saved
        level: Logging level (DEBUG, INFO, etc.)
        max_bytes: Max size in bytes before rotating
        backup_count: Number of backup files to keep
        console: If True, logs also print to console

    Returns:
        Configured logger instance
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Avoid adding multiple handlers if already added
    if not logger.handlers:
        log_path = os.path.join(log_dir, log_file)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    # Avoid log propagation to root logger
    logger.propagate = False

    return logger
