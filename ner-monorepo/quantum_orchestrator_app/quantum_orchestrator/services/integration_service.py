"""
Integration Service: Provides service discovery and integration capabilities.

This module implements active and passive service discovery mechanisms,
allowing the Quantum Orchestrator to automatically discover and integrate
with external services.
"""

import json
import time
import uuid
import re
import threading
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import requests

from quantum_orchestrator.utils.logging_utils import get_logger

# Initialize logger
logger = get_logger(__name__)

# Global registry for discovered services
_service_registry = {}
_discovery_lock = threading.Lock()
_discovery_in_progress = False
_last_discovery_time = 0

# Common API endpoints to probe during active discovery
COMMON_ENDPOINTS = [
    # Weather services
    "https://api.openweathermap.org/data/2.5/weather",
    "https://api.weatherapi.com/v1/current.json",
    "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/weatherdata",
    # Time services
    "https://worldtimeapi.org/api/ip",
    "https://timeapi.io/api/Time/current/zone",
    # Utility services
    "https://api.ipify.org",
    "https://api.thecatapi.com/v1/images/search",
    "https://api.publicapis.org/entries",
    "https://api.chucknorris.io/jokes/random",
    # General purpose APIs
    "https://jsonplaceholder.typicode.com/posts",
    "https://httpbin.org/get",
    "https://reqres.in/api/users",
    # Data services
    "https://data.cityofnewyork.us/api/views",
    "https://data.gov/api/3/action/package_search",
    # Mock Quantum Computing API
    "https://quantum-simulator.example.com/api/v1/simulation",
    # Mock Neural Network API
    "https://neural-engine.example.com/api/v1/infer",
]

# Service feature patterns for passive discovery
SERVICE_PATTERNS = {
    "weather": [
        r"temp(erature)?",
        r"forecast",
        r"humidity",
        r"precipitation",
        r"weather",
        r"climate",
        r"wind",
        r"cloud",
    ],
    "time": [
        r"time(zone)?",
        r"date",
        r"clock",
        r"utc",
        r"gmt",
        r"timestamp",
        r"epoch",
        r"calendar",
    ],
    "location": [
        r"geo",
        r"location",
        r"coordinate",
        r"latitude",
        r"longitude",
        r"city",
        r"country",
        r"address",
        r"map",
    ],
    "data": [
        r"data",
        r"dataset",
        r"statistic",
        r"analytics",
        r"metric",
        r"report",
        r"information",
        r"record",
    ],
    "image": [
        r"image",
        r"photo",
        r"picture",
        r"thumbnail",
        r"avatar",
        r"icon",
        r"graphic",
        r"visual",
    ],
    "user": [
        r"user",
        r"profile",
        r"account",
        r"auth",
        r"identity",
        r"login",
        r"register",
        r"member",
    ],
    "content": [
        r"content",
        r"article",
        r"post",
        r"message",
        r"comment",
        r"feed",
        r"blog",
        r"news",
    ],
    "calculation": [
        r"calc",
        r"compute",
        r"math",
        r"formula",
        r"equation",
        r"arithmetic",
        r"numeric",
        r"algorithm",
    ],
    "quantum": [
        r"quantum",
        r"qubit",
        r"superposition",
        r"entanglement",
        r"wave function",
        r"simulation",
        r"probability",
        r"interference",
    ],
    "neural": [
        r"neural",
        r"ai",
        r"ml",
        r"model",
        r"inference",
        r"prediction",
        r"training",
        r"learning",
        r"classification",
    ],
}


class ServiceInfo:
    """Information about a discovered service."""

    def __init__(
        self,
        service_id: str,
        name: str,
        url: str,
        description: str = "",
        service_type: str = "unknown",
        endpoints: Dict[str, Any] = None,
        auth_required: bool = False,
        auth_type: str = "none",
        response_time_ms: int = 0,
        features: List[str] = None,
        metadata: Dict[str, Any] = None,
        discovery_method: str = "unknown",
        last_check: float = 0,
    ):
        """
        Initialize service information.

        Args:
            service_id: Unique identifier for the service
            name: Service name
            url: Base URL for the service
            description: Service description
            service_type: Type of service (e.g., weather, time, utility)
            endpoints: Available API endpoints
            auth_required: Whether authentication is required
            auth_type: Type of authentication required
            response_time_ms: Average response time in milliseconds
            features: List of service features
            metadata: Additional metadata about the service
            discovery_method: How the service was discovered
            last_check: Timestamp of last availability check
        """
        self.service_id = service_id
        self.name = name
        self.url = url
        self.description = description
        self.service_type = service_type
        self.endpoints = {} if endpoints is None else endpoints
        self.auth_required = auth_required
        self.auth_type = auth_type
        self.response_time_ms = response_time_ms
        self.features = [] if features is None else features
        self.metadata = {} if metadata is None else metadata
        self.discovery_method = discovery_method
        self.last_check = last_check
        self.is_available = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert service info to dictionary."""
        return {
            "service_id": self.service_id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "service_type": self.service_type,
            "endpoints": self.endpoints,
            "auth_required": self.auth_required,
            "auth_type": self.auth_type,
            "response_time_ms": self.response_time_ms,
            "features": self.features,
            "metadata": self.metadata,
            "discovery_method": self.discovery_method,
            "last_check": self.last_check,
            "is_available": self.is_available,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceInfo":
        """Create service info from dictionary."""
        return cls(
            service_id=data.get("service_id", ""),
            name=data.get("name", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            service_type=data.get("service_type", "unknown"),
            endpoints=data.get("endpoints", {}),
            auth_required=data.get("auth_required", False),
            auth_type=data.get("auth_type", "none"),
            response_time_ms=data.get("response_time_ms", 0),
            features=data.get("features", []),
            metadata=data.get("metadata", {}),
            discovery_method=data.get("discovery_method", "unknown"),
            last_check=data.get("last_check", 0),
        )


def get_service_registry() -> Dict[str, ServiceInfo]:
    """
    Get the registry of discovered services.

    Returns:
        Dict mapping service IDs to ServiceInfo objects
    """
    global _service_registry
    with _discovery_lock:
        return _service_registry.copy()


def get_service(service_id: str) -> Optional[ServiceInfo]:
    """
    Get information about a specific service.

    Args:
        service_id: The ID of the service to retrieve

    Returns:
        ServiceInfo for the specified service, or None if not found
    """
    global _service_registry
    with _discovery_lock:
        return _service_registry.get(service_id)


def get_services_by_type(service_type: str) -> List[ServiceInfo]:
    """
    Get all services of a specific type.

    Args:
        service_type: The type of services to retrieve

    Returns:
        List of ServiceInfo objects matching the specified type
    """
    global _service_registry
    with _discovery_lock:
        return [
            service
            for service in _service_registry.values()
            if service.service_type == service_type
        ]


def register_service(service: ServiceInfo) -> str:
    """
    Register a service in the service registry.

    Args:
        service: ServiceInfo object to register

    Returns:
        Service ID of the registered service
    """
    global _service_registry
    with _discovery_lock:
        # Update the existing service if it exists
        if service.service_id in _service_registry:
            _service_registry[service.service_id] = service
            return service.service_id

        # Generate a new ID if none provided
        if not service.service_id:
            service.service_id = str(uuid.uuid4())

        _service_registry[service.service_id] = service
        logger.info(f"Registered service: {service.name} ({service.service_id})")

        return service.service_id


def discover_services(force: bool = False) -> List[ServiceInfo]:
    """
    Discover available services using active and passive discovery.

    This function probes known API endpoints and analyzes responses to infer
    functionality. It combines active discovery (direct probing) with passive
    discovery (analyzing logs and traffic patterns).

    Args:
        force: Whether to force discovery even if recently performed

    Returns:
        List of discovered ServiceInfo objects
    """
    global _discovery_in_progress, _last_discovery_time

    # Check if discovery is already in progress
    with _discovery_lock:
        if _discovery_in_progress:
            logger.info("Service discovery already in progress")
            return list(_service_registry.values())

        # Check if discovery was recently performed (within 60 seconds)
        current_time = time.time()
        if not force and current_time - _last_discovery_time < 60:
            logger.info("Using cached service discovery results")
            return list(_service_registry.values())

        _discovery_in_progress = True

    try:
        logger.info("Starting service discovery...")

        # Reset last discovery time
        _last_discovery_time = time.time()

        # Perform active discovery
        active_services = _active_discovery()

        # Perform passive discovery
        passive_services = _passive_discovery()

        # Merge results
        discovered_services = []

        with _discovery_lock:
            # Register/update active discovery results
            for service in active_services:
                register_service(service)
                discovered_services.append(service)

            # Register/update passive discovery results
            for service in passive_services:
                register_service(service)
                discovered_services.append(service)

            logger.info(
                f"Service discovery completed: {len(discovered_services)} services found"
            )

            return discovered_services

    finally:
        with _discovery_lock:
            _discovery_in_progress = False


def _active_discovery() -> List[ServiceInfo]:
    """
    Perform active service discovery by probing known endpoints.

    Returns:
        List of discovered ServiceInfo objects
    """
    discovered_services = []

    # Probe common API endpoints
    for endpoint in COMMON_ENDPOINTS:
        try:
            # Parse the URL to extract the base service URL
            parsed_url = urlparse(endpoint)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # Skip URLs for example domains (which wouldn't be real services)
            if "example.com" in base_url:
                # Create a simulated service for demonstration
                service = _create_simulated_service(endpoint)
                if service:
                    discovered_services.append(service)
                continue

            # Probe the endpoint
            logger.debug(f"Probing endpoint: {endpoint}")
            start_time = time.time()

            response = requests.get(endpoint, timeout=5)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Check for valid JSON response
            if response.status_code == 200:
                try:
                    content_type = response.headers.get("Content-Type", "")

                    # Process JSON responses
                    if "application/json" in content_type:
                        json_data = response.json()
                        service = _analyze_json_service(
                            endpoint, json_data, response_time_ms
                        )
                        if service:
                            discovered_services.append(service)

                    # Process other successful responses
                    else:
                        service = _analyze_general_service(
                            endpoint, response, response_time_ms
                        )
                        if service:
                            discovered_services.append(service)

                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"Error processing response from {endpoint}: {str(e)}")

        except requests.RequestException as e:
            logger.debug(f"Error probing endpoint {endpoint}: {str(e)}")

    logger.info(f"Active discovery found {len(discovered_services)} services")
    return discovered_services


def _passive_discovery() -> List[ServiceInfo]:
    """
    Perform passive service discovery by analyzing logs and traffic patterns.

    Returns:
        List of discovered ServiceInfo objects
    """
    discovered_services = []

    # In a real implementation, this would analyze logs and traffic patterns
    # For demonstration purposes, we'll create some simulated services

    # Simulate discovering a few interesting services
    simulated_services = [
        {
            "name": "Quantum Computing Service",
            "url": "https://quantum-simulator.example.com/api/v1",
            "description": "Quantum circuit simulation API",
            "service_type": "quantum",
            "endpoints": {
                "simulate": {
                    "path": "/simulation",
                    "method": "POST",
                    "parameters": {
                        "circuit": "JSON description of quantum circuit",
                        "shots": "Number of simulation runs",
                        "noise_model": "Optional noise model",
                    },
                    "returns": {
                        "results": "Simulation results",
                        "probabilities": "State probabilities",
                        "execution_time": "Execution time in milliseconds",
                    },
                },
                "optimize": {
                    "path": "/optimize",
                    "method": "POST",
                    "parameters": {
                        "circuit": "JSON description of quantum circuit",
                        "optimization_level": "Optimization level (1-5)",
                    },
                    "returns": {
                        "optimized_circuit": "Optimized circuit description",
                        "gate_count": "Number of gates in optimized circuit",
                        "depth": "Circuit depth",
                    },
                },
            },
            "auth_required": True,
            "auth_type": "apikey",
            "features": [
                "circuit_simulation",
                "quantum_optimization",
                "noise_modeling",
            ],
        },
        {
            "name": "Neural Network Inference API",
            "url": "https://neural-engine.example.com/api/v1",
            "description": "API for neural network inference and model management",
            "service_type": "neural",
            "endpoints": {
                "infer": {
                    "path": "/infer",
                    "method": "POST",
                    "parameters": {
                        "model_id": "ID of the model to use",
                        "input_data": "Input data for inference",
                        "options": "Optional inference parameters",
                    },
                    "returns": {
                        "predictions": "Model predictions",
                        "confidence": "Prediction confidence scores",
                        "execution_time": "Execution time in milliseconds",
                    },
                },
                "models": {
                    "path": "/models",
                    "method": "GET",
                    "parameters": {},
                    "returns": {"models": "List of available models"},
                },
            },
            "auth_required": True,
            "auth_type": "bearer",
            "features": ["inference", "classification", "embeddings"],
        },
        {
            "name": "Weather Data Service",
            "url": "https://weather-api.example.com/api",
            "description": "Global weather data and forecasts",
            "service_type": "weather",
            "endpoints": {
                "current": {
                    "path": "/current",
                    "method": "GET",
                    "parameters": {
                        "location": "City name or coordinates",
                        "units": "Measurement units (metric/imperial)",
                    },
                    "returns": {
                        "temperature": "Current temperature",
                        "conditions": "Weather conditions",
                        "humidity": "Humidity percentage",
                        "wind": "Wind speed and direction",
                    },
                },
                "forecast": {
                    "path": "/forecast",
                    "method": "GET",
                    "parameters": {
                        "location": "City name or coordinates",
                        "days": "Number of days to forecast",
                        "units": "Measurement units (metric/imperial)",
                    },
                    "returns": {
                        "daily": "Daily forecast data",
                        "hourly": "Hourly forecast data",
                    },
                },
            },
            "auth_required": True,
            "auth_type": "apikey",
            "features": ["current_weather", "forecast", "historical_data"],
        },
    ]

    # Create ServiceInfo objects for simulated services
    for service_data in simulated_services:
        service = ServiceInfo(
            service_id=str(uuid.uuid4()),
            name=service_data["name"],
            url=service_data["url"],
            description=service_data["description"],
            service_type=service_data["service_type"],
            endpoints=service_data["endpoints"],
            auth_required=service_data["auth_required"],
            auth_type=service_data["auth_type"],
            features=service_data["features"],
            discovery_method="passive",
            last_check=time.time(),
        )

        discovered_services.append(service)

    logger.info(f"Passive discovery found {len(discovered_services)} services")
    return discovered_services


def _analyze_json_service(
    endpoint: str, json_data: Dict[str, Any], response_time_ms: int
) -> Optional[ServiceInfo]:
    """
    Analyze a JSON API response to infer service functionality.

    Args:
        endpoint: The API endpoint URL
        json_data: JSON response data
        response_time_ms: Response time in milliseconds

    Returns:
        ServiceInfo object if analysis was successful, None otherwise
    """
    # Parse the URL to extract the base service URL
    parsed_url = urlparse(endpoint)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Extract the API path
    api_path = parsed_url.path

    # Try to infer service name from the URL or response
    service_name = _infer_service_name(endpoint, json_data)

    # Try to infer service type from the response
    service_type, features = _infer_service_type(json_data)

    # Create endpoint info
    endpoint_info = {
        "path": api_path,
        "method": "GET",
        "parameters": {},
        "response_example": (
            json_data
            if not isinstance(json_data, list)
            else {"items": json_data[:2] if json_data else []}
        ),
    }

    # Try to extract parameters from the URL
    if parsed_url.query:
        import urllib.parse

        query_params = urllib.parse.parse_qs(parsed_url.query)
        endpoint_info["parameters"] = {
            key: "Query parameter" for key in query_params.keys()
        }

    # Check for authentication information in the response or headers
    auth_required = False
    auth_type = "none"

    # Look for common auth-related fields in the response
    auth_fields = ["token", "api_key", "auth", "authentication"]
    for field in auth_fields:
        if isinstance(json_data, dict) and field in json_data:
            auth_required = True
            auth_type = "unknown"
            break

    # Create a service description
    description = _generate_service_description(
        service_name, service_type, json_data, features
    )

    # Create and return the ServiceInfo
    service = ServiceInfo(
        service_id=str(uuid.uuid4()),
        name=service_name,
        url=base_url,
        description=description,
        service_type=service_type,
        endpoints={api_path: endpoint_info},
        auth_required=auth_required,
        auth_type=auth_type,
        response_time_ms=response_time_ms,
        features=features,
        metadata={
            "content_type": "application/json",
            "response_size": len(str(json_data)),
        },
        discovery_method="active",
        last_check=time.time(),
    )

    return service


def _analyze_general_service(
    endpoint: str, response: requests.Response, response_time_ms: int
) -> Optional[ServiceInfo]:
    """
    Analyze a general (non-JSON) API response to infer service functionality.

    Args:
        endpoint: The API endpoint URL
        response: Response object
        response_time_ms: Response time in milliseconds

    Returns:
        ServiceInfo object if analysis was successful, None otherwise
    """
    # Parse the URL to extract the base service URL
    parsed_url = urlparse(endpoint)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Extract the API path
    api_path = parsed_url.path

    # Try to infer service name from the URL or response
    service_name = _infer_service_name(endpoint, response.text)

    # Try to infer service type from the response
    content_type = response.headers.get("Content-Type", "")

    if "text/html" in content_type:
        service_type = "web"
        features = ["html", "web_content"]
    elif "text/plain" in content_type:
        service_type = "text"
        features = ["text_content"]
    elif "xml" in content_type:
        service_type = "xml"
        features = ["xml_data"]
    else:
        service_type = "unknown"
        features = []

    # Create endpoint info
    endpoint_info = {
        "path": api_path,
        "method": "GET",
        "parameters": {},
        "response_example": (
            response.text[:200] if len(response.text) > 200 else response.text
        ),
    }

    # Try to extract parameters from the URL
    if parsed_url.query:
        import urllib.parse

        query_params = urllib.parse.parse_qs(parsed_url.query)
        endpoint_info["parameters"] = {
            key: "Query parameter" for key in query_params.keys()
        }

    # Create a service description
    description = f"{service_name} ({service_type} service)"

    # Create and return the ServiceInfo
    service = ServiceInfo(
        service_id=str(uuid.uuid4()),
        name=service_name,
        url=base_url,
        description=description,
        service_type=service_type,
        endpoints={api_path: endpoint_info},
        auth_required=False,
        auth_type="none",
        response_time_ms=response_time_ms,
        features=features,
        metadata={"content_type": content_type, "response_size": len(response.text)},
        discovery_method="active",
        last_check=time.time(),
    )

    return service


def _infer_service_name(endpoint: str, response_data: Any) -> str:
    """
    Infer a service name from the endpoint URL or response data.

    Args:
        endpoint: The API endpoint URL
        response_data: Response data (JSON or text)

    Returns:
        Inferred service name
    """
    # Parse the URL
    parsed_url = urlparse(endpoint)

    # Try to extract name from the hostname
    hostname = parsed_url.netloc

    # Remove common subdomains
    hostname = re.sub(r"^(api|www|data)\.", "", hostname)

    # Extract domain name without TLD
    domain_parts = hostname.split(".")
    if len(domain_parts) >= 2:
        domain_name = domain_parts[-2]

        # Clean up the domain name
        domain_name = domain_name.replace("-", " ").title()

        # Check if domain name is meaningful
        if len(domain_name) > 3:
            return f"{domain_name} API"

    # Use path components as fallback
    path = parsed_url.path.strip("/")
    if path:
        path_parts = path.split("/")
        if len(path_parts) > 0:
            api_name = path_parts[0].replace("-", " ").replace("_", " ").title()
            if len(api_name) > 3:
                return f"{api_name} API"

    # Use JSON fields as a last resort
    if isinstance(response_data, dict):
        for name_field in ["name", "title", "service", "api"]:
            if name_field in response_data and isinstance(
                response_data[name_field], str
            ):
                return response_data[name_field]

    # Default name
    return "Unknown API"


def _infer_service_type(response_data: Any) -> Tuple[str, List[str]]:
    """
    Infer service type and features from response data.

    Args:
        response_data: Response data (JSON or text)

    Returns:
        Tuple of (service_type, features)
    """
    # Convert response data to string for pattern matching
    if isinstance(response_data, dict):
        response_str = json.dumps(response_data).lower()
    elif isinstance(response_data, list):
        response_str = json.dumps(response_data[:3] if response_data else []).lower()
    else:
        response_str = str(response_data).lower()

    # Check for each service type pattern
    matched_types = {}
    features = []

    for service_type, patterns in SERVICE_PATTERNS.items():
        match_count = 0
        for pattern in patterns:
            if re.search(pattern, response_str):
                match_count += 1

                # Add pattern as a feature
                feature = pattern.replace(r"\b", "").replace(r"(.*)?", "")
                if "|" in feature:
                    feature = feature.split("|")[0]
                features.append(feature)

        if match_count > 0:
            matched_types[service_type] = match_count

    # Determine the most likely service type
    if matched_types:
        # Sort by match count (descending)
        sorted_types = sorted(matched_types.items(), key=lambda x: x[1], reverse=True)
        primary_type = sorted_types[0][0]
    else:
        primary_type = "generic"

    # Remove duplicates from features
    features = list(set(features))

    return primary_type, features


def _generate_service_description(
    name: str, service_type: str, response_data: Any, features: List[str]
) -> str:
    """
    Generate a service description based on inferred information.

    Args:
        name: Service name
        service_type: Inferred service type
        response_data: Response data
        features: Inferred features

    Returns:
        Generated service description
    """
    # Base description based on service type
    type_descriptions = {
        "weather": "Weather data and forecast service",
        "time": "Time and date information service",
        "location": "Geolocation and mapping service",
        "data": "Data access and analysis service",
        "image": "Image generation or processing service",
        "user": "User management and authentication service",
        "content": "Content management and delivery service",
        "calculation": "Calculation and computation service",
        "quantum": "Quantum computing simulation service",
        "neural": "Neural network and AI inference service",
    }

    description = type_descriptions.get(service_type, f"{name} API")

    # Add feature information
    if features:
        feature_str = ", ".join(features[:3])
        if len(features) > 3:
            feature_str += f" and {len(features) - 3} more"

        description += f". Features: {feature_str}"

    return description


def _create_simulated_service(endpoint: str) -> Optional[ServiceInfo]:
    """
    Create a simulated service for demonstration purposes.

    Args:
        endpoint: The API endpoint URL

    Returns:
        ServiceInfo for the simulated service
    """
    parsed_url = urlparse(endpoint)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Create endpoint info based on URL patterns
    if "quantum-simulator" in base_url:
        return ServiceInfo(
            service_id=str(uuid.uuid4()),
            name="Quantum Simulator API",
            url=base_url,
            description="Quantum circuit simulation service",
            service_type="quantum",
            endpoints={
                "/simulation": {
                    "path": "/api/v1/simulation",
                    "method": "POST",
                    "parameters": {
                        "circuit": "JSON description of quantum circuit",
                        "shots": "Number of simulation runs",
                        "noise_model": "Optional noise model",
                    },
                    "returns": {
                        "results": "Simulation results",
                        "probabilities": "State probabilities",
                        "execution_time": "Execution time in milliseconds",
                    },
                }
            },
            auth_required=True,
            auth_type="apikey",
            features=["circuit_simulation", "quantum_optimization", "noise_modeling"],
            discovery_method="active",
            last_check=time.time(),
        )

    elif "neural-engine" in base_url:
        return ServiceInfo(
            service_id=str(uuid.uuid4()),
            name="Neural Engine API",
            url=base_url,
            description="Neural network inference and management service",
            service_type="neural",
            endpoints={
                "/infer": {
                    "path": "/api/v1/infer",
                    "method": "POST",
                    "parameters": {
                        "model_id": "ID of the model to use",
                        "input_data": "Input data for inference",
                        "options": "Optional inference parameters",
                    },
                    "returns": {
                        "predictions": "Model predictions",
                        "confidence": "Prediction confidence scores",
                        "execution_time": "Execution time in milliseconds",
                    },
                }
            },
            auth_required=True,
            auth_type="bearer",
            features=["inference", "classification", "embeddings"],
            discovery_method="active",
            last_check=time.time(),
        )

    return None


def invoke_service(
    service_url: str,
    api_endpoint: str,
    parameters: Dict[str, Any],
    auth_credentials: Dict[str, Any] = None,
    method: str = "GET",
) -> Dict[str, Any]:
    """
    Invoke a discovered service API.

    This function makes an API call to a discovered service, handling authentication
    and parameter formatting. It ensures secure handling of credentials and provides
    appropriate error handling.

    Args:
        service_url: Base URL of the service
        api_endpoint: API endpoint to call
        parameters: Parameters to pass to the API
        auth_credentials: Authentication credentials (if required)
        method: HTTP method to use (GET, POST, PUT, DELETE)

    Returns:
        Dict containing API response and metadata
    """
    # Normalize method
    method = method.upper()

    # Normalize URLs
    service_url = service_url.rstrip("/")
    api_endpoint = api_endpoint.lstrip("/")

    # Construct full URL
    full_url = f"{service_url}/{api_endpoint}"

    logger.info(f"Invoking service API: {method} {full_url}")

    # Find the service in the registry
    service_info = None
    for service in _service_registry.values():
        if service.url == service_url or service.url.rstrip("/") == service_url:
            service_info = service
            break

    # Prepare headers
    headers = {"User-Agent": "Quantum-Orchestrator/1.0"}

    # Apply authentication if required
    if service_info and service_info.auth_required:
        # Check if credentials were provided
        if not auth_credentials:
            logger.warning(
                f"Service {service_info.name} requires authentication, but no credentials provided"
            )
            return {
                "success": False,
                "error": "Authentication required but no credentials provided",
                "service": service_info.name if service_info else "Unknown",
                "url": full_url,
            }

        # Apply authentication based on type
        if service_info.auth_type == "apikey":
            key_name = auth_credentials.get("key_name", "api_key")
            key_value = auth_credentials.get("key", "")
            in_header = auth_credentials.get("in_header", True)

            if in_header:
                headers[key_name] = key_value
            else:
                # Add as query parameter
                if "?" in full_url:
                    full_url += f"&{key_name}={key_value}"
                else:
                    full_url += f"?{key_name}={key_value}"

        elif service_info.auth_type == "bearer":
            token = auth_credentials.get("token", "")
            headers["Authorization"] = f"Bearer {token}"

        elif service_info.auth_type == "basic":
            import base64

            username = auth_credentials.get("username", "")
            password = auth_credentials.get("password", "")
            auth_str = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"

    # Record start time for performance tracking
    start_time = time.time()

    try:
        # Execute the request
        if method == "GET":
            response = requests.get(
                full_url, headers=headers, params=parameters, timeout=30
            )
        elif method == "POST":
            # Check for JSON data
            content_type = "application/json"
            headers["Content-Type"] = content_type
            response = requests.post(
                full_url, headers=headers, json=parameters, timeout=30
            )
        elif method == "PUT":
            headers["Content-Type"] = "application/json"
            response = requests.put(
                full_url, headers=headers, json=parameters, timeout=30
            )
        elif method == "DELETE":
            response = requests.delete(
                full_url, headers=headers, params=parameters, timeout=30
            )
        else:
            return {
                "success": False,
                "error": f"Unsupported HTTP method: {method}",
                "service": service_info.name if service_info else "Unknown",
                "url": full_url,
            }

        # Record response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Update service info if available
        if service_info:
            service_info.response_time_ms = response_time_ms
            service_info.last_check = time.time()
            service_info.is_available = True

        # Parse response
        try:
            if response.headers.get("Content-Type", "").startswith("application/json"):
                response_data = response.json()
            else:
                response_data = {"raw_content": response.text[:1000]}
        except json.JSONDecodeError:
            response_data = {"raw_content": response.text[:1000]}

        # Prepare result
        result = {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response": response_data,
            "headers": dict(response.headers),
            "response_time_ms": response_time_ms,
            "service": service_info.name if service_info else "Unknown",
            "url": full_url,
        }

        if response.status_code >= 400:
            result["error"] = f"Service returned error status: {response.status_code}"

        return result

    except requests.RequestException as e:
        # Update service info if available
        if service_info:
            service_info.last_check = time.time()
            service_info.is_available = False

        logger.error(f"Error invoking service {full_url}: {str(e)}")

        return {
            "success": False,
            "error": f"Error invoking service: {str(e)}",
            "service": service_info.name if service_info else "Unknown",
            "url": full_url,
        }


def refresh_service_status() -> Dict[str, Any]:
    """
    Refresh the status of all discovered services.

    Returns:
        Dict containing status information for all services
    """
    global _service_registry

    with _discovery_lock:
        services = list(_service_registry.values())

    updated_count = 0
    available_count = 0

    for service in services:
        try:
            # Skip services discovered too recently
            if time.time() - service.last_check < 300:  # 5 minutes
                if service.is_available:
                    available_count += 1
                continue

            # Make a simple request to check availability
            url = service.url
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            response = requests.get(url, timeout=5)

            # Update service status
            service.is_available = response.status_code < 500
            service.last_check = time.time()

            if service.is_available:
                available_count += 1

            updated_count += 1

        except requests.RequestException:
            # Service is unavailable
            service.is_available = False
            service.last_check = time.time()
            updated_count += 1

    return {
        "total_services": len(services),
        "updated_count": updated_count,
        "available_count": available_count,
        "timestamp": time.time(),
    }


# Initialize service discovery on module load
def _initialize():
    # Start a background thread for periodic service discovery
    def discovery_thread():
        while True:
            try:
                # Discover services
                discover_services()

                # Sleep for 10 minutes
                time.sleep(600)
            except Exception as e:
                logger.error(f"Error in discovery thread: {str(e)}")
                # Sleep for 1 minute on error
                time.sleep(60)

    # Start the thread
    threading.Thread(target=discovery_thread, daemon=True).start()


# Run initialization
_initialize()
