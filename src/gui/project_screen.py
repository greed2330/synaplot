import logging
import os
import shutil
import threading
import customtkinter as ctk
from tkinter import messagebox

from src import i18n
from src.llm_provider import get_available_models
from src.project_manager import ProjectManager, INVALID_NAME_RE

logger = logging.getLogger(__name__)

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "projects")

FONT_H1    = ("Malgun Gothic", 18, "bold")
FONT_H2    = ("Malgun Gothic", 14, "bold")
FONT_BODY  = ("Malgun Gothic", 13)
FONT_SMALL = ("Malgun Gothic", 11)


class ProjectSelectionScreen(ctk.CTkFrame):
    def __init__(self, master, on_project_selected, on_project_created, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
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
        self.grid_rowconfigure(1, weight=1)

        # Model selection bar at top (full width)
        model_bar = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=10)
        model_bar.grid(row=0, column=0, columnspan=2, padx=24, pady=(20, 12), sticky="ew")
        model_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(model_bar, text=i18n.t("ollama_model"), font=FONT_BODY).grid(
            row=0, column=0, padx=16, pady=10, sticky="w"
        )
        self.model_var = ctk.StringVar(value=i18n.t("model_loading"))
        self.model_dropdown = ctk.CTkOptionMenu(
            model_bar, variable=self.model_var, values=[i18n.t("model_loading")],
            font=FONT_BODY, width=220, state="disabled"
        )
        self.model_dropdown.grid(row=0, column=1, padx=8, pady=10, sticky="w")

        self.model_status_label = ctk.CTkLabel(model_bar, text="", font=FONT_SMALL, text_color="gray")
        self.model_status_label.grid(row=0, column=2, padx=16, pady=10, sticky="e")

        # Left panel — existing projects
        left = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray92", "gray17"))
        left.grid(row=1, column=0, padx=(24, 10), pady=(0, 24), sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text=i18n.t("existing_projects"), font=FONT_H2).grid(
            row=0, column=0, padx=20, pady=(20, 12), sticky="w"
        )

        self.project_list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.project_list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.project_list_frame.grid_columnconfigure(0, weight=1)

        self._refresh_project_list()

        # Right panel — create new project
        right = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray92", "gray17"))
        right.grid(row=1, column=1, padx=(10, 24), pady=(0, 24), sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text=i18n.t("create_new_project"), font=FONT_H2).grid(
            row=0, column=0, padx=20, pady=(20, 16), sticky="w"
        )
        ctk.CTkLabel(right, text=i18n.t("project_name"), font=FONT_BODY).grid(
            row=1, column=0, padx=20, sticky="w"
        )
        self.name_entry = ctk.CTkEntry(
            right, placeholder_text=i18n.t("project_name_placeholder"),
            font=FONT_BODY, height=40, corner_radius=8
        )
        self.name_entry.grid(row=2, column=0, padx=20, pady=(6, 0), sticky="ew")
        self.name_entry.bind("<KeyRelease>", self._validate_name)

        self.name_error_label = ctk.CTkLabel(
            right, text="", text_color="#E74C3C", font=FONT_SMALL, wraplength=280, anchor="w"
        )
        self.name_error_label.grid(row=3, column=0, padx=20, pady=(4, 0), sticky="w")

        self.create_btn = ctk.CTkButton(
            right, text=i18n.t("create_project"),
            font=FONT_BODY, height=42, corner_radius=8,
            command=self._create_project
        )
        self.create_btn.grid(row=4, column=0, padx=20, pady=(20, 0), sticky="ew")

        # Filler
        ctk.CTkFrame(right, fg_color="transparent").grid(row=5, column=0, pady=(0, 20))

    def _load_models_async(self):
        def _fetch():
            models = get_available_models()
            self.after(0, lambda: self._on_models_loaded(models))
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_models_loaded(self, models: list):
        self.available_models = models
        if not models:
            self.model_status_label.configure(text=i18n.t("model_not_available"), text_color="#E74C3C")
            self.model_dropdown.configure(values=["(none)"], state="disabled")
            self.model_var.set("(none)")
        else:
            self.model_dropdown.configure(values=models, state="normal")
            self.model_var.set(models[0])
            self.model_status_label.configure(
                text=i18n.t("model_found", n=len(models)), text_color="#27AE60"
            )
        if self.selected_project:
            self._check_model_warning(self.selected_project)

    def _refresh_project_list(self):
        for w in self.project_list_frame.winfo_children():
            w.destroy()
        projects = self.pm.list_projects(PROJECTS_DIR)
        if not projects:
            ctk.CTkLabel(
                self.project_list_frame, text=i18n.t("no_projects"),
                font=FONT_SMALL, text_color="gray"
            ).grid(row=0, column=0, pady=20)
            return

        for i, folder in enumerate(projects):
            name = self.pm.get_project_name(folder)
            row = ctk.CTkFrame(self.project_list_frame, corner_radius=8, fg_color=("gray85", "gray22"))
            row.grid(row=i, column=0, sticky="ew", pady=4, padx=2)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(row, text=name, font=FONT_BODY, anchor="w").grid(
                row=0, column=0, padx=14, pady=10, sticky="w"
            )

            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.grid(row=0, column=1, padx=8, pady=6, sticky="e")

            ctk.CTkButton(
                btn_frame, text=i18n.t("open_project"),
                font=FONT_SMALL, width=80, height=30, corner_radius=6,
                command=lambda f=folder: self._open_project(f)
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                btn_frame, text=i18n.t("delete_project"),
                font=FONT_SMALL, width=52, height=30, corner_radius=6,
                fg_color="#C0392B", hover_color="#96281B",
                command=lambda f=folder, n=name: self._delete_project(f, n)
            ).pack(side="left")

    def _open_project(self, folder: str):
        self.selected_project = folder
        model = self.model_var.get()
        if model not in ("(none)", i18n.t("model_loading")):
            try:
                self.pm.update_config(folder, {"llm_model": model})
            except Exception:
                pass
        self._check_model_warning(folder)
        self.on_project_selected(folder)

    def _delete_project(self, folder: str, name: str):
        msg = i18n.t("delete_confirm_msg", name=name)
        title = i18n.t("delete_confirm_title")
        if not messagebox.askyesno(title, msg):
            return
        try:
            shutil.rmtree(folder)
            logger.info("프로젝트 삭제: %s", folder)
            if self.selected_project == folder:
                self.selected_project = None
            self._refresh_project_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _check_model_warning(self, folder: str):
        if not self.available_models:
            return
        try:
            config = self.pm.load_project(folder)
            saved_model = config.get("llm_model", "")
        except Exception:
            return
        if saved_model and saved_model not in self.available_models:
            self.model_status_label.configure(
                text=i18n.t("model_not_found_warning", model=saved_model),
                text_color="orange"
            )
        else:
            self.model_status_label.configure(
                text=i18n.t("model_found", n=len(self.available_models)),
                text_color="#27AE60"
            )

    def _validate_name(self, event=None):
        name = self.name_entry.get()
        if INVALID_NAME_RE.search(name):
            self.name_error_label.configure(text=i18n.t("invalid_name"))
        else:
            self.name_error_label.configure(text="")

    def _create_project(self):
        name = self.name_entry.get().strip()
        if not name:
            self.name_error_label.configure(text=i18n.t("empty_name"))
            return
        if INVALID_NAME_RE.search(name):
            self.name_error_label.configure(text=i18n.t("invalid_name"))
            return
        model = self.model_var.get()
        try:
            folder = self.pm.create_project(PROJECTS_DIR, name)
            if model not in ("(none)", i18n.t("model_loading")):
                self.pm.update_config(folder, {"llm_model": model})
            self._refresh_project_list()
            self.on_project_created(folder)
        except ValueError as e:
            self.name_error_label.configure(text=str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))
