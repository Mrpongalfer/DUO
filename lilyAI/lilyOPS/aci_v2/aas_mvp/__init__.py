"""
AAS v2.0 MVP: Architect Authentication & Authorization Service
Exports AASServiceMVP and key exceptions.
"""

from .exceptions import AASError, AuthenticationFailedError, NotAuthorizedError
from .service import AASServiceMVP

__all__ = [
    "AASServiceMVP",
    "AASError",
    "AuthenticationFailedError",
    "NotAuthorizedError",
]
