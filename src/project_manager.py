import json
import logging
import os
import re
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


INVALID_NAME_CHARS = r'\/:*?"<>|'
INVALID_NAME_RE = re.compile(r'[\\/:*?"<>|]')

_APP_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app_config.json")

DEFAULT_CONFIG = {
    "llm_provider": "ollama",
    "llm_model": "gemma2:9b",
    "initialized": False,
    "current_chapter": 1,
    "active_episode_id": None,
}

DEFAULT_EPISODES = {"episodes": []}


class ProjectManager:
    def create_project(self, base_dir: str, name: str) -> str:
        if INVALID_NAME_RE.search(name):
            raise ValueError(f'Project name cannot contain: {INVALID_NAME_CHARS}')
        if not name.strip():
            raise ValueError("Project name cannot be empty.")

        project_folder = os.path.join(base_dir, name)
        if os.path.exists(project_folder):
            raise ValueError(f"Project '{name}' already exists.")
        logger.info("프로젝트 생성: %s", project_folder)

        # Create folder structure
        for sub in ("settings", "chapters", "context", "inbox", "backup"):
            os.makedirs(os.path.join(project_folder, sub), exist_ok=True)

        # Write default JSON files
        self._write_json(os.path.join(project_folder, "project_config.json"), DEFAULT_CONFIG)
        self._write_json(os.path.join(project_folder, "episodes.json"), DEFAULT_EPISODES)
        self._write_json(os.path.join(project_folder, "chat_history_write.json"), [])
        self._write_json(os.path.join(project_folder, "chat_history_setting.json"), [])

        return project_folder

    def load_project(self, project_folder: str) -> dict:
        logger.info("프로젝트 로드: %s", project_folder)
        config_path = os.path.join(project_folder, "project_config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"project_config.json not found in {project_folder}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Recalculate current_chapter from chapters/ scan
        chapters_dir = os.path.join(project_folder, "chapters")
        chapter_numbers = []
        if os.path.isdir(chapters_dir):
            for fname in os.listdir(chapters_dir):
                m = re.match(r"^(\d+)화", fname)
                if m:
                    chapter_numbers.append(int(m.group(1)))
        config["current_chapter"] = max(chapter_numbers) + 1 if chapter_numbers else 1

        # Save updated current_chapter back
        self._write_json(config_path, config)
        return config

    def list_projects(self, base_dir: str) -> list[str]:
        if not os.path.isdir(base_dir):
            return []
        result = []
        for entry in os.scandir(base_dir):
            if entry.is_dir():
                config_path = os.path.join(entry.path, "project_config.json")
                if os.path.exists(config_path):
                    result.append(entry.path)
        result.sort()
        return result

    def get_project_name(self, project_folder: str) -> str:
        return os.path.basename(project_folder)

    def create_backup(self, project_folder: str):
        logger.info("백업 생성 중: %s", project_folder)
        backup_base = os.path.join(project_folder, "backup")
        existing = [d for d in os.listdir(backup_base) if re.match(r"^\d{3}_", d)]
        next_num = len(existing) + 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{next_num:03d}_{timestamp}"
        dest = os.path.join(backup_base, backup_name)

        # Copy everything except backup/ itself to avoid recursion
        def ignore_backup(src, names):
            if os.path.abspath(src) == os.path.abspath(project_folder):
                return ["backup"]
            return []

        shutil.copytree(project_folder, dest, ignore=ignore_backup)
        logger.info("백업 완료: %s", dest)

    def save_temp_draft(self, project_folder: str, data: dict):
        data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self._write_json(os.path.join(project_folder, "temp_draft.json"), data)

    def load_temp_draft(self, project_folder: str) -> dict | None:
        path = os.path.join(project_folder, "temp_draft.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_temp_draft(self, project_folder: str):
        path = os.path.join(project_folder, "temp_draft.json")
        if os.path.exists(path):
            os.remove(path)

    def scan_inbox(self, project_folder: str) -> list[str]:
        inbox_dir = os.path.join(project_folder, "inbox")
        if not os.path.isdir(inbox_dir):
            return []
        files = [
            os.path.join(inbox_dir, f)
            for f in sorted(os.listdir(inbox_dir))
            if os.path.isfile(os.path.join(inbox_dir, f))
        ]
        return files

    def read_context_files(self, project_folder: str) -> dict:
        """Read all context/settings files and return as a dict."""
        def read_file(path):
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            return ""

        return {
            "settings_world": read_file(os.path.join(project_folder, "settings", "세계관.md")),
            "settings_plot": read_file(os.path.join(project_folder, "settings", "줄거리.md")),
            "settings_novel": read_file(os.path.join(project_folder, "settings", "소설설정.md")),
            "story_context": read_file(os.path.join(project_folder, "context", "story_context.md")),
            "character_relations": read_file(os.path.join(project_folder, "context", "character_relations.md")),
        }

    def write_settings_files(self, project_folder: str, files: dict):
        """Write the 5 files generated by the Recorder during initialization."""
        mapping = {
            "세계관": os.path.join(project_folder, "settings", "세계관.md"),
            "줄거리": os.path.join(project_folder, "settings", "줄거리.md"),
            "소설설정": os.path.join(project_folder, "settings", "소설설정.md"),
            "story_context": os.path.join(project_folder, "context", "story_context.md"),
            "character_relations": os.path.join(project_folder, "context", "character_relations.md"),
        }
        for key, path in mapping.items():
            content = files.get(key, "")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def mark_initialized(self, project_folder: str):
        logger.info("프로젝트 초기화 완료 표시: %s", project_folder)
        config_path = os.path.join(project_folder, "project_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config["initialized"] = True
        self._write_json(config_path, config)

    def update_config(self, project_folder: str, updates: dict):
        config_path = os.path.join(project_folder, "project_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config.update(updates)
        self._write_json(config_path, config)

    def load_app_config(self) -> dict:
        if not os.path.exists(_APP_CONFIG_PATH):
            return {"language": "ko"}
        with open(_APP_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_app_config(self, data: dict):
        with open(_APP_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _write_json(self, path: str, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
