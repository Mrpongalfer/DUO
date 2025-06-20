# In aci_v2/aas_mvp/exceptions.py
# Date: June 3, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

from aci_v2.common_exceptions import ACIError


class AASError(ACIError):
    """Base exception for AAS MVP module related errors."""

    pass


class AuthenticationFailedError(AASError):  # Renamed for consistency
    """Raised when authentication fails (for future use)."""

    pass


class NotAuthorizedError(AASError):  # Renamed for consistency
    """Raised when an action is not authorized (for future use)."""

    pass
    pass
