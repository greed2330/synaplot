import os
import queue
import sys

# CrewAI requires OPENAI_API_KEY to be set even when using local Ollama.
# Set a dummy value to suppress the import error.
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "NA"

from src.logger import setup_logging
setup_logging()

import logging
import customtkinter as ctk

logger = logging.getLogger(__name__)
from tkinter import messagebox

# Allow running from project root
sys.path.insert(0, os.path.dirname(__file__))

from src.project_manager import ProjectManager
from src.gui.project_screen import ProjectSelectionScreen, PROJECTS_DIR
from src.gui.init_screen import InitializationScreen

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Web Novel AI Writer")
        self.geometry("1100x720")
        self.minsize(800, 600)

        self.result_queue = queue.Queue()
        self.pm = ProjectManager()
        self.current_screen = None
        self.current_init_screen = None

        self._show_project_selection()
        self.after(100, self._poll_queue)

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
        screen = ProjectSelectionScreen(
            self,
            on_project_selected=self._on_project_selected,
            on_project_created=self._on_project_created,
        )
        screen.pack(fill="both", expand=True)
        self.current_screen = screen

    def _on_project_selected(self, project_folder: str):
        try:
            config = self.pm.load_project(project_folder)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {e}")
            return

        if config.get("initialized"):
            # Phase 2: go to writing room (stub)
            messagebox.showinfo("Writing Room", "Writing Room will be available in Phase 2.")
        else:
            self._show_init_screen(project_folder)

    def _on_project_created(self, project_folder: str):
        self._show_init_screen(project_folder)

    def _show_init_screen(self, project_folder: str):
        self._clear_screen()
        project_name = self.pm.get_project_name(project_folder)
        self.title(f"Web Novel AI Writer — {project_name} [Initialization]")

        screen = InitializationScreen(
            self,
            project_folder=project_folder,
            result_queue=self.result_queue,
            on_init_complete=self._on_init_complete,
        )
        screen.pack(fill="both", expand=True)
        self.current_screen = screen
        self.current_init_screen = screen

    def _on_init_complete(self, project_folder: str):
        project_name = self.pm.get_project_name(project_folder)
        messagebox.showinfo(
            "Initialization Complete",
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
