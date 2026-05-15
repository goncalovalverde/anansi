"""Tests for CORS header configuration.

Verifies that CORS middleware is correctly configured with hardened settings
per SECURITY-001 requirements.
"""


class TestCORSConfiguration:
    """Tests for CORS configuration validation."""

    def test_cors_config_module_exports_correct_origins(self):
        """CORS config module returns the correct allowed origins."""
        from backend import cors_config

        origins = cors_config.get_cors_origins()
        assert isinstance(origins, list)
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_cors_config_module_exports_correct_methods(self):
        """CORS config module restricts allowed methods appropriately."""
        from backend import cors_config

        config = cors_config.get_cors_config()
        assert "allow_methods" in config
        allowed_methods = config["allow_methods"]

        # Should only have the restricted set
        expected_methods = {"GET", "POST", "PUT", "DELETE", "OPTIONS"}
        assert set(allowed_methods) == expected_methods

        # Should NOT have "*" (wildcard)
        assert "*" not in allowed_methods

    def test_cors_config_module_restricts_headers(self):
        """CORS config module restricts allowed headers to essentials."""
        from backend import cors_config

        config = cors_config.get_cors_config()
        assert "allow_headers" in config
        allowed_headers = config["allow_headers"]

        # Should only include Content-Type and Authorization
        assert "Content-Type" in allowed_headers or "content-type" in [h.lower() for h in allowed_headers]
        assert "Authorization" in allowed_headers or "authorization" in [h.lower() for h in allowed_headers]

        # Should NOT have "*" (wildcard)
        assert "*" not in allowed_headers

    def test_cors_config_module_sets_max_age(self):
        """CORS config includes max_age for preflight caching."""
        from backend import cors_config

        config = cors_config.get_cors_config()
        assert "max_age" in config
        assert config["max_age"] == 600  # 10 minutes

    def test_cors_config_module_allows_credentials(self):
        """CORS config allows credentials when needed."""
        from backend import cors_config

        config = cors_config.get_cors_config()
        assert "allow_credentials" in config
        assert config["allow_credentials"] is True

    def test_cors_environment_variable_override(self, monkeypatch):
        """CORS origins can be overridden via environment variable."""
        from backend import cors_config

        # Mock the environment variable
        monkeypatch.setenv("ANANSI_CORS_ORIGINS", "https://example.com,https://staging.example.com")

        # Need to reload the module to pick up the new env var
        import importlib

        importlib.reload(cors_config)

        origins = cors_config.get_cors_origins()
        assert "https://example.com" in origins
        assert "https://staging.example.com" in origins
