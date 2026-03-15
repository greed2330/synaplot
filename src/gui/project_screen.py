import logging
import os
import shutil
import threading
import customtkinter as ctk
from tkinter import messagebox

from src import i18n
from src.gui import theme as th
from src.llm_provider import get_available_models
from src.project_manager import ProjectManager, INVALID_NAME_RE

logger = logging.getLogger(__name__)

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "projects")


class ProjectSelectionScreen(ctk.CTkFrame):
    def __init__(self, master, on_project_selected, on_project_created, **kwargs):
        super().__init__(master, fg_color=th.BG, **kwargs)
        self.on_project_selected = on_project_selected
        self.on_project_created = on_project_created
        self.pm = ProjectManager()
        self.available_models = []
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        self._build_ui()
        self._load_models_async()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # ── Top: model bar ─────────────────────────────────────────────────
        mbar = ctk.CTkFrame(self, fg_color=th.SURFACE, corner_radius=0,
                            border_width=0, height=52)
        mbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        mbar.grid_propagate(False)
        mbar.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(mbar, text=i18n.t("ollama_model"),
                     font=th.FONT_SMALL, text_color=th.TEXT2).grid(
            row=0, column=0, padx=(th.PAD, 8), pady=14, sticky="w")

        self.model_var = ctk.StringVar(value=i18n.t("model_loading"))
        self.model_dropdown = ctk.CTkOptionMenu(
            mbar, variable=self.model_var,
            values=[i18n.t("model_loading")],
            fg_color=th.SURFACE2, button_color=th.SURFACE3,
            button_hover_color=th.PRIMARY, dropdown_fg_color=th.SURFACE,
            text_color=th.TEXT, font=th.FONT_BODY,
            corner_radius=th.RADIUS_MD, width=200, state="disabled"
        )
        self.model_dropdown.grid(row=0, column=1, pady=14, sticky="w")

        self.model_status = ctk.CTkLabel(mbar, text="", font=th.FONT_SMALL,
                                         text_color=th.TEXT3)
        self.model_status.grid(row=0, column=2, padx=th.PAD, pady=14, sticky="w")

        # ── Left: project list ──────────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color=th.BG)
        left.grid(row=1, column=0, sticky="nsew", padx=(th.PAD, 8), pady=th.PAD)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, th.PAD_SM))
        ctk.CTkLabel(hdr, text=i18n.t("existing_projects"),
                     font=th.FONT_H1, text_color=th.TEXT).pack(side="left")

        self.project_scroll = ctk.CTkScrollableFrame(
            left, fg_color="transparent",
            scrollbar_button_color=th.SURFACE3,
            scrollbar_button_hover_color=th.BORDER
        )
        self.project_scroll.grid(row=1, column=0, sticky="nsew")
        self.project_scroll.grid_columnconfigure(0, weight=1)
        self._refresh_project_list()

        # ── Right: create form ──────────────────────────────────────────────
        right = ctk.CTkFrame(self, **th.card(), corner_radius=th.RADIUS_LG)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, th.PAD), pady=th.PAD)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text=i18n.t("create_new_project"),
                     font=th.FONT_H1, text_color=th.TEXT).grid(
            row=0, column=0, padx=th.PAD, pady=(th.PAD + 4, th.PAD), sticky="w")

        ctk.CTkLabel(right, text=i18n.t("project_name"),
                     font=th.FONT_SMALL, text_color=th.TEXT2).grid(
            row=1, column=0, padx=th.PAD, sticky="w")

        self.name_entry = ctk.CTkEntry(right, **th.input_style(),
                                       placeholder_text=i18n.t("project_name_placeholder"),
                                       height=40)
        self.name_entry.grid(row=2, column=0, padx=th.PAD, pady=(4, 0), sticky="ew")
        self.name_entry.bind("<KeyRelease>", self._validate_name)

        self.name_error = ctk.CTkLabel(right, text="", font=th.FONT_SMALL,
                                       text_color=th.DANGER, anchor="w", wraplength=260)
        self.name_error.grid(row=3, column=0, padx=th.PAD, pady=(4, 0), sticky="w")

        self.create_btn = ctk.CTkButton(
            right, text=i18n.t("create_project"), height=42,
            **th.btn_primary(), command=self._create_project
        )
        self.create_btn.grid(row=4, column=0, padx=th.PAD, pady=(th.PAD, 0), sticky="ew")

        # Spacer
        ctk.CTkFrame(right, fg_color="transparent", height=th.PAD).grid(row=5, column=0)

    # ── Project list ────────────────────────────────────────────────────────

    def _refresh_project_list(self):
        for w in self.project_scroll.winfo_children():
            w.destroy()
        projects = self.pm.list_projects(PROJECTS_DIR)
        if not projects:
            ctk.CTkLabel(self.project_scroll, text=i18n.t("no_projects"),
                         font=th.FONT_BODY, text_color=th.TEXT3).grid(
                row=0, column=0, pady=40)
            return
        for i, folder in enumerate(projects):
            self._add_project_row(i, folder)

    def _add_project_row(self, idx: int, folder: str):
        name = self.pm.get_project_name(folder)
        try:
            cfg = self.pm.load_project(folder)
            initialized = cfg.get("initialized", False)
        except Exception:
            initialized = False

        # Card
        row_card = ctk.CTkFrame(self.project_scroll, **th.card(),
                                corner_radius=th.RADIUS_LG)
        row_card.grid(row=idx, column=0, sticky="ew", pady=(0, th.PAD_SM))
        row_card.grid_columnconfigure(0, weight=1)

        # Left: name + status
        info = ctk.CTkFrame(row_card, fg_color="transparent")
        info.grid(row=0, column=0, padx=th.PAD, pady=th.PAD, sticky="w")

        ctk.CTkLabel(info, text=name, font=th.FONT_H2, text_color=th.TEXT).pack(anchor="w")

        status_text = "초기화 완료" if initialized else "초기화 필요"
        status_color = th.SUCCESS if initialized else th.WARNING
        ctk.CTkLabel(info, text=status_text, font=th.FONT_SMALL,
                     text_color=status_color).pack(anchor="w", pady=(2, 0))

        # Right: buttons
        btns = ctk.CTkFrame(row_card, fg_color="transparent")
        btns.grid(row=0, column=1, padx=th.PAD, pady=th.PAD, sticky="e")

        ctk.CTkButton(btns, text=i18n.t("open_project"), width=80, height=32,
                      **th.btn_primary({"font": th.FONT_SMALL}),
                      command=lambda f=folder: self._open_project(f)).pack(side="left", padx=(0, th.PAD_SM))

        ctk.CTkButton(btns, text=i18n.t("delete_project"), width=60, height=32,
                      **th.btn_danger({"font": th.FONT_SMALL}),
                      command=lambda f=folder, n=name: self._delete_project(f, n)).pack(side="left")

    # ── Model loading ────────────────────────────────────────────────────────

    def _load_models_async(self):
        def _fetch():
            models = get_available_models()
            self.after(0, lambda: self._on_models_loaded(models))
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_models_loaded(self, models):
        self.available_models = models
        if not models:
            self.model_status.configure(text=i18n.t("model_not_available"), text_color=th.DANGER)
            self.model_dropdown.configure(values=["(없음)"], state="disabled")
            self.model_var.set("(없음)")
        else:
            self.model_dropdown.configure(values=models, state="normal")
            self.model_var.set(models[0])
            self.model_status.configure(
                text=i18n.t("model_found", n=len(models)), text_color=th.SUCCESS)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _open_project(self, folder: str):
        model = self.model_var.get()
        if model not in ("(없음)", i18n.t("model_loading")):
            try:
                self.pm.update_config(folder, {"llm_model": model})
            except Exception:
                pass
        self.on_project_selected(folder)

    def _delete_project(self, folder: str, name: str):
        if not messagebox.askyesno(
            i18n.t("delete_confirm_title"),
            i18n.t("delete_confirm_msg", name=name)
        ):
            return
        try:
            shutil.rmtree(folder)
            logger.info("프로젝트 삭제: %s", folder)
            self._refresh_project_list()
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def _validate_name(self, event=None):
        self.name_error.configure(
            text=i18n.t("invalid_name") if INVALID_NAME_RE.search(self.name_entry.get()) else ""
        )

    def _create_project(self):
        name = self.name_entry.get().strip()
        if not name:
            self.name_error.configure(text=i18n.t("empty_name"))
            return
        if INVALID_NAME_RE.search(name):
            self.name_error.configure(text=i18n.t("invalid_name"))
            return
        model = self.model_var.get()
        try:
            folder = self.pm.create_project(PROJECTS_DIR, name)
            if model not in ("(없음)", i18n.t("model_loading")):
                self.pm.update_config(folder, {"llm_model": model})
            self._refresh_project_list()
            self.on_project_created(folder)
        except ValueError as e:
            self.name_error.configure(text=str(e))
        except Exception as e:
            messagebox.showerror("오류", str(e))
