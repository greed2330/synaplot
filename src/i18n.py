# src/i18n.py
_lang = "ko"

STRINGS = {
    "ko": {
        # App
        "app_title": "시나플롯",
        "back_to_projects": "← 프로젝트 목록",
        "language_toggle": "🌐 EN",

        # Project screen
        "existing_projects": "기존 프로젝트",
        "open_project": "프로젝트 열기",
        "delete_project": "삭제",
        "no_projects": "프로젝트가 없습니다",
        "create_new_project": "새 프로젝트 만들기",
        "project_name": "프로젝트 이름",
        "project_name_placeholder": "예: 나의 판타지 소설",
        "create_project": "프로젝트 생성",
        "model_loading": "불러오는 중...",
        "model_not_available": "Ollama를 사용할 수 없습니다",
        "model_found": "{n}개 모델 발견",
        "model_not_found_warning": "⚠ '{model}' 모델이 Ollama에 없습니다",
        "ollama_model": "Ollama 모델",
        "invalid_name": "프로젝트 이름에 사용할 수 없는 문자: \\ / : * ? \" < > |",
        "empty_name": "프로젝트 이름을 입력해주세요.",
        "delete_confirm_title": "프로젝트 삭제",
        "delete_confirm_msg": "'{name}' 프로젝트를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.",

        # Init screen
        "settings_files": "설정 파일",
        "project_label": "프로젝트",
        "project_files": "프로젝트 파일",
        "new_file": "+ 새 파일",
        "send_btn": "전송 (Ctrl+Enter)",
        "check_inbox": "Inbox 확인",
        "coord_done": "조율 완료",
        "confirm_gen": "문서 생성 확인",
        "view": "보기",
        "edit": "편집",
        "delete": "삭제",
        "init_welcome": "Director가 초기화를 시작합니다. 소설에 대한 아이디어를 자유롭게 이야기해 주세요!",

        # Flavor texts (loading indicator)
        "flavor_wait": "아직 생각 중이에요, 조금만 기다려 주세요! 🤔",
        "flavor_director": [
            "🎬 Director가 아이디어를 정리하는 중이에요...",
            "🎬 좋은 질문들이 떠오르고 있어요...",
            "🎬 잠깐, 더 생각해볼게요! 🤔",
        ],
        "flavor_recorder": [
            "📦 Recorder가 기록을 정리하는 중이에요...",
            "📦 문서를 꼼꼼히 작성하는 중이에요...",
            "📦 거의 다 됐어요!",
        ],
        "flavor_writer": [
            "✍️ Writer가 설정 파일을 읽는 중이에요...",
            "✍️ Writer가 열심히 쓰는 중이에요...",
            "✍️ 문장을 다듬는 중이에요...",
        ],
        "flavor_editor": [
            "🔍 Editor가 꼼꼼히 읽는 중이에요...",
            "🔍 Editor가 체크리스트를 확인하는 중이에요...",
            "🔍 논리적 오류가 없는지 살피는 중이에요...",
        ],
        "flavor_default": [
            "열심히 처리 중이에요...",
            "조금만 기다려 주세요...",
        ],

        # Writing screen
        "writing_room": "집필실",
        "chapter_label": "{n}화",
        "episode_label": "현재 에피소드",
        "no_episode": "(없음)",
        "writing_welcome": "집필실입니다. 이번 챕터의 방향을 자유롭게 이야기해 주세요.",
        "approve": "승인",
        "request_revision": "수정 요청",
        "ignore_approve": "무시하고 승인",
        "writer_running": "Writer가 집필 중...",
        "editor_running": "Editor가 검토 중...",
        "recorder_running": "Recorder가 문서화 중...",
        "revision_running": "Writer가 수정 중...",
        "revision_max_warning": "2회 수정 후에도 문제가 남아있습니다. 무시하고 승인하거나 직접 편집하세요.",
        "chapter_saved": "{n}화가 저장되었습니다. 백업이 생성되었습니다.",
    },
    "en": {
        # App
        "app_title": "Synaplot",
        "back_to_projects": "← Projects",
        "language_toggle": "🌐 KO",

        # Project screen
        "existing_projects": "Existing Projects",
        "open_project": "Open Project",
        "delete_project": "Delete",
        "no_projects": "No projects yet",
        "create_new_project": "Create New Project",
        "project_name": "Project Name",
        "project_name_placeholder": "e.g. My Fantasy Novel",
        "create_project": "Create Project",
        "model_loading": "Loading...",
        "model_not_available": "Ollama not available",
        "model_found": "{n} model(s) found",
        "model_not_found_warning": "⚠ '{model}' not found in Ollama",
        "ollama_model": "Ollama Model",
        "invalid_name": "Project name cannot contain: \\ / : * ? \" < > |",
        "empty_name": "Project name cannot be empty.",
        "delete_confirm_title": "Delete Project",
        "delete_confirm_msg": "Delete project '{name}'?\n\nThis cannot be undone.",

        # Init screen
        "settings_files": "Settings Files",
        "project_label": "Project",
        "project_files": "Project Files",
        "new_file": "+ New File",
        "send_btn": "Send (Ctrl+Enter)",
        "check_inbox": "Check Inbox",
        "coord_done": "Coordination Complete",
        "confirm_gen": "Confirm Document Generation",
        "view": "View",
        "edit": "Edit",
        "delete": "Del",
        "init_welcome": "Director is starting initialization. Feel free to share your novel ideas!",

        # Flavor texts (loading indicator)
        "flavor_wait": "Still thinking, please wait a moment! 🤔",
        "flavor_director": [
            "🎬 Director is organizing your ideas...",
            "🎬 Good questions are forming...",
            "🎬 Let me think about this a bit more! 🤔",
        ],
        "flavor_recorder": [
            "📦 Recorder is organizing the notes...",
            "📦 Writing the documents carefully...",
            "📦 Almost done!",
        ],
        "flavor_writer": [
            "✍️ Writer is reading the settings...",
            "✍️ Writer is hard at work...",
            "✍️ Polishing the sentences...",
        ],
        "flavor_editor": [
            "🔍 Editor is reading carefully...",
            "🔍 Editor is going through the checklist...",
            "🔍 Checking for logical inconsistencies...",
        ],
        "flavor_default": [
            "Working hard...",
            "Please wait a moment...",
        ],

        # Writing screen
        "writing_room": "Writing Room",
        "chapter_label": "Chapter {n}",
        "episode_label": "Current Episode",
        "no_episode": "(none)",
        "writing_welcome": "Welcome to the Writing Room. Tell the Writer what direction to take this chapter.",
        "approve": "Approve",
        "request_revision": "Request Revision",
        "ignore_approve": "Ignore & Approve",
        "writer_running": "Writer is writing...",
        "editor_running": "Editor is reviewing...",
        "recorder_running": "Recorder is documenting...",
        "revision_running": "Writer is revising...",
        "revision_max_warning": "Issues remain after 2 revisions. Ignore and approve, or edit manually.",
        "chapter_saved": "Chapter {n} saved. Backup created.",
    },
}

def t(key: str, **kwargs) -> str:
    s = STRINGS.get(_lang, STRINGS["ko"]).get(key, key)
    return s.format(**kwargs) if kwargs else s

def tlist(key: str) -> list:
    val = STRINGS.get(_lang, STRINGS["ko"]).get(key, [])
    return val if isinstance(val, list) else [val]

def get_lang() -> str:
    return _lang

def set_lang(lang: str):
    global _lang
    if lang in STRINGS:
        _lang = lang
