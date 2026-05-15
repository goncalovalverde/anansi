"""Structured JSON logging configuration with correlation IDs and secret masking."""

import logging
import logging.config
import sys
import uuid
import re
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar

# Context variable to store correlation ID per request
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to the log record."""
        record.correlation_id = correlation_id_var.get() or str(uuid.uuid4())
        return True


class SafeJsonFormatter(jsonlogger.JsonFormatter):
    """Safe JSON formatter that handles format string mismatches and masks secrets."""
    
    # Patterns to match and mask secrets in formatted output
    SECRET_PATTERNS = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'password=***'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'api_key=***'),
        (r'(?:oauth_|pat_)?token["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'token=***'),
        (r'token[_-]?secret["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'token_secret=***'),
        (r'jira[_-]?pat[_-]?token["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'jira_pat_token=***'),
        (r'consumer[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'consumer_key=***'),
        (r'key[_-]?cert[_-]?file["\']?\s*[:=]\s*["\']?([^"\'\\s,}]+)', 'key_cert_file=***'),
    ]

    def format(self, record: logging.LogRecord) -> str:
        """Format log record safely with secret masking."""
        try:
            # Ensure args are tuple
            if record.args and isinstance(record.args, dict):
                record.msg = record.getMessage()
                record.args = ()
            msg = super().format(record)
            
            # Apply secret masking to the formatted output
            for pattern, replacement in self.SECRET_PATTERNS:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            
            return msg
        except (TypeError, ValueError):
            # Fall back to basic formatting if JSON formatting fails
            msg = super().format(record)
            # Still apply secret masking even in fallback
            for pattern, replacement in self.SECRET_PATTERNS:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            return msg


def setup_logging() -> None:
    """Configure structured JSON logging."""
    # Configure specific loggers to avoid format string issues
    # These loggers may have format strings that don't play well with JSON formatting
    for logger_name in ["httpx", "httpcore", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Remove existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stream handler with safe JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    
    # Use safe JSON formatter
    formatter = SafeJsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(correlation_id)s %(message)s",
        timestamp=True,
    )
    handler.setFormatter(formatter)
    
    # Add correlation ID filter
    handler.addFilter(CorrelationIdFilter())
    
    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("anansi").setLevel(logging.INFO)


def get_or_create_correlation_id() -> str:
    """Get existing correlation ID or create a new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(cid)
