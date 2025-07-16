"""
Logging configuration for the Core Processor
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    output: str = "stdout",
    file_path: Optional[str] = None
) -> structlog.stdlib.BoundLogger:
    """
    Setup structured logging for the application
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format type (json, console)
        output: Output destination (stdout, stderr, file)
        file_path: Path to log file (if output is file)
    
    Returns:
        Configured logger instance
    """
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if format_type == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout if output == "stdout" else sys.stderr,
        level=getattr(logging, level.upper()),
    )
    
    # Configure file logging if specified
    if output == "file" and file_path:
        log_file = Path(file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(getattr(logging, level.upper()))
        
        # Add file handler to root logger
        logging.getLogger().addHandler(file_handler)
    
    # Create and return logger
    logger = structlog.get_logger("core-processor")
    
    # Log initial configuration
    logger.info(
        "Logging configured",
        level=level,
        format=format_type,
        output=output,
        file_path=file_path
    )
    
    return logger


def get_logger(name: str = "core-processor") -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes"""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class"""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


def log_function_call(func):
    """Decorator to log function calls with parameters and results"""
    def wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        
        # Log function call
        logger.info(
            "Function called",
            function=func.__name__,
            args=args,
            kwargs=kwargs
        )
        
        try:
            result = func(*args, **kwargs)
            logger.info(
                "Function completed successfully",
                function=func.__name__,
                result_type=type(result).__name__
            )
            return result
        except Exception as e:
            logger.error(
                "Function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls with parameters and results"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(f"{func.__module__}.{func.__name__}")
        
        # Log function call
        logger.info(
            "Async function called",
            function=func.__name__,
            args=args,
            kwargs=kwargs
        )
        
        try:
            result = await func(*args, **kwargs)
            logger.info(
                "Async function completed successfully",
                function=func.__name__,
                result_type=type(result).__name__
            )
            return result
        except Exception as e:
            logger.error(
                "Async function failed",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    return wrapper 