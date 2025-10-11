"""Configuration module for the obs-graphs project."""

from .db_settings import DBSettings
from .obs_graphs_settings import ObsGraphsSettings
from .redis_settings import RedisSettings
from .research_api_settings import ResearchAPISettings
from .workflow_settings import WorkflowSettings

# Singleton instances for direct access
obs_graphs_settings = ObsGraphsSettings()
db_settings = DBSettings()
redis_settings = RedisSettings()
research_api_settings = ResearchAPISettings()
workflow_settings = WorkflowSettings()

__all__ = [
    # Classes
    "DBSettings",
    "ObsGraphsSettings",
    "RedisSettings",
    "ResearchAPISettings",
    "WorkflowSettings",
    # Singleton instances
    "obs_graphs_settings",
    "db_settings",
    "redis_settings",
    "research_api_settings",
    "workflow_settings",
]
