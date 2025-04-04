import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from colorama import init, Fore, Style

# Initialize colorama for Windows support
init()

class Colors:
    RESET = Style.RESET_ALL
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    PURPLE = Fore.MAGENTA
    CYAN = Fore.CYAN
    LBLUE = Fore.LIGHTBLUE_EX


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Colors.BLUE,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.PURPLE,
    }

    def format(self, record):
        # Add color to the level name
        color = self.COLORS.get(record.levelname, Colors.RESET)
        record.msg = f"{color}{record.msg}{Colors.RESET}"
        return super().format(record)

class CSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Convert UTC time to CST
        utc_time = datetime.fromtimestamp(record.created, tz=timezone.utc)
        cst_time = utc_time.astimezone(ZoneInfo("US/Central"))
        if datefmt:
            return cst_time.strftime(datefmt)
        else:
            return cst_time.isoformat()

class Logger:
    def __init__(self, logger_name, log_file='app.log', level=logging.DEBUG, max_bytes=5 * 1024 * 1024, backup_count=3):
        """
        Initialize the logger.

        :param logger_name: Name of the logger.
        :param log_file: Log file path.
        :param level: Logging level (default: DEBUG).
        :param max_bytes: Max size of the log file before rotation (default: 5MB).
        :param backup_count: Number of backup files to keep (default: 3).
        """
        # Create the logger
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(level)
        colors=Colors()

        # Check if handlers are already attached
        if not self.logger.handlers:
            # Create a file handler with rotation
            file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
            file_formatter = CSTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(file_formatter)

            # Create a console handler
            console_handler = logging.StreamHandler()
            console_formatter = CSTFormatter(f'{colors.RESET}%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            console_handler.setFormatter(console_formatter)

            # Add handlers to the logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        """
        Return the configured logger.

        :return: Configured logger instance.
        """
        return self.logger