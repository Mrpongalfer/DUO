"""
MCES v2.0 MVP: Macro & Command Execution Service
Exports MCESServiceMVP and key exceptions.
"""
from .exceptions import (DuplicateMacroNameError, InvalidMacroDefinitionError,
                         MacroNotFoundError, MCESError)
from .service import MCESServiceMVP

__all__ = [
    "MCESServiceMVP",
    "MCESError",
    "MacroNotFoundError",
    "DuplicateMacroNameError",
    "InvalidMacroDefinitionError",
]
    "MCESError",
    "MacroNotFoundError",
    "DuplicateMacroNameError",
    "InvalidMacroDefinitionError",
]
