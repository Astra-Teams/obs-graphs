"""Configuration module for the obs-graphs project."""

from .db_settings import DBSettings
from .nexus_settings import NexusSettings
from .obs_glx_settings import ObsGlxSettings
from .redis_settings import RedisSettings
from .starprobe_settings import StarprobeSettings
from .stl_conn_settings import StlConnSettings
from .workflow_settings import WorkflowSettings

# Singleton instances for direct access
obs_glx_settings = ObsGlxSettings()
stl_conn_settings = StlConnSettings()
nexus_settings = NexusSettings()
db_settings = DBSettings()
redis_settings = RedisSettings()
starprobe_settings = StarprobeSettings()
workflow_settings = WorkflowSettings()

__all__ = [
    # Classes
    "DBSettings",
    "NexusSettings",
    "ObsGlxSettings",
    "RedisSettings",
    "StarprobeSettings",
    "StlConnSettings",
    "WorkflowSettings",
    # Singleton instances
    "obs_glx_settings",
    "stl_conn_settings",
    "nexus_settings",
    "db_settings",
    "redis_settings",
    "starprobe_settings",
    "workflow_settings",
]
