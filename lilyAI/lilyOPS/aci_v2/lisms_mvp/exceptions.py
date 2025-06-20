# In aci_v2/lisms_mvp/exceptions.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

from aci_v2.common_exceptions import (
    ACIError,
)


class LISMSError(ACIError):
    """Base exception for LISMS MVP module related errors."""

    pass


class InstantiationError(LISMSError):
    """Raised when instantiation of a Lily persona fails during the PKEIP sequence."""

    pass


class SessionNotActiveError(LISMSError):
    """Raised when an operation requiring an active Lily session is attempted without one."""

    pass


class LLMCommunicationError(LISMSError):
    """Raised for errors during communication with the LLM backend API."""

    pass


class LLMCommunicationError(LISMSError):
    """Raised for errors during communication with the LLM backend API."""

    pass
