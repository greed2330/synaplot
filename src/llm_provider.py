import logging
import subprocess
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


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
        logger.info("LLM 생성: ollama/%s @ %s", self.model, self.base_url)
        return LLM(model=f"ollama/{self.model}", base_url=self.base_url)


def get_available_models() -> list[str]:
    logger.debug("ollama list 실행 중...")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("ollama list 실패 (returncode=%d)", result.returncode)
            return []
        lines = result.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        logger.info("사용 가능한 모델: %s", models)
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        logger.warning("ollama 감지 실패: %s", e)
        return []
