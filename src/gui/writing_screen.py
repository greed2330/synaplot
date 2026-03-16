import json
import logging
import os
import threading
import customtkinter as ctk
from tkinter import messagebox, simpledialog

from src import i18n
from src.gui import theme as th
from src.gui.init_screen import FILE_DISPLAY_NAMES
from src.loop_controller import ManualLoopController
from src.project_manager import ProjectManager

logger = logging.getLogger(__name__)

CHAT_ROLES = {
    "user":     ("나",       th.TEXT2),
    "writer":   ("Writer",   th.SUCCESS),
    "editor":   ("Editor",   th.PRIMARY),
    "recorder": ("Recorder", "#7B68EE"),
    "system":   ("System",   th.TEXT3),
}

# Files that cannot be deleted or edited directly
READONLY_FILES = {"project_config.json"}


class WritingScreen(ctk.CTkFrame):
    """집필실 — Writer → Editor → (revision) → Recorder pipeline."""

    def __init__(self, master, project_folder: str, result_queue, on_back=None, **kwargs):
        super().__init__(master, fg_color=th.BG, **kwargs)
        self.project_folder = project_folder
        self.result_queue = result_queue
        self.on_back = on_back
        self.pm = ProjectManager()
        self.controller = ManualLoopController(project_folder)

        # Pipeline state
        self.stage = "idle"          # idle | writer_running | editor_running | awaiting_decision | revision_running | recorder_running
        self.revision_count = 0      # 0, 1, or 2
        self.current_writer_output = ""
        self.current_design_intent = ""
        self.current_editor_review = ""
        self.current_user_input = ""
        self._agent_running = False

        # Project state
        config = self.pm.load_project(project_folder)
        self.current_chapter = config.get("current_chapter", 1)
        self.active_episode_id = config.get("active_episode_id")

        # Chat history
        self.chat_history = []

        self._build_ui()
        self._refresh_left_sidebar()
        self._refresh_right_sidebar()
        self._restore_session()
        self._post_system_message(i18n.t("writing_welcome"))

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self._build_left_sidebar()
        self._build_chat_area()
        self._build_right_sidebar()

    def _build_left_sidebar(self):
        frame = ctk.CTkFrame(
            self, width=th.SIDEBAR_L,
            fg_color=th.SURFACE, border_width=1, border_color=th.BORDER,
            corner_radius=0
        )
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_propagate(False)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Chapter / episode info
        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=th.PAD, pady=(th.PAD, th.PAD_SM), sticky="ew")

        self.chapter_label = ctk.CTkLabel(
            info_frame, text=i18n.t("chapter_label", n=self.current_chapter),
            font=th.FONT_H1, text_color=th.TEXT, anchor="w"
        )
        self.chapter_label.pack(anchor="w")

        self.episode_label = ctk.CTkLabel(
            info_frame, text=f"{i18n.t('episode_label')}: {i18n.t('no_episode')}",
            font=th.FONT_SMALL, text_color=th.TEXT3, anchor="w"
        )
        self.episode_label.pack(anchor="w", pady=(2, 0))
        self._update_episode_label()

        ctk.CTkLabel(
            frame, text=i18n.t("settings_files"),
            font=th.FONT_SMALL, text_color=th.TEXT2
        ).grid(row=1, column=0, pady=(th.PAD_SM, 4), padx=th.PAD, sticky="w")

        self.left_file_list = ctk.CTkScrollableFrame(
            frame, fg_color="transparent",
            scrollbar_button_color=th.SURFACE3,
            scrollbar_button_hover_color=th.BORDER
        )
        self.left_file_list.grid(row=2, column=0, sticky="nsew", padx=th.PAD_SM, pady=(0, th.PAD_SM))
        self.left_file_list.grid_columnconfigure(0, weight=1)

        project_name = self.pm.get_project_name(self.project_folder)
        ctk.CTkLabel(
            frame,
            text=i18n.t("project_label") + ":\n" + project_name,
            text_color=th.TEXT3, wraplength=th.SIDEBAR_L - 16,
            font=th.FONT_SMALL
        ).grid(row=3, column=0, pady=(0, th.PAD), padx=th.PAD, sticky="w")

    def _build_chat_area(self):
        frame = ctk.CTkFrame(self, fg_color=th.BG)
        frame.grid(row=0, column=1, sticky="nsew", padx=1)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Chat display
        self.chat_display = ctk.CTkTextbox(
            frame, state="disabled", wrap="word",
            fg_color=th.SURFACE, text_color=th.TEXT, font=th.FONT_BODY,
            corner_radius=0
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", pady=(0, 1))

        # Input area
        input_frame = ctk.CTkFrame(frame, fg_color=th.SURFACE, corner_radius=0)
        input_frame.grid(row=1, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.user_input = ctk.CTkTextbox(
            input_frame, height=80, wrap="word",
            fg_color=th.SURFACE2, text_color=th.TEXT, font=th.FONT_BODY,
            border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD
        )
        self.user_input.grid(row=0, column=0, sticky="ew", padx=th.PAD, pady=(th.PAD_SM, th.PAD_SM))
        self.user_input.bind("<Control-Return>", self._on_send)

        self.send_btn = ctk.CTkButton(
            input_frame, text=i18n.t("send_btn"), width=120, height=32,
            **th.btn_primary({"font": th.FONT_SMALL}),
            command=self._on_send
        )
        self.send_btn.grid(row=1, column=0, sticky="e", padx=th.PAD, pady=(0, th.PAD_SM))

        # Action bar (Approve / Request Revision)
        self.action_bar = ctk.CTkFrame(frame, fg_color=th.SURFACE, corner_radius=0, height=48)
        self.action_bar.grid(row=2, column=0, sticky="ew")
        self.action_bar.grid_propagate(False)

        self.approve_btn = ctk.CTkButton(
            self.action_bar, text=i18n.t("approve"), height=30, width=80,
            fg_color=th.SUCCESS, hover_color="#16A34A",
            corner_radius=th.RADIUS_MD, text_color=th.TEXT, font=th.FONT_SMALL,
            command=self._on_approve, state="disabled"
        )
        self.approve_btn.pack(side="left", padx=(th.PAD, th.PAD_SM), pady=9)

        self.revision_btn = ctk.CTkButton(
            self.action_bar, text=i18n.t("request_revision"), height=30, width=90,
            fg_color="transparent", hover_color=th.SURFACE3,
            corner_radius=th.RADIUS_MD, text_color=th.WARNING, font=th.FONT_SMALL,
            command=self._on_request_revision, state="disabled"
        )
        self.revision_btn.pack(side="left", padx=(0, th.PAD_SM), pady=9)

        self.ignore_approve_btn = ctk.CTkButton(
            self.action_bar, text=i18n.t("ignore_approve"), height=30, width=110,
            **th.btn_danger({"font": th.FONT_SMALL}),
            command=self._on_ignore_and_approve, state="disabled"
        )
        self.ignore_approve_btn.pack(side="left", pady=9)

        self.status_label = ctk.CTkLabel(
            self.action_bar, text="", font=th.FONT_SMALL, text_color=th.TEXT3
        )
        self.status_label.pack(side="right", padx=(th.PAD_SM, th.PAD), pady=9)

    def _build_right_sidebar(self):
        frame = ctk.CTkFrame(
            self, width=th.SIDEBAR_R,
            fg_color=th.SURFACE, border_width=1, border_color=th.BORDER,
            corner_radius=0
        )
        frame.grid(row=0, column=2, sticky="nsew")
        frame.grid_propagate(False)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text=i18n.t("project_files"),
            font=th.FONT_SMALL, text_color=th.TEXT2
        ).grid(row=0, column=0, pady=(th.PAD, th.PAD_SM), padx=th.PAD, sticky="w")

        self.right_file_list = ctk.CTkScrollableFrame(
            frame, fg_color="transparent",
            scrollbar_button_color=th.SURFACE3,
            scrollbar_button_hover_color=th.BORDER
        )
        self.right_file_list.grid(row=1, column=0, sticky="nsew", padx=th.PAD_SM, pady=(0, th.PAD_SM))
        self.right_file_list.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            frame, text=i18n.t("new_file"), height=30,
            **th.btn_ghost({"font": th.FONT_SMALL}),
            command=self._on_new_file
        ).grid(row=2, column=0, pady=(0, th.PAD), padx=th.PAD, sticky="ew")

    # ── Sidebar refresh ───────────────────────────────────────────────────────

    def _refresh_left_sidebar(self):
        for w in self.left_file_list.winfo_children():
            w.destroy()
        settings_dir = os.path.join(self.project_folder, "settings")
        context_dir = os.path.join(self.project_folder, "context")
        files = []
        for d in (settings_dir, context_dir):
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    full = os.path.join(d, f)
                    if os.path.isfile(full):
                        files.append(full)
        for i, fpath in enumerate(files):
            fname = os.path.basename(fpath)
            display_name = FILE_DISPLAY_NAMES.get(fname, fname)
            btn = ctk.CTkButton(
                self.left_file_list, text=display_name, anchor="w",
                font=th.FONT_BODY, fg_color="transparent", text_color=th.TEXT,
                hover_color=th.SURFACE3, corner_radius=th.RADIUS_SM,
                command=lambda p=fpath: self._view_file(p),
            )
            btn.grid(row=i, column=0, sticky="ew", pady=1)

    def _refresh_right_sidebar(self):
        for w in self.right_file_list.winfo_children():
            w.destroy()

        groups = {"설정 파일": [], "컨텍스트": [], "챕터": [], "Inbox": [], "시스템": []}
        system_json = {
            "project_config.json", "episodes.json",
            "chat_history_write.json", "chat_history_setting.json",
            "chat_history_init.json", "temp_draft.json",
        }
        skip_dirs = {"backup", "__pycache__"}

        for root, dirs, files in os.walk(self.project_folder):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            folder = os.path.relpath(root, self.project_folder)
            for f in sorted(files):
                fpath = os.path.join(root, f)
                if folder == "settings":
                    groups["설정 파일"].append(fpath)
                elif folder == "context":
                    groups["컨텍스트"].append(fpath)
                elif folder == "chapters":
                    groups["챕터"].append(fpath)
                elif folder == "inbox":
                    groups["Inbox"].append(fpath)
                elif f in system_json:
                    groups["시스템"].append(fpath)

        row_idx = 0
        for group_name, files in groups.items():
            if not files:
                continue
            ctk.CTkLabel(
                self.right_file_list, text=group_name,
                font=th.FONT_SMALL, text_color=th.TEXT3, anchor="w"
            ).grid(row=row_idx, column=0, sticky="ew", padx=th.PAD_SM, pady=(10, 2))
            row_idx += 1

            for fpath in files:
                fname = os.path.basename(fpath)
                file_card = ctk.CTkFrame(
                    self.right_file_list,
                    fg_color=th.SURFACE2, border_width=1, border_color=th.BORDER,
                    corner_radius=th.RADIUS_MD
                )
                file_card.grid(row=row_idx, column=0, sticky="ew", pady=2, padx=2)
                file_card.grid_columnconfigure(0, weight=1)

                display_name = FILE_DISPLAY_NAMES.get(fname, fname)
                ctk.CTkLabel(
                    file_card, text=display_name, anchor="w",
                    font=th.FONT_SMALL, text_color=th.TEXT,
                    wraplength=th.SIDEBAR_R - 32
                ).grid(row=0, column=0, padx=th.PAD_SM, pady=(th.PAD_SM, 2), sticky="w")

                btn_row = ctk.CTkFrame(file_card, fg_color="transparent")
                btn_row.grid(row=1, column=0, padx=th.PAD_SM, pady=(0, th.PAD_SM), sticky="w")

                ctk.CTkButton(
                    btn_row, text=i18n.t("view"), width=44, height=22,
                    **th.btn_ghost({"font": th.FONT_SMALL, "corner_radius": th.RADIUS_SM}),
                    command=lambda p=fpath: self._view_file(p)
                ).pack(side="left", padx=(0, 4))

                if fname not in READONLY_FILES:
                    ctk.CTkButton(
                        btn_row, text=i18n.t("edit"), width=44, height=22,
                        **th.btn_ghost({"font": th.FONT_SMALL, "corner_radius": th.RADIUS_SM}),
                        command=lambda p=fpath: self._edit_file(p)
                    ).pack(side="left", padx=(0, 4))
                    ctk.CTkButton(
                        btn_row, text=i18n.t("delete"), width=44, height=22,
                        fg_color="transparent", hover_color=th.SURFACE3,
                        corner_radius=th.RADIUS_SM, text_color=th.DANGER,
                        font=th.FONT_SMALL,
                        command=lambda p=fpath: self._delete_file(p)
                    ).pack(side="left")

                row_idx += 1

    def _update_episode_label(self):
        episode_title = i18n.t("no_episode")
        if self.active_episode_id:
            try:
                ep_path = os.path.join(self.project_folder, "episodes.json")
                with open(ep_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for ep in data.get("episodes", []):
                    if ep.get("id") == self.active_episode_id:
                        episode_title = ep.get("title", i18n.t("no_episode"))
                        break
            except Exception:
                pass
        self.episode_label.configure(
            text=f"{i18n.t('episode_label')}: {episode_title}"
        )

    # ── Chat helpers ──────────────────────────────────────────────────────────

    def _post_message(self, role: str, content: str):
        label, color = CHAT_ROLES.get(role, ("Unknown", th.TEXT))
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\n[{label}]\n", f"role_{role}")
        self.chat_display.insert("end", f"  {content}\n", "content")
        self.chat_display.insert("end", "\u2500" * 40 + "\n", "separator")
        self.chat_display.tag_config(f"role_{role}", foreground=color)
        self.chat_display.tag_config("content", foreground=th.TEXT)
        self.chat_display.tag_config("separator", foreground=th.BORDER)
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _post_system_message(self, msg: str):
        self._post_message("system", msg)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_send(self, event=None):
        if self._agent_running or self.stage != "idle":
            return
        text = self.user_input.get("1.0", "end").strip()
        if not text:
            return
        self.user_input.delete("1.0", "end")
        self.current_user_input = text
        self.revision_count = 0
        self._post_message("user", text)
        self.chat_history.append({"role": "user", "content": text})
        self._save_chat_history()
        self._run_writer(text)

    def _on_approve(self):
        if self._agent_running or self.stage != "awaiting_decision":
            return
        self._run_recorder()

    def _on_request_revision(self):
        if self._agent_running or self.stage != "awaiting_decision":
            return
        feedback = self.user_input.get("1.0", "end").strip()
        if not feedback:
            messagebox.showwarning("수정 요청", "수정 내용을 입력란에 입력해주세요.")
            return
        if self.revision_count >= 2:
            messagebox.showwarning("수정 한도 초과", "최대 2회 수정 가능합니다. '무시하고 승인'을 사용하거나 직접 편집하세요.")
            return
        self.revision_count += 1
        self.user_input.delete("1.0", "end")
        self._post_system_message(f"수정 요청: {feedback}")
        self.chat_history.append({"role": "system", "content": f"수정 요청: {feedback}"})
        self._save_chat_history()
        self._run_writer_revision(feedback)

    def _on_ignore_and_approve(self):
        if self._agent_running:
            return
        self._post_system_message("Editor 검토를 무시하고 승인합니다.")
        self._run_recorder()

    # ── Worker launchers ──────────────────────────────────────────────────────

    def _run_writer(self, user_input: str):
        self._set_busy(True, i18n.t("writer_running"))
        chapter = self.current_chapter
        folder = self.project_folder

        def _worker():
            try:
                body, intent = self.controller.run_writer(user_input, chapter, folder)
                self.result_queue.put({"type": "writer_done", "body": body, "intent": intent})
            except ConnectionError as e:
                self.result_queue.put({"type": "error", "content": str(e)})
            except Exception as e:
                self.result_queue.put({"type": "error", "content": f"Error: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _run_editor(self, is_revision: bool = False):
        self._set_busy(True, i18n.t("editor_running"))
        body = self.current_writer_output
        intent = self.current_design_intent
        user_input = self.current_user_input
        folder = self.project_folder

        def _worker():
            try:
                review = self.controller.run_editor_review(body, intent, user_input, folder, is_revision)
                self.result_queue.put({"type": "editor_done", "review": review, "is_revision": is_revision})
            except ConnectionError as e:
                self.result_queue.put({"type": "error", "content": str(e)})
            except Exception as e:
                self.result_queue.put({"type": "error", "content": f"Error: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _run_writer_revision(self, feedback: str):
        self._set_busy(True, i18n.t("revision_running"))
        body = self.current_writer_output
        intent = self.current_design_intent
        review = self.current_editor_review
        folder = self.project_folder

        def _worker():
            try:
                new_body, new_intent = self.controller.run_writer_revision(
                    body, intent, review, feedback, folder)
                self.result_queue.put({"type": "writer_done", "body": new_body, "intent": new_intent})
            except ConnectionError as e:
                self.result_queue.put({"type": "error", "content": str(e)})
            except Exception as e:
                self.result_queue.put({"type": "error", "content": f"Error: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _run_recorder(self):
        self._set_busy(True, i18n.t("recorder_running"))
        body = self.current_writer_output
        intent = self.current_design_intent
        chapter = self.current_chapter
        folder = self.project_folder

        def _worker():
            try:
                draft = self.controller.run_writing_recorder(body, intent, chapter, folder)
                self.result_queue.put({"type": "recorder_draft_done", "draft": draft})
            except ConnectionError as e:
                self.result_queue.put({"type": "error", "content": str(e)})
            except Exception as e:
                self.result_queue.put({"type": "error", "content": f"Error: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    # ── Result processing ─────────────────────────────────────────────────────

    def process_result(self, result: dict):
        rtype = result.get("type")

        if rtype == "writer_done":
            body = result["body"]
            intent = result["intent"]
            self.current_writer_output = body
            self.current_design_intent = intent
            # Show body in chat; show design intent as separate system message
            self._post_message("writer", body)
            if intent:
                self._post_message("system", f"[설계 의도]\n{intent}")
            self.chat_history.append({"role": "writer", "content": body})
            self._save_chat_history()
            self._auto_save_draft("writer_done")
            self._run_editor(is_revision=self.revision_count > 0)

        elif rtype == "editor_done":
            review = result["review"]
            is_revision = result.get("is_revision", False)
            self.current_editor_review = review
            self._post_message("editor", review)
            self.chat_history.append({"role": "editor", "content": review})
            self._save_chat_history()
            self._auto_save_draft("editor_reviewed")
            self._set_busy(False)
            self.stage = "awaiting_decision"
            self.approve_btn.configure(state="normal")
            self.revision_btn.configure(state="normal")
            if self.revision_count >= 2:
                self.ignore_approve_btn.configure(state="normal")
                self._post_system_message(i18n.t("revision_max_warning"))

        elif rtype == "recorder_draft_done":
            draft = result["draft"]
            self._auto_save_draft("recorder_drafted", recorder_draft=draft)
            self._set_busy(False)
            self._show_recorder_draft(draft)

        elif rtype == "error":
            self._post_system_message(f"오류: {result['content']}")
            self.stage = "idle"
            self._set_busy(False)

    def _show_recorder_draft(self, draft: dict):
        chapter_n = draft.get("chapter_number", self.current_chapter)
        self._post_message("recorder", f"{chapter_n}화 문서화 초안이 생성되었습니다.")

        win = ctk.CTkToplevel(self)
        win.title(f"{chapter_n}화 — Recorder 초안 검토")
        win.geometry("640x560")
        win.configure(fg_color=th.BG)
        win.grab_set()

        ctk.CTkLabel(
            win, text=f"{chapter_n}화 문서가 생성되었습니다.",
            font=th.FONT_H2, text_color=th.TEXT
        ).pack(pady=(th.PAD + 4, 4), padx=th.PAD, anchor="w")
        ctk.CTkLabel(
            win, text="저장하시겠습니까?",
            font=th.FONT_SMALL, text_color=th.TEXT2
        ).pack(padx=th.PAD, anchor="w")

        def _approve():
            win.destroy()
            self._save_chapter(draft)

        def _cancel():
            win.destroy()
            self._post_system_message("저장이 취소되었습니다.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=th.PAD, padx=th.PAD, anchor="w")
        ctk.CTkButton(btn_frame, text="저장", width=100, height=34,
                      **th.btn_primary(), command=_approve).pack(side="left", padx=(0, th.PAD_SM))
        ctk.CTkButton(btn_frame, text="취소", width=80, height=34,
                      **th.btn_ghost(), command=_cancel).pack(side="left")

        preview = ctk.CTkTextbox(
            win, state="normal",
            fg_color=th.SURFACE, text_color=th.TEXT, font=th.FONT_SMALL,
            border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD
        )
        preview.pack(fill="both", expand=True, padx=th.PAD, pady=(0, th.PAD))
        preview.insert("end", f"=== {chapter_n}화 소설 본문 ===\n{draft.get('chapter_text', '')}\n\n")
        preview.insert("end", f"=== story_context.md ===\n{draft.get('story_context', '')}\n\n")
        preview.insert("end", f"=== character_relations.md ===\n{draft.get('character_relations', '')}\n")
        preview.configure(state="disabled")

    def _save_chapter(self, draft: dict):
        try:
            chapter_n = draft["chapter_number"]
            self.pm.save_chapter_files(
                self.project_folder,
                chapter_n,
                draft.get("chapter_text", ""),
                draft.get("story_context", ""),
                draft.get("character_relations", ""),
            )
            self.pm.create_backup(self.project_folder)
            self.pm.delete_temp_draft(self.project_folder)
            self.current_chapter = chapter_n + 1
            self.chapter_label.configure(text=i18n.t("chapter_label", n=self.current_chapter))
            self._post_system_message(i18n.t("chapter_saved", n=chapter_n))
            self.stage = "idle"
            self.revision_count = 0
            self.current_writer_output = ""
            self.current_design_intent = ""
            self.current_editor_review = ""
            self._disable_decision_buttons()
            self._refresh_left_sidebar()
            self._refresh_right_sidebar()
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))

    # ── File management ───────────────────────────────────────────────────────

    def _view_file(self, path: str):
        fname = os.path.basename(path)
        win = ctk.CTkToplevel(self)
        win.title(FILE_DISPLAY_NAMES.get(fname, fname))
        win.geometry("640x560")
        win.configure(fg_color=th.BG)
        win.grab_set()

        if path.endswith(".json"):
            _view_json_file(win, path, fname)
        else:
            text = ctk.CTkTextbox(
                win, state="normal", font=th.FONT_BODY, wrap="word",
                fg_color=th.SURFACE, text_color=th.TEXT,
                border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD
            )
            text.pack(fill="both", expand=True, padx=th.PAD, pady=(th.PAD, 0))
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text.insert("end", f.read())
            except Exception as e:
                text.insert("end", f"읽기 오류: {e}")
            if fname in READONLY_FILES:
                text.configure(state="disabled")
            else:
                def _save():
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(text.get("1.0", "end"))
                        win.destroy()
                        self._post_system_message(f"파일 저장됨: {os.path.relpath(path, self.project_folder)}")
                        self._refresh_right_sidebar()
                        self._refresh_left_sidebar()
                    except Exception as e:
                        messagebox.showerror("Error", str(e))
                ctk.CTkButton(
                    win, text="저장", height=34,
                    **th.btn_primary({"font": th.FONT_SMALL}),
                    command=_save
                ).pack(pady=th.PAD_SM, padx=th.PAD, anchor="e")

    def _edit_file(self, path: str):
        win = ctk.CTkToplevel(self)
        win.title(f"편집: {os.path.basename(path)}")
        win.geometry("600x500")
        win.configure(fg_color=th.BG)
        text = ctk.CTkTextbox(
            win, state="normal", font=th.FONT_BODY,
            fg_color=th.SURFACE, text_color=th.TEXT,
            border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD
        )
        text.pack(fill="both", expand=True, padx=th.PAD, pady=(th.PAD, 0))
        try:
            with open(path, "r", encoding="utf-8") as f:
                text.insert("end", f.read())
        except Exception as e:
            text.insert("end", f"Could not read file: {e}")

        def _save():
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text.get("1.0", "end"))
                win.destroy()
                self._post_system_message(f"파일 저장됨: {os.path.relpath(path, self.project_folder)}")
                self._refresh_right_sidebar()
                self._refresh_left_sidebar()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ctk.CTkButton(
            win, text="저장", height=34,
            **th.btn_primary({"font": th.FONT_SMALL}),
            command=_save
        ).pack(pady=th.PAD_SM, padx=th.PAD, anchor="e")

    def _delete_file(self, path: str):
        rel = os.path.relpath(path, self.project_folder)
        in_chapters = path.startswith(os.path.join(self.project_folder, "chapters"))
        msg = f"'{rel}' 파일을 삭제하시겠습니까?"
        if in_chapters:
            msg += "\n\n챕터 파일을 삭제하면 컨텍스트 파일이 불일치할 수 있습니다."
        if not messagebox.askyesno("파일 삭제", msg):
            return
        try:
            os.remove(path)
            self._refresh_right_sidebar()
            self._refresh_left_sidebar()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_new_file(self):
        name = simpledialog.askstring("새 파일", "파일 이름 (프로젝트 폴더 기준 상대 경로):")
        if not name:
            return
        full_path = os.path.join(self.project_folder, name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write("")
            self._refresh_right_sidebar()
            self._edit_file(full_path)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Session persistence ───────────────────────────────────────────────────

    def _save_chat_history(self):
        try:
            self.pm.save_chat_history(self.project_folder, "chat_history_write.json", self.chat_history)
        except Exception:
            pass

    def _restore_session(self):
        """Restore chat history and optionally draft state from previous session."""
        history = self.pm.load_chat_history(self.project_folder, "chat_history_write.json")
        if history:
            for msg in history:
                self._post_message(msg.get("role", "user"), msg.get("content", ""))
            self.chat_history = history

        draft = self.pm.load_temp_draft(self.project_folder)
        if not draft or draft.get("room") != "writing":
            return
        stage = draft.get("stage", "")
        if stage in ("writer_done", "editor_reviewed"):
            self.current_writer_output = draft.get("writer_output") or ""
            self.current_design_intent = draft.get("design_intent") or ""
            self.current_editor_review = draft.get("editor_output") or ""
            self._post_system_message("이전 작업이 복원되었습니다. 승인하거나 새 지시를 입력하세요.")
            self.stage = "awaiting_decision"
            self.approve_btn.configure(state="normal")
            self.revision_btn.configure(state="normal")
        elif stage == "recorder_drafted" and draft.get("recorder_draft"):
            self.current_writer_output = draft.get("writer_output") or ""
            self.current_design_intent = draft.get("design_intent") or ""
            self._show_recorder_draft(draft["recorder_draft"])

    def _auto_save_draft(self, stage: str, recorder_draft=None):
        data = {
            "room": "writing",
            "stage": stage,
            "chapter_number": self.current_chapter,
            "active_episode_id": self.active_episode_id,
            "user_input": self.current_user_input,
            "writer_output": self.current_writer_output,
            "design_intent": self.current_design_intent,
            "editor_output": self.current_editor_review,
            "recorder_draft": recorder_draft,
        }
        try:
            self.pm.save_temp_draft(self.project_folder, data)
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool, status: str = ""):
        self._agent_running = busy
        self.status_label.configure(text=status)
        self.send_btn.configure(state="disabled" if busy else "normal")
        if busy:
            self.approve_btn.configure(state="disabled")
            self.revision_btn.configure(state="disabled")
            self.ignore_approve_btn.configure(state="disabled")

    def _disable_decision_buttons(self):
        self.approve_btn.configure(state="disabled")
        self.revision_btn.configure(state="disabled")
        self.ignore_approve_btn.configure(state="disabled")


# ── Standalone JSON viewer (shared, no self dependency) ───────────────────────

def _view_json_file(win: ctk.CTkToplevel, path: str, fname: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        ctk.CTkLabel(win, text=f"파일 읽기 오류: {e}", text_color=th.DANGER).pack(pady=20)
        return

    scroll = ctk.CTkScrollableFrame(
        win, fg_color=th.BG,
        scrollbar_button_color=th.SURFACE3,
        scrollbar_button_hover_color=th.BORDER
    )
    scroll.pack(fill="both", expand=True, padx=th.PAD, pady=th.PAD)
    scroll.grid_columnconfigure(0, weight=1)

    if fname == "project_config.json":
        _render_project_config(scroll, data)
    elif fname == "episodes.json":
        _render_episodes(scroll, data)
    elif "chat_history" in fname:
        _render_chat_history(scroll, data)
    elif fname == "temp_draft.json":
        _render_temp_draft(scroll, data)
    else:
        _render_generic_json(scroll, data)


def _render_section(parent, row: int, title: str, value: str, color: str = None):
    ctk.CTkLabel(parent, text=title, font=th.FONT_SMALL,
                 text_color=th.TEXT2, anchor="w").grid(row=row * 2, column=0, sticky="w", pady=(10, 0))
    ctk.CTkLabel(parent, text=value or "—", font=th.FONT_BODY,
                 anchor="w", wraplength=550, justify="left",
                 text_color=color or th.TEXT).grid(row=row * 2 + 1, column=0, sticky="w", padx=th.PAD_SM)


def _render_project_config(parent, data: dict):
    ctk.CTkLabel(parent, text="프로젝트 설정", font=th.FONT_H1, text_color=th.TEXT).grid(
        row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
    rows = [
        ("LLM 모델", data.get("llm_model", "—")),
        ("초기화 완료", "예" if data.get("initialized") else "아니오"),
        ("현재 챕터", str(data.get("current_chapter", 1))),
        ("활성 에피소드", data.get("active_episode_id") or "없음"),
    ]
    for i, (label, val) in enumerate(rows):
        _render_section(parent, i + 1, label, val)


def _render_episodes(parent, data: dict):
    episodes = data.get("episodes", [])
    ctk.CTkLabel(parent, text=f"에피소드 목록 ({len(episodes)}개)", font=th.FONT_H1, text_color=th.TEXT).grid(
        row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
    if not episodes:
        ctk.CTkLabel(parent, text="등록된 에피소드가 없습니다.",
                     text_color=th.TEXT3, font=th.FONT_BODY).grid(row=1, column=0, sticky="w", pady=th.PAD_SM)
        return
    status_map = {"planned": "계획됨", "in_progress": "진행 중", "completed": "완료", "on_hold": "보류"}
    for i, ep in enumerate(episodes):
        card = ctk.CTkFrame(parent, **th.card())
        card.grid(row=i + 1, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(0, weight=1)
        status_str = status_map.get(ep.get("status", ""), ep.get("status", ""))
        ctk.CTkLabel(card, text=f"{ep.get('title', '제목 없음')}  [{status_str}]",
                     font=th.FONT_H2, text_color=th.TEXT, anchor="w").grid(
            row=0, column=0, padx=th.PAD, pady=(th.PAD_SM, 2), sticky="w")
        if ep.get("description"):
            ctk.CTkLabel(card, text=ep["description"], font=th.FONT_SMALL,
                         text_color=th.TEXT2, anchor="w", wraplength=500).grid(
                row=1, column=0, padx=th.PAD, pady=(0, th.PAD_SM), sticky="w")


def _render_chat_history(parent, data: list):
    ctk.CTkLabel(parent, text=f"대화 기록 ({len(data)}개 메시지)", font=th.FONT_H1, text_color=th.TEXT).grid(
        row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
    if not data:
        ctk.CTkLabel(parent, text="대화 기록이 없습니다.", text_color=th.TEXT3, font=th.FONT_BODY).grid(
            row=1, column=0, sticky="w", pady=th.PAD_SM)
        return
    role_label = {"user": "나", "writer": "Writer", "editor": "Editor", "recorder": "Recorder", "system": "System"}
    role_color = {"user": th.TEXT2, "writer": th.SUCCESS, "editor": th.PRIMARY, "recorder": "#7B68EE", "system": th.TEXT3}
    for i, msg in enumerate(data):
        role = msg.get("role", "user")
        card = ctk.CTkFrame(parent, **th.card())
        card.grid(row=i + 1, column=0, sticky="ew", pady=3)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=role_label.get(role, role), font=th.FONT_SMALL,
                     text_color=role_color.get(role, th.TEXT2), anchor="w").grid(
            row=0, column=0, padx=th.PAD, pady=(th.PAD_SM, 0), sticky="w")
        ctk.CTkLabel(card, text=msg.get("content", ""), font=th.FONT_BODY,
                     text_color=th.TEXT, anchor="w", wraplength=520, justify="left").grid(
            row=1, column=0, padx=th.PAD, pady=(2, th.PAD_SM), sticky="w")


def _render_temp_draft(parent, data: dict):
    ctk.CTkLabel(parent, text="임시 저장 상태", font=th.FONT_H1, text_color=th.TEXT).grid(
        row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
    stage_label = {
        "chatting": "대화 중", "writer_done": "Writer 완료",
        "editor_reviewed": "Editor 검토 완료", "recorder_drafted": "Recorder 초안 생성",
        "editor_done": "Editor 요약 완료",
    }
    rows = [
        ("저장 시각", data.get("updated_at", "—")),
        ("현재 단계", stage_label.get(data.get("stage", ""), data.get("stage", "—"))),
        ("방", {"writing": "집필실", "init": "초기화", "setting": "설정실"}.get(data.get("room", ""), "—")),
    ]
    for i, (label, val) in enumerate(rows):
        _render_section(parent, i + 1, label, val)


def _render_generic_json(parent, data):
    text = ctk.CTkTextbox(parent, font=th.FONT_MONO, wrap="word", state="normal",
                          fg_color=th.SURFACE, text_color=th.TEXT,
                          border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD)
    text.grid(row=0, column=0, sticky="nsew")
    text.insert("end", json.dumps(data, ensure_ascii=False, indent=2))
    text.configure(state="disabled")
