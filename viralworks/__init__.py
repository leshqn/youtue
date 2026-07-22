"""VIRALWORKS — a self-growing AI short-form video company.

An assembly line of specialized AI department-agents that discover trends, refine
ideas into scripts and shot plans, produce a render-ready reel spec, gate it for
brand safety, "publish" it, measure real performance, and — crucially — learn
from the results to rewrite their own playbooks so next cycle beats this one.

Entry points:
    python -m viralworks            # run the whole company on stubs
    from viralworks import Orchestrator, load_config
"""

from .config import Config, load_config
from .orchestrator import CycleResult, Orchestrator

__all__ = ["Orchestrator", "CycleResult", "Config", "load_config"]
__version__ = "0.1.0"
