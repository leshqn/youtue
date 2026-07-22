"""The company's departments, each behind the common Agent interface."""

from .analytics import AnalyticsAgent, AnalyticsReport
from .base import Agent, AgentContext
from .creative import CreativeAgent
from .discovery import DiscoveryAgent
from .distribution import DistributionAgent
from .hr import HRAgent, HRReport
from .ops import OpsAgent, OpsReport
from .production import ProductionAgent
from .qa import QAAgent
from .strategy import StrategyAgent, StrategyReport

__all__ = [
    "Agent",
    "AgentContext",
    "DiscoveryAgent",
    "CreativeAgent",
    "ProductionAgent",
    "QAAgent",
    "DistributionAgent",
    "AnalyticsAgent",
    "AnalyticsReport",
    "OpsAgent",
    "OpsReport",
    "HRAgent",
    "HRReport",
    "StrategyAgent",
    "StrategyReport",
]
