import os
import re
import threading
import customtkinter as ctk
from tkinter import messagebox

from src.llm_provider import get_available_models
from src.project_manager import ProjectManager, INVALID_NAME_CHARS, INVALID_NAME_RE

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "projects")


class ProjectSelectionScreen(ctk.CTkFrame):
    def __init__(self, master, on_project_selected, on_project_created, **kwargs):
        super().__init__(master, **kwargs)
        self.on_project_selected = on_project_selected
        self.on_project_created = on_project_created
        self.pm = ProjectManager()
        self.selected_project = None
        self.available_models = []

        os.makedirs(PROJECTS_DIR, exist_ok=True)
        self._build_ui()
        self._load_models_async()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Title
        title = ctk.CTkLabel(self, text="Web Novel AI Writer", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(30, 10))

        # Model selection row
        model_frame = ctk.CTkFrame(self, fg_color="transparent")
        model_frame.grid(row=1, column=0, columnspan=2, pady=(0, 16), padx=30, sticky="ew")
        model_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(model_frame, text="Ollama Model:").grid(row=0, column=0, padx=(0, 8))
        self.model_var = ctk.StringVar(value="Loading...")
        self.model_dropdown = ctk.CTkOptionMenu(model_frame, variable=self.model_var, values=["Loading..."])
        self.model_dropdown.grid(row=0, column=1, sticky="ew")
        self.model_dropdown.configure(state="disabled")

        self.model_status_label = ctk.CTkLabel(model_frame, text="", text_color="gray")
        self.model_status_label.grid(row=0, column=2, padx=(8, 0))

        # Left: existing projects
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=2, column=0, padx=(30, 8), pady=0, sticky="nsew")
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left_frame, text="Existing Projects", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, pady=(16, 8), padx=16
        )
        self.project_listbox = ctk.CTkScrollableFrame(left_frame)
        self.project_listbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.project_listbox.grid_columnconfigure(0, weight=1)

        self.open_btn = ctk.CTkButton(left_frame, text="Open Project", command=self._open_project, state="disabled")
        self.open_btn.grid(row=2, column=0, pady=(0, 16), padx=16, sticky="ew")

        self._refresh_project_list()

        # Right: create new project
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=2, column=1, padx=(8, 30), pady=0, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_frame, text="Create New Project", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, pady=(16, 8), padx=16
        )
        ctk.CTkLabel(right_frame, text="Project Name:").grid(row=1, column=0, padx=16, sticky="w")
        self.name_entry = ctk.CTkEntry(right_frame, placeholder_text="e.g. My Fantasy Novel")
        self.name_entry.grid(row=2, column=0, padx=16, pady=(4, 0), sticky="ew")
        self.name_entry.bind("<KeyRelease>", self._validate_name)

        self.name_error_label = ctk.CTkLabel(right_frame, text="", text_color="red", wraplength=260)
        self.name_error_label.grid(row=3, column=0, padx=16, sticky="w")

        self.create_btn = ctk.CTkButton(right_frame, text="Create Project", command=self._create_project)
        self.create_btn.grid(row=4, column=0, pady=(16, 0), padx=16, sticky="ew")

        # Spacer
        ctk.CTkFrame(right_frame, fg_color="transparent").grid(row=5, column=0, pady=(0, 16))

    def _load_models_async(self):
        def _fetch():
            models = get_available_models()
            self.after(0, lambda: self._on_models_loaded(models))

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_models_loaded(self, models: list):
        if not models:
            self.model_status_label.configure(text="Ollama not available", text_color="red")
            self.model_dropdown.configure(values=["(no models)"], state="disabled")
            self.model_var.set("(no models)")
        else:
            self.model_dropdown.configure(values=models, state="normal")
            self.model_var.set(models[0])
            self.model_status_label.configure(text=f"{len(models)} model(s) found", text_color="green")
        self.available_models = models
        # Re-check warning if a project is already selected
        if self.selected_project:
            self._check_model_warning(self.selected_project)

    def _refresh_project_list(self):
        for w in self.project_listbox.winfo_children():
            w.destroy()
        self.project_buttons = {}
        projects = self.pm.list_projects(PROJECTS_DIR)
        if not projects:
            ctk.CTkLabel(self.project_listbox, text="No projects yet", text_color="gray").grid(row=0, column=0)
        for i, folder in enumerate(projects):
            name = self.pm.get_project_name(folder)
            btn = ctk.CTkButton(
                self.project_listbox,
                text=name,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
                anchor="w",
                command=lambda f=folder: self._select_project(f),
            )
            btn.grid(row=i, column=0, sticky="ew", pady=2)
            self.project_buttons[folder] = btn

    def _select_project(self, folder: str):
        self.selected_project = folder
        for f, btn in self.project_buttons.items():
            if f == folder:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")
        self.open_btn.configure(state="normal")
        self._check_model_warning(folder)

    def _check_model_warning(self, folder: str):
        """If the project's saved model is not in the available model list, show a warning."""
        if not self.available_models:
            return
        try:
            config = self.pm.load_project(folder)
            saved_model = config.get("llm_model", "")
        except Exception:
            return
        if saved_model and saved_model not in self.available_models:
            self.model_status_label.configure(
                text=f"⚠ '{saved_model}' not found in Ollama",
                text_color="orange"
            )
        else:
            count = len(self.available_models)
            self.model_status_label.configure(
                text=f"{count} model(s) found",
                text_color="green"
            )

    def _open_project(self):
        if not self.selected_project:
            return
        model = self.model_var.get()
        if model not in ("(no models)", "Loading..."):
            try:
                self.pm.update_config(self.selected_project, {"llm_model": model})
            except Exception:
                pass
        self.on_project_selected(self.selected_project)

    def _validate_name(self, event=None):
        name = self.name_entry.get()
        if INVALID_NAME_RE.search(name):
            self.name_error_label.configure(
                text=f'Project name cannot contain: {INVALID_NAME_CHARS}'
            )
        else:
            self.name_error_label.configure(text="")

    def _create_project(self):
        name = self.name_entry.get().strip()
        if not name:
            self.name_error_label.configure(text="Project name cannot be empty.")
            return
        if INVALID_NAME_RE.search(name):
            self.name_error_label.configure(
                text=f'Project name cannot contain: {INVALID_NAME_CHARS}'
            )
            return

        model = self.model_var.get()
        try:
            folder = self.pm.create_project(PROJECTS_DIR, name)
            if model not in ("(no models)", "Loading..."):
                self.pm.update_config(folder, {"llm_model": model})
            self._refresh_project_list()
            self.on_project_created(folder)
        except ValueError as e:
            self.name_error_label.configure(text=str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_selected_model(self) -> str:
        return self.model_var.get()
