# In aci_v2/mces_mvp/exceptions.py
# Date: June 3, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

from aci_v2.common_exceptions import (
    ACIError,
)


class MCESError(ACIError):
    """Base exception for MCES MVP module related errors."""

    pass


class MacroNotFoundError(MCESError):
    """Raised when a specific macro definition is not found."""

    pass


class DuplicateMacroNameError(MCESError):
    """Raised when attempting to add a macro with a name that already exists."""

    pass


class InvalidMacroDefinitionError(MCESError):
    """Raised if a macro definition is malformed or its steps are invalid for MVP."""

    pass


class InvalidMacroDefinitionError(MCESError):
    """Raised if a macro definition is malformed or its steps are invalid for MVP."""

    pass
