# file: duo/vectorize_constitution.py
# (Updated to recursively scan subdirectories)
import json
import os
import sys
from pathlib import Path
import numpy as np
import httpx

# --- Configuration ---
# The location of your Nexus Edict Repository.
# It will use the NER_PATH environment variable if set, 
# otherwise defaults to "Rules" relative to this script's location.
NER_ABSOLUTE_PATH="/home/pong/Projects/games/NPTPAC/ner_repository"

NER_PATH_FROM_ENV = os.getenv("NER_PATH")
# Use the user's previously specified absolute path if NER_PATH_FROM_ENV is not set
# Defaulting to a local "Rules" directory if neither is set.
NER_RULES_DIR = NER_PATH_FROM_ENV if NER_PATH_FROM_ENV else \
    os.getenv("NER_ABSOLUTE_PATH", "/home/pong/Projects/games/NPTPAC/ner_repository") if os.getenv("NER_ABSOLUTE_PATH") else \
    "Rules"


VECTORS_OUTPUT_DIR = "goal_vectors"  # Still relative to where this script is run
EMBEDDING_MODEL = "mxbai-embed-large:latest" 
OLLAMA_API_URL = "http://localhost:11434/api/embeddings"


class ConstitutionVectorizer:
    """
    Reads foundational documents from a directory (and its subdirectories),
    generates vector embeddings for each, and saves them.
    """
    def __init__(self, rules_dir: str, output_dir: str):
        self.rules_dir = Path(rules_dir).resolve() # Resolve to absolute path
        self.output_dir = Path(output_dir).resolve() # Resolve to absolute path
        self.output_dir.mkdir(parents=True, exist_ok=True) # parents=True in case output_dir is nested
        print(f"[VECTORIZER] Reading constitution from: {self.rules_dir}")
        print(f"[VECTORIZER] Saving goal vectors to: {self.output_dir}")

    def get_embedding(self, text: str) -> np.ndarray | None:
        """Generates an embedding for a given text using the Ollama API."""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    OLLAMA_API_URL,
                    json={"model": EMBEDDING_MODEL, "prompt": text}
                )
                response.raise_for_status()
            
            embedding_data = response.json().get("embedding")
            if embedding_data:
                return np.array(embedding_data, dtype=np.float32)
            else:
                print(f"Warning: API response did not contain an embedding for a document.", file=sys.stderr)
                return None
        except httpx.RequestError as e:
            print(f"Error: Ollama API request failed: {e}", file=sys.stderr)
            print(f"Please ensure your Ollama server is running and the model '{EMBEDDING_MODEL}' is available.", file=sys.stderr)
            return None
        except (json.JSONDecodeError, KeyError):
            print(f"Error: Failed to parse JSON response from Ollama API.", file=sys.stderr)
            return None

    def sanitize_path_for_filename(self, path_segment: str) -> str:
        """Replaces common path separators and problematic characters with underscores."""
        # Replace path separators (OS-agnostic)
        path_segment = path_segment.replace(os.sep, '_')
        # Replace other problematic characters (e.g., spaces, periods before suffix)
        # For simplicity, we'll replace non-alphanumeric (excluding underscore) with underscore
        return "".join(c if c.isalnum() else '_' for c in path_segment)

    def vectorize_all_documents(self):
        """
        Iterates through all .md files in the rules directory and its subdirectories, 
        creating a separate Goal Vector for each one.
        """
        if not self.rules_dir.is_dir():
            print(f"Error: Rules directory not found at '{self.rules_dir}'", file=sys.stderr)
            sys.exit(1)

        print("\n--- Starting Vectorization Process (Recursive Scan) ---")
        # Use rglob to find all .md files recursively
        found_files = list(self.rules_dir.rglob("*.md"))
        if not found_files:
            print(f"Warning: No markdown files found in '{self.rules_dir}' or its subdirectories. No vectors will be generated.", file=sys.stderr)
            return

        for doc_path in found_files:
            print(f"\nProcessing '{doc_path.relative_to(self.rules_dir.parent)}'...") # Show relative path from base
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    print(f"Skipping empty file: {doc_path.name}")
                    continue

                embedding = self.get_embedding(content)
                
                if embedding is not None:
                    # Create a unique filename based on its relative path from NER_RULES_DIR root
                    relative_path = doc_path.relative_to(self.rules_dir)
                    # Combine parent directory names and the file stem for uniqueness
                    if relative_path.parent != Path('.'): # If it's in a subdirectory
                        path_prefix = self.sanitize_path_for_filename(str(relative_path.parent))
                        file_stem_sanitized = self.sanitize_path_for_filename(doc_path.stem)
                        vector_filename_base = f"{path_prefix}_{file_stem_sanitized}"
                    else: # If it's in the root of NER_RULES_DIR
                        vector_filename_base = self.sanitize_path_for_filename(doc_path.stem)
                    
                    vector_filename = f"goal_{vector_filename_base.lower()}.npy"
                    output_path = self.output_dir / vector_filename
                    
                    np.save(output_path, embedding)
                    print(f"Success! Saved vector to '{output_path}'")

            except Exception as e:
                print(f"Failed to process {doc_path.name}: {e}", file=sys.stderr)
        
        print("\n--- Vectorization Process Complete ---")

def main():
    """Main execution function."""
    # You can set the NER_ABSOLUTE_PATH environment variable if you prefer
    # export NER_ABSOLUTE_PATH="/home/pong/Projects/games/NPTPAC/ner_repository"
    # For this example, I'm keeping the script's logic for NER_RULES_DIR resolution.
    
    # If using Option 1 from previous suggestion (hardcoded absolute path):
    NER_RULES_DIR_TO_USE = "/home/pong/Projects/games/NPTPAC/ner_repository"
    
    # Using the script's built-in logic for NER_RULES_DIR:
    # NER_RULES_DIR_TO_USE = Path(NER_RULES_DIR).expanduser().resolve()


    print(f"Resolved NER Rules Directory to: {NER_RULES_DIR_TO_USE}")

    vectorizer = ConstitutionVectorizer(rules_dir=str(NER_RULES_DIR_TO_USE), output_dir=VECTORS_OUTPUT_DIR)
    vectorizer.vectorize_all_documents()

if __name__ == "__main__":
    main()
