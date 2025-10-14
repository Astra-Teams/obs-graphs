"""Configuration module for the obs-graphs project."""

from .db_settings import DBSettings
from .gateway_settings import GatewaySettings
from .obs_graphs_settings import ObsGraphsSettings
from .redis_settings import RedisSettings
from .research_api_settings import ResearchAPISettings
from .stl_conn_settings import StlConnSettings
from .workflow_settings import WorkflowSettings

# Singleton instances for direct access
obs_graphs_settings = ObsGraphsSettings()
stl_conn_settings = StlConnSettings()
gateway_settings = GatewaySettings()
db_settings = DBSettings()
redis_settings = RedisSettings()
research_api_settings = ResearchAPISettings()
workflow_settings = WorkflowSettings()

__all__ = [
    # Classes
    "DBSettings",
    "ObsGraphsSettings",
    "StlConnSettings",
    "GatewaySettings",
    "RedisSettings",
    "ResearchAPISettings",
    "WorkflowSettings",
    # Singleton instances
    "obs_graphs_settings",
    "stl_conn_settings",
    "gateway_settings",
    "db_settings",
    "redis_settings",
    "research_api_settings",
    "workflow_settings",
]
