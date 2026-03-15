import logging
import time
from crewai import Task, Crew

from src.agent_factory import AgentFactory
from src.llm_provider import OllamaProvider
from src.project_manager import ProjectManager

logger = logging.getLogger(__name__)

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
        logger.debug("crew.kickoff() 시도 %d/%d", attempt + 1, max_retries)
        try:
            result = crew.kickoff()
            logger.debug("crew.kickoff() 완료")
            return str(result)
        except Exception as e:
            err = str(e).lower()
            if "connect" in err or "timeout" in err or "connection" in err:
                if attempt < max_retries - 1:
                    logger.warning("Ollama 연결 실패 (시도 %d), %.1fs 후 재시도: %s", attempt + 1, delay, e)
                    time.sleep(delay)
                    delay *= 2
                    continue
            logger.error("crew.kickoff() 오류: %s", e)
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
        logger.info("[Editor] 초기화 대화 응답 생성 시작")
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
        logger.info("[Editor] 조율 완료 요약 생성 시작 (대화 %d건)", len(chat_history))
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
        logger.info("[Recorder] 초기 문서 생성 시작")
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
        parsed = _parse_recorder_output(raw)
        logger.info("[Recorder] 문서 생성 완료: %s", list(parsed.keys()))
        return parsed

    def run_inbox_file(self, file_content: str, filename: str, chat_history: list, project_folder: str) -> tuple[str, bool]:
        logger.info("[Editor] inbox 파일 처리: %s (%d자)", filename, len(file_content))
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

    def run_writer(self, user_input: str, chapter_number: int, project_folder: str) -> tuple[str, str]:
        logger.info("[Writer] %d화 집필 시작", chapter_number)
        llm = self._get_llm()
        context = self.pm.read_context_files(project_folder)
        agent = self.factory.create_writer_agent(llm, context)
        task_description = (
            f"지금은 {chapter_number}화를 작성할 차례입니다.\n\n"
            f"사용자 지시사항:\n{user_input}\n\n"
            "위의 지시사항과 프로젝트 설정을 바탕으로 이번 챕터의 소설 본문을 작성하세요.\n"
            "작성 후 반드시 아래 형식으로 출력하세요:\n\n"
            "=== 소설 본문 ===\n"
            "(본문 내용)\n\n"
            "=== 설계 의도 ===\n"
            "확정된 사실:\n"
            "- (이번 챕터에서 확정된 사실들)\n\n"
            "심은 복선:\n"
            "- (의도적으로 심은 복선, 없으면 '없음')\n\n"
            "설정 변경사항:\n"
            "- (기존 설정과 달라진 점, 없으면 '없음')\n"
        )
        raw = _run_crew(agent, task_description)
        body, intent = _parse_writer_output(raw)
        logger.info("[Writer] %d화 집필 완료 (본문 %d자)", chapter_number, len(body))
        return body, intent

    def run_editor_review(self, body_text: str, design_intent: str, user_input: str,
                          project_folder: str, is_revision: bool = False) -> str:
        logger.info("[Editor] 집필실 검토 시작 (수정 라운드: %s)", is_revision)
        llm = self._get_llm()
        context = self.pm.read_context_files(project_folder)
        agent = self.factory.create_editor_agent(llm, context, mode="writing")
        if is_revision:
            task_description = (
                f"수정된 소설 본문:\n{body_text}\n\n"
                f"Writer 설계 의도:\n{design_intent}\n\n"
                "이전에 지적한 문제들이 해결되었는지 확인하고, 남은 중요 문제가 있다면 번호와 함께 보고하세요. "
                "문제가 없으면 '✅ 통과'라고 명시하세요. 한국어로 작성하세요."
            )
        else:
            task_description = (
                f"사용자 집필 지시사항:\n{user_input}\n\n"
                f"Writer가 작성한 소설 본문:\n{body_text}\n\n"
                f"Writer의 설계 의도:\n{design_intent}\n\n"
                "위 7가지 체크리스트를 기준으로 본문을 검토하세요. "
                "문제가 있는 항목은 '⚠️ N. 내용'으로, 문제없는 항목은 '✅ N. 내용'으로 출력하세요. "
                "한국어로 작성하세요."
            )
        return _run_crew(agent, task_description)

    def run_writer_revision(self, body_text: str, design_intent: str, editor_review: str,
                            user_feedback: str, project_folder: str) -> tuple[str, str]:
        logger.info("[Writer] 수정 시작")
        llm = self._get_llm()
        context = self.pm.read_context_files(project_folder)
        agent = self.factory.create_writer_agent(llm, context)
        task_description = (
            f"이전에 작성한 소설 본문:\n{body_text}\n\n"
            f"설계 의도:\n{design_intent}\n\n"
            f"Editor 검토 결과:\n{editor_review}\n\n"
            f"사용자 수정 지시:\n{user_feedback}\n\n"
            "위 피드백을 반영하여 소설 본문을 수정하세요. 아래 형식으로 출력하세요:\n\n"
            "=== 소설 본문 ===\n"
            "(수정된 본문)\n\n"
            "=== 설계 의도 ===\n"
            "확정된 사실:\n- ...\n\n심은 복선:\n- ...\n\n설정 변경사항:\n- ..."
        )
        raw = _run_crew(agent, task_description)
        body, intent = _parse_writer_output(raw)
        logger.info("[Writer] 수정 완료 (본문 %d자)", len(body))
        return body, intent

    def run_writing_recorder(self, body_text: str, design_intent: str,
                             chapter_number: int, project_folder: str) -> dict:
        logger.info("[Recorder] %d화 문서화 시작", chapter_number)
        llm = self._get_llm()
        context = self.pm.read_context_files(project_folder)
        agent = self.factory.create_recorder_agent(llm, context)
        task_description = (
            f"{chapter_number}화 소설 본문:\n{body_text}\n\n"
            f"Writer 설계 의도:\n{design_intent}\n\n"
            "위 내용을 바탕으로 컨텍스트 파일 두 개를 전면 재작성하세요. "
            "기존 내용에 이번 챕터의 정보를 추가하여 전체를 재작성합니다. "
            "반드시 아래 형식으로 출력하세요:\n\n"
            "=== story_context.md ===\n"
            "[복선 목록]\n"
            "- n화: (복선 내용) (미해결/해결됨)\n\n"
            "[스토리 흐름]\n"
            "- 1화: (핵심 사건 요약)\n\n"
            "[확정된 설정 변경]\n"
            "- (변경된 설정, 없으면 '없음')\n\n"
            "=== character_relations.md ===\n"
            "[캐릭터명] (n화 기준)\n"
            "✅ 알고 있음: ...\n"
            "❌ 모르고 있음: ...\n"
            "🤔 의심/추측 중: ...\n\n"
            "모든 내용은 한국어로 작성하세요."
        )
        raw = _run_crew(agent, task_description)
        parsed = _parse_writing_recorder_output(raw)
        logger.info("[Recorder] %d화 문서화 완료", chapter_number)
        return {
            "chapter_number": chapter_number,
            "chapter_text": body_text,
            **parsed,
        }


def _parse_writer_output(raw: str) -> tuple[str, str]:
    """Parse Writer output into (body_text, design_intent)."""
    body_marker = "=== 소설 본문 ==="
    intent_marker = "=== 설계 의도 ==="
    body_start = raw.find(body_marker)
    intent_start = raw.find(intent_marker)
    if body_start == -1 and intent_start == -1:
        return raw.strip(), ""
    if body_start != -1 and intent_start != -1:
        body = raw[body_start + len(body_marker):intent_start].strip()
        intent = raw[intent_start + len(intent_marker):].strip()
    elif body_start != -1:
        body = raw[body_start + len(body_marker):].strip()
        intent = ""
    else:
        body = raw[:intent_start].strip()
        intent = raw[intent_start + len(intent_marker):].strip()
    return body, intent


def _parse_writing_recorder_output(raw: str) -> dict:
    """Parse Recorder output for Writing Room into {story_context, character_relations}."""
    markers = {
        "=== story_context.md ===": "story_context",
        "=== character_relations.md ===": "character_relations",
    }
    order = list(markers.keys())
    result = {"story_context": "", "character_relations": ""}
    for i, marker in enumerate(order):
        key = markers[marker]
        start = raw.find(marker)
        if start == -1:
            continue
        start += len(marker)
        end = len(raw)
        for next_marker in order[i + 1:]:
            pos = raw.find(next_marker, start)
            if pos != -1:
                end = pos
                break
        result[key] = raw[start:end].strip()
    return result


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
