import subprocess
from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_llm(self):
        pass


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = "gemma2:9b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def get_llm(self):
        from crewai import LLM
        return LLM(model=f"ollama/{self.model}", base_url=self.base_url)


def get_available_models() -> list[str]:
    """Run `ollama list` and return a list of model name strings."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
