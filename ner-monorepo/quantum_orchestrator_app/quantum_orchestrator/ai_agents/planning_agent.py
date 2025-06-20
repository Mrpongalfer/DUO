"""
PlanningAgent: AI agent responsible for planning and workflow design.

Part of the Cognitive Fusion Core, responsible for task planning, workflow
design, and resource allocation based on user intents and available tools.
"""

import json
import time
import re
import uuid
from typing import Dict, Any, List

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.services.llm_service import (
    generate_completion_async,
)
from quantum_orchestrator.utils.quantum_optimization import optimize_workflow

logger = get_logger(__name__)


class PlanningAgent:
    """
    PlanningAgent: Responsible for planning and workflow design.

    Translates high-level user intents into executable workflows using
    available tools, handlers, and services. Uses advanced natural language
    understanding to break down complex requests and design optimized execution plans.
    """

    def __init__(self, orchestrator: Any):
        """
        Initialize the PlanningAgent.

        Args:
            orchestrator: The central Orchestrator instance
        """
        self.orchestrator = orchestrator
        self.recent_plans = []
        self.recent_workflows = []
        self.intent_templates = self._load_intent_templates()
        self.logger = get_logger(__name__)
        self.logger.info("PlanningAgent initialized")

    def _load_intent_templates(self) -> Dict[str, Any]:
        """Load intent recognition templates."""
        # In a real implementation, this would load from a file or database
        return {
            "data_processing": [
                "process",
                "analyze",
                "compute",
                "calculate",
                "transform",
                "filter",
                "clean",
                "extract",
            ],
            "content_generation": [
                "create",
                "generate",
                "write",
                "compose",
                "design",
                "produce",
                "draft",
            ],
            "knowledge_retrieval": [
                "find",
                "search",
                "retrieve",
                "lookup",
                "get",
                "fetch",
                "query",
            ],
            "workflow_management": [
                "run",
                "execute",
                "schedule",
                "automate",
                "orchestrate",
                "manage",
                "track",
            ],
            "cognitive_processing": [
                "understand",
                "learn",
                "reason",
                "infer",
                "classify",
                "predict",
                "assess",
            ],
            "integration": [
                "connect",
                "integrate",
                "link",
                "combine",
                "merge",
                "sync",
                "interface",
            ],
        }

    async def analyze_intent(self, user_intent: str) -> Dict[str, Any]:
        """
        Analyze a user intent to identify key components and requirements.

        This method uses natural language understanding to break down a user intent
        into actionable components, identifying required tools, data, and operations.

        Args:
            user_intent: The natural language intent provided by the user

        Returns:
            Dict containing analysis results including intent type, entities, and required tools
        """
        self.logger.info(f"Analyzing intent: {user_intent}")

        # Create a prompt for the LLM to analyze the intent
        system_prompt = """You are a specialized AI assistant that analyzes user intentions to identify key components for an AI orchestration system to execute.
        Precisely parse the input to extract:

        1. Primary Intent Type(s): What is the user trying to accomplish?
        2. Required Data/Entities: What data, inputs, resources or entities are required?
        3. Actions/Operations: What operations need to be performed?
        4. Constraints/Parameters: Are there any specific requirements or constraints?
        5. Dependencies: What sequential dependencies exist between operations?
        6. Expected Output: What result is the user expecting?

        Format your response as a JSON object with these components as keys.
        """

        # Combine system prompt with user intent
        prompt = f"{system_prompt}\n\nUser Intent: {user_intent}"

        try:
            # Call LLM service to analyze intent
            response = await generate_completion_async(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for more deterministic analysis
                max_tokens=1500,
            )

            # Extract and parse JSON from the response
            json_match = re.search(r"{.*}", response, re.DOTALL)
            if json_match:
                intent_analysis = json.loads(json_match.group(0))
            else:
                # Fallback parsing for non-JSON responses
                intent_analysis = self._extract_structured_analysis(response)

            # Determine intent category
            intent_category = self._categorize_intent(user_intent, intent_analysis)
            intent_analysis["intent_category"] = intent_category

            # Determine required tools
            required_tools = await self._identify_required_tools(intent_analysis)
            intent_analysis["required_tools"] = required_tools

            # Evaluate complexity
            complexity = self._evaluate_complexity(intent_analysis)
            intent_analysis["complexity"] = complexity

            self.logger.info(
                f"Intent analysis complete. Type: {intent_category}, Complexity: {complexity}"
            )

            return intent_analysis

        except Exception as e:
            self.logger.error(f"Error analyzing intent: {str(e)}")

            # Fallback basic analysis
            return {
                "intent_category": "unknown",
                "required_data": [],
                "actions": [{"action": "process", "target": "intent"}],
                "constraints": [],
                "dependencies": [],
                "expected_output": "processed result",
                "complexity": "medium",
                "error": str(e),
            }

    def _extract_structured_analysis(self, text: str) -> Dict[str, Any]:
        """Extract structured analysis from text."""
        # Basic extraction for fallback cases
        analysis = {
            "primary_intent": [],
            "required_data": [],
            "actions": [],
            "constraints": [],
            "dependencies": [],
            "expected_output": "",
        }

        # Extract sections
        sections = {
            "primary_intent": r"(?:Primary Intent|Intent Type)[^:]*:(.*?)(?:\n\d|\n\n|$)",
            "required_data": r"(?:Required Data|Entities)[^:]*:(.*?)(?:\n\d|\n\n|$)",
            "actions": r"(?:Actions|Operations)[^:]*:(.*?)(?:\n\d|\n\n|$)",
            "constraints": r"(?:Constraints|Parameters)[^:]*:(.*?)(?:\n\d|\n\n|$)",
            "dependencies": r"(?:Dependencies)[^:]*:(.*?)(?:\n\d|\n\n|$)",
            "expected_output": r"(?:Expected Output|Result)[^:]*:(.*?)(?:\n\d|\n\n|$)",
        }

        for key, pattern in sections.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if key == "actions":
                    # Parse actions into structured format
                    action_items = []
                    for action in re.findall(r"[^,;.]+", content):
                        action = action.strip()
                        if action:
                            # Try to extract verb and target
                            verb_match = re.search(r"(\w+)", action)
                            verb = verb_match.group(1) if verb_match else "process"
                            action_items.append({"action": verb, "target": action})
                    analysis[key] = action_items
                else:
                    # Split by common delimiters
                    items = [
                        item.strip()
                        for item in re.split(r"[,;.]", content)
                        if item.strip()
                    ]
                    analysis[key] = items if key != "expected_output" else content

        return analysis

    def _categorize_intent(
        self, user_intent: str, intent_analysis: Dict[str, Any]
    ) -> str:
        """Categorize the user intent based on keyword matching and analysis."""
        user_intent_lower = user_intent.lower()

        # Count matches for each intent category
        category_matches = {}

        for category, keywords in self.intent_templates.items():
            match_count = 0
            for keyword in keywords:
                if re.search(r"\b" + re.escape(keyword) + r"\b", user_intent_lower):
                    match_count += 1

            if match_count > 0:
                category_matches[category] = match_count

        # Also check action verbs in the analysis
        actions = intent_analysis.get("actions", [])
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, dict) and "action" in action:
                    action_verb = action["action"].lower()
                    for category, keywords in self.intent_templates.items():
                        if action_verb in keywords:
                            category_matches[category] = (
                                category_matches.get(category, 0) + 2
                            )  # Higher weight for actions

        # Determine primary category
        if category_matches:
            primary_category = max(category_matches.items(), key=lambda x: x[1])[0]
        else:
            # Default to cognitive processing if no matches
            primary_category = "cognitive_processing"

        return primary_category

    async def _identify_required_tools(
        self, intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify tools required to fulfill the intent."""
        # Get available tools from orchestrator
        available_tools = self.orchestrator.get_available_tools()

        # Extract key elements from intent analysis
        intent_category = intent_analysis.get("intent_category", "")
        primary_intent = intent_analysis.get("primary_intent", [])
        actions = intent_analysis.get("actions", [])

        # Convert to strings for easier matching
        if isinstance(primary_intent, list):
            primary_intent = " ".join(primary_intent)

        action_text = ""
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, dict):
                    action_text += (
                        f"{action.get('action', '')} {action.get('target', '')} "
                    )
                else:
                    action_text += f"{action} "

        # Combine text for matching
        matching_text = f"{intent_category} {primary_intent} {action_text}"

        # Match tools based on descriptions and capabilities
        matched_tools = []

        for tool_id, tool_info in available_tools.items():
            tool_name = tool_info.get("name", "")
            tool_description = tool_info.get("description", "")
            tool_capabilities = tool_info.get("capabilities", [])

            # Convert capabilities to string
            capabilities_text = (
                " ".join(tool_capabilities)
                if isinstance(tool_capabilities, list)
                else str(tool_capabilities)
            )

            # Simple keyword matching
            match_score = 0

            # Check tool name and description
            if tool_name and any(
                word in tool_name.lower() for word in matching_text.lower().split()
            ):
                match_score += 2

            if tool_description:
                for word in matching_text.lower().split():
                    if word in tool_description.lower():
                        match_score += 1

            # Check capabilities
            if capabilities_text:
                for word in matching_text.lower().split():
                    if word in capabilities_text.lower():
                        match_score += 3  # Higher weight for capability matches

            if match_score > 0:
                matched_tools.append(
                    {"tool_id": tool_id, "name": tool_name, "match_score": match_score}
                )

        # Sort by match score
        matched_tools.sort(key=lambda x: x["match_score"], reverse=True)

        # For more complex scenarios, use LLM to identify required tools
        if (
            intent_analysis.get("complexity", "medium") in ["high", "very_high"]
            and len(matched_tools) < 2
        ):
            llm_tools = await self._llm_tool_selection(intent_analysis, available_tools)

            # Merge LLM-selected tools with matched tools
            existing_ids = {tool["tool_id"] for tool in matched_tools}
            for tool in llm_tools:
                if tool["tool_id"] not in existing_ids:
                    matched_tools.append(tool)

            # Re-sort
            matched_tools.sort(key=lambda x: x["match_score"], reverse=True)

        # Limit to top matches
        return matched_tools[:5]

    async def _llm_tool_selection(
        self, intent_analysis: Dict[str, Any], available_tools: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to select appropriate tools for complex intents."""
        # Create a prompt describing the intent and available tools
        tools_description = ""
        for tool_id, tool_info in available_tools.items():
            tools_description += f"- Tool ID: {tool_id}\n"
            tools_description += f"  Name: {tool_info.get('name', '')}\n"
            tools_description += f"  Description: {tool_info.get('description', '')}\n"
            tools_description += (
                f"  Capabilities: {', '.join(tool_info.get('capabilities', []))}\n\n"
            )

        # Format intent analysis
        intent_summary = json.dumps(intent_analysis, indent=2)

        prompt = f"""Given the following user intent analysis:

        {intent_summary}

        And these available tools:

        {tools_description}

        Select the most appropriate tools to fulfill this intent. For each tool, provide:
        1. The Tool ID
        2. A reason why this tool is appropriate
        3. A match score from 1-10

        Format your response as a JSON array of objects, each with tool_id, reason, and match_score keys.
        """

        try:
            # Call LLM service
            response = await generate_completion_async(
                prompt=prompt, temperature=0.3, max_tokens=1500
            )

            # Extract JSON from response
            json_match = re.search(r"\[\s*{.*}\s*\]", response, re.DOTALL)
            if json_match:
                selected_tools = json.loads(json_match.group(0))

                # Format and return selected tools
                formatted_tools = []
                for tool in selected_tools:
                    if "tool_id" in tool:
                        formatted_tools.append(
                            {
                                "tool_id": tool["tool_id"],
                                "name": available_tools.get(tool["tool_id"], {}).get(
                                    "name", ""
                                ),
                                "match_score": tool.get("match_score", 5),
                                "reason": tool.get("reason", ""),
                            }
                        )

                return formatted_tools

            else:
                # Fallback: extract tool IDs using regex
                tool_ids = re.findall(r"Tool ID: ([^\n]+)", response)
                return [
                    {
                        "tool_id": tool_id,
                        "name": available_tools.get(tool_id, {}).get("name", ""),
                        "match_score": 5,
                    }
                    for tool_id in tool_ids
                ]

        except Exception as e:
            self.logger.error(f"Error in LLM tool selection: {str(e)}")
            return []

    def _evaluate_complexity(self, intent_analysis: Dict[str, Any]) -> str:
        """Evaluate the complexity of an intent."""
        # Basic complexity scoring
        complexity_score = 0

        # Check number of actions
        actions = intent_analysis.get("actions", [])
        num_actions = len(actions) if isinstance(actions, list) else 1
        complexity_score += min(num_actions, 5)

        # Check dependencies
        dependencies = intent_analysis.get("dependencies", [])
        num_dependencies = len(dependencies) if isinstance(dependencies, list) else 0
        complexity_score += num_dependencies * 2

        # Check constraints
        constraints = intent_analysis.get("constraints", [])
        num_constraints = len(constraints) if isinstance(constraints, list) else 0
        complexity_score += num_constraints

        # Map score to complexity level
        if complexity_score <= 3:
            return "low"
        elif complexity_score <= 6:
            return "medium"
        elif complexity_score <= 10:
            return "high"
        else:
            return "very_high"

    async def design_workflow(
        self,
        user_intent: str,
        available_tools: Dict[str, Any],
        available_services: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Design a workflow based on user intent and available tools/services.

        This method performs advanced natural language understanding to break down
        complex user intents, maps them to available tools and services, and generates
        an optimized multi-step workflow with clear data flow and error handling.

        Args:
            user_intent: Natural language description of the user's intention
            available_tools: Dictionary of available tools/handlers
            available_services: Dictionary of available external services

        Returns:
            Dict containing the designed workflow and metadata
        """
        self.logger.info(f"Designing workflow for intent: {user_intent}")

        # Step 1: Analyze the user intent
        intent_analysis = await self.analyze_intent(user_intent)

        # Step 2: Create a detailed workflow description using LLM
        workflow_description = await self._generate_workflow_description(
            user_intent, intent_analysis, available_tools, available_services
        )

        # Step 3: Convert the description to structured workflow steps
        workflow_steps = await self._convert_to_workflow_steps(
            workflow_description, intent_analysis, available_tools, available_services
        )

        # Step 4: Apply quantum-inspired optimization to the workflow
        optimized_workflow = await self._optimize_workflow(
            workflow_steps, intent_analysis
        )

        # Step 5: Add error handling and monitoring
        final_workflow = self._add_error_handling(optimized_workflow)

        # Save the workflow for future reference
        workflow_id = str(uuid.uuid4())
        self.recent_workflows.append(
            {
                "id": workflow_id,
                "intent": user_intent,
                "steps": final_workflow,
                "created_at": time.time(),
            }
        )

        return {
            "workflow_id": workflow_id,
            "intent": user_intent,
            "intent_analysis": intent_analysis,
            "steps": final_workflow,
            "metadata": {
                "created_at": time.time(),
                "complexity": intent_analysis.get("complexity", "medium"),
                "tools_used": [
                    step.get("handler") for step in final_workflow if "handler" in step
                ],
                "services_used": [
                    step.get("service_id")
                    for step in final_workflow
                    if "service_id" in step
                ],
                "estimated_execution_time": self._estimate_execution_time(
                    final_workflow
                ),
            },
        }

    async def _generate_workflow_description(
        self,
        user_intent: str,
        intent_analysis: Dict[str, Any],
        available_tools: Dict[str, Any],
        available_services: Dict[str, Any],
    ) -> str:
        """Generate a detailed workflow description using LLM."""
        # Prepare tool descriptions
        tool_descriptions = "\n".join(
            [
                f"- {tool_info.get('name', '')}: {tool_info.get('description', '')}"
                for tool_id, tool_info in available_tools.items()
            ]
        )

        # Prepare service descriptions
        service_descriptions = "\n".join(
            [
                f"- {service_info.get('name', '')}: {service_info.get('description', '')}"
                for service_id, service_info in available_services.items()
            ]
        )

        # Create a prompt for the LLM
        system_prompt = """You are an expert workflow designer for an AI orchestration system.
        Your task is to create a detailed step-by-step workflow that fulfills the user's intent.

        For each step in the workflow, specify:
        1. The step's purpose
        2. The tool or service to use
        3. The input parameters
        4. The expected output
        5. Any dependencies on previous steps

        Design an efficient workflow that:
        - Breaks down complex tasks into logical steps
        - Handles data flow between steps clearly
        - Includes validation and error checking
        - Optimizes for performance and resource usage

        Your response should be a detailed description of the workflow steps, including the specific tools and services to use at each step.
        """

        intent_json = json.dumps(intent_analysis, indent=2)

        prompt = f"""{system_prompt}

USER INTENT:
{user_intent}

INTENT ANALYSIS:
{intent_json}

AVAILABLE TOOLS:
{tool_descriptions}

AVAILABLE SERVICES:
{service_descriptions}

Please design a detailed workflow to fulfill this intent.
"""

        try:
            # Call LLM service to generate workflow description
            response = await generate_completion_async(
                prompt=prompt, temperature=0.4, max_tokens=2000
            )

            return response

        except Exception as e:
            self.logger.error(f"Error generating workflow description: {str(e)}")
            return "Error generating workflow description"

    async def _convert_to_workflow_steps(
        self,
        workflow_description: str,
        intent_analysis: Dict[str, Any],
        available_tools: Dict[str, Any],
        available_services: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Convert a workflow description to structured steps."""
        # Create a prompt for the LLM to convert the description to structured steps
        system_prompt = """Convert the following workflow description into a structured JSON format.
        Each step should have the following properties:
        - id: A unique identifier for the step
        - name: A descriptive name for the step
        - description: What the step does
        - handler: The tool/handler to use (must match one of the available tools exactly)
        - parameters: An object containing the parameters for the handler
        - depends_on: An array of step IDs that this step depends on
        - error_handling: How to handle errors in this step

        Format your response as a valid JSON array of step objects.
        """

        # Format available tools and services
        tools_json = json.dumps(
            {
                tool_id: {
                    "name": info.get("name", ""),
                    "description": info.get("description", ""),
                }
                for tool_id, info in available_tools.items()
            },
            indent=2,
        )

        services_json = json.dumps(
            {
                service_id: {
                    "name": info.get("name", ""),
                    "description": info.get("description", ""),
                }
                for service_id, info in available_services.items()
            },
            indent=2,
        )

        prompt = f"""{system_prompt}

WORKFLOW DESCRIPTION:
{workflow_description}

AVAILABLE TOOLS:
{tools_json}

AVAILABLE SERVICES:
{services_json}

INTENT ANALYSIS:
{json.dumps(intent_analysis, indent=2)}

Convert to structured workflow steps:
"""

        try:
            # Call LLM service to convert description to structured steps
            response = await generate_completion_async(
                prompt=prompt, temperature=0.2, max_tokens=2000
            )

            # Extract and parse JSON from the response
            json_match = re.search(r"\[\s*{.*}\s*\]", response, re.DOTALL)
            if json_match:
                workflow_steps = json.loads(json_match.group(0))

                # Validate and enhance steps
                return self._validate_workflow_steps(
                    workflow_steps, available_tools, available_services
                )
            else:
                # Fallback: create basic steps
                self.logger.warning(
                    "Failed to extract JSON workflow steps, creating basic steps"
                )
                return self._create_basic_workflow_steps(
                    intent_analysis, available_tools, available_services
                )

        except Exception as e:
            self.logger.error(
                f"Error converting workflow description to steps: {str(e)}"
            )
            return self._create_basic_workflow_steps(
                intent_analysis, available_tools, available_services
            )

    def _validate_workflow_steps(
        self,
        workflow_steps: List[Dict[str, Any]],
        available_tools: Dict[str, Any],
        available_services: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Validate and enhance workflow steps."""
        # Track used IDs to avoid duplicates
        used_ids = set()

        for i, step in enumerate(workflow_steps):
            # Ensure each step has a unique ID
            if "id" not in step or step["id"] in used_ids:
                step["id"] = f"step_{i + 1}"

            used_ids.add(step["id"])

            # Ensure handler exists in available tools
            if "handler" in step:
                handler_name = step["handler"]
                if not any(
                    tool_info.get("name") == handler_name
                    for tool_info in available_tools.values()
                ):
                    # Try to find a matching handler
                    for tool_id, tool_info in available_tools.items():
                        if handler_name.lower() in tool_info.get("name", "").lower():
                            step["handler"] = tool_info.get("name", "")
                            break

            # Ensure service exists in available services
            if "service_id" in step:
                service_id = step["service_id"]
                if service_id not in available_services:
                    # Try to find a matching service
                    for avail_service_id, service_info in available_services.items():
                        if service_id.lower() in service_info.get("name", "").lower():
                            step["service_id"] = avail_service_id
                            break

            # Ensure parameters is a dictionary
            if "parameters" not in step or not isinstance(step["parameters"], dict):
                step["parameters"] = {}

            # Ensure depends_on is a list
            if "depends_on" not in step or not isinstance(step["depends_on"], list):
                step["depends_on"] = []

            # Add default error handling if not present
            if "error_handling" not in step:
                step["error_handling"] = "retry_once"

        return workflow_steps

    def _create_basic_workflow_steps(
        self,
        intent_analysis: Dict[str, Any],
        available_tools: Dict[str, Any],
        available_services: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Create basic workflow steps when structured conversion fails."""
        workflow_steps = []

        # Look for required tools in intent analysis
        required_tools = intent_analysis.get("required_tools", [])

        # If no specific tools were identified, select based on intent category
        if not required_tools:
            intent_category = intent_analysis.get("intent_category", "")

            # Map intent categories to relevant tool types
            category_tool_map = {
                "data_processing": ["filter", "transform", "clean", "analyze"],
                "content_generation": ["generate", "create", "compose"],
                "knowledge_retrieval": ["search", "retrieve", "query"],
                "workflow_management": ["execute", "schedule", "monitor"],
                "cognitive_processing": ["understand", "classify", "predict"],
                "integration": ["connect", "sync", "import"],
            }

            # Get relevant tool types for this intent category
            relevant_types = category_tool_map.get(intent_category, ["process"])

            # Find tools matching these types
            for tool_id, tool_info in available_tools.items():
                tool_name = tool_info.get("name", "").lower()
                if any(tool_type in tool_name for tool_type in relevant_types):
                    required_tools.append(
                        {
                            "tool_id": tool_id,
                            "name": tool_info.get("name", ""),
                            "match_score": 5,
                        }
                    )

        # Create steps based on required tools
        for i, tool in enumerate(required_tools[:3]):  # Limit to top 3 tools
            step = {
                "id": f"step_{i + 1}",
                "name": f"Use {tool.get('name', 'tool')}",
                "description": f"Process data using {tool.get('name', 'tool')}",
                "handler": tool.get("name", ""),
                "parameters": {},
                "depends_on": [f"step_{i}"] if i > 0 else [],
                "error_handling": "retry_once",
            }

            workflow_steps.append(step)

        # Add a final step to aggregate results if there are multiple steps
        if len(workflow_steps) > 1:
            final_step = {
                "id": f"step_{len(workflow_steps) + 1}",
                "name": "Aggregate results",
                "description": "Combine results from previous steps",
                "handler": "aggregate_results",
                "parameters": {},
                "depends_on": [step["id"] for step in workflow_steps],
                "error_handling": "continue",
            }

            workflow_steps.append(final_step)

        return workflow_steps

    async def _optimize_workflow(
        self, workflow_steps: List[Dict[str, Any]], intent_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply quantum-inspired optimization to the workflow."""
        # Only optimize if there are enough steps
        if len(workflow_steps) <= 2:
            return workflow_steps

        # Prepare optimization parameters based on intent complexity
        complexity = intent_analysis.get("complexity", "medium")

        optimization_params = {
            "optimization_objective": "balanced",
            "quantum_algorithm": "annealing",
            "constraints": {
                "max_iterations": 300 if complexity in ["high", "very_high"] else 100,
                "initial_temperature": 2.0,
                "cooling_rate": 0.95,
            },
        }

        # Use the quantum optimization module
        try:
            optimization_result = optimize_workflow(
                workflow_steps, **optimization_params
            )
            return optimization_result["optimized_workflow"]

        except Exception as e:
            self.logger.error(f"Error optimizing workflow: {str(e)}")
            return workflow_steps

    def _add_error_handling(
        self, workflow_steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add error handling and monitoring to workflow steps."""
        enhanced_steps = []

        # First pass: enhance each step with appropriate error handling
        for step in workflow_steps:
            enhanced_step = step.copy()

            # Add error handling if not already present
            if (
                "error_handling" not in enhanced_step
                or not enhanced_step["error_handling"]
            ):
                # Steps with no dependencies can use retry
                if not enhanced_step.get("depends_on"):
                    enhanced_step["error_handling"] = {
                        "strategy": "retry",
                        "max_retries": 3,
                        "backoff_factor": 2,
                    }
                # Steps with dependencies need more careful handling
                else:
                    enhanced_step["error_handling"] = {
                        "strategy": "conditional_retry",
                        "max_retries": 2,
                        "backoff_factor": 1.5,
                        "fallback": "skip",  # Skip if retries fail
                    }
            # Convert string error handling to object format
            elif isinstance(enhanced_step["error_handling"], str):
                strategy = enhanced_step["error_handling"]
                if strategy == "retry_once":
                    enhanced_step["error_handling"] = {
                        "strategy": "retry",
                        "max_retries": 1,
                    }
                elif strategy == "continue":
                    enhanced_step["error_handling"] = {"strategy": "continue_on_error"}
                else:
                    enhanced_step["error_handling"] = {"strategy": strategy}

            # Add monitoring
            if "monitoring" not in enhanced_step:
                enhanced_step["monitoring"] = {
                    "track_execution_time": True,
                    "log_level": "info",
                }

            enhanced_steps.append(enhanced_step)

        # Second pass: add monitoring wrapper and validation steps
        final_steps = []

        # Start with monitoring initialization
        monitor_start = {
            "id": "workflow_monitor_start",
            "name": "Initialize workflow monitoring",
            "description": "Set up monitoring for the workflow execution",
            "handler": "workflow_monitor",
            "parameters": {
                "action": "start",
                "workflow_id": str(uuid.uuid4()),
                "track_metrics": True,
            },
            "depends_on": [],
        }

        final_steps.append(monitor_start)

        # Add a validation step if the workflow has inputs
        validate_step = {
            "id": "input_validation",
            "name": "Validate inputs",
            "description": "Validate all workflow inputs before execution",
            "handler": "validate_inputs",
            "parameters": {"strict": False},
            "depends_on": ["workflow_monitor_start"],
            "error_handling": {
                "strategy": "fail_workflow",
                "message": "Input validation failed",
            },
        }

        final_steps.append(validate_step)

        # Add the enhanced steps, updating dependencies
        for step in enhanced_steps:
            updated_step = step.copy()

            # Update dependencies to include validation step
            depends_on = updated_step.get("depends_on", [])

            # If step had no dependencies, make it depend on validation
            if not depends_on:
                updated_step["depends_on"] = ["input_validation"]
            # Otherwise, make sure original dependencies are in the final workflow
            else:
                valid_depends = []
                for dep in depends_on:
                    # Keep dependency if it's in the final workflow
                    if (
                        dep == "workflow_monitor_start"
                        or dep == "input_validation"
                        or any(s["id"] == dep for s in enhanced_steps)
                    ):
                        valid_depends.append(dep)

                # If all dependencies were invalid, depend on validation
                if not valid_depends:
                    valid_depends = ["input_validation"]

                updated_step["depends_on"] = valid_depends

            final_steps.append(updated_step)

        # Add a final step to compile results
        result_step = {
            "id": "compile_results",
            "name": "Compile workflow results",
            "description": "Gather and format results from all workflow steps",
            "handler": "compile_results",
            "parameters": {"format": "json", "include_step_details": True},
            "depends_on": [step["id"] for step in enhanced_steps],
        }

        final_steps.append(result_step)

        # End with monitoring completion
        monitor_end = {
            "id": "workflow_monitor_end",
            "name": "Complete workflow monitoring",
            "description": "Finalize monitoring and record metrics",
            "handler": "workflow_monitor",
            "parameters": {
                "action": "end",
                "workflow_id": monitor_start["parameters"]["workflow_id"],
                "generate_report": True,
            },
            "depends_on": ["compile_results"],
        }

        final_steps.append(monitor_end)

        return final_steps

    def _estimate_execution_time(self, workflow_steps: List[Dict[str, Any]]) -> float:
        """Estimate the execution time for a workflow."""
        # Base time per step
        base_time_per_step = 1.0  # 1 second

        # Calculate critical path
        critical_path = self._calculate_critical_path(workflow_steps)

        # Sum execution time along critical path
        total_time = 0.0

        for step_id in critical_path:
            step = next((s for s in workflow_steps if s.get("id") == step_id), None)
            if step:
                # Get estimated duration or use base time
                step_time = step.get("estimated_duration", base_time_per_step)
                total_time += step_time

        return total_time

    def _calculate_critical_path(
        self, workflow_steps: List[Dict[str, Any]]
    ) -> List[str]:
        """Calculate the critical path through a workflow."""
        # Build dependency graph
        dependency_graph = {}

        for step in workflow_steps:
            step_id = step.get("id", "")
            if step_id:
                dependency_graph[step_id] = step.get("depends_on", [])

        # Find all leaf nodes (steps with no dependents)
        leaf_nodes = set(dependency_graph.keys())

        for dependencies in dependency_graph.values():
            for dep in dependencies:
                if dep in leaf_nodes:
                    leaf_nodes.remove(dep)

        # Find all root nodes (steps with no dependencies)
        root_nodes = []

        for step_id, dependencies in dependency_graph.items():
            if not dependencies:
                root_nodes.append(step_id)

        # Find the longest path from any root to any leaf
        longest_path = []
        longest_length = 0

        for root in root_nodes:
            for leaf in leaf_nodes:
                paths = self._find_all_paths(dependency_graph, root, leaf)
                for path in paths:
                    if len(path) > longest_length:
                        longest_length = len(path)
                        longest_path = path

        return longest_path

    def _find_all_paths(
        self, graph: Dict[str, List[str]], start: str, end: str, path: List[str] = None
    ) -> List[List[str]]:
        """Find all paths from start to end in a directed graph."""
        if path is None:
            path = []

        path = path + [start]

        if start == end:
            return [path]

        if start not in graph:
            return []

        paths = []
        for node in graph[start]:
            if node not in path:
                new_paths = self._find_all_paths(graph, node, end, path)
                for new_path in new_paths:
                    paths.append(new_path)

        return paths

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the planning agent.

        Returns:
            Dict containing status information
        """
        return {
            "status": "ready",
            "type": "planning",
            "recent_plans": len(self.recent_plans),
            "recent_workflows": len(self.recent_workflows),
        }

    async def consult_core_team(
        self, workflow_steps: List[Dict[str, Any]], intent_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Consult the Core Team archetypes for workflow improvements.

        Args:
            workflow_steps: Proposed workflow steps
            intent_analysis: Analysis of the user intent

        Returns:
            Dict containing improvements and insights from the Core Team
        """
        self.logger.info("Consulting Core Team for workflow improvements")

        # Get Core Team from orchestrator
        if hasattr(self.orchestrator, "core_team"):
            core_team = getattr(self.orchestrator, "core_team")

            try:
                # Prepare context for the Core Team
                context = {
                    "workflow_steps": workflow_steps,
                    "intent_analysis": intent_analysis,
                    "type": "workflow_review",
                }

                # Get insights from Core Team
                team_insights = await core_team.get_team_insights(context)

                # Return insights
                return {
                    "success": True,
                    "insights": team_insights,
                    "timestamp": time.time(),
                }

            except Exception as e:
                self.logger.error(f"Error consulting Core Team: {str(e)}")
                return {
                    "success": False,
                    "error": f"Core Team consultation failed: {str(e)}",
                    "timestamp": time.time(),
                }

        # If no Core Team is available
        return {
            "success": False,
            "error": "Core Team not available",
            "insights": [],
            "timestamp": time.time(),
        }
