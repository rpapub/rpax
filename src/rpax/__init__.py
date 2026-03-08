"""rpax - Code-first CLI tool for UiPath project analysis.

rpax parses UiPath Process and Library projects into JSON call graphs, arguments, 
and diagrams for documentation, validation, and CI impact analysis.
"""

__version__ = "0.0.6"
__author__ = "rpapub"
__email__ = "contact@rpapub.dev"
__description__ = "Code-first CLI tool for UiPath project analysis"

from rpax.config import RpaxConfig
import rpax.utils.logging_setup  # registers TRACE level on first import  # noqa: F401

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "RpaxConfig",
]
