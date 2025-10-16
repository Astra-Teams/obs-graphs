"""Configuration module for the obs-graphs project."""

from .db_settings import DBSettings
from .github_settings import GitHubSettings
from .nexus_settings import NexusSettings
from .obs_glx_settings import ObsGlxSettings
from .redis_settings import RedisSettings
from .starprobe_settings import StarprobeSettings
from .workflow_settings import WorkflowSettings

# Singleton instances for direct access
obs_glx_settings = ObsGlxSettings()
nexus_settings = NexusSettings()
github_settings = GitHubSettings()
db_settings = DBSettings()
redis_settings = RedisSettings()
starprobe_settings = StarprobeSettings()
workflow_settings = WorkflowSettings()

__all__ = [
    # Classes
    "DBSettings",
    "GitHubSettings",
    "ObsGlxSettings",
    "RedisSettings",
    "StarprobeSettings",
    "NexusSettings",
    "WorkflowSettings",
    # Singleton instances
    "obs_glx_settings",
    "nexus_settings",
    "github_settings",
    "db_settings",
    "redis_settings",
    "starprobe_settings",
    "workflow_settings",
]
