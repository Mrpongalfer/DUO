# File: ~/Projects/quantum_orchestrator_app/quantum_orchestrator/ai_agents/meta_agent.py
# Version: 1.1 - Integrated & Refined

"""
MetaAgent: Responsible for tasks related to the Orchestrator's own
capabilities, such as generating new tools/handlers based on descriptions.
"""

import logging
import time
from typing import Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports at runtime for Orchestrator hint
if TYPE_CHECKING:
    from quantum_orchestrator.games.nexus_omniengine_v3.core.agent import Orchestrator

try:
    # Attempt to import the handler decorator for use in generated code
    from quantum_orchestrator.handlers import handler
except ImportError:
    # Define dummy if not found (should not happen if handlers/__init__.py is correct)
    logging.warning(
        "Could not import @handler decorator from handlers. Defining dummy."
    )

    def handler(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


logger = logging.getLogger(__name__)


class MetaAgent:
    """
    AI Agent focused on meta-tasks like self-improvement, tool generation,
    and workflow analysis.
    """

    def __init__(self, orchestrator: "Orchestrator"):
        """
        Initializes the MetaAgent.

        Args:
            orchestrator: Reference to the main Orchestrator instance.
        """
        self.orchestrator = orchestrator
        self.settings = orchestrator.settings
        self.llm_service = orchestrator.llm_service  # Get LLM service from orchestrator
        logger.info("MetaAgent initialized.")

    async def generate_tool(
        self, description: str, suggested_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Uses the LLM service to generate Python code for a new handler/tool
        based on a natural language description.

        Args:
            description: Natural language description of the tool's function.
            suggested_name: An optional preferred name for the handler function.

        Returns:
            A string containing the generated Python code for the handler,
            or None if generation fails.
        """
        logger.info(
            f"Generating new tool/handler for description: {description[:100]}..."
        )

        # Create a more robust function name
        base_name = suggested_name or "custom_generated_handler"
        handler_func_name = "".join(
            c if c.isalnum() or c == "_" else "_" for c in base_name
        )
        if (
            not handler_func_name
            or not handler_func_name[0].isalpha()
            and handler_func_name[0] != "_"
        ):
            handler_func_name = f"handler_{int(time.time_ns())}"

        # Construct the prompt for the LLM
        prompt = f"""
Generate a Python function suitable for use as a Quantum Orchestrator handler.
The function should implement the following capability: "{description}"

Guidelines:
1. Define a single function named `{handler_func_name}`.
2. The function MUST accept a single argument: `params: Dict[str, Any]`. Access required inputs via `params.get("key_name", default_value)`.
3. The function MUST return a dictionary containing at least a key `'success': True` on success or `'success': False` and `'error': 'message'` on failure. It can include other relevant data under a 'result' key.
4. Include necessary standard library imports (e.g., `os`, `json`, `requests`, `logging`). Do NOT import non-standard libraries unless essential.
5. Include basic error handling using `try...except Exception as e:`. Log errors using `logger.error()` and return `{{'success': False, 'error': str(e)}}`.
6. Add a concise Python docstring explaining the function's purpose.
7. Ensure the generated code is syntactically correct Python 3.11+.
8. IMPORTANT: Decorate the function with `@handler(name="{handler_func_name}", description="{description}")`. Ensure the `handler` decorator is imported (`from quantum_orchestrator.handlers import handler`).
9. Add basic logging using `logger = logging.getLogger(__name__)`.

Example Structure:
```python
import logging
from typing import Dict, Any
from quantum_orchestrator.handlers import handler

logger = logging.getLogger(__name__)

@handler(name="{handler_func_name}", description="{description}")
def {handler_func_name}(params: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Handler Docstring based on description.\"\"\"
    logger = logging.getLogger(__name__) # Get logger inside function if needed
    try:
        # --- Implement core logic here ---
        input_val = params.get("example_param", "default")
        logger.info(f"Executing {handler_func_name} with example_param: {{input_val}}")
        result_data = f"Processed: {{input_val}}"
        # --- End core logic ---
        return {{"success": True, "result": result_data}}
    except Exception as e:
        logger.error(f"Error in {handler_func_name}: {{e}}", exc_info=True)
        return {{"success": False, "error": str(e)}}
Generate only the Python code for the handler function, including necessary imports and the decorator.
"""

        try:
            # Use the LLM service to generate the code
            generated_code = await self.llm_service.generate_code(prompt)

            if not generated_code:
                logger.error("LLM service returned empty code for tool generation.")
                return None

            # Basic validation/cleanup
            generated_code = generated_code.strip()
            # Add decorator if LLM likely missed it
            if (
                f'@handler(name="{handler_func_name}"' not in generated_code
                and f"def {handler_func_name}" in generated_code
            ):
                generated_code = f'@handler(name="{handler_func_name}", description="{description}")\n{generated_code}'
                logger.info(f"Added missing @handler decorator for {handler_func_name}")
            # Ensure necessary imports are present (basic check)
            if "import logging" not in generated_code:
                generated_code = f"import logging\n{generated_code}"
            if (
                "from quantum_orchestrator.handlers import handler"
                not in generated_code
            ):
                generated_code = f"from quantum_orchestrator.handlers import handler\n{generated_code}"

            logger.info(f"Successfully generated tool code for: {handler_func_name}")
            return generated_code

        except Exception as e:
            logger.error(f"Error during tool generation LLM call: {e}", exc_info=True)
            return None
