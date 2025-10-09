"""Application configuration for the obs-graphs project."""

# Re-export the main Settings class from the config module
from src.config import ObsGraphsSettings

# Alias for backward compatibility
Settings = ObsGraphsSettings

# Singleton instance for easy access across the application
settings = ObsGraphsSettings()


def get_settings() -> ObsGraphsSettings:
    """Return the application settings singleton."""
    return settings
