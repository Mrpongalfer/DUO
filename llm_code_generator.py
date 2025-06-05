# file: duo/llm_code_generator.py
import argparse
import json
import os
import sys
from pathlib import Path
import httpx # Assuming httpx is installed in your environment
import time # For potential future use with retries

# --- Configuration ---
# These should ideally match or be configurable like in Scribe/Ex-Work
# For simplicity, using fixed values here, but can be enhanced.
DEFAULT_OLLAMA_MODEL = "gemma:2b"  # Or another capable code generation model
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_REQUEST_TIMEOUT = 300.0  # Seconds

class CodeGeneratorLLMClient:
    def __init__(self, model: str = DEFAULT_OLLAMA_MODEL, api_url: str = OLLAMA_API_URL, timeout: float = OLLAMA_REQUEST_TIMEOUT):
        self.model = model
        self.api_url = api_url
        self.timeout = timeout
        self.logger = logging.getLogger("CodeGeneratorLLMClient") # Using standard logging
        self.logger.info(f"LLM Client for Code Generator initialized. Model: {self.model}, URL: {self.api_url}")

    def _call_ollama_api(self, prompt_text: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt_text,
            "stream": False
        }
        self.logger.debug(f"Sending prompt to Ollama (first 200 chars): {prompt_text[:200]}...")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.api_url, json=payload)
                response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
            
            response_data = response.json()
            if "response" in response_data:
                self.logger.info("Successfully received code generation response from Ollama.")
                return response_data["response"].strip()
            else:
                self.logger.error(f"Ollama API response missing 'response' key. Full response: {response_data}")
                return "" # Return empty on unexpected format
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Ollama API HTTP error: {e.response.status_code} - {e.response.text}")
            return ""
        except httpx.RequestError as e:
            self.logger.error(f"Ollama API request error: {e}")
            return ""
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON response from Ollama: {e}")
            return ""


    def _extract_raw_code(self, llm_response_text: str) -> str:
        """
        Extracts Python code from LLM response text, assuming LLM is instructed
        to ONLY return raw code. Removes common markdown fences if present.
        """
        self.logger.debug("Attempting to extract raw code from LLM response...")
        
        # Basic check for markdown code fences
        if llm_response_text.startswith("```python") and llm_response_text.endswith("```"):
            code = llm_response_text[len("```python"):-len("```")].strip()
            self.logger.debug("Removed '```python' fences.")
            return code
        if llm_response_text.startswith("```") and llm_response_text.endswith("```"):
            code = llm_response_text[len("```"):-len("```")].strip()
            self.logger.debug("Removed generic '```' fences.")
            return code
        
        # If no fences, assume the whole response is code (as per prompt instructions)
        self.logger.debug("No code fences found, using entire response as code.")
        return llm_response_text # Already stripped by _call_ollama_api

    def generate_improved_code(self, original_code: str, improvement_suggestion: str) -> str:
        prompt_template = (
            "You are an expert Python programmer tasked with refactoring code based on a specific suggestion.\n"
            "Given the original Python code and an improvement suggestion, rewrite the ENTIRE original code block, "
            "incorporating ONLY the suggested improvement. \n"
            "VERY IMPORTANT: Your output MUST BE ONLY the complete, new Python code. Do NOT include any explanations, "
            "markdown formatting (like ```python or ```), introductory phrases, or concluding remarks. "
            "Just the raw, modified Python code block.\n\n"
            "ORIGINAL CODE:\n"
            "------------------------------------\n"
            "{original_code}\n"
            "------------------------------------\n\n"
            "IMPROVEMENT SUGGESTION:\n"
            "{suggestion}\n\n"
            "REWRITTEN PYTHON CODE (raw code only):\n"
        )
        
        prompt = prompt_template.format(original_code=original_code, suggestion=improvement_suggestion)
        
        generated_text = self._call_ollama_api(prompt)
        if not generated_text:
            self.logger.error("LLM returned no text for code generation.")
            return "" # Return empty string on failure

        # The prompt asks for raw code, but we can still run a light cleanup
        clean_code = self._extract_raw_code(generated_text)
        return clean_code

def main():
    # Setup basic logging for the script itself
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s [%(levelname)s] - %(message)s')
    logger = logging.getLogger("LLMCodeGeneratorScript")

    parser = argparse.ArgumentParser(description="Generates improved Python code using an LLM based on an original script and a suggestion.")
    parser.add_argument("original_code_file_path", type=str, help="Path to the Python file containing the original code.")
    parser.add_argument("improvement_suggestion", type=str, help="The suggestion for how to improve the code.")
    parser.add_argument("output_code_file_path", type=str, help="Path where the newly generated Python code will be saved.")
    parser.add_argument("--model", type=str, default=DEFAULT_OLLAMA_MODEL, help="Ollama model to use for code generation.")
    
    args = parser.parse_args()

    logger.info(f"Reading original code from: {args.original_code_file_path}")
    try:
        with open(args.original_code_file_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
    except FileNotFoundError:
        logger.error(f"Error: Original code file not found at '{args.original_code_file_path}'")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading original code file: {e}")
        sys.exit(1)

    logger.info(f"Improvement suggestion: \"{args.improvement_suggestion}\"")
    logger.info(f"Using LLM model: {args.model}")

    client = CodeGeneratorLLMClient(model=args.model)
    new_code = client.generate_improved_code(original_code, args.improvement_suggestion)

    if new_code and new_code.strip(): # Check if new_code is not empty
        logger.info(f"Saving newly generated code to: {args.output_code_file_path}")
        try:
            with open(args.output_code_file_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            logger.info("Code generation successful.")
            sys.exit(0) # Success
        except Exception as e:
            logger.error(f"Error writing new code to file: {e}")
            sys.exit(1)
    else:
        logger.error("Failed to generate new code (LLM returned empty or failed).")
        # Outputting the (empty) new_code file can sometimes be useful for debugging the orchestrator
        # to see that the file was indeed created but empty.
        try:
            with open(args.output_code_file_path, 'w', encoding='utf-8') as f:
                f.write("# LLM Code Generation Failed: No code returned.\n")
        except Exception:
            pass # Ignore if even writing the failure message fails
        sys.exit(1) # Failure

if __name__ == "__main__":
    main()