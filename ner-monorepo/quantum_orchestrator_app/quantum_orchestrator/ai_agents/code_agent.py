"""
CodeAgent: AI agent responsible for generating and improving code.

Part of the Cognitive Fusion Core system, generates code based on requirements.
"""

from typing import Any, Dict

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.services.llm_service import (
    generate_completion_async,
)


class CodeAgent:
    """
    CodeAgent: Responsible for generating and improving code.

    Uses LLM services to generate code based on requirements and improve
    existing code through refactoring and optimization.
    """

    def __init__(self, orchestrator: Any):
        """
        Initialize the CodeAgent.

        Args:
            orchestrator: The central Orchestrator instance
        """
        self.logger = get_logger(__name__)
        self.orchestrator = orchestrator
        self.logger.info("CodeAgent initialized")

    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Dict[str, Any] = None,
        code_style: str = "clean",
    ) -> Dict[str, Any]:
        """
        Generate code based on a description.

        Args:
            description: Description of what the code should do
            language: Programming language to use
            context: Additional context information
            code_style: Style preference (clean, verbose, compact)

        Returns:
            Dictionary containing generated code and explanation
        """
        self.logger.info(f"Generating {language} code for: {description[:50]}...")

        # Process context information
        context_str = ""
        if context:
            context_str = "\n\nAdditional context:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"

        # Check for messages from other agents
        planning_messages = self.orchestrator.check_messages("code")
        planning_context = ""

        for message in planning_messages:
            if message["sender"] == "planning" and "plan" in message["payload"]:
                planning_context = (
                    f"\n\nFrom planning agent:\n{message['payload']['plan']}"
                )

        # Set style guidance based on preference
        style_guidance = ""
        if code_style == "clean":
            style_guidance = "Write clean, maintainable code with appropriate comments."
        elif code_style == "verbose":
            style_guidance = (
                "Write verbose code with detailed comments explaining each step."
            )
        elif code_style == "compact":
            style_guidance = "Write compact, efficient code with minimal comments."

        # Prepare prompt for the LLM
        prompt = f"""You are an expert {language} developer. Generate code based on the following description:

Description: {description}
{context_str}
{planning_context}

Requirements:
- Language: {language}
- Style: {style_guidance}
- The code should be complete and ready to use
- Include error handling for robustness
- Follow best practices for {language}

Please provide:
1. The complete code implementation
2. A brief explanation of how the code works
3. Any assumptions made during implementation

Code:
"""

        # Generate code using LLM
        try:
            completion = await generate_completion_async(prompt)

            if not completion:
                return {"success": False, "error": "Failed to generate code"}

            # Extract code and explanation
            code, explanation = self._parse_code_response(completion, language)

            # Notify optimization agent about the generated code
            self.orchestrator.send_message(
                sender="code",
                recipient="optimization",
                message={
                    "code": code,
                    "language": language,
                    "description": description,
                },
            )

            return {
                "success": True,
                "code": code,
                "explanation": explanation,
                "language": language,
            }

        except Exception as e:
            self.logger.error(f"Error generating code: {str(e)}")
            return {"success": False, "error": f"Error generating code: {str(e)}"}

    async def refactor_code(
        self,
        code: str,
        language: str = "python",
        requirements: str = "",
        preserve_functionality: bool = True,
    ) -> Dict[str, Any]:
        """
        Refactor existing code based on requirements.

        Args:
            code: Existing code to refactor
            language: Programming language of the code
            requirements: Specific refactoring requirements
            preserve_functionality: Whether to strictly preserve functionality

        Returns:
            Dictionary containing refactored code and explanation
        """
        self.logger.info("Refactoring code...")

        # Check for messages from test agent
        test_messages = self.orchestrator.check_messages("code")

        for message in test_messages:
            if message["sender"] == "test" and "test_results" in message["payload"]:
                test_results = (
                    f"\n\nTest Results:\n{message['payload']['test_results']}"
                )

        # Prepare prompt for the LLM

        prompt = f"""You are an expert {language} developer. Refactor the following code according to the given requirements:

Code to refactor:
{code}

Requirements:
{requirements}

{preserve_str}

Please provide:
1. The refactored code
2. A brief explanation of the changes made
3. Any assumptions made during refactoring

Refactored Code:
"""

        # Generate refactored code using LLM
        try:
            completion = await generate_completion_async(prompt)

            if not completion:
                return {"success": False, "error": "Failed to refactor code"}

            # Extract refactored code and explanation
            refactored_code, explanation = self._parse_code_response(
                completion, language
            )

            return {
                "success": True,
                "code": refactored_code,
                "explanation": explanation,
                "language": language,
            }

        except Exception as e:
            self.logger.error(f"Error refactoring code: {str(e)}")
            return {"success": False, "error": f"Error refactoring code: {str(e)}"}

    def _parse_code_response(self, completion: str, language: str):
        """
        Parse the code response from the LLM.

        Args:
            completion: The completion text from the LLM
            language: The programming language of the code

        Returns:
            Tuple containing the code and explanation
        """
        # Placeholder implementation - to be replaced with actual parsing logic
        code = completion
        explanation = "This is a placeholder explanation."

        return code, explanation
