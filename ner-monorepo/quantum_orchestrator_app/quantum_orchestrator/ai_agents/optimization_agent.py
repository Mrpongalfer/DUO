"""
OptimizationAgent: AI agent responsible for code refinement and optimization.

Part of the Cognitive Fusion Core system, refines and optimizes code based on
various metrics and reinforcement learning.
"""

import json
import re  # Add this import
from typing import Any, Dict

from quantum_orchestrator.utils.logging_utils import get_logger


class OptimizationAgent:
    """
    OptimizationAgent: Responsible for refining and optimizing code.

    Uses various techniques including static analysis, performance metrics,
    and reinforcement learning to suggest and implement code improvements.
    """

    def __init__(self, orchestrator: Any):
        """
        Initialize the OptimizationAgent.

        Args:
            orchestrator: The central Orchestrator instance
        """
        self.logger = get_logger(__name__)
        self.orchestrator = orchestrator

        # Reinforcement learning model (simple for now)
        self.optimization_model = self._initialize_model()

        self.logger.info("OptimizationAgent initialized")

    def _initialize_model(self) -> Dict[str, Any]:
        """
        Initialize the reinforcement learning model.

        Returns:
            A simple reinforcement learning model
        """
        return {
            # Pattern-based optimization rules with weights
            "patterns": {
                # Code optimization patterns for Python
                r"for\s+.*?\s+in\s+range\(len\((.*?)\)\)": {
                    "weight": 0.8,
                    "suggestion": "Use enumerate() instead of range(len())",
                    "category": "readability",
                },
                r"if\s+(.*?)\s*==\s*True": {
                    "weight": 0.5,
                    "suggestion": "Simplify boolean comparison",
                    "category": "readability",
                },
                r"if\s+(.*?)\s*==\s*False": {
                    "weight": 0.5,
                    "suggestion": "Use 'if not expr' instead of 'if expr == False'",
                    "category": "readability",
                },
                r"except:\s*$": {
                    "weight": 0.9,
                    "suggestion": "Use specific exception types instead of bare except",
                    "category": "robustness",
                },
                r"while\s+True:\s*[^#\n]{0,50}break": {
                    "weight": 0.7,
                    "suggestion": "Consider replacing while True with a more specific condition",
                    "category": "readability",
                },
                r"\.append\(.*?\)\s*\n.*?\.append\(.*?\)": {
                    "weight": 0.6,
                    "suggestion": "Consider using list comprehension for multiple appends",
                    "category": "performance",
                },
                r"(\w+)\s*=\s*\[\s*\]\s*\n\s*for.*?:\s*\n\s*\1\.append": {
                    "weight": 0.7,
                    "suggestion": "Use list comprehension instead of building list with append",
                    "category": "performance",
                },
                r"print\(.*?\)": {
                    "weight": 0.3,
                    "suggestion": "Consider using logging instead of print statements",
                    "category": "robustness",
                },
                r"dict\(\)": {
                    "weight": 0.4,
                    "suggestion": "Use {} instead of dict() for dictionary creation",
                    "category": "performance",
                },
                r"list\(\)": {
                    "weight": 0.4,
                    "suggestion": "Use [] instead of list() for list creation",
                    "category": "performance",
                },
                r"[^\n:]+:[^\S\n]*(?:#[^\n]*)?$[^\S\n]*\n[^\S\n]*pass": {
                    "weight": 0.4,
                    "suggestion": "Consider implementing or removing pass statement",
                    "category": "readability",
                },
            },
            # Category weights
            "category_weights": {
                "performance": 1.0,
                "readability": 0.8,
                "robustness": 0.9,
                "security": 1.0,
            },
            # Learning rate for weight updates
            "learning_rate": 0.05,
            # History of optimizations and rewards
            "history": [],
        }

    async def refine_code(self, code: str, context: Dict[str, Any] = None) -> str:
        """
        Refine code based on various metrics and learned patterns.

        Args:
            code: Code to refine
            context: Additional context for refinement

        Returns:
            Refined code
        """
        self.logger.info("Refining code...")

        if not code:
            return ""

        # Get optimization suggestions based on patterns and metrics
        suggestions = self._get_optimization_suggestions(code)

        # Check messages from other agents for additional context
        messages = self.orchestrator.check_messages("optimization")

        # Extract test results from test agent if available
        test_results = None
        test_analysis = None
        for message in messages:
            if message["sender"] == "test":
                test_results = message["payload"].get("test_results")
                test_analysis = message["payload"].get("test_analysis")

        # If we don't have any suggestions and tests passed, no need to optimize
        if not suggestions and test_results and test_results.get("all_passed", False):
            self.logger.info("No optimizations needed, code is already good")
            return code

        # Prepare context for LLM
        context_str = ""
        if context:
            context_str += "Context:\n"
            for key, value in context.items():
                if isinstance(value, dict) or isinstance(value, list):
                    context_str += f"- {key}: {json.dumps(value)}\n"
                else:
                    context_str += f"- {key}: {value}\n"

        # Add test results to context if available
        if test_results:
            context_str += "\nTest Results:\n"
            context_str += f"- Tests run: {test_results.get('tests_run', 0)}\n"
            context_str += f"- Passed: {test_results.get('passed', 0)}\n"
            context_str += f"- Failed: {test_results.get('failed', 0)}\n"
            context_str += f"- All passed: {test_results.get('all_passed', False)}\n"

        # Add test analysis to context if available
        if test_analysis:
            context_str += "\nTest Analysis:\n"
            for issue in test_analysis.get("issues", []):
                context_str += f"- Issue: {issue}\n"
            for recommendation in test_analysis.get("recommendations", []):
                context_str += f"- Recommendation: {recommendation}\n"

        return context_str

    def _get_optimization_suggestions(self, code: str) -> list:
        """
        Get optimization suggestions for the given code.

        Args:
            code: The code to analyze

        Returns:
            A list of optimization suggestions
        """
        # This method should contain the logic to analyze the code and
        # return a list of suggestions based on the patterns and model
        suggestions = []
        # Example: Check for patterns
        for pattern, info in self.optimization_model["patterns"].items():
            if re.search(pattern, code):
                suggestions.append(info["suggestion"])
        return suggestions
