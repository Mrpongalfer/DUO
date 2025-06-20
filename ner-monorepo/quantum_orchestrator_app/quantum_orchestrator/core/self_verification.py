# File: ~/Projects/quantum_orchestrator_app/quantum_orchestrator/core/self_verification.py
# Version: 2.0 - Robust verification with graceful handling of missing components

import importlib
import inspect
import logging
import sys
import time
from typing import Any, Dict, List, Optional

# Attempt to import core components needed for verification context
try:
    from quantum_orchestrator.games.nexus_omniengine_v3.core.agent import Orchestrator
    from quantum_orchestrator.games.nexus_omniengine_v3.core.config import get_settings
except ImportError as e:
    # If core components themselves fail, verification cannot proceed meaningfully
    logging.getLogger(__name__).critical(
        f"Failed to import core components for verification: {e}"
    )

    # Define dummy classes to allow SelfVerification class definition below
    class Orchestrator:
        pass

    def get_settings():
        return None


logger = logging.getLogger(__name__)


class SelfVerification:
    """
    Performs self-verification checks on the Quantum Orchestrator system components.
    Designed to run at startup or on demand.
    Handles missing optional/future components gracefully.
    """

    # Define expected modules/components per category for verification
    # Add to these lists as new components are implemented
    CORE_MODULES = [
        "quantum_orchestrator.core.agent",
        "quantum_orchestrator.core.config",
        "quantum_orchestrator.core.state_manager",
        "quantum_orchestrator.core.instruction_parser",
        "quantum_orchestrator.core.self_verification",  # Verify self
    ]
    SERVICE_MODULES = [
        "quantum_orchestrator.services.llm_service",
        "quantum_orchestrator.services.watcher_service",
        "quantum_orchestrator.services.api_service",
        "quantum_orchestrator.services.quality_service",
        "quantum_orchestrator.services.integration_service",  # Added from logs
    ]
    AGENT_MODULES = [
        "quantum_orchestrator.ai_agents.planning_agent",
        "quantum_orchestrator.ai_agents.code_agent",
        "quantum_orchestrator.ai_agents.test_agent",
        "quantum_orchestrator.ai_agents.optimization_agent",
        "quantum_orchestrator.ai_agents.meta_agent",
        "quantum_orchestrator.ai_agents.core_team",
    ]
    UTIL_MODULES = [
        "quantum_orchestrator.utils.logging_utils",
        "quantum_orchestrator.utils.path_resolver",
        "quantum_orchestrator.utils.security",
        "quantum_orchestrator.utils.telemetry",
        "quantum_orchestrator.utils.quantum_optimization",  # Advanced
        "quantum_orchestrator.utils.error_utils",  # Expected for Block 1/2
    ]
    HANDLER_MODULES = [
        "quantum_orchestrator.handlers.file_operations",  # Essential Block 1 handler
        "quantum_orchestrator.handlers.execution",
        "quantum_orchestrator.handlers.git_operations",
        "quantum_orchestrator.handlers.llm_operations",
        "quantum_orchestrator.handlers.quality_operations",
        # Add paths to custom handlers if applicable
    ]

    # Define expected core classes/functions within modules (for deeper checks)
    # Format: "module.name": ["Class1", "function2"]
    # Focus on essentials for Block 1 initially
    EXPECTED_MEMBERS = {
        "quantum_orchestrator.core.agent": ["Orchestrator"],
        "quantum_orchestrator.core.config": ["Settings", "get_settings"],
        "quantum_orchestrator.core.state_manager": ["StateManager"],
        "quantum_orchestrator.core.instruction_parser": ["InstructionParser"],
        "quantum_orchestrator.handlers.file_operations": [
            "create_file",
            "modify_file",
            "read_file",
            "delete_file",
            "list_files",
        ],
        "quantum_orchestrator.utils.logging_utils": ["get_logger", "setup_logging"],
        # Add more checks as components are implemented
    }

    def __init__(self, orchestrator_instance: Optional[Orchestrator] = None):
        """
        Initialize the verifier.

        Args:
            orchestrator_instance: An optional instance of the main Orchestrator
                                    to allow verification of its runtime state.
        """
        self.orchestrator = orchestrator_instance
        self.settings = (
            get_settings() if get_settings else None
        )  # Handle case where config fails
        self.component_registry: Dict[str, Dict[str, Any]] = (
            {}
        )  # Stores imported modules

    def verify_all(self) -> Dict[str, Any]:
        """Runs all verification checks and returns a summary report."""
        logger.info("Starting comprehensive self-verification...")
        start_time = time.time()
        overall_status = "success"
        results: Dict[str, Any] = {"tests": {}}  # Use sub-dict for clarity

        checks_to_run = [
            ("core_modules", self.verify_core_modules),
            ("service_modules", self.verify_service_modules),
            ("agent_modules", self.verify_ai_agents),
            ("util_modules", self.verify_utils),
            ("handlers", self.verify_handlers),
            # Add more checks here, e.g., config validation, DB connection, LLM connection
            # ("config_validation", self.verify_config_values),
            # ("db_connection", self.verify_db_connection),
            # ("llm_connection", self.verify_llm_connection),
            # ("advanced_features", self.verify_advanced_features), # Check optional modules
        ]

        for name, check_func in checks_to_run:
            logger.info(f"Verifying: {name}...")
            component_result = check_func()
            results[name] = component_result
            if component_result.get("status") == "failed":
                overall_status = "failed"
                logger.warning(f"Verification failed for: {name}")
            elif component_result.get("status") == "warning":
                if overall_status == "success":  # Don't overwrite a failure
                    overall_status = "warning"
                logger.warning(f"Verification warning for: {name}")
            else:
                logger.info(f"Verification succeeded for: {name}")

        end_time = time.time()
        results["overall_status"] = overall_status
        results["execution_time"] = end_time - start_time
        logger.info(
            f"Self-verification completed. Overall Status: {overall_status.upper()}. Duration: {results['execution_time']:.2f}s"
        )
        return results

    # --- Verification Methods for Categories ---

    def verify_core_modules(self) -> Dict[str, Any]:
        """Verify core system modules can be imported and have key members."""
        return self._verify_module_category("Core", self.CORE_MODULES)

    def verify_service_modules(self) -> Dict[str, Any]:
        """Verify service modules can be imported."""
        return self._verify_module_category(
            "Service", self.SERVICE_MODULES, check_members=False
        )  # Basic check for now

    def verify_ai_agents(self) -> Dict[str, Any]:
        """Verify AI agent modules can be imported."""
        return self._verify_module_category(
            "AI Agent", self.AGENT_MODULES, check_members=False
        )

    def verify_utils(self) -> Dict[str, Any]:
        """Verify utility modules can be imported."""
        return self._verify_module_category(
            "Utility", self.UTIL_MODULES, check_members=True
        )  # Check members for core utils

    def verify_handlers(self) -> Dict[str, Any]:
        """Verify core handlers can be imported and registered."""
        results = self._verify_module_category(
            "Handler", self.HANDLER_MODULES, check_members=True
        )
        errors = results.get("errors", [])
        test_results = results.get("tests", {})

        # Additionally check if the orchestrator instance has registered them
        if self.orchestrator and hasattr(self.orchestrator, "available_tools"):
            # CORRECTED: Access attribute directly
            registered_handlers = self.orchestrator.available_tools
            expected_handler_funcs = []
            for mod_name, members in self.EXPECTED_MEMBERS.items():
                if mod_name.startswith("quantum_orchestrator.handlers."):
                    expected_handler_funcs.extend(members)

            missing_in_orchestrator = []
            for func_name in expected_handler_funcs:
                # Need to find the handler key associated with the function, which might differ
                # This check assumes handler registration uses function names directly or maps them
                # A more robust check would inspect the function objects in the available_tools dict
                found = False
                for key, handler_obj in registered_handlers.items():
                    if callable(handler_obj) and handler_obj.__name__ == func_name:
                        found = True
                        break
                if not found:
                    # Check if maybe the key is based on the @handler 'name'
                    if func_name in registered_handlers:
                        found = True

                if not found:
                    missing_in_orchestrator.append(func_name)
                    test_results[f"handler_registration_{func_name}"] = {
                        "status": "failed",
                        "message": f"Handler function '{func_name}' not found in orchestrator.available_tools",
                    }

            if missing_in_orchestrator:
                err_msg = f"Orchestrator missing registered handlers: {', '.join(missing_in_orchestrator)}"
                logger.warning(err_msg)
                errors.append(err_msg)
                if results["status"] == "success":  # Don't overwrite failure
                    results["status"] = "warning"
            else:
                test_results["handler_registration"] = {
                    "status": "success",
                    "message": "Core handlers seem registered",
                }

        elif not self.orchestrator:
            test_results["handler_registration"] = {
                "status": "skipped",
                "message": "Orchestrator instance not provided",
            }
        else:  # Orchestrator exists but no available_tools attribute
            err_msg = "Orchestrator instance missing 'available_tools' attribute"
            logger.error(err_msg)
            errors.append(err_msg)
            results["status"] = "failed"
            test_results["handler_registration"] = {
                "status": "failed",
                "message": err_msg,
            }

        # Recalculate overall status
        if errors and results["status"] != "failed":
            results["status"] = "warning"
        if any(t.get("status") == "failed" for t in test_results.values()):
            results["status"] = "failed"

        results["errors"] = errors
        results["tests"] = test_results
        return results

    # --- Advanced / Optional Feature Verification (Examples) ---

    def verify_advanced_features(self) -> Dict[str, Any]:
        """Wrapper for verifying optional/advanced features."""
        # Example: Chain checks, return combined result
        quantum_res = self.verify_quantum_optimization()
        intent_res = self.verify_intent_driven_workflow()
        core_team_res = self.verify_core_team_integration()

        # Combine results (simple combination for now)
        combined_results = {
            "status": "success",
            "tests": {
                **quantum_res["tests"],
                **intent_res["tests"],
                **core_team_res["tests"],
            },
            "errors": quantum_res["errors"]
            + intent_res["errors"]
            + core_team_res["errors"],
        }
        if "failed" in [
            quantum_res["status"],
            intent_res["status"],
            core_team_res["status"],
        ]:
            combined_results["status"] = "failed"
        elif "warning" in [
            quantum_res["status"],
            intent_res["status"],
            core_team_res["status"],
        ]:
            combined_results["status"] = "warning"
        elif "skipped" in [
            quantum_res["status"],
            intent_res["status"],
            core_team_res["status"],
        ]:
            combined_results["status"] = "warning"  # Treat skipped as warning overall

        return combined_results

    def verify_quantum_optimization(self) -> Dict[str, Any]:
        """Verify optional Quantum Optimization components."""
        logger.info("Verifying Quantum Optimization Components (Optional)...")
        module_name = "quantum_orchestrator.utils.quantum_optimization"
        result = {"status": "success", "tests": {}, "errors": []}
        expected_classes = [
            "QuantumAnnealer",
            "QuantumGeneticAlgorithm",
            "WorkflowOptimizer",
        ]
        expected_funcs = ["optimize_workflow", "quantum_resource_allocation"]

        try:
            module = importlib.import_module(module_name)
            # Check classes
            for class_name in expected_classes:
                if hasattr(module, class_name) and inspect.isclass(
                    getattr(module, class_name)
                ):
                    result["tests"][f"{class_name}_class"] = {
                        "status": "success",
                        "message": f"{class_name} present",
                    }
                else:
                    result["tests"][f"{class_name}_class"] = {
                        "status": "warning",
                        "message": f"{class_name} class not found",
                    }
                    result["status"] = (
                        "warning"  # Mark as warning if optional component missing
                    )
            # Check functions
            for func_name in expected_funcs:
                if hasattr(module, func_name) and callable(getattr(module, func_name)):
                    result["tests"][f"{func_name}_func"] = {
                        "status": "success",
                        "message": f"{func_name} present",
                    }
                else:
                    result["tests"][f"{func_name}_func"] = {
                        "status": "warning",
                        "message": f"{func_name} function not found",
                    }
                    result["status"] = "warning"

        except ImportError:
            logger.warning(
                f"Optional module {module_name} not found. Skipping verification."
            )
            result["status"] = "skipped"
            result["message"] = f"Module {module_name} not found"
        except Exception as e:
            logger.error(f"Error verifying {module_name}: {e}", exc_info=True)
            result["status"] = "failed"
            result["errors"].append(f"Exception verifying {module_name}: {str(e)}")

        return result

    def verify_intent_driven_workflow(self) -> Dict[str, Any]:
        """Verify optional Intent-Driven Workflow components."""
        logger.info("Verifying Intent-Driven Workflow Components (Optional)...")
        module_name = "quantum_orchestrator.ai_agents.planning_agent"
        result = {"status": "success", "tests": {}, "errors": []}
        expected_methods = ["analyze_intent", "design_workflow"]

        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "PlanningAgent") and inspect.isclass(
                module.PlanningAgent
            ):
                result["tests"]["planning_agent_class"] = {
                    "status": "success",
                    "message": "PlanningAgent class present",
                }
                # Check methods on the class
                for method_name in expected_methods:
                    if hasattr(module.PlanningAgent, method_name) and callable(
                        getattr(module.PlanningAgent, method_name)
                    ):
                        result["tests"][f"planning_method_{method_name}"] = {
                            "status": "success",
                            "message": f"Method {method_name} present",
                        }
                    else:
                        result["tests"][f"planning_method_{method_name}"] = {
                            "status": "warning",
                            "message": f"Method {method_name} missing",
                        }
                        result["status"] = "warning"
            else:
                result["tests"]["planning_agent_class"] = {
                    "status": "warning",
                    "message": "PlanningAgent class not found",
                }
                result["status"] = "warning"

        except ImportError:
            logger.warning(
                f"Optional module {module_name} not found. Skipping verification."
            )
            result["status"] = "skipped"
            result["message"] = f"Module {module_name} not found"
        except Exception as e:
            logger.error(f"Error verifying {module_name}: {e}", exc_info=True)
            result["status"] = "failed"
            result["errors"].append(f"Exception verifying {module_name}: {str(e)}")

        return result

    def verify_core_team_integration(self) -> Dict[str, Any]:
        """Verify optional Core Team components."""
        logger.info("Verifying Core Team Integration (Optional)...")
        module_name = "quantum_orchestrator.ai_agents.core_team"
        result = {"status": "success", "tests": {}, "errors": []}
        expected_classes = [
            "CoreTeam",
            "CoreTeamMember",
            "StarkArchetype",
            "SanchezArchetype",
            "RocketArchetype",
            "HarleyArchetype",
            "MakimaArchetype",  # Note: Typo in original logs? Assuming Makima -> Makina? Or keep as is?
            "PowerArchetype",
            "YodaArchetype",
            "LucyArchetype",
        ]
        expected_methods = [
            "get_team_insights",
            "solve_problem_collaboratively",
        ]  # Methods on CoreTeam

        try:
            module = importlib.import_module(module_name)
            # Check classes
            for class_name in expected_classes:
                if hasattr(module, class_name) and inspect.isclass(
                    getattr(module, class_name)
                ):
                    result["tests"][f"{class_name}_class"] = {
                        "status": "success",
                        "message": f"{class_name} present",
                    }
                else:
                    result["tests"][f"{class_name}_class"] = {
                        "status": "warning",
                        "message": f"{class_name} class not found",
                    }
                    result["status"] = "warning"
            # Check CoreTeam methods
            if hasattr(module, "CoreTeam"):
                for method_name in expected_methods:
                    if hasattr(module.CoreTeam, method_name) and callable(
                        getattr(module.CoreTeam, method_name)
                    ):
                        result["tests"][f"coreteam_method_{method_name}"] = {
                            "status": "success",
                            "message": f"Method {method_name} present",
                        }
                    else:
                        result["tests"][f"coreteam_method_{method_name}"] = {
                            "status": "warning",
                            "message": f"Method {method_name} missing",
                        }
                        result["status"] = "warning"

        except ImportError:
            logger.warning(
                f"Optional module {module_name} not found. Skipping verification."
            )
            result["status"] = "skipped"
            result["message"] = f"Module {module_name} not found"
        except Exception as e:
            logger.error(f"Error verifying {module_name}: {e}", exc_info=True)
            result["status"] = "failed"
            result["errors"].append(f"Exception verifying {module_name}: {str(e)}")

        return result

    # --- Helper for Module Verification ---

    def _verify_module_category(
        self, category_name: str, module_list: List[str], check_members: bool = True
    ) -> Dict[str, Any]:
        """Helper to verify a list of modules."""
        results = {
            "status": "success",
            "tests": {},
            "errors": [],
            "missing_modules": [],
            "error_modules": [],
        }
        logger.info(
            f"Verifying {category_name} Modules: {', '.join(m.split('.')[-1] for m in module_list)}"
        )

        for module_name in module_list:
            module_short_name = module_name.split(".")[-1]
            verification_key = f"import_{module_short_name}"
            try:
                module = importlib.import_module(module_name)
                results["tests"][verification_key] = {
                    "status": "success",
                    "message": f"Imported {module_name}",
                }
                self.component_registry[module_name] = {
                    "module": module,
                    "classes": [],
                    "functions": [],
                }

                # Optionally check for specific members if requested and defined
                if check_members and module_name in self.EXPECTED_MEMBERS:
                    expected = self.EXPECTED_MEMBERS[module_name]
                    missing_members = []
                    for member_name in expected:
                        if not hasattr(module, member_name):
                            missing_members.append(member_name)
                    if missing_members:
                        err_msg = f"Module {module_name} missing expected members: {', '.join(missing_members)}"
                        logger.warning(err_msg)
                        results["tests"][f"members_{module_short_name}"] = {
                            "status": "warning",
                            "message": err_msg,
                        }
                        results["errors"].append(err_msg)
                        if results["status"] == "success":
                            results["status"] = "warning"
                    else:
                        results["tests"][f"members_{module_short_name}"] = {
                            "status": "success",
                            "message": "Core members present",
                        }

            except ImportError:
                logger.warning(f"Module not found: {module_name}. Skipping.")
                results["tests"][verification_key] = {
                    "status": "skipped",
                    "message": f"Module {module_name} not found",
                }
                results["missing_modules"].append(module_name)
                if results["status"] == "success":
                    results["status"] = (
                        "warning"  # Mark overall as warning if optional modules missing
                    )
            except Exception as e:
                logger.error(
                    f"Error importing/checking module {module_name}: {e}",
                    exc_info=False,
                )  # Avoid excessive traceback in summary
                results["tests"][verification_key] = {
                    "status": "failed",
                    "message": f"Error importing {module_name}: {str(e)}",
                }
                results["error_modules"].append(module_name)
                results["errors"].append(f"Error in {module_name}: {str(e)}")
                results["status"] = (
                    "failed"  # Mark overall as failed if any import errors
                )

        return results


# --- Standalone Verification Function ---
def verify_system() -> None:
    """
    Run a standalone verification of the system components.
    Can be called directly for diagnostic purposes.
    """
    # Ensure root logger is configured if run standalone
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )

    verifier = SelfVerification()
    results = verifier.verify_all()

    # Print results summary
    print("\n=== Quantum Orchestrator Self-Verification Results ===")
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Execution Time: {results['execution_time']:.2f} seconds")
    print("\nComponent Category Statuses:")

    # Print category summaries
    for component, result in results.items():
        if isinstance(result, dict) and "status" in result:
            status_str = f"{result['status'].upper()}"
            if result.get("missing_modules"):
                status_str += f" (Missing: {len(result['missing_modules'])})"
            if result.get("error_modules"):
                status_str += f" (Errors: {len(result['error_modules'])})"
            print(f"  {component.ljust(25)}: {status_str}")

    # Print failure/warning details
    if results["overall_status"] != "success":
        print("\n--- Issues Found ---")
        for component, result in results.items():
            if (
                isinstance(result, dict)
                and result.get("status") != "success"
                and component != "overall_status"
            ):
                print(f"\n* Category: {component} (Status: {result['status'].upper()})")
                if result.get("missing_modules"):
                    print(
                        f"  - Missing Modules: {', '.join(result['missing_modules'])}"
                    )
                if result.get("error_modules"):
                    print(f"  - Error Modules: {', '.join(result['error_modules'])}")
                if result.get("errors"):
                    for error in result["errors"]:
                        print(f"  - Detail: {error}")
                # Print specific test failures/warnings within the category
                if "tests" in result:
                    for test_name, test_res in result["tests"].items():
                        if test_res.get("status") != "success":
                            print(
                                f"  - Test '{test_name}': {test_res['status'].upper()} - {test_res['message']}"
                            )
        print("--------------------")


if __name__ == "__main__":
    # Run verification if this script is executed directly
    verify_system()
