# src/i18n.py
_lang = "ko"

STRINGS = {
    "ko": {
        # App
        "app_title": "시나플롯",
        "back_to_projects": "← 프로젝트 목록",
        "language_toggle": "EN",

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
        "init_welcome": "Editor가 초기화를 시작합니다. 소설에 대한 아이디어를 자유롭게 이야기해 주세요!",
    },
    "en": {
        # App
        "app_title": "Synaplot",
        "back_to_projects": "← Projects",
        "language_toggle": "KO",

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
        "init_welcome": "Editor is starting initialization. Feel free to share your novel ideas!",
    },
}

def t(key: str, **kwargs) -> str:
    s = STRINGS.get(_lang, STRINGS["ko"]).get(key, key)
    return s.format(**kwargs) if kwargs else s

def get_lang() -> str:
    return _lang

def set_lang(lang: str):
    global _lang
    if lang in STRINGS:
        _lang = lang
