import os
import queue
import sys
import json

# CrewAI requires OPENAI_API_KEY to be set even when using local Ollama.
# Set a dummy value to suppress the import error.
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "NA"

from src.logger import setup_logging
setup_logging()

import logging
import customtkinter as ctk
from tkinter import messagebox

from src import i18n
from src.project_manager import ProjectManager
from src.gui.project_screen import ProjectSelectionScreen, PROJECTS_DIR
from src.gui.init_screen import InitializationScreen

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

logger = logging.getLogger(__name__)

FONT_TITLE = ("Malgun Gothic", 20, "bold")   # Windows Korean font
FONT_BODY  = ("Malgun Gothic", 12)
FONT_SMALL = ("Malgun Gothic", 11)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(i18n.t("app_title"))
        self.geometry("1200x760")
        self.minsize(900, 620)

        self.result_queue = queue.Queue()
        self.pm = ProjectManager()
        self.current_screen = None
        self.current_init_screen = None

        # Load language from app_config
        cfg = self.pm.load_app_config()
        i18n.set_lang(cfg.get("language", "ko"))

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._show_project_selection()
        self.after(100, self._poll_queue)

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, height=48, corner_radius=0, fg_color=("gray85", "gray20"))
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        bar.grid_propagate(False)

        self._back_btn = ctk.CTkButton(
            bar, text=i18n.t("back_to_projects"), width=140, height=32,
            fg_color="transparent", hover_color=("gray75", "gray30"),
            command=self._on_back_to_projects
        )
        self._back_btn.grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self._back_btn.grid_remove()  # hidden initially

        self._title_label = ctk.CTkLabel(
            bar, text=i18n.t("app_title"),
            font=ctk.CTkFont(family="Malgun Gothic", size=16, weight="bold")
        )
        self._title_label.grid(row=0, column=1, pady=8)

        self._lang_btn = ctk.CTkButton(
            bar, text=i18n.t("language_toggle"), width=48, height=32,
            fg_color="transparent", hover_color=("gray75", "gray30"),
            command=self._toggle_language
        )
        self._lang_btn.grid(row=0, column=2, padx=12, pady=8, sticky="e")

    def _toggle_language(self):
        new_lang = "en" if i18n.get_lang() == "ko" else "ko"
        i18n.set_lang(new_lang)
        cfg = self.pm.load_app_config()
        cfg["language"] = new_lang
        self.pm.save_app_config(cfg)
        self.title(i18n.t("app_title"))
        self._title_label.configure(text=i18n.t("app_title"))
        self._lang_btn.configure(text=i18n.t("language_toggle"))
        self._back_btn.configure(text=i18n.t("back_to_projects"))
        # Rebuild current screen to apply new language
        if self.current_init_screen:
            project_folder = self.current_init_screen.project_folder
            self._show_init_screen(project_folder)
        else:
            self._show_project_selection()

    def _poll_queue(self):
        try:
            while True:
                result = self.result_queue.get_nowait()
                if self.current_init_screen:
                    self.current_init_screen.process_result(result)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _clear_screen(self):
        if self.current_screen:
            self.current_screen.destroy()
            self.current_screen = None
        self.current_init_screen = None

    def _show_project_selection(self):
        self._clear_screen()
        self._back_btn.grid_remove()
        screen = ProjectSelectionScreen(
            self._content,
            on_project_selected=self._on_project_selected,
            on_project_created=self._on_project_created,
        )
        screen.grid(row=0, column=0, sticky="nsew")
        self.current_screen = screen

    def _on_back_to_projects(self):
        if self.current_init_screen and self.current_init_screen._agent_running:
            if not messagebox.askyesno("작업 중", "에이전트가 실행 중입니다. 메인 화면으로 돌아가시겠습니까?"):
                return
        self._show_project_selection()

    def _on_project_selected(self, project_folder: str):
        try:
            config = self.pm.load_project(project_folder)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {e}")
            return
        if config.get("initialized"):
            messagebox.showinfo("Writing Room", "Writing Room은 Phase 2에서 구현됩니다.")
        else:
            self._show_init_screen(project_folder)

    def _on_project_created(self, project_folder: str):
        self._show_init_screen(project_folder)

    def _show_init_screen(self, project_folder: str):
        self._clear_screen()
        project_name = self.pm.get_project_name(project_folder)
        self.title(f"{i18n.t('app_title')} — {project_name}")
        self._back_btn.configure(text=i18n.t("back_to_projects"))
        self._back_btn.grid()

        screen = InitializationScreen(
            self._content,
            project_folder=project_folder,
            result_queue=self.result_queue,
            on_init_complete=self._on_init_complete,
        )
        screen.grid(row=0, column=0, sticky="nsew")
        self.current_screen = screen
        self.current_init_screen = screen

    def _on_init_complete(self, project_folder: str):
        project_name = self.pm.get_project_name(project_folder)
        messagebox.showinfo(
            "초기화 완료" if i18n.get_lang() == "ko" else "Initialization Complete",
            f"'{project_name}' 프로젝트 초기화가 완료되었습니다!\n\nWriting Room은 Phase 2에서 구현됩니다."
        )
        self._show_project_selection()


def main():
    logger.info("앱 시작")
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    app = App()
    app.mainloop()
    logger.info("앱 종료")


if __name__ == "__main__":
    main()
