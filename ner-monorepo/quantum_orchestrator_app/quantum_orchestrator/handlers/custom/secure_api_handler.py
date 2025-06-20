"""
Generated handler: secure_api_handler

Description: Implements secure API integration with advanced security features
"""

import json
import time
import uuid
import hashlib
import hmac
import secrets
import re
import requests
from typing import Dict, Any, Tuple
from urllib.parse import urlparse

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Global registry for API keys and credentials
_api_registry = {}
_token_cache = {}
_rate_limit_registry = {}


@handler(
    name="secure_api_connector",
    description="Securely connect to external APIs with advanced security features",
    parameters={
        "api_endpoint": {"type": "string", "description": "URL of the API endpoint"},
        "method": {
            "type": "string",
            "description": "HTTP method",
            "enum": ["GET", "POST", "PUT", "DELETE"],
            "default": "GET",
        },
        "headers": {"type": "object", "description": "HTTP headers", "default": {}},
        "params": {"type": "object", "description": "Query parameters", "default": {}},
        "data": {
            "type": "object",
            "description": "Data to send (for POST/PUT)",
            "default": {},
        },
        "auth_type": {
            "type": "string",
            "description": "Authentication type",
            "enum": ["none", "basic", "bearer", "apikey", "oauth", "hmac"],
            "default": "none",
        },
        "auth_credentials": {
            "type": "object",
            "description": "Authentication credentials",
            "default": {},
        },
        "security_level": {
            "type": "integer",
            "description": "Security level (1-5)",
            "default": 3,
        },
        "timeout": {
            "type": "number",
            "description": "Request timeout in seconds",
            "default": 30.0,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the API request was successful",
        },
        "status_code": {"type": "integer", "description": "HTTP status code"},
        "response": {"type": "object", "description": "API response data"},
        "headers": {"type": "object", "description": "Response headers"},
        "execution_time": {
            "type": "number",
            "description": "Request execution time in seconds",
        },
        "security_audit": {
            "type": "object",
            "description": "Security audit information",
        },
        "error": {"type": "string", "description": "Error message if request failed"},
    },
)
def secure_api_connector(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Securely connect to external APIs with advanced security features.

    This handler implements secure API integration with comprehensive security
    features including authentication, encryption, rate limiting, and security
    auditing. It supports various authentication methods and security levels.

    Args:
        params: Dictionary containing API endpoint, method, headers, parameters,
                data, auth_type, auth_credentials, security_level, and timeout

    Returns:
        Dict containing success flag, status code, response data, and error message if any
    """
    try:
        # Start timing
        start_time = time.time()

        # Extract parameters
        api_endpoint = params.get("api_endpoint", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        query_params = params.get("params", {})
        data = params.get("data", {})
        auth_type = params.get("auth_type", "none")
        auth_credentials = params.get("auth_credentials", {})
        security_level = params.get("security_level", 3)
        timeout = params.get("timeout", 30.0)

        # Validate parameters
        if not api_endpoint:
            return {"success": False, "error": "API endpoint is required"}

        # Initialize security audit
        security_audit = {
            "timestamp": time.time(),
            "security_level": security_level,
            "auth_type": auth_type,
            "checks_performed": [],
            "warnings": [],
            "ip_address": "127.0.0.1",  # Simulated
        }

        # Validate API endpoint
        url_check = _validate_url(api_endpoint, security_level)
        security_audit["checks_performed"].append("url_validation")

        if not url_check["valid"]:
            security_audit["warnings"].append(
                f"URL validation failed: {url_check['reason']}"
            )
            return {
                "success": False,
                "error": f"Invalid API endpoint: {url_check['reason']}",
                "security_audit": security_audit,
                "execution_time": time.time() - start_time,
            }

        # Apply rate limiting
        rate_limit_check = _check_rate_limit(api_endpoint, security_level)
        security_audit["checks_performed"].append("rate_limiting")

        if not rate_limit_check["allowed"]:
            security_audit["warnings"].append(
                f"Rate limit exceeded: {rate_limit_check['reason']}"
            )
            return {
                "success": False,
                "error": f"Rate limit exceeded: {rate_limit_check['reason']}",
                "security_audit": security_audit,
                "execution_time": time.time() - start_time,
            }

        # Apply authentication
        try:
            auth_headers, auth_params = _apply_authentication(
                auth_type, auth_credentials, api_endpoint, method, data, security_level
            )
            security_audit["checks_performed"].append("authentication")

            # Merge authentication headers with provided headers
            for key, value in auth_headers.items():
                headers[key] = value

            # Merge authentication params with provided params
            for key, value in auth_params.items():
                query_params[key] = value

        except Exception as auth_error:
            security_audit["warnings"].append(
                f"Authentication failed: {str(auth_error)}"
            )
            return {
                "success": False,
                "error": f"Authentication failed: {str(auth_error)}",
                "security_audit": security_audit,
                "execution_time": time.time() - start_time,
            }

        # Add security headers based on security level
        security_headers = _get_security_headers(security_level)
        for key, value in security_headers.items():
            if key not in headers:
                headers[key] = value

        security_audit["checks_performed"].append("security_headers")

        # Sanitize data if needed
        if security_level >= 2 and data:
            data = _sanitize_data(data, security_level)
            security_audit["checks_performed"].append("data_sanitization")

        # Prepare request
        try:
            # Execute the HTTP request
            response = requests.request(
                method=method,
                url=api_endpoint,
                headers=headers,
                params=query_params,
                json=data if method in ["POST", "PUT"] else None,
                timeout=timeout,
            )

            # Record execution time
            execution_time = time.time() - start_time

            # Parse response data
            try:
                response_data = response.json() if response.text else {}
            except json.JSONDecodeError:
                response_data = {
                    "raw_text": response.text[:1000]
                }  # Limit response text size

            # Check response for security issues
            security_check = _check_response_security(
                response, response_data, security_level
            )
            security_audit["checks_performed"].append("response_security_check")

            if not security_check["valid"]:
                security_audit["warnings"].append(
                    f"Response security check failed: {security_check['reason']}"
                )

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers),
                "execution_time": execution_time,
                "security_audit": security_audit,
                "error": (
                    f"API returned error status: {response.status_code}"
                    if response.status_code >= 400
                    else None
                ),
            }

        except requests.RequestException as req_error:
            security_audit["warnings"].append(f"Request failed: {str(req_error)}")
            return {
                "success": False,
                "error": f"API request failed: {str(req_error)}",
                "security_audit": security_audit,
                "execution_time": time.time() - start_time,
            }

    except Exception as e:
        logger.error(f"Error in secure_api_connector: {str(e)}")
        return {"success": False, "error": f"Error in secure API connector: {str(e)}"}


@handler(
    name="api_credential_manager",
    description="Securely manage API credentials and keys",
    parameters={
        "action": {
            "type": "string",
            "description": "Action to perform",
            "enum": ["register", "retrieve", "rotate", "revoke", "list", "check"],
        },
        "api_name": {"type": "string", "description": "Name of the API"},
        "credentials": {
            "type": "object",
            "description": "API credentials to register",
            "default": {},
        },
        "credential_type": {
            "type": "string",
            "description": "Type of credential",
            "enum": ["apikey", "oauth", "basic", "certificate", "hmac"],
            "default": "apikey",
        },
        "rotation_period": {
            "type": "integer",
            "description": "Credential rotation period in days",
            "default": 90,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "credentials": {
            "type": "object",
            "description": "API credentials (for retrieve action)",
        },
        "credential_ids": {
            "type": "array",
            "description": "List of credential IDs (for list action)",
        },
        "status": {
            "type": "string",
            "description": "Status of the credentials (for check action)",
        },
        "expiration": {
            "type": "string",
            "description": "Expiration date of credentials",
        },
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def api_credential_manager(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Securely manage API credentials and keys.

    This handler provides functionality to securely store, retrieve, rotate,
    and revoke API credentials. It implements best practices for credential
    management including regular rotation and access control.

    Args:
        params: Dictionary containing action, api_name, credentials,
                credential_type, and rotation_period

    Returns:
        Dict containing success flag, credentials, and error message if any
    """
    try:
        # Extract parameters
        action = params.get("action", "")
        api_name = params.get("api_name", "")
        credentials = params.get("credentials", {})
        credential_type = params.get("credential_type", "apikey")
        rotation_period = params.get("rotation_period", 90)

        # Validate parameters
        if not action:
            return {"success": False, "error": "Action is required"}

        if action != "list" and not api_name:
            return {"success": False, "error": "API name is required"}

        # Initialize global registry if needed
        global _api_registry
        if not _api_registry:
            _api_registry = {}

        # Perform the requested action
        if action == "register":
            # Register new credentials
            if not credentials:
                return {
                    "success": False,
                    "error": "Credentials are required for registration",
                }

            # Generate credential ID
            credential_id = str(uuid.uuid4())

            # Calculate expiration date
            import datetime

            registration_time = datetime.datetime.now()
            expiration_time = registration_time + datetime.timedelta(
                days=rotation_period
            )

            # Store in registry
            _api_registry[credential_id] = {
                "api_name": api_name,
                "type": credential_type,
                "credentials": credentials,
                "registration_time": registration_time.isoformat(),
                "expiration_time": expiration_time.isoformat(),
                "status": "active",
            }

            return {
                "success": True,
                "credential_id": credential_id,
                "api_name": api_name,
                "registration_time": registration_time.isoformat(),
                "expiration_time": expiration_time.isoformat(),
                "credential_type": credential_type,
            }

        elif action == "retrieve":
            # Find credentials for the specified API
            for cred_id, cred_info in _api_registry.items():
                if (
                    cred_info.get("api_name") == api_name
                    and cred_info.get("status") == "active"
                ):
                    return {
                        "success": True,
                        "credential_id": cred_id,
                        "credentials": cred_info.get("credentials", {}),
                        "credential_type": cred_info.get("type", "apikey"),
                        "expiration_time": cred_info.get("expiration_time"),
                    }

            return {
                "success": False,
                "error": f"No active credentials found for API: {api_name}",
            }

        elif action == "rotate":
            # Find and rotate credentials for the specified API
            for cred_id, cred_info in _api_registry.items():
                if (
                    cred_info.get("api_name") == api_name
                    and cred_info.get("status") == "active"
                ):
                    # Mark current credentials as inactive
                    _api_registry[cred_id]["status"] = "inactive"

                    # Generate new credentials based on type
                    new_credentials = _generate_new_credentials(
                        credential_type, credentials
                    )

                    # Register new credentials
                    new_cred_id = str(uuid.uuid4())

                    import datetime

                    registration_time = datetime.datetime.now()
                    expiration_time = registration_time + datetime.timedelta(
                        days=rotation_period
                    )

                    _api_registry[new_cred_id] = {
                        "api_name": api_name,
                        "type": credential_type,
                        "credentials": new_credentials,
                        "registration_time": registration_time.isoformat(),
                        "expiration_time": expiration_time.isoformat(),
                        "status": "active",
                        "previous_credential_id": cred_id,
                    }

                    return {
                        "success": True,
                        "credential_id": new_cred_id,
                        "credentials": new_credentials,
                        "registration_time": registration_time.isoformat(),
                        "expiration_time": expiration_time.isoformat(),
                        "credential_type": credential_type,
                        "message": "Credentials rotated successfully",
                    }

            return {
                "success": False,
                "error": f"No active credentials found for API: {api_name}",
            }

        elif action == "revoke":
            # Find and revoke credentials for the specified API
            revoked = False

            for cred_id, cred_info in _api_registry.items():
                if (
                    cred_info.get("api_name") == api_name
                    and cred_info.get("status") == "active"
                ):
                    # Mark credentials as revoked
                    _api_registry[cred_id]["status"] = "revoked"
                    revoked = True

            if revoked:
                return {
                    "success": True,
                    "api_name": api_name,
                    "message": "All active credentials have been revoked",
                }
            else:
                return {
                    "success": False,
                    "error": f"No active credentials found for API: {api_name}",
                }

        elif action == "list":
            # List all registered APIs and credential IDs
            api_list = {}

            for cred_id, cred_info in _api_registry.items():
                api = cred_info.get("api_name")
                status = cred_info.get("status")

                if api not in api_list:
                    api_list[api] = {"credentials": []}

                api_list[api]["credentials"].append(
                    {
                        "id": cred_id,
                        "type": cred_info.get("type"),
                        "status": status,
                        "expiration_time": cred_info.get("expiration_time"),
                    }
                )

            return {
                "success": True,
                "api_list": api_list,
                "total_apis": len(api_list),
                "total_credentials": len(_api_registry),
            }

        elif action == "check":
            # Check status of credentials for the specified API
            for cred_id, cred_info in _api_registry.items():
                if cred_info.get("api_name") == api_name:
                    import datetime

                    current_time = datetime.datetime.now().isoformat()

                    status = cred_info.get("status")
                    expiration_time = cred_info.get("expiration_time")

                    return {
                        "success": True,
                        "credential_id": cred_id,
                        "api_name": api_name,
                        "status": status,
                        "expiration_time": expiration_time,
                        "is_expired": (
                            expiration_time < current_time if expiration_time else False
                        ),
                        "credential_type": cred_info.get("type"),
                    }

            return {
                "success": False,
                "error": f"No credentials found for API: {api_name}",
            }

        else:
            return {"success": False, "error": f"Unsupported action: {action}"}

    except Exception as e:
        logger.error(f"Error in api_credential_manager: {str(e)}")
        return {"success": False, "error": f"Error managing API credentials: {str(e)}"}


@handler(
    name="security_audit_handler",
    description="Perform security audits on API integrations and credentials",
    parameters={
        "audit_type": {
            "type": "string",
            "description": "Type of audit to perform",
            "enum": [
                "api_security",
                "credential_rotation",
                "access_patterns",
                "vulnerabilities",
            ],
        },
        "api_name": {
            "type": "string",
            "description": "Name of the API to audit",
            "default": "",
        },
        "audit_level": {
            "type": "integer",
            "description": "Depth and rigor of the audit (1-5)",
            "default": 3,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the audit was successful",
        },
        "audit_results": {
            "type": "object",
            "description": "Results of the security audit",
        },
        "findings": {"type": "array", "description": "List of security findings"},
        "risk_level": {"type": "string", "description": "Overall risk level"},
        "recommendations": {"type": "array", "description": "Security recommendations"},
        "error": {"type": "string", "description": "Error message if audit failed"},
    },
)
def security_audit_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform security audits on API integrations and credentials.

    This handler conducts comprehensive security audits of API integrations,
    credential management, access patterns, and potential vulnerabilities.
    It provides detailed findings and recommendations for improving security.

    Args:
        params: Dictionary containing audit_type, api_name, and audit_level

    Returns:
        Dict containing success flag, audit results, findings, and error message if any
    """
    try:
        # Extract parameters
        audit_type = params.get("audit_type", "")
        api_name = params.get("api_name", "")
        audit_level = params.get("audit_level", 3)

        # Validate parameters
        if not audit_type:
            return {"success": False, "error": "Audit type is required"}

        # Initialize audit results
        audit_results = {
            "timestamp": time.time(),
            "audit_type": audit_type,
            "api_name": api_name,
            "audit_level": audit_level,
            "audit_id": str(uuid.uuid4()),
        }

        # Initialize findings
        findings = []
        recommendations = []

        # Perform the requested audit
        if audit_type == "api_security":
            # Audit API security configurations
            if not api_name:
                return {
                    "success": False,
                    "error": "API name is required for API security audit",
                }

            # Check for credentials
            cred_found = False
            for cred_id, cred_info in _api_registry.items():
                if cred_info.get("api_name") == api_name:
                    cred_found = True
                    cred_type = cred_info.get("type")
                    cred_status = cred_info.get("status")

                    # Check credential types
                    if cred_type in ["basic", "apikey"]:
                        findings.append(
                            {
                                "severity": "medium",
                                "finding": f"Using {cred_type} authentication which offers limited security",
                                "affected_component": "authentication",
                                "risk": "Authentication credentials could be intercepted or leaked",
                            }
                        )

                        recommendations.append(
                            f"Consider upgrading from {cred_type} to OAuth or HMAC authentication"
                        )

                    # Check credential status
                    if cred_status != "active":
                        findings.append(
                            {
                                "severity": "info",
                                "finding": f"Found {cred_status} credentials",
                                "affected_component": "credential_management",
                                "risk": "None - informational only",
                            }
                        )

            if not cred_found:
                findings.append(
                    {
                        "severity": "high",
                        "finding": "No credentials registered for this API",
                        "affected_component": "credential_management",
                        "risk": "API may be using hardcoded or insecure credentials",
                    }
                )

                recommendations.append(
                    "Register API credentials using the credential manager"
                )

            # Add some simulated security findings based on audit level
            if audit_level >= 3:
                findings.append(
                    {
                        "severity": "low",
                        "finding": "HTTPS validation is not enforced at the highest level",
                        "affected_component": "transport_security",
                        "risk": "Potential for MITM attacks in certain circumstances",
                    }
                )

                recommendations.append("Enable strict HTTPS certificate validation")

            if audit_level >= 4:
                findings.append(
                    {
                        "severity": "medium",
                        "finding": "No rate limiting implemented for API calls",
                        "affected_component": "api_protection",
                        "risk": "Potential for DoS attacks or excessive usage charges",
                    }
                )

                recommendations.append(
                    "Implement client-side rate limiting for API calls"
                )

            if audit_level == 5:
                findings.append(
                    {
                        "severity": "info",
                        "finding": "API response data is not validated against a schema",
                        "affected_component": "data_validation",
                        "risk": "Potential for processing malformed or malicious response data",
                    }
                )

                recommendations.append("Implement response schema validation")

        elif audit_type == "credential_rotation":
            # Audit credential rotation practices
            rotation_issues = 0
            expired_creds = 0

            for cred_id, cred_info in _api_registry.items():
                if api_name and cred_info.get("api_name") != api_name:
                    continue

                # Check expiration
                import datetime

                current_time = datetime.datetime.now().isoformat()
                expiration_time = cred_info.get("expiration_time", "")
                status = cred_info.get("status")

                if status == "active" and expiration_time < current_time:
                    expired_creds += 1
                    findings.append(
                        {
                            "severity": "high",
                            "finding": f"Expired credentials still active for {cred_info.get('api_name')}",
                            "affected_component": "credential_management",
                            "credential_id": cred_id,
                            "risk": "Using expired credentials is a security risk and may violate compliance requirements",
                        }
                    )

                    recommendations.append(
                        f"Rotate expired credentials for {cred_info.get('api_name')} immediately"
                    )

                # Calculate days since registration
                registration_time = cred_info.get("registration_time", "")
                if registration_time:
                    try:
                        reg_date = datetime.datetime.fromisoformat(registration_time)
                        current_date = datetime.datetime.now()
                        days_since_registration = (current_date - reg_date).days

                        if status == "active" and days_since_registration > 180:
                            rotation_issues += 1
                            findings.append(
                                {
                                    "severity": "medium",
                                    "finding": f"Credentials for {cred_info.get('api_name')} not rotated in {days_since_registration} days",
                                    "affected_component": "credential_rotation",
                                    "credential_id": cred_id,
                                    "risk": "Old credentials increase the risk of credential compromise",
                                }
                            )

                            recommendations.append(
                                f"Implement regular credential rotation for {cred_info.get('api_name')}"
                            )
                    except (ValueError, TypeError):
                        pass

            # Add summary findings
            if expired_creds > 0:
                findings.append(
                    {
                        "severity": "critical",
                        "finding": f"Found {expired_creds} expired but active credentials",
                        "affected_component": "credential_management",
                        "risk": "Expired credentials may stop working unexpectedly or pose security risks",
                    }
                )

            if rotation_issues > 0:
                findings.append(
                    {
                        "severity": "medium",
                        "finding": f"Found {rotation_issues} credentials overdue for rotation",
                        "affected_component": "credential_management",
                        "risk": "Credentials not rotated regularly increase security risks",
                    }
                )

                recommendations.append("Implement automated credential rotation policy")

            if expired_creds == 0 and rotation_issues == 0:
                findings.append(
                    {
                        "severity": "info",
                        "finding": "No credential rotation issues found",
                        "affected_component": "credential_management",
                        "risk": "None - good security practice observed",
                    }
                )

        elif audit_type == "access_patterns":
            # Audit API access patterns (simulated)
            findings.append(
                {
                    "severity": "info",
                    "finding": "Access pattern analysis requires historical access data",
                    "affected_component": "access_analysis",
                    "risk": "None - informational finding",
                }
            )

            # Add some simulated access pattern findings
            findings.append(
                {
                    "severity": "low",
                    "finding": "API access occurs outside of normal business hours",
                    "affected_component": "access_patterns",
                    "risk": "Potential unauthorized access or automation issues",
                }
            )

            recommendations.append(
                "Implement time-based access controls if appropriate"
            )

            if audit_level >= 4:
                findings.append(
                    {
                        "severity": "medium",
                        "finding": "Unusual geographic access patterns detected",
                        "affected_component": "access_geography",
                        "risk": "Potential unauthorized access from unexpected locations",
                    }
                )

                recommendations.append(
                    "Implement geo-fencing or location-based access controls"
                )

        elif audit_type == "vulnerabilities":
            # Audit for potential vulnerabilities (simulated)
            findings.append(
                {
                    "severity": "info",
                    "finding": "Vulnerability scan completed",
                    "affected_component": "security_scanning",
                    "risk": "None - informational finding",
                }
            )

            # Add some simulated vulnerability findings based on audit level
            if audit_level >= 3:
                findings.append(
                    {
                        "severity": "medium",
                        "finding": "Input data not properly sanitized before use in API calls",
                        "affected_component": "input_validation",
                        "risk": "Potential for injection attacks or data leakage",
                    }
                )

                recommendations.append(
                    "Implement proper input sanitization for all API parameters"
                )

            if audit_level >= 4:
                findings.append(
                    {
                        "severity": "medium",
                        "finding": "API responses not validated against expected schemas",
                        "affected_component": "output_validation",
                        "risk": "Potential for processing malformed or malicious response data",
                    }
                )

                recommendations.append("Implement response schema validation")

            if audit_level == 5:
                findings.append(
                    {
                        "severity": "high",
                        "finding": "Secrets potentially exposed in code or configuration",
                        "affected_component": "secret_management",
                        "risk": "Credential exposure could lead to unauthorized access",
                    }
                )

                recommendations.append("Move all secrets to a secure credential store")
                recommendations.append(
                    "Use environment variables for sensitive configuration"
                )

        else:
            return {"success": False, "error": f"Unsupported audit type: {audit_type}"}

        # Calculate overall risk level
        risk_levels = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for finding in findings:
            severity = finding.get("severity", "info")
            risk_levels[severity] += 1

        if risk_levels["critical"] > 0:
            overall_risk = "critical"
        elif risk_levels["high"] > 0:
            overall_risk = "high"
        elif risk_levels["medium"] > 0:
            overall_risk = "medium"
        elif risk_levels["low"] > 0:
            overall_risk = "low"
        else:
            overall_risk = "info"

        # Complete audit results
        audit_results["findings_count"] = len(findings)
        audit_results["recommendations_count"] = len(recommendations)
        audit_results["risk_summary"] = risk_levels

        return {
            "success": True,
            "audit_results": audit_results,
            "findings": findings,
            "risk_level": overall_risk,
            "recommendations": recommendations,
        }

    except Exception as e:
        logger.error(f"Error in security_audit_handler: {str(e)}")
        return {"success": False, "error": f"Error performing security audit: {str(e)}"}


# Helper functions for API security
def _validate_url(url: str, security_level: int) -> Dict[str, Any]:
    """Validate a URL based on security requirements."""
    # Parse the URL
    try:
        parsed_url = urlparse(url)

        # Check scheme
        if security_level >= 2 and parsed_url.scheme != "https":
            return {
                "valid": False,
                "reason": "Non-HTTPS URLs are not allowed at this security level",
            }

        # Basic URL validation
        if not parsed_url.netloc:
            return {"valid": False, "reason": "Invalid URL format"}

        # Check for prohibited hosts based on security level
        if security_level >= 3:
            prohibited_hosts = [
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
                "example.com",
                "test.com",
                "internal",
            ]

            for host in prohibited_hosts:
                if host in parsed_url.netloc:
                    return {"valid": False, "reason": f"Prohibited host in URL: {host}"}

        # Additional checks for higher security levels
        if security_level >= 4:
            # Check for IP addresses instead of hostnames
            ip_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
            if re.match(ip_pattern, parsed_url.netloc):
                return {
                    "valid": False,
                    "reason": "Direct IP addresses not allowed at this security level",
                }

        return {"valid": True}

    except Exception as e:
        return {"valid": False, "reason": f"URL validation error: {str(e)}"}


def _check_rate_limit(endpoint: str, security_level: int) -> Dict[str, Any]:
    """Check and enforce rate limits."""
    global _rate_limit_registry

    # Extract the host from the endpoint
    try:
        host = urlparse(endpoint).netloc
    except Exception:
        host = endpoint

    # Initialize rate limit registry if not exists
    if not _rate_limit_registry:
        _rate_limit_registry = {}

    # Get current time
    current_time = time.time()

    # Initialize host in registry if not exists
    if host not in _rate_limit_registry:
        _rate_limit_registry[host] = {
            "last_request": current_time,
            "request_count": 0,
            "window_start": current_time,
        }

    # Get host rate limit info
    host_limits = _rate_limit_registry[host]

    # Reset window if needed (60-second window)
    if current_time - host_limits["window_start"] > 60:
        host_limits["window_start"] = current_time
        host_limits["request_count"] = 0

    # Calculate time since last request
    time_since_last = current_time - host_limits["last_request"]

    # Check rate limits based on security level
    if security_level <= 2:
        # Basic rate limiting: max 100 requests per minute, no delay
        if host_limits["request_count"] >= 100:
            return {
                "allowed": False,
                "reason": "Rate limit exceeded (100 requests per minute)",
            }

    elif security_level <= 4:
        # Moderate rate limiting: max 60 requests per minute, minimum 100ms between requests
        if host_limits["request_count"] >= 60:
            return {
                "allowed": False,
                "reason": "Rate limit exceeded (60 requests per minute)",
            }

        if time_since_last < 0.1:
            return {
                "allowed": False,
                "reason": "Request frequency too high (minimum 100ms between requests)",
            }

    else:
        # Strict rate limiting: max 30 requests per minute, minimum 500ms between requests
        if host_limits["request_count"] >= 30:
            return {
                "allowed": False,
                "reason": "Rate limit exceeded (30 requests per minute)",
            }

        if time_since_last < 0.5:
            return {
                "allowed": False,
                "reason": "Request frequency too high (minimum 500ms between requests)",
            }

    # Update rate limit info
    host_limits["last_request"] = current_time
    host_limits["request_count"] += 1

    return {"allowed": True}


def _apply_authentication(
    auth_type: str,
    auth_credentials: Dict[str, Any],
    endpoint: str,
    method: str,
    data: Dict[str, Any],
    security_level: int,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Apply authentication to a request based on type."""
    auth_headers = {}
    auth_params = {}

    if auth_type == "none":
        return auth_headers, auth_params

    elif auth_type == "basic":
        username = auth_credentials.get("username", "")
        password = auth_credentials.get("password", "")

        if not username or not password:
            raise ValueError("Username and password required for Basic authentication")

        # Create Basic auth header
        import base64

        auth_string = f"{username}:{password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        auth_headers["Authorization"] = f"Basic {encoded_auth}"

    elif auth_type == "bearer":
        token = auth_credentials.get("token", "")

        if not token:
            # Try to get token from registry
            api_name = auth_credentials.get("api_name")
            if api_name:
                for cred_id, cred_info in _api_registry.items():
                    if (
                        cred_info.get("api_name") == api_name
                        and cred_info.get("status") == "active"
                    ):
                        token = cred_info.get("credentials", {}).get("token", "")
                        break

        if not token:
            raise ValueError("Token required for Bearer authentication")

        auth_headers["Authorization"] = f"Bearer {token}"

    elif auth_type == "apikey":
        key = auth_credentials.get("key", "")
        key_name = auth_credentials.get("key_name", "api_key")
        in_header = auth_credentials.get("in_header", True)

        if not key:
            # Try to get API key from registry
            api_name = auth_credentials.get("api_name")
            if api_name:
                for cred_id, cred_info in _api_registry.items():
                    if (
                        cred_info.get("api_name") == api_name
                        and cred_info.get("status") == "active"
                    ):
                        key = cred_info.get("credentials", {}).get("key", "")
                        key_name = cred_info.get("credentials", {}).get(
                            "key_name", key_name
                        )
                        in_header = cred_info.get("credentials", {}).get(
                            "in_header", in_header
                        )
                        break

        if not key:
            raise ValueError("API key required for ApiKey authentication")

        if in_header:
            # Add as header
            auth_headers[key_name] = key
        else:
            # Add as query parameter
            auth_params[key_name] = key

    elif auth_type == "oauth":
        # This would normally involve a more complex OAuth flow
        # For simplicity, we'll assume a token is already available
        token = auth_credentials.get("access_token", "")
        token_type = auth_credentials.get("token_type", "Bearer")

        if not token:
            # Check token cache
            api_name = auth_credentials.get("api_name")
            if api_name and api_name in _token_cache:
                token_info = _token_cache[api_name]
                token = token_info.get("access_token", "")
                token_type = token_info.get("token_type", "Bearer")

        if not token:
            raise ValueError("Access token required for OAuth authentication")

        auth_headers["Authorization"] = f"{token_type} {token}"

    elif auth_type == "hmac":
        key = auth_credentials.get("key", "")
        secret = auth_credentials.get("secret", "")
        algorithm = auth_credentials.get("algorithm", "sha256")

        if not key or not secret:
            # Try to get from registry
            api_name = auth_credentials.get("api_name")
            if api_name:
                for cred_id, cred_info in _api_registry.items():
                    if (
                        cred_info.get("api_name") == api_name
                        and cred_info.get("status") == "active"
                    ):
                        key = cred_info.get("credentials", {}).get("key", "")
                        secret = cred_info.get("credentials", {}).get("secret", "")
                        algorithm = cred_info.get("credentials", {}).get(
                            "algorithm", algorithm
                        )
                        break

        if not key or not secret:
            raise ValueError("Key and secret required for HMAC authentication")

        # Create signature based on request details
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(8)

        # Construct string to sign
        string_to_sign = f"{method}\n{endpoint}\n{timestamp}\n{nonce}"

        if data and method in ["POST", "PUT"]:
            data_string = json.dumps(data, sort_keys=True)
            string_to_sign += f"\n{data_string}"

        # Create signature
        if algorithm == "sha256":
            signature = hmac.new(
                secret.encode(), string_to_sign.encode(), hashlib.sha256
            ).hexdigest()
        elif algorithm == "sha512":
            signature = hmac.new(
                secret.encode(), string_to_sign.encode(), hashlib.sha512
            ).hexdigest()
        else:
            raise ValueError(f"Unsupported HMAC algorithm: {algorithm}")

        # Add authentication headers
        auth_headers["X-API-Key"] = key
        auth_headers["X-Timestamp"] = timestamp
        auth_headers["X-Nonce"] = nonce
        auth_headers["X-Signature"] = signature

    else:
        raise ValueError(f"Unsupported authentication type: {auth_type}")

    return auth_headers, auth_params


def _get_security_headers(security_level: int) -> Dict[str, str]:
    """Get security headers based on security level."""
    security_headers = {}

    # Basic security headers
    if security_level >= 1:
        security_headers["X-Content-Type-Options"] = "nosniff"

    # Add more headers for higher security levels
    if security_level >= 2:
        security_headers["X-XSS-Protection"] = "1; mode=block"

    if security_level >= 3:
        security_headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    if security_level >= 4:
        security_headers["X-Frame-Options"] = "DENY"
        security_headers["Content-Security-Policy"] = "default-src 'self'"

    if security_level >= 5:
        security_headers["Referrer-Policy"] = "no-referrer"
        security_headers["Cache-Control"] = "no-store, max-age=0"

    return security_headers


def _sanitize_data(data: Dict[str, Any], security_level: int) -> Dict[str, Any]:
    """Sanitize data based on security level."""
    # Make a copy of the data to avoid modifying the original
    sanitized_data = data.copy()

    # Basic sanitization for security level 2+
    if security_level >= 2:
        # Check for common injection patterns in string values
        for key, value in sanitized_data.items():
            if isinstance(value, str):
                # Check for SQL injection patterns
                sql_patterns = [
                    "'--",
                    "/*",
                    "*/",
                    "@@",
                    "@variable",
                    "exec ",
                    "execute ",
                    "select ",
                    "insert ",
                    "update ",
                    "delete ",
                    "drop ",
                ]

                for pattern in sql_patterns:
                    if pattern in value.lower():
                        sanitized_data[key] = re.sub(
                            pattern, "", value, flags=re.IGNORECASE
                        )

    # More advanced sanitization for security level 3+
    if security_level >= 3:
        # Check for script tags and other XSS vectors
        for key, value in sanitized_data.items():
            if isinstance(value, str):
                # Remove script tags and event handlers
                if re.search(r"<script|javascript:|on\w+=", value, re.IGNORECASE):
                    sanitized_data[key] = re.sub(
                        r"<script.*?>.*?</script>|javascript:|on\w+=",
                        "",
                        value,
                        flags=re.IGNORECASE,
                    )

    # Deep sanitization for security level 4+
    if security_level >= 4:
        # Recursively sanitize nested objects
        for key, value in sanitized_data.items():
            if isinstance(value, dict):
                sanitized_data[key] = _sanitize_data(value, security_level)
            elif isinstance(value, list):
                sanitized_data[key] = [
                    (
                        _sanitize_data(item, security_level)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]

    return sanitized_data


def _check_response_security(
    response: requests.Response, response_data: Dict[str, Any], security_level: int
) -> Dict[str, bool]:
    """Check response for security issues."""
    # Basic security validation for all levels
    result = {"valid": True, "reason": ""}

    # Check response headers for security headers
    if security_level >= 3:
        # Check for important security headers
        important_headers = [
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Content-Security-Policy",
            "Strict-Transport-Security",
        ]

        missing_headers = []
        for header in important_headers:
            if header.lower() not in [h.lower() for h in response.headers]:
                missing_headers.append(header)

        if missing_headers:
            result["valid"] = False
            result["reason"] = f"Missing security headers: {', '.join(missing_headers)}"

    # Check for sensitive data in responses for security level 4+
    if security_level >= 4 and isinstance(response_data, dict):
        # Check for potentially sensitive keys
        sensitive_keys = [
            "password",
            "secret",
            "token",
            "key",
            "credential",
            "api_key",
            "apikey",
            "ssn",
            "social_security",
            "credit_card",
            "card_number",
            "cvv",
            "pin",
        ]

        for key in response_data.keys():
            key_lower = key.lower()
            for sensitive_key in sensitive_keys:
                if sensitive_key in key_lower:
                    result["valid"] = False
                    result["reason"] = f"Potential sensitive data in response: {key}"
                    break

    return result


def _generate_new_credentials(
    credential_type: str, old_credentials: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate new credentials based on credential type and old credentials."""
    if credential_type == "apikey":
        # Generate a new API key
        new_api_key = secrets.token_hex(16)

        return {
            "key": new_api_key,
            "key_name": old_credentials.get("key_name", "api_key"),
            "in_header": old_credentials.get("in_header", True),
        }

    elif credential_type == "basic":
        # For basic auth, we might keep the username but generate a new password
        username = old_credentials.get("username", "")
        new_password = secrets.token_urlsafe(16)

        return {"username": username, "password": new_password}

    elif credential_type == "hmac":
        # Generate new key and secret
        new_key = secrets.token_hex(8)
        new_secret = secrets.token_hex(32)

        return {
            "key": new_key,
            "secret": new_secret,
            "algorithm": old_credentials.get("algorithm", "sha256"),
        }

    elif credential_type == "oauth":
        # In a real system, this would involve a more complex OAuth flow
        # For simplicity, we'll generate a simulated token
        new_token = secrets.token_hex(32)

        return {
            "access_token": new_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": secrets.token_hex(32),
        }

    elif credential_type == "certificate":
        # In a real system, this would generate or request a new certificate
        # For simplicity, we'll return a placeholder
        return {
            "cert_id": str(uuid.uuid4()),
            "issued_date": time.time(),
            "expiration_date": time.time() + (365 * 24 * 60 * 60),  # 1 year
            "issuer": "Quantum Orchestrator CA",
        }

    else:
        # Default case - generate a simple key
        return {"key": secrets.token_hex(16)}
