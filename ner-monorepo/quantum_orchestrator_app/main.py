#!/usr/bin/env python3
"""
Quantum Orchestrator - Main Entry Point

This is the main entry point for the Quantum Orchestrator system.
It initializes the core components, verifies system integrity,
and starts the web interface.

Features:
- Neural Flow Pipeline for instruction processing
- Cognitive Fusion Core with specialized AI agents
- Zero-Touch Integration with service discovery
- Quantum-Inspired Optimization for workflow execution
- Intent-Driven Workflow Synthesis with natural language understanding
- Core Team Archetype Integration for collaborative problem-solving
- Self-Verification and Completion Assurance
"""

import sys
import logging
import argparse
from typing import Dict, Any

from quantum_orchestrator import init_api
from quantum_orchestrator.gui import create_app
from quantum_orchestrator.games.nexus_omniengine_v3.core.self_verification import SelfVerification

# Create Flask application - for gunicorn
app = create_app()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Quantum Orchestrator - Neural Flow Pipeline with Cognitive Fusion Core"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to (default: 5000)"
    )

    parser.add_argument(
        "--no-api", action="store_true", help="Do not start the API service"
    )

    parser.add_argument(
        "--verify", action="store_true", help="Perform self-verification and exit"
    )

    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip self-verification during startup",
    )

    return parser.parse_args()


def verify_system(orchestrator_instance=None) -> Dict[str, Any]:
    """
    Verify system integrity and component functionality.

    This function runs comprehensive self-verification to ensure that
    all required components are present and functioning correctly.

    Args:
        orchestrator_instance: The orchestrator instance (optional)

    Returns:
        Dict containing verification results
    """
    logging.info("Starting system verification")

    # Create self-verification instance
    verifier = SelfVerification(orchestrator_instance)

    # Run verification
    results = verifier.verify_all()

    # Print summary
    print("\n=== Quantum Orchestrator Self-Verification Results ===")
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Execution Time: {results['execution_time']:.2f} seconds")
    print("\nComponent Statuses:")

    for component, result in results.items():
        if isinstance(result, dict) and "status" in result:
            status_str = f"{result['status'].upper()}"
            print(f"  {component.ljust(25)}: {status_str}")

    # Print details of any failures
    if results["overall_status"] != "success":
        print("\nFailure Details:")

        for component, result in results.items():
            if (
                isinstance(result, dict)
                and result.get("status") != "success"
                and component != "overall_status"
            ):
                print(f"\n  {component}:")

                if "missing_modules" in result and result["missing_modules"]:
                    print(
                        f"    Missing modules: {', '.join(result['missing_modules'])}"
                    )

                if "error_modules" in result and result["error_modules"]:
                    print(f"    Error modules: {', '.join(result['error_modules'])}")

                if "missing_handlers" in result and result["missing_handlers"]:
                    print(
                        f"    Missing handlers: {', '.join(result['missing_handlers'])}"
                    )

                if "errors" in result and result["errors"]:
                    for error in result["errors"]:
                        print(f"    Error: {error}")

    return results


def initialize_orchestrator() -> Any:
    """
    Initialize the Quantum Orchestrator with all required components.

    This function initializes the main orchestrator instance and ensures
    that all required components are configured and initialized properly.

    Returns:
        The initialized orchestrator instance
    """
    from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Config
    from quantum_orchestrator.games.nexus_omniengine_v3.core.state_manager import StateManager
    from quantum_orchestrator.games.nexus_omniengine_v3.core.instruction_parser import InstructionParser

    # Initialize configuration
    config = Config()

    # Initialize state manager
    state_manager = StateManager()

    # Initialize instruction parser
    instruction_parser = InstructionParser()

    # Get orchestrator class and initialize it
    from quantum_orchestrator.games.nexus_omniengine_v3.core.agent import Orchestrator

    orchestrator_instance = Orchestrator(
        state_manager=state_manager,
        instruction_parser=instruction_parser,
        config=config,
    )

    # Initialize PlanningAgent
    from quantum_orchestrator.ai_agents.planning_agent import PlanningAgent

    planning_agent = PlanningAgent(orchestrator_instance)
    setattr(orchestrator_instance, "planning_agent", planning_agent)

    # Initialize CoreTeam
    from quantum_orchestrator.ai_agents.core_team import CoreTeam

    core_team = CoreTeam(orchestrator_instance)
    setattr(orchestrator_instance, "core_team", core_team)

    # Initialize service discovery
    try:
        from quantum_orchestrator.services.integration_service import discover_services

        discovered_services = discover_services()
        logging.info(f"Discovered {len(discovered_services)} external services")
    except Exception as e:
        logging.warning(f"Service discovery failed: {str(e)}")

    return orchestrator_instance


def run_self_tests(orchestrator_instance: Any) -> None:
    """
    Run self-tests to verify functionality of key components.

    Args:
        orchestrator_instance: The orchestrator instance
    """
    logging.info("Running self-tests")

    # Test 1: Verify that quantum optimization is working
    try:
        from quantum_orchestrator.utils.quantum_optimization import QuantumAnnealer

        # Define a simple cost function
        def test_cost_function(state):
            return sum((x - 5) ** 2 for x in state)

        # Create a small test annealer
        annealer = QuantumAnnealer(
            cost_function=test_cost_function, initial_state=[10, 0, 8], iterations=10
        )

        # Run optimization
        best_state, best_cost, _ = annealer.run()

        # Verify result
        initial_cost = test_cost_function([10, 0, 8])
        if best_cost < initial_cost:
            logging.info(
                f"Quantum optimization test passed: {initial_cost} -> {best_cost}"
            )
        else:
            logging.warning(
                f"Quantum optimization test warning: {initial_cost} -> {best_cost}"
            )

    except Exception as e:
        logging.error(f"Quantum optimization test failed: {str(e)}")

    # Test 2: Verify handler registration
    try:
        handlers = orchestrator_instance.get_available_tools()
        logging.info(f"Verified {len(handlers)} registered handlers")
    except Exception as e:
        logging.error(f"Handler verification failed: {str(e)}")


def main():
    """Initialize and run the Quantum Orchestrator web UI."""
    # Parse command line arguments
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Configure Flask application
    app.config["DEBUG"] = args.debug

    # Perform self-verification if requested
    if args.verify:
        verify_system()
        return 0

    # Initialize the orchestrator
    try:
        logging.info("Initializing Quantum Orchestrator")
        orchestrator_instance = initialize_orchestrator()
        logging.info("Quantum Orchestrator initialized successfully")

        # Set the orchestrator instance in the Flask app context
        app.config["ORCHESTRATOR"] = orchestrator_instance

    except Exception as e:
        logging.error(f"Failed to initialize Quantum Orchestrator: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    # Perform self-verification unless skipped
    if not args.skip_verify:
        verification_results = verify_system(orchestrator_instance)

        # Check verification results
        if verification_results["overall_status"] == "failed":
            logging.warning(
                "Self-verification failed. Some components may not work correctly."
            )
        else:
            logging.info("Self-verification completed successfully")

    # Run self-tests
    run_self_tests(orchestrator_instance)

    # Start API service unless --no-api is specified
    if not args.no_api:
        try:
            init_api(orchestrator_instance)
            logging.info("API service started on port 8000")
        except Exception as e:
            logging.error(f"Failed to start API service: {str(e)}")

    # Log startup information
    logging.info(f"Starting Quantum Orchestrator web UI on {args.host}:{args.port}")

    # Run the Flask application
    app.run(host=args.host, port=args.port, debug=args.debug)

    return 0


if __name__ == "__main__":
    sys.exit(main())
