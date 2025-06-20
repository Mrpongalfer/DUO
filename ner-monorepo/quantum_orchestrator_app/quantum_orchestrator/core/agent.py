# File: ~/Projects/quantum_orchestrator_app/quantum_orchestrator/core/agent.py
# Version: 1.3 - Corrected logger definition scope and refined integration

"""
Orchestrator: The central component of the Quantum Orchestrator system.

Integrates recovered Replit logic. Implements the Neural Flow Pipeline concept
through instruction routing and coordinates the Cognitive Fusion Core of
specialized AI agents. Adheres to TPC standards and Drake v0.1 protocols.
"""

import asyncio
import importlib
import inspect
import json
import logging  # Ensure logging is at the very top
import pkgutil
import sys
import time
import traceback
import re
from functools import partial
from pathlib import Path
from queue import Queue  # Consider asyncio.Queue for fully async operation later
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Union

# --- Global Logger ---
# DEFINE LOGGER AT MODULE LEVEL *BEFORE* IT'S USED IN IMPORTS BELOW
logger = logging.getLogger(__name__)  # Move logger definition here

# --- Core Imports ---
try:
    from .config import Settings, get_settings, PROJECT_ROOT_DIR, DEFAULT_CONFIG_PATH

    logger.info("Loaded core config.")  # Logger is now defined
except ImportError as e:
    # Cannot log effectively if logging/config fails early, print instead
    print(f"FATAL: Failed to import core config: {e}", file=sys.stderr)

    # Define dummy get_settings if import failed
    class Settings:
        pass  # type: ignore

    def get_settings():
        return Settings()  # type: ignore

    PROJECT_ROOT_DIR = Path(".").resolve()
    DEFAULT_CONFIG_PATH = PROJECT_ROOT_DIR / "config.json"


# --- Component Imports (Attempt actuals, fallback to placeholders) ---
# Define placeholders FIRST, then try to import actuals
class StateManager:  # Placeholder Definition
    def __init__(self, config: Optional[Settings] = None):
        logger.info("StateManagerPlaceholder Initialized.")

    def begin_transaction(self, id: str):
        logger.debug(f"Placeholder: Begin Transaction {id}")

    def commit_transaction(self, id: str):
        logger.debug(f"Placeholder: Commit Transaction {id}")

    def rollback_transaction(self, id: str):
        logger.warning(f"Placeholder: Rollback Transaction {id}")

    def get_state(self, key: str, default: Any = None) -> Any:
        logger.debug(f"Placeholder: Get State '{key}'")
        return default

    def set_state(self, key: str, value: Any):
        logger.debug(f"Placeholder: Set State '{key}'")

    def update(self, key: str, value: Any):
        self.set_state(key, value)


class InstructionParser:  # Placeholder Definition
    def __init__(self, schema_path: Optional[str] = None):
        logger.info(
            f"InstructionParserPlaceholder Initialized with schema: {schema_path}"
        )

    def parse(self, instruction_data: Dict) -> Dict:
        return instruction_data

    def validate(self, instruction_data: Dict) -> Dict:
        logger.debug(
            f"Placeholder: Validating instruction: {instruction_data.get('step_id', 'N/A')}"
        )
        valid = isinstance(instruction_data.get("type"), str)
        return {
            "valid": valid,
            "errors": [] if valid else ["Missing or invalid 'type' field."],
        }


class LLMService:  # Placeholder Definition
    def __init__(self, settings: Settings):
        self.settings = settings
        logger.info("LLMServicePlaceholder Initialized.")

    async def generate_text(
        self, prompt: str, model_override: Optional[str] = None
    ) -> str:
        effective_model = model_override or self.settings.llm_service.model_name
        logger.info(f"LLM Placeholder generating text (model: {effective_model})...")
        await asyncio.sleep(0.05)
        return f"LLM Placeholder Response: {prompt[:50]}"

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        model_override: Optional[str] = None,
    ) -> str:
        effective_model = model_override or self.settings.llm_service.model_name
        logger.info(f"LLM Placeholder generating code (model: {effective_model})...")
        await asyncio.sleep(0.05)
        return f"# LLM Placeholder Code: {prompt[:50]}"


class PlanningAgent:  # Placeholder Definition
    def __init__(self, orchestrator: Any):
        logger.info("PlanningAgentPlaceholder Initialized.")

    async def design_workflow(self, intent: str, available_tools: Dict) -> List[Dict]:
        logger.info(f"Placeholder plan generation for intent: {intent}")
        await asyncio.sleep(0.05)
        plan = []
        if "file" in intent.lower():
            plan.append(
                {
                    "type": "list_files",
                    "description": "List files first (placeholder step)",
                }
            )
        plan.append(
            {
                "type": "PLACEHOLDER_ACTION",
                "description": "Execute core intent (placeholder step)",
            }
        )
        return plan


class CodeAgent:
    pass


class TestAgent:
    pass


class OptimizationAgent:
    def __init__(self, orchestrator: Any):
        logger.info("OptimizationAgentPlaceholder Initialized.")

    async def refine_code(self, code: str, context: Dict) -> Optional[str]:
        logger.info("Placeholder: Skipping code optimization.")
        await asyncio.sleep(0.05)
        return None


class MetaAgent:
    def __init__(self, orchestrator: Any):
        logger.info("MetaAgentPlaceholder Initialized.")

    async def generate_tool(
        self, description: str, suggested_name: str
    ) -> Optional[str]:
        logger.info(f"Placeholder: Generating tool for '{description}'")
        await asyncio.sleep(0.1)
        return f"def {suggested_name or 'placeholder_tool'}(params: dict):\n    print(f'Placeholder tool executed with: {{params}}')\n    return {{'success': True, 'result': 'placeholder success'}}"


class CoreTeamSimulator:
    pass


class Telemetry:
    def __init__(self):
        self.start_time = time.time()
        self.execution_count = 0
        self.success_count = 0
        self.total_time = 0.0
        logger.info("TelemetryPlaceholder Initialized.")

    def record_start_execution(self):
        self.execution_count += 1

    def record_execution_complete(self, *args, **kwargs):
        if kwargs.get("success"):
            self.success_count += 1
        self.total_time += kwargs.get("execution_time", 0)

    @property
    def success_rate(self):
        return (
            (self.success_count / self.execution_count) * 100
            if self.execution_count
            else 0
        )

    @property
    def average_execution_time(self):
        return self.total_time / self.execution_count if self.execution_count else 0


# Try to import actual implementations, replacing placeholders if successful
try:
    from .state_manager import StateManager

    logger.info("Loaded actual StateManager.")
except ImportError:
    logger.info("Using StateManager placeholder.")
try:
    from .instruction_parser import InstructionParser

    logger.info("Loaded actual InstructionParser.")
except ImportError:
    logger.info("Using InstructionParser placeholder.")
try:
    from ..services.llm_service import LLMService

    logger.info("Loaded actual LLMService.")
except ImportError:
    logger.info("Using LLMService placeholder.")
try:
    from ..ai_agents.planning_agent import PlanningAgent

    logger.info("Loaded actual PlanningAgent.")
except ImportError:
    logger.info("Using PlanningAgent placeholder.")
try:
    from ..ai_agents.code_agent import CodeAgent

    logger.info("Loaded actual CodeAgent.")
except ImportError:
    logger.info("Using CodeAgent placeholder.")
try:
    from ..ai_agents.test_agent import TestAgent

    logger.info("Loaded actual TestAgent.")
except ImportError:
    logger.info("Using TestAgent placeholder.")
try:
    from ..ai_agents.optimization_agent import OptimizationAgent

    logger.info("Loaded actual OptimizationAgent.")
except ImportError:
    logger.info("Using OptimizationAgent placeholder.")
try:
    from ..ai_agents.meta_agent import MetaAgent

    logger.info("Loaded actual MetaAgent.")
except ImportError:
    logger.info("Using MetaAgent placeholder.")
try:
    from ..ai_agents.core_team import CoreTeamSimulator

    logger.info("Loaded actual CoreTeamSimulator.")
except ImportError:
    logger.info("Using CoreTeamSimulator placeholder.")
try:
    from ..utils.telemetry import Telemetry

    logger.info("Loaded actual Telemetry.")
except ImportError:
    logger.info("Using Telemetry placeholder.")

try:
    # Assumes decorator is defined in handlers/__init__.py
    from ..handlers import handler

    logger.info("Loaded actual @handler decorator.")
except ImportError:
    logger.warning("Could not import @handler decorator. Defining dummy.")

    def handler(*args, **kwargs):  # Dummy decorator definition
        def decorator(func: Callable) -> Callable:
            setattr(func, "is_handler", True)
            setattr(
                func,
                "_handler_metadata",
                {
                    "name": kwargs.get("name", func.__name__),
                    "description": kwargs.get(
                        "description", func.__doc__ or "No description"
                    ),
                    "parameters": kwargs.get("parameters", {}),
                    "returns": kwargs.get("returns", {}),
                },
            )
            return func

        return decorator


try:
    from ..utils.logging_utils import get_logger

    logger.info("Loaded actual logging utils.")
except ImportError:
    get_logger = logging.getLogger  # Fallback


# --- Orchestrator Class Implementation ---
class Orchestrator:
    """
    The central orchestrator for receiving instructions, managing state,
    dispatching actions to handlers, and coordinating AI agents.
    Embodies the 'Neural Flow Pipeline' concept through its execution logic.
    """

    def __init__(self):
        """Initializes the Orchestrator instance."""
        # Critical: Get settings *first* to configure logging etc.
        self.settings: Settings = get_settings()
        global logger  # Allow updating the module-level logger based on config
        logger = get_logger(__name__)  # Get potentially configured logger

        logger.info(f"Initializing Orchestrator '{self.settings.app_name}'...")
        llm_config = self.settings.llm_service
        logger.info(
            f"LLM Service Config: Provider='{llm_config.default_provider}', Model='{llm_config.model_name}', Base='{llm_config.api_base}'"
        )

        # Initialize core components
        self.state_manager = StateManager(config=self.settings)
        schema_file = PROJECT_ROOT_DIR / "instruction_schema.json"
        self.parser = InstructionParser(schema_path=str(schema_file))
        self.llm_service = LLMService(self.settings)
        self.telemetry = Telemetry()

        # Handler / Tool Registry
        self.handlers: Dict[str, Callable] = {}
        self.handler_lock = Lock()
        self.available_tools: Dict[str, Any] = {}
        self._register_handlers()
        self._update_available_tools()

        # Initialize AI Agents
        self.planning_agent = PlanningAgent(self)
        self.code_agent = (
            CodeAgent(self)
            if "CodeAgent" in globals() and not isinstance(CodeAgent, type(type))
            else None
        )
        self.test_agent = (
            TestAgent(self)
            if "TestAgent" in globals() and not isinstance(TestAgent, type(type))
            else None
        )
        self.optimization_agent = (
            OptimizationAgent(self)
            if "OptimizationAgent" in globals()
            and not isinstance(OptimizationAgent, type(type))
            else None
        )
        self.meta_agent = (
            MetaAgent(self)
            if "MetaAgent" in globals() and not isinstance(MetaAgent, type(type))
            else None
        )
        self.core_team = (
            CoreTeamSimulator()
            if "CoreTeamSimulator" in globals()
            and not isinstance(CoreTeamSimulator, type(type))
            else None
        )

        self.agents: Dict[str, Optional[Any]] = {
            "planning": self.planning_agent,
            "code": self.code_agent,
            "test": self.test_agent,
            "optimization": self.optimization_agent,
            "meta": self.meta_agent,
            "core_team": self.core_team,
        }
        self.message_queues: Dict[str, Queue] = {
            name: Queue()
            for name in list(self.agents.keys()) + ["orchestrator"]
            if self.agents.get(name) or name == "orchestrator"
        }

        logger.info("Orchestrator initialization complete.")

    def _register_handlers(self):
        """Dynamically discovers and registers handlers."""
        logger.info("Registering action handlers...")
        handlers_package_dir = Path(__file__).parent.parent / "handlers"
        package_name = "quantum_orchestrator.handlers"
        logger.debug(f"Scanning for handlers in: {handlers_package_dir}")

        with self.handler_lock:
            self.handlers = {}
            if not handlers_package_dir.is_dir():
                logger.error(f"Handlers directory not found: {handlers_package_dir}.")
                self.handlers["PLACEHOLDER_ACTION"] = self._placeholder_handler
                return

            module_paths_to_scan = [str(handlers_package_dir)]
            for _, name, ispkg in pkgutil.iter_modules(
                path=[str(handlers_package_dir)]
            ):
                if ispkg:
                    module_paths_to_scan.append(str(handlers_package_dir / name))

            for path in module_paths_to_scan:
                for importer, modname, ispkg in pkgutil.walk_packages(
                    path=[path], prefix=package_name + "."
                ):
                    if not ispkg:
                        self._load_handlers_from_module(modname)

            if not self.handlers:
                logger.warning("No handlers registered dynamically. Using placeholder.")
                self.handlers["PLACEHOLDER_ACTION"] = self._placeholder_handler

            logger.info(
                f"Registered {len(self.handlers)} handlers: {list(self.handlers.keys())}"
            )

    def _load_handlers_from_module(self, module_name: str):
        """Loads and registers handlers from a specific module."""
        try:
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
            logger.debug(f"Processing module: {module_name}")

            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if callable(attribute) and getattr(attribute, "is_handler", False):
                    metadata = getattr(attribute, "_handler_metadata", {})
                    handler_name = metadata.get("name", attribute.__name__)
                    if handler_name in self.handlers:
                        logger.warning(
                            f"Duplicate handler name '{handler_name}' in {module_name}. Overwriting."
                        )
                    self.handlers[handler_name] = attribute
                    logger.info(
                        f"Registered handler: '{handler_name}' from {module_name}"
                    )
        except Exception as e:
            logger.error(
                f"Failed to load/register from module {module_name}: {e}",
                exc_info=False,
            )

    def _update_available_tools(self):
        """Updates the registry of tools available for AI agents."""
        logger.debug("Updating available tools registry...")
        with self.handler_lock:
            self.available_tools = {}
            for name, handler_func in self.handlers.items():
                metadata = getattr(handler_func, "_handler_metadata", {})
                self.available_tools[name] = {
                    "description": metadata.get(
                        "description", "No description available."
                    ),
                    "parameters": metadata.get("parameters", {}),
                    "returns": metadata.get("returns", {}),
                    "module": getattr(handler_func, "__module__", "N/A"),
                }
        logger.info(
            f"Updated available_tools registry with {len(self.available_tools)} tools."
        )
        if not self.available_tools:
            logger.warning("Available tools registry empty.")

    def get_status(self) -> Dict[str, Any]:
        """Returns the current operational status."""
        uptime = time.time() - getattr(self.telemetry, "start_time", time.time())
        return {
            "status": "running",
            "app_name": self.settings.app_name,
            "handlers_count": len(self.handlers),
            "registered_handlers": list(self.handlers.keys()),
            "timestamp": time.time(),
            "uptime_seconds": round(uptime, 2),
            "telemetry": {
                "execution_count": getattr(self.telemetry, "execution_count", 0),
                "success_rate": round(getattr(self.telemetry, "success_rate", 0), 2),
                "average_execution_time": round(
                    getattr(self.telemetry, "average_execution_time", 0), 3
                ),
            },
        }

    async def execute_instruction(
        self, instruction: Union[Dict[str, Any], str]
    ) -> Dict[str, Any]:
        """Executes a single instruction or a workflow."""
        start_time = time.time()
        step_id = "unknown"
        result = {}
        try:
            if hasattr(self.telemetry, "record_start_execution"):
                self.telemetry.record_start_execution()

            # 1. Parse and Validate Input
            instruction_dict: Dict[str, Any] = {}
            if isinstance(instruction, str):
                instruction_dict = json.loads(instruction)
            elif isinstance(instruction, dict):
                instruction_dict = instruction
            else:
                raise TypeError("Instruction must be dict or JSON string.")
            step_id = instruction_dict.get("step_id", f"instr_{time.time_ns()}")

            validation_result = self.parser.validate(instruction_dict)
            if not validation_result["valid"]:
                raise ValueError(f"Invalid instruction: {validation_result['errors']}")

            # 2. Route based on Type
            instruction_type = instruction_dict.get("type", "").lower()
            logger.info(
                f"Routing instruction ID: {step_id}, Type: '{instruction_type}'"
            )

            if instruction_type == "intent":
                result = await self._process_intent_instruction(
                    step_id, instruction_dict
                )
            elif instruction_type in self.handlers:
                result = await self._process_direct_action(
                    step_id, instruction_dict
                )  # Pass whole instruction dict as action
            elif instruction_type == "workflow":
                result = await self._process_workflow_instruction(
                    step_id, instruction_dict
                )
            elif instruction_type == "generate_tool":
                result = await self._process_tool_generation(step_id, instruction_dict)
            else:
                raise ValueError(
                    f"Unknown instruction type or handler: '{instruction_type}'"
                )

        except json.JSONDecodeError as e:
            result = {"success": False, "error": f"Invalid JSON: {e}"}
        except ValueError as e:
            result = {"success": False, "error": f"Validation/Value Error: {e}"}
        except Exception as e:
            logger.error(
                f"Core execution error for instruction ID {step_id}: {e}", exc_info=True
            )
            result = {
                "success": False,
                "error": f"Core execution error: {type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }

        # Finalize result
        final_status = result.get("status", "UNKNOWN").upper()
        result["success"] = final_status in ["COMPLETED", "SUCCESS"] or result.get(
            "success", False
        )
        if "status" not in result:
            result["status"] = "COMPLETED" if result["success"] else "FAILED"
        result["step_id"] = step_id
        result["execution_time"] = time.time() - start_time
        if hasattr(self.telemetry, "record_execution_complete"):
            self.telemetry.record_execution_complete(
                success=result["success"], execution_time=result["execution_time"]
            )

        logger.info(
            f"Completed instruction ID: {step_id} | Success: {result['success']} | Status: {result['status']} | Time: {result['execution_time']:.3f}s"
        )
        return result

    async def _process_intent_instruction(
        self, step_id: str, instruction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processes intent by generating and executing a workflow."""
        intent = instruction.get("intent", "")
        if not intent:
            return {"success": False, "error": "Missing 'intent' field."}
        logger.info(f"Processing intent for ID {step_id}: '{intent[:100]}...'")
        if not self.planning_agent or not hasattr(
            self.planning_agent, "design_workflow"
        ):
            return {"success": False, "error": "Planning agent not available."}
        try:
            workflow_steps = await self.planning_agent.design_workflow(
                intent, self.available_tools
            )
            if not workflow_steps or not isinstance(workflow_steps, list):
                raise ValueError("Planning agent returned invalid plan.")
        except Exception as e:
            return {
                "success": False,
                "error": f"Planning failed: {type(e).__name__}: {e}",
            }
        workflow_instruction = {
            "type": "workflow",
            "steps": workflow_steps,
            "fail_fast": instruction.get("fail_fast", True),
        }
        logger.info(
            f"Executing generated workflow ({len(workflow_steps)} steps) for ID: {step_id}"
        )
        return await self._process_workflow_instruction(
            f"{step_id}_wf", workflow_instruction
        )

    async def _process_direct_action(
        self, step_id: str, action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processes a single direct action via its handler."""
        action_type = action.get("type")
        if not action_type:
            return {"success": False, "error": "Action missing 'type'."}
        params = {k: v for k, v in action.items() if k != "type"}
        logger.info(f"Processing direct action ID {step_id}: Type '{action_type}'")
        if action_type not in self.handlers:
            return {"success": False, "error": f"Unknown handler: '{action_type}'"}
        handler = self.handlers[action_type]
        transaction_id = f"tx_{step_id}_{time.time_ns()}"
        try:
            self.state_manager.begin_transaction(transaction_id)
            logger.debug(
                f"Executing handler '{action_type}'"
            )  # Params logged separately if needed
            if inspect.iscoroutinefunction(handler):
                handler_result = await handler(params=params)
            else:
                handler_result = await asyncio.get_running_loop().run_in_executor(
                    None, partial(handler, params=params)
                )
            if not isinstance(handler_result, dict) or "success" not in handler_result:
                raise TypeError("Handler returned invalid result format")
            if handler_result["success"]:
                self.state_manager.commit_transaction(transaction_id)
                return handler_result
            else:
                raise RuntimeError(
                    f"Handler reported failure: {handler_result.get('error', 'Unknown')}"
                )
        except Exception as e:
            logger.error(
                f"Handler '{action_type}' error ID {step_id}: {e}", exc_info=True
            )
            self.state_manager.rollback_transaction(transaction_id)
            return {
                "success": False,
                "action_type": action_type,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }

    async def _process_workflow_instruction(
        self, step_id: str, instruction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processes a workflow (currently sequential only)."""
        steps = instruction.get("steps", [])
        fail_fast = instruction.get("fail_fast", True)
        if not steps or not isinstance(steps, list):
            return {"success": False, "error": "Invalid/missing 'steps' list."}
        workflow_results: List[Dict[str, Any]] = []
        overall_success = True
        logger.info(
            f"Starting sequential workflow ID: {step_id} ({len(steps)} steps). FailFast={fail_fast}"
        )
        for i, step in enumerate(steps):
            step_start_time = time.time()
            step_internal_id = f"{step_id}_step{i + 1}"
            if not isinstance(step, dict) or "type" not in step:
                logger.warning(
                    f"Workflow {step_id}, Step {i + 1}: Invalid format, skipping."
                )
                step_result = {
                    "step_index": i + 1,
                    "success": False,
                    "error": "Invalid step format",
                    "step_duration": 0,
                }
            else:
                step_type = step["type"]
                logger.info(
                    f"Workflow {step_id}, executing Step {i + 1}: Type '{step_type}'"
                )
                step_result = await self._process_direct_action(
                    step_internal_id, step
                )  # Process step
                step_result["step_index"] = i + 1
            step_result["step_duration"] = time.time() - step_start_time
            workflow_results.append(step_result)
            if not step_result.get("success", False):
                overall_success = False
                logger.warning(
                    f"Workflow {step_id}, Step {i + 1} (Type: {step.get('type')}) failed."
                )
                if fail_fast:
                    logger.warning(f"FailFast stopping workflow {step_id}.")
                    break
        final_status = "COMPLETED" if overall_success else "FAILED"
        logger.info(f"Workflow ID: {step_id} finished. Overall Status: {final_status}")
        return {
            "success": overall_success,
            "status": final_status,
            "workflow_results": workflow_results,
        }

    async def _process_tool_generation(
        self, step_id: str, instruction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Processes a request to generate and optionally integrate a new tool."""
        description = instruction.get("description", "")
        suggested_name = instruction.get("suggested_name", "")
        integrate = instruction.get("integrate", True)
        logger.info(f"Processing tool generation ID: {step_id}.")
        if not description:
            return {"success": False, "error": "Tool description required."}
        if not self.meta_agent or not hasattr(self.meta_agent, "generate_tool"):
            return {"success": False, "error": "Meta agent unavailable."}
        try:
            tool_code = await self.meta_agent.generate_tool(description, suggested_name)
            if not tool_code:
                raise RuntimeError("Meta agent failed to generate tool code.")
            match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", tool_code)
            func_name = (
                match.group(1)
                if match
                else suggested_name or f"custom_tool_{time.time_ns()}"
            )
            handler_name = func_name
            result_payload = {
                "success": True,
                "message": f"Tool '{handler_name}' generated.",
                "tool_name": handler_name,
                "tool_code": tool_code,
                "integrated": False,
            }
            if integrate:
                logger.info(f"Integrating generated tool: {handler_name}")
                tool_file_path = None
                try:
                    custom_handlers_dir = (
                        Path(__file__).parent.parent / "handlers" / "custom"
                    )
                    custom_handlers_dir.mkdir(parents=True, exist_ok=True)
                    (custom_handlers_dir / "__init__.py").touch(exist_ok=True)
                    full_tool_code = f'# File: {custom_handlers_dir / f"{handler_name}.py"}\n# Generated tool for instruction {step_id}\n"""\n{description}\n"""\nimport json, os, asyncio, logging\nfrom typing import *\nfrom quantum_orchestrator.handlers import handler\nlogger = logging.getLogger(__name__)\n\n'
                    if (
                        f'@handler(name="{handler_name}"' not in tool_code
                        and f"def {func_name}" in tool_code
                    ):
                        full_tool_code += f'@handler(name="{handler_name}", description="{description}")\n'
                    full_tool_code += tool_code
                    tool_file_path = custom_handlers_dir / f"{handler_name}.py"
                    with open(tool_file_path, "w", encoding="utf-8") as f:
                        f.write(full_tool_code)
                    logger.info(f"Saved generated tool: {tool_file_path}")
                    module_name = f"quantum_orchestrator.handlers.custom.{handler_name}"
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    module = importlib.import_module(module_name)
                    registered = False
                    for name, obj in module.__dict__.items():
                        if (
                            inspect.isfunction(obj)
                            and obj.__module__ == module_name
                            and getattr(obj, "is_handler", False)
                        ):
                            metadata = getattr(obj, "_handler_metadata", {})
                            reg_name = metadata.get("name", name)
                            self.register_handler(reg_name, obj)
                            registered = True
                            result_payload.update(
                                {
                                    "message": f"Tool '{reg_name}' integrated.",
                                    "integrated": True,
                                    "tool_file": str(tool_file_path),
                                }
                            )
                            break
                    if not registered:
                        raise ImportError(
                            f"Could not find @handler func in {tool_file_path}"
                        )
                except Exception as integration_e:
                    logger.error(
                        f"Integration failed for '{handler_name}': {integration_e}",
                        exc_info=True,
                    )
                    result_payload.update(
                        {
                            "success": False,
                            "error": f"Integration failed: {integration_e}",
                            "integrated": False,
                            "tool_file": (
                                str(tool_file_path) if tool_file_path else None
                            ),
                        }
                    )
            return result_payload
        except Exception as e:
            logger.error(f"Tool generation error ID {step_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Tool generation error: {type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }

    @handler(name="PLACEHOLDER_ACTION", description="A dummy action for testing.")
    def _placeholder_handler(self, params: Dict) -> Dict:
        """Dummy handler for testing."""
        logger.info(f"Executed _placeholder_handler with params: {params}")
        return {"success": True, "result": "Placeholder OK"}


# --- Main Execution Logic (for testing) ---
async def main_async_runner():
    """Async main function for testing the Orchestrator."""
    print("Initializing Orchestrator for async test...")
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    try:
        orchestrator = Orchestrator()
        print("Orchestrator initialized.")
        print(f"Registered Handlers: {list(orchestrator.handlers.keys())}")
        test_instr = {
            "step_id": "test-direct-001",
            "description": "Test placeholder",
            "type": "PLACEHOLDER_ACTION",
            "detail": "Test data",
        }
        print("\nProcessing test instruction:")
        result = await orchestrator.execute_instruction(test_instr)
        print("\nTest Instruction Result:")
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"\n--- CONFIGURATION ERROR ---\nError: {e}")
    except Exception as e:
        print(f"\n--- Test Execution Error ---\nError: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        asyncio.run(main_async_runner())
    except KeyboardInterrupt:
        print("\nExecution interrupted.")
    except Exception as e:
        print(f"Unhandled error: {e}")
        traceback.print_exc()
