import requests
import os


class OllamaInterfaceAgent:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.environ.get(
            "OLLAMA_URL", "http://localhost:11434"
        )

    def query(self, prompt, model="llama3"):
        r = requests.post(
            f"{self.base_url}/api/generate", json={"model": model, "prompt": prompt}
        )
        r.raise_for_status()
        return r.json().get("response", "")


def query_llama(prompt, context, memory, knowledge):
    agent = OllamaInterfaceAgent()
    full_prompt = (
        f"Context: {context}\nMemory: {memory}\nKnowledge: {knowledge}\nUser: {prompt}"
    )
    return agent.query(full_prompt)
