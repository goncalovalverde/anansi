"""CORS configuration for the Anansi backend.

This module manages Cross-Origin Resource Sharing (CORS) settings with a security-first approach.

Security Policy:
- Explicit origin allowlist instead of wildcards to prevent unauthorized access
- Only necessary HTTP methods are allowed
- Only needed headers are exposed to reduce information leakage
- Preflight requests are cached (max_age) to reduce cross-origin traffic
- Credentials are only allowed when needed by the frontend
"""

import os


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins from environment variables or use secure defaults.
    
    Environment variable: ANANSI_CORS_ORIGINS
    - Use comma-separated values for multiple origins (e.g., "http://localhost:3000,http://localhost:5173")
    - Default: ["http://localhost:3000", "http://localhost:5173"] for development
    
    Origins by environment:
    - Development: http://localhost:3000 (legacy Vue CLI), http://localhost:5173 (Vite)
    - Production: https://yourdomain.com (must be configured via env var)
    
    Returns:
        List of allowed CORS origins
    """
    origins_env = os.environ.get(
        "ANANSI_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    )
    # Parse comma-separated list and strip whitespace
    return [origin.strip() for origin in origins_env.split(",") if origin.strip()]


def get_cors_config() -> dict:
    """Get the complete CORS middleware configuration.
    
    Returns:
        Dictionary of CORS middleware options
    """
    return {
        "allow_origins": get_cors_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "max_age": 600,  # Cache preflight requests for 10 minutes
    }
