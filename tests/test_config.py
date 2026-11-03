"""Tests for core configuration."""

import os
import unittest
from unittest.mock import patch

from core.config import Config, load_config


class TestConfig(unittest.TestCase):
    """Unit tests for configuration loading."""

    def test_config_is_frozen(self) -> None:
        """Config instances should be immutable."""
        config = Config(env="test", log_level="DEBUG")
        self.assertEqual(config.env, "test")
        self.assertEqual(config.log_level, "DEBUG")

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_defaults(self) -> None:
        """load_config should return sensible defaults when env vars are unset."""
        config = load_config()
        self.assertEqual(config.env, "development")
        self.assertEqual(config.log_level, "INFO")


if __name__ == "__main__":
    unittest.main()
