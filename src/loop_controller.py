import time
from crewai import Task, Crew

from src.agent_factory import AgentFactory
from src.llm_provider import OllamaProvider
from src.project_manager import ProjectManager

INBOX_CHUNK_SIZE = 10000


def _split_into_chunks(text: str, chunk_size: int = INBOX_CHUNK_SIZE) -> list[str]:
    """Split text at paragraph boundaries, keeping each chunk under chunk_size."""
    if len(text) <= chunk_size:
        return [text]
    paragraphs = text.split("\n\n")
    chunks = []
    current = []
    current_len = 0
    for para in paragraphs:
        if current_len + len(para) + 2 > chunk_size and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _run_crew(agent, task_description: str, max_retries: int = 3) -> str:
    task = Task(description=task_description, agent=agent, expected_output="A detailed text response")
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    delay = 2
    for attempt in range(max_retries):
        try:
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            err = str(e).lower()
            if "connect" in err or "timeout" in err or "connection" in err:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            raise
    raise ConnectionError("Please check the Ollama server (failed after 3 attempts).")


class ManualLoopController:
    def __init__(self, project_folder: str):
        self.project_folder = project_folder
        self.pm = ProjectManager()
        self.factory = AgentFactory()
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            config = self.pm.load_project(self.project_folder)
            provider = OllamaProvider(
                model=config.get("llm_model", "gemma2:9b"),
                base_url="http://localhost:11434",
            )
            self._llm = provider.get_llm()
        return self._llm

    def invalidate_llm(self):
        """Call this when model settings change."""
        self._llm = None

    def run_init_editor(self, user_message: str, chat_history: list, project_folder: str) -> str:
        """Run Editor agent for initialization stage. Returns response string."""
        llm = self._get_llm()
        context = self.pm.read_context_files(project_folder)
        agent = self.factory.create_editor_agent(llm, context)

        # Build conversation history for context
        history_text = ""
        if chat_history:
            history_lines = []
            for msg in chat_history[-10:]:  # last 10 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_lines.append(f"[{role}]: {content}")
            history_text = "\n".join(history_lines) + "\n\n"

        task_description = (
            f"{history_text}"
            f"The user says: {user_message}\n\n"
            "Continue the initialization conversation. Ask focused questions to help build out "
            "the novel's worldbuilding, plot, and character settings. "
            "If information seems complete enough, acknowledge it and suggest what might still be missing. "
            "Respond in Korean."
        )
        return _run_crew(agent, task_description)

    def run_init_editor_summary(self, chat_history: list, project_folder: str) -> str:
        """Generate a full summary when user clicks [Coordination Complete]."""
        llm = self._get_llm()
        context = self.pm.read_context_files(project_folder)
        agent = self.factory.create_editor_agent(llm, context)

        history_lines = []
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_lines.append(f"[{role}]: {content}")
        history_text = "\n".join(history_lines)

        task_description = (
            f"The following is the full conversation log from the initialization stage:\n\n"
            f"{history_text}\n\n"
            "The user has clicked [Coordination Complete]. "
            "Please output a comprehensive, well-structured summary of ALL finalized content discussed, including:\n"
            "- Worldbuilding details\n"
            "- Plot overview and key events\n"
            "- Characters (names, roles, abilities, relationships)\n"
            "- Rules and special settings\n"
            "- Any other confirmed details\n\n"
            "Format this as a clear, structured document in Korean that will be handed to the Recorder agent."
        )
        return _run_crew(agent, task_description)

    def run_init_recorder(self, summary: str, project_folder: str) -> dict:
        """Run Recorder agent. Returns dict with 5-file content."""
        llm = self._get_llm()
        context = self.pm.read_context_files(project_folder)
        agent = self.factory.create_recorder_agent(llm, context)

        task_description = (
            f"Based on the following coordination summary, generate all 5 initial project documents.\n\n"
            f"SUMMARY:\n{summary}\n\n"
            "Generate exactly these 5 documents. Use the following exact section markers:\n\n"
            "=== 세계관.md ===\n"
            "(worldbuilding content here)\n\n"
            "=== 줄거리.md ===\n"
            "(plot overview content here)\n\n"
            "=== 소설설정.md ===\n"
            "(characters, abilities, rules content here)\n\n"
            "=== story_context.md ===\n"
            "(leave this as a placeholder with empty sections for future use)\n\n"
            "=== character_relations.md ===\n"
            "(initial character knowledge state based on the summary)\n\n"
            "Write all content in Korean. Be thorough and well-structured."
        )
        raw = _run_crew(agent, task_description)
        return _parse_recorder_output(raw)

    def run_inbox_file(self, file_content: str, filename: str, chat_history: list, project_folder: str) -> tuple[str, bool]:
        """Pass an inbox file to the Editor. Returns (response, was_split)."""
        chunks = _split_into_chunks(file_content)
        was_split = len(chunks) > 1

        responses = []
        for i, chunk in enumerate(chunks):
            llm = self._get_llm()
            context = self.pm.read_context_files(project_folder)
            agent = self.factory.create_editor_agent(llm, context)

            chunk_label = f" (part {i+1}/{len(chunks)})" if was_split else ""
            task_description = (
                f"The user has loaded an idea file named '{filename}'{chunk_label}.\n\n"
                f"FILE CONTENT:\n{chunk}\n\n"
                "Please read and acknowledge this content. Extract any useful worldbuilding, "
                "plot, or character information. Ask clarifying questions if anything is unclear "
                "or if there are gaps. Respond in Korean."
            )
            response = _run_crew(agent, task_description)
            responses.append(response)

        return "\n\n---\n\n".join(responses), was_split

    def run_writing_loop(self, *args, **kwargs):
        """Stub for Phase 2."""
        raise NotImplementedError("Writing loop is not implemented in Phase 1.")


def _parse_recorder_output(raw: str) -> dict:
    """Parse the Recorder's output into a dict of {key: content}."""
    sections = {
        "세계관": "",
        "줄거리": "",
        "소설설정": "",
        "story_context": "",
        "character_relations": "",
    }
    markers = {
        "=== 세계관.md ===": "세계관",
        "=== 줄거리.md ===": "줄거리",
        "=== 소설설정.md ===": "소설설정",
        "=== story_context.md ===": "story_context",
        "=== character_relations.md ===": "character_relations",
    }
    # Find each section
    order = list(markers.keys())
    for i, marker in enumerate(order):
        key = markers[marker]
        start = raw.find(marker)
        if start == -1:
            continue
        start += len(marker)
        # Find the next marker
        end = len(raw)
        for next_marker in order[i+1:]:
            pos = raw.find(next_marker, start)
            if pos != -1:
                end = pos
                break
        sections[key] = raw[start:end].strip()
    return sections
