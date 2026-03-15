import os
import queue
import threading
import customtkinter as ctk
from tkinter import messagebox, simpledialog

from src import i18n
from src.gui import theme as th
from src.loop_controller import ManualLoopController
from src.project_manager import ProjectManager


FILE_DISPLAY_NAMES = {
    "project_config.json":       "프로젝트 설정",
    "episodes.json":             "에피소드 목록",
    "chat_history_write.json":   "집필실 대화 기록",
    "chat_history_setting.json": "설정실 대화 기록",
    "chat_history_init.json":    "초기화 대화 기록",
    "temp_draft.json":           "임시 저장",
    "세계관.md":                 "세계관",
    "줄거리.md":                 "줄거리",
    "소설설정.md":               "소설 설정",
    "story_context.md":          "스토리 흐름",
    "character_relations.md":    "인물 관계도",
}

CHAT_ROLES = {
    "user":     ("You",      th.TEXT2),
    "editor":   ("Editor",   th.PRIMARY),
    "recorder": ("Recorder", "#7B68EE"),
    "system":   ("System",   th.TEXT3),
}


class InitializationScreen(ctk.CTkFrame):
    def __init__(self, master, project_folder: str, result_queue: queue.Queue,
                 on_init_complete=None, **kwargs):
        super().__init__(master, fg_color=th.BG, **kwargs)
        self.project_folder = project_folder
        self.result_queue = result_queue
        self.on_init_complete = on_init_complete
        self.pm = ProjectManager()
        self.controller = ManualLoopController(project_folder)
        self.chat_history = []
        self.stage = "chatting"  # chatting | summary_ready | recorder_done
        self.editor_summary = ""
        self.recorder_draft = {}
        self._agent_running = False

        self._build_ui()
        self._restore_chat_history()
        self._refresh_right_sidebar()
        self._post_system_message(i18n.t("init_welcome"))

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
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text=i18n.t("settings_files"),
            font=th.FONT_SMALL, text_color=th.TEXT2
        ).grid(row=0, column=0, pady=(th.PAD, th.PAD_SM), padx=th.PAD, sticky="w")

        self.left_file_list = ctk.CTkScrollableFrame(
            frame, fg_color="transparent",
            scrollbar_button_color=th.SURFACE3,
            scrollbar_button_hover_color=th.BORDER
        )
        self.left_file_list.grid(row=1, column=0, sticky="nsew", padx=th.PAD_SM, pady=(0, th.PAD_SM))
        self.left_file_list.grid_columnconfigure(0, weight=1)

        project_name = self.pm.get_project_name(self.project_folder)
        ctk.CTkLabel(
            frame,
            text=i18n.t("project_label") + ":\n" + project_name,
            text_color=th.TEXT3, wraplength=th.SIDEBAR_L - 16,
            font=th.FONT_SMALL
        ).grid(row=2, column=0, pady=(0, th.PAD), padx=th.PAD, sticky="w")

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
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 1))

        # Input area
        input_frame = ctk.CTkFrame(frame, fg_color=th.SURFACE, corner_radius=0)
        input_frame.grid(row=1, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.user_input = ctk.CTkTextbox(
            input_frame, height=80, wrap="word",
            fg_color=th.SURFACE2, text_color=th.TEXT, font=th.FONT_BODY,
            border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD
        )
        self.user_input.grid(row=0, column=0, sticky="ew", columnspan=2,
                             padx=th.PAD, pady=(th.PAD_SM, th.PAD_SM))
        self.user_input.bind("<Control-Return>", self._on_send)

        send_btn = ctk.CTkButton(
            input_frame, text=i18n.t("send_btn"), width=120, height=32,
            **th.btn_primary({"font": th.FONT_SMALL}),
            command=self._on_send
        )
        send_btn.grid(row=1, column=0, sticky="e", padx=th.PAD, pady=(0, th.PAD_SM))

        # Action buttons bar
        btn_frame = ctk.CTkFrame(frame, fg_color=th.SURFACE, corner_radius=0, height=48)
        btn_frame.grid(row=2, column=0, sticky="ew")
        btn_frame.grid_propagate(False)

        self.inbox_btn = ctk.CTkButton(
            btn_frame, text=i18n.t("check_inbox"), height=30,
            **th.btn_ghost({"font": th.FONT_SMALL}),
            command=self._on_check_inbox
        )
        self.inbox_btn.pack(side="left", padx=(th.PAD, th.PAD_SM), pady=9)

        self.coord_done_btn = ctk.CTkButton(
            btn_frame, text=i18n.t("coord_done"), height=30,
            fg_color="transparent", hover_color=th.SURFACE3,
            corner_radius=th.RADIUS_MD, text_color=th.WARNING,
            font=th.FONT_SMALL,
            command=self._on_coordination_done
        )
        self.coord_done_btn.pack(side="left", padx=(0, th.PAD_SM), pady=9)

        self.confirm_gen_btn = ctk.CTkButton(
            btn_frame, text=i18n.t("confirm_gen"), height=30,
            fg_color="transparent", hover_color=th.SURFACE3,
            corner_radius=th.RADIUS_MD, text_color=th.SUCCESS,
            font=th.FONT_SMALL,
            command=self._on_confirm_generation,
            state="disabled"
        )
        self.confirm_gen_btn.pack(side="left", pady=9)

        self.status_label = ctk.CTkLabel(
            btn_frame, text="", font=th.FONT_SMALL, text_color=th.TEXT3
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

        new_file_btn = ctk.CTkButton(
            frame, text=i18n.t("new_file"), height=30,
            **th.btn_ghost({"font": th.FONT_SMALL}),
            command=self._on_new_file
        )
        new_file_btn.grid(row=2, column=0, pady=(0, th.PAD), padx=th.PAD, sticky="ew")

    def _refresh_right_sidebar(self):
        for w in self.right_file_list.winfo_children():
            w.destroy()

        # Group files by category
        groups = {
            "설정 파일":  [],
            "컨텍스트":   [],
            "챕터":       [],
            "Inbox":      [],
            "시스템":     [],
        }
        system_json = {
            "project_config.json", "episodes.json",
            "chat_history_write.json", "chat_history_setting.json",
            "chat_history_init.json", "temp_draft.json",
        }
        # Only project_config.json is truly read-only (editing it directly could break state)
        readonly_files = {"project_config.json"}
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
            # Section header
            header = ctk.CTkLabel(
                self.right_file_list, text=group_name,
                font=th.FONT_SMALL, text_color=th.TEXT3, anchor="w"
            )
            header.grid(row=row_idx, column=0, sticky="ew", padx=th.PAD_SM, pady=(10, 2))
            row_idx += 1

            for fpath in files:
                fname = os.path.basename(fpath)
                is_system = fname in system_json

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

                if fname not in readonly_files:
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
                font=th.FONT_BODY,
                fg_color="transparent", text_color=th.TEXT,
                hover_color=th.SURFACE3,
                corner_radius=th.RADIUS_SM,
                command=lambda p=fpath: self._view_file(p),
            )
            btn.grid(row=i, column=0, sticky="ew", pady=1)

    def _get_all_project_files(self) -> list[str]:
        result = []
        skip_dirs = {"backup", "__pycache__"}
        for root, dirs, files in os.walk(self.project_folder):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in sorted(files):
                result.append(os.path.join(root, f))
        return result

    # --- Chat helpers ---

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

    # --- Event handlers ---

    def _on_send(self, event=None):
        if self._agent_running:
            return
        text = self.user_input.get("1.0", "end").strip()
        if not text:
            return
        self.user_input.delete("1.0", "end")
        self._post_message("user", text)
        self.chat_history.append({"role": "user", "content": text})
        self._save_chat_history()
        self._run_editor(text)

    def _run_editor(self, user_message: str):
        self._set_busy(True, "Editor가 응답 중...")
        history = list(self.chat_history)
        folder = self.project_folder

        def _worker():
            try:
                response = self.controller.run_init_editor(user_message, history, folder)
                self.result_queue.put({"type": "editor_reply", "content": response})
            except ConnectionError as e:
                self.result_queue.put({"type": "error", "content": str(e)})
            except Exception as e:
                self.result_queue.put({"type": "error", "content": f"Error: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_check_inbox(self):
        if self._agent_running:
            return
        files = self.pm.scan_inbox(self.project_folder)
        if not files:
            messagebox.showinfo("Inbox", "Inbox is empty. Place files in the inbox/ folder first.")
            return

        file_names = [os.path.basename(f) for f in files]
        msg = "Files found in inbox:\n\n" + "\n".join(f"{i+1}. {n}" for i, n in enumerate(file_names))
        msg += "\n\nLoad these files and send to Editor?"
        if not messagebox.askyesno("Check Inbox", msg):
            return

        self._load_inbox_files(files)

    def _load_inbox_files(self, files: list):
        self._set_busy(True, "Inbox 파일 처리 중...")
        folder = self.project_folder
        history = list(self.chat_history)

        def _worker():
            for fpath in files:
                fname = os.path.basename(fpath)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    response, was_split = self.controller.run_inbox_file(content, fname, history, folder)
                    payload = {
                        "type": "inbox_file_done",
                        "filename": fname,
                        "response": response,
                        "was_split": was_split,
                    }
                    self.result_queue.put(payload)
                    history.append({"role": "editor", "content": response})
                except Exception as e:
                    self.result_queue.put({"type": "error", "content": f"Failed to load {fname}: {e}"})
            self.result_queue.put({"type": "inbox_all_done"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_coordination_done(self):
        if self._agent_running:
            return
        if not messagebox.askyesno("Coordination Complete",
                                   "Coordination을 완료하고 Editor에게 최종 요약을 생성하도록 하시겠습니까?"):
            return
        self._set_busy(True, "Editor가 최종 요약을 생성 중...")
        history = list(self.chat_history)
        folder = self.project_folder

        def _worker():
            try:
                summary = self.controller.run_init_editor_summary(history, folder)
                self.result_queue.put({"type": "editor_summary_done", "content": summary})
            except ConnectionError as e:
                self.result_queue.put({"type": "error", "content": str(e)})
            except Exception as e:
                self.result_queue.put({"type": "error", "content": f"Error: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_confirm_generation(self):
        if self._agent_running:
            return
        if not self.editor_summary:
            return
        if not messagebox.askyesno("Confirm Document Generation",
                                   "Recorder가 5개의 초기 문서를 생성합니다. 계속하시겠습니까?"):
            return
        self._set_busy(True, "Recorder가 문서를 생성 중...")
        summary = self.editor_summary
        folder = self.project_folder

        def _worker():
            try:
                draft = self.controller.run_init_recorder(summary, folder)
                self.result_queue.put({"type": "recorder_draft_done", "content": draft})
            except ConnectionError as e:
                self.result_queue.put({"type": "error", "content": str(e)})
            except Exception as e:
                self.result_queue.put({"type": "error", "content": f"Error: {e}"})

        threading.Thread(target=_worker, daemon=True).start()

    # --- Result queue processing ---

    def process_result(self, result: dict):
        rtype = result.get("type")

        if rtype == "editor_reply":
            content = result["content"]
            self._post_message("editor", content)
            self.chat_history.append({"role": "editor", "content": content})
            self._save_chat_history()
            self._auto_save_draft("chatting", editor_output=content)
            self._set_busy(False)

        elif rtype == "inbox_file_done":
            fname = result["filename"]
            response = result["response"]
            was_split = result["was_split"]
            if was_split:
                self._post_system_message(f"[{fname}] 파일이 크기 초과로 분할 처리되었습니다.")
            self._post_message("system", f"[{fname}] 로드됨")
            self._post_message("editor", response)
            self.chat_history.append({"role": "editor", "content": response})
            self._save_chat_history()

        elif rtype == "inbox_all_done":
            self._set_busy(False)
            self._auto_save_draft("chatting")

        elif rtype == "editor_summary_done":
            content = result["content"]
            self.editor_summary = content
            self._post_message("editor", content)
            self.chat_history.append({"role": "editor", "content": content})
            self._save_chat_history()
            self.stage = "summary_ready"
            self.confirm_gen_btn.configure(state="normal")
            self.coord_done_btn.configure(state="disabled")
            self._auto_save_draft("editor_done", editor_output=content)
            self._set_busy(False)
            self._post_system_message("Editor 요약이 완료되었습니다. [Confirm Document Generation]을 눌러 문서를 생성하세요.")

        elif rtype == "recorder_draft_done":
            draft = result["content"]
            self.recorder_draft = draft
            self._show_recorder_draft(draft)
            self._auto_save_draft("recorder_drafted", recorder_draft=draft)
            self._set_busy(False)

        elif rtype == "error":
            self._post_system_message(f"오류: {result['content']}")
            self._set_busy(False)

    def _show_recorder_draft(self, draft: dict):
        self._post_message("recorder", "=== 생성된 문서 미리보기 ===")
        for key, content in draft.items():
            preview = content[:300] + "..." if len(content) > 300 else content
            self._post_message("recorder", f"[{key}]\n{preview}")

        # Show approve/reject dialog
        win = ctk.CTkToplevel(self)
        win.title("문서 생성 완료 - 검토")
        win.geometry("560x460")
        win.configure(fg_color=th.BG)
        win.grab_set()

        ctk.CTkLabel(
            win, text="Recorder가 문서를 생성했습니다.",
            font=th.FONT_H2, text_color=th.TEXT
        ).pack(pady=(th.PAD + 4, 4), padx=th.PAD, anchor="w")

        ctk.CTkLabel(
            win, text="저장하시겠습니까?",
            font=th.FONT_SMALL, text_color=th.TEXT2
        ).pack(padx=th.PAD, anchor="w")

        def _approve():
            win.destroy()
            self._save_recorder_draft()

        def _reject():
            win.destroy()
            self._post_system_message("저장이 취소되었습니다. 문서를 수동으로 검토한 후 다시 시도하세요.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=th.PAD, padx=th.PAD, anchor="w")
        ctk.CTkButton(
            btn_frame, text="저장", width=100, height=34,
            **th.btn_primary(),
            command=_approve
        ).pack(side="left", padx=(0, th.PAD_SM))
        ctk.CTkButton(
            btn_frame, text="취소", width=80, height=34,
            **th.btn_ghost(),
            command=_reject
        ).pack(side="left")

        # Preview text
        preview_box = ctk.CTkTextbox(
            win, state="normal",
            fg_color=th.SURFACE, text_color=th.TEXT, font=th.FONT_SMALL,
            border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD
        )
        preview_box.pack(fill="both", expand=True, padx=th.PAD, pady=(0, th.PAD))
        for key, content in draft.items():
            preview_box.insert("end", f"\n=== {key} ===\n{content}\n")
        preview_box.configure(state="disabled")

    def _save_recorder_draft(self):
        try:
            self.pm.write_settings_files(self.project_folder, self.recorder_draft)
            self.pm.mark_initialized(self.project_folder)
            self.pm.create_backup(self.project_folder)
            self.pm.delete_temp_draft(self.project_folder)
            self.pm.save_chat_history(self.project_folder, "chat_history_init.json", [])
            self._post_system_message("문서가 저장되었습니다. 백업이 생성되었습니다.")
            self._refresh_left_sidebar()
            self._refresh_right_sidebar()
            if self.on_init_complete:
                self.after(1000, lambda: self.on_init_complete(self.project_folder))
        except Exception as e:
            messagebox.showerror("Error", f"저장 실패: {e}")

    # --- File management ---

    def _view_file(self, path: str):
        fname = os.path.basename(path)
        win = ctk.CTkToplevel(self)
        win.title(FILE_DISPLAY_NAMES.get(fname, fname))
        win.geometry("640x560")
        win.configure(fg_color=th.BG)
        win.grab_set()

        readonly_files = {"project_config.json"}
        if path.endswith(".json"):
            self._view_json_file(win, path, fname)
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
            if fname in readonly_files:
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

    def _view_json_file(self, win: ctk.CTkToplevel, path: str, fname: str):
        import json as _json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
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
            self._render_project_config(scroll, data)
        elif fname == "episodes.json":
            self._render_episodes(scroll, data)
        elif fname in ("chat_history_write.json", "chat_history_setting.json", "chat_history_init.json"):
            self._render_chat_history(scroll, data)
        elif fname == "temp_draft.json":
            self._render_temp_draft(scroll, data)
        else:
            self._render_generic_json(scroll, data)

    def _render_section(self, parent, row: int, title: str, value: str, color: str = None):
        ctk.CTkLabel(
            parent, text=title, font=th.FONT_SMALL,
            text_color=th.TEXT2, anchor="w"
        ).grid(row=row * 2, column=0, sticky="w", pady=(10, 0))
        ctk.CTkLabel(
            parent, text=value or "—", font=th.FONT_BODY,
            anchor="w", wraplength=550, justify="left",
            text_color=color or th.TEXT
        ).grid(row=row * 2 + 1, column=0, sticky="w", padx=th.PAD_SM)

    def _render_project_config(self, parent, data: dict):
        ctk.CTkLabel(
            parent, text="프로젝트 설정",
            font=th.FONT_H1, text_color=th.TEXT
        ).grid(row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
        rows = [
            ("LLM 모델", data.get("llm_model", "—")),
            ("초기화 완료", "예" if data.get("initialized") else "아니오"),
            ("현재 챕터", str(data.get("current_chapter", 1))),
            ("활성 에피소드", data.get("active_episode_id") or "없음"),
        ]
        for i, (label, val) in enumerate(rows):
            self._render_section(parent, i + 1, label, val)

    def _render_episodes(self, parent, data: dict):
        episodes = data.get("episodes", [])
        ctk.CTkLabel(
            parent, text=f"에피소드 목록 ({len(episodes)}개)",
            font=th.FONT_H1, text_color=th.TEXT
        ).grid(row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
        if not episodes:
            ctk.CTkLabel(parent, text="등록된 에피소드가 없습니다.",
                         text_color=th.TEXT3, font=th.FONT_BODY).grid(
                row=1, column=0, sticky="w", pady=th.PAD_SM)
            return
        status_label_map = {
            "planned": "계획됨", "in_progress": "진행 중",
            "completed": "완료", "on_hold": "보류"
        }
        for i, ep in enumerate(episodes):
            ep_card = ctk.CTkFrame(parent, **th.card())
            ep_card.grid(row=i + 1, column=0, sticky="ew", pady=4)
            ep_card.grid_columnconfigure(0, weight=1)
            status_str = status_label_map.get(ep.get("status", ""), ep.get("status", ""))
            title_text = f"{ep.get('title', '제목 없음')}  [{status_str}]"
            ctk.CTkLabel(ep_card, text=title_text, font=th.FONT_H2,
                         text_color=th.TEXT, anchor="w").grid(
                row=0, column=0, padx=th.PAD, pady=(th.PAD_SM, 2), sticky="w")
            if ep.get("description"):
                ctk.CTkLabel(ep_card, text=ep["description"], font=th.FONT_SMALL,
                             text_color=th.TEXT2, anchor="w", wraplength=500).grid(
                    row=1, column=0, padx=th.PAD, pady=(0, 2), sticky="w")
            chapters = ep.get("chapters", [])
            chap_text = f"챕터: {', '.join(str(c) for c in chapters)}" if chapters else "챕터 없음"
            ctk.CTkLabel(ep_card, text=chap_text, font=th.FONT_SMALL,
                         text_color=th.TEXT3, anchor="w").grid(
                row=2, column=0, padx=th.PAD, pady=(0, th.PAD_SM), sticky="w")

    def _render_chat_history(self, parent, data: list):
        ctk.CTkLabel(
            parent, text=f"대화 기록 ({len(data)}개 메시지)",
            font=th.FONT_H1, text_color=th.TEXT
        ).grid(row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
        if not data:
            ctk.CTkLabel(parent, text="대화 기록이 없습니다.",
                         text_color=th.TEXT3, font=th.FONT_BODY).grid(
                row=1, column=0, sticky="w", pady=th.PAD_SM)
            return
        role_label = {"user": "나", "editor": "Editor", "recorder": "Recorder", "system": "System"}
        role_color = {
            "user": th.TEXT2,
            "editor": th.PRIMARY,
            "recorder": "#7B68EE",
            "system": th.TEXT3,
        }
        for i, msg in enumerate(data):
            role = msg.get("role", "user")
            label = role_label.get(role, role)
            color = role_color.get(role, th.TEXT2)
            msg_card = ctk.CTkFrame(parent, **th.card())
            msg_card.grid(row=i + 1, column=0, sticky="ew", pady=3)
            msg_card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(msg_card, text=label, font=th.FONT_SMALL,
                         text_color=color, anchor="w").grid(
                row=0, column=0, padx=th.PAD, pady=(th.PAD_SM, 0), sticky="w")
            ctk.CTkLabel(msg_card, text=msg.get("content", ""), font=th.FONT_BODY,
                         text_color=th.TEXT, anchor="w", wraplength=520, justify="left").grid(
                row=1, column=0, padx=th.PAD, pady=(2, th.PAD_SM), sticky="w")

    def _render_temp_draft(self, parent, data: dict):
        ctk.CTkLabel(
            parent, text="임시 저장 상태",
            font=th.FONT_H1, text_color=th.TEXT
        ).grid(row=0, column=0, sticky="w", pady=(0, th.PAD_SM))
        stage_label = {
            "chatting": "대화 중",
            "writer_done": "Writer 완료",
            "editor_reviewed": "Editor 검토 완료",
            "recorder_drafted": "Recorder 초안 생성",
            "editor_done": "Editor 요약 완료",
        }
        rows = [
            ("저장 시각", data.get("updated_at", "—")),
            ("현재 단계", stage_label.get(data.get("stage", ""), data.get("stage", "—"))),
            ("방", {"writing": "집필실", "init": "초기화", "setting": "설정실"}.get(data.get("room", ""), "—")),
        ]
        for i, (label, val) in enumerate(rows):
            self._render_section(parent, i + 1, label, val)

    def _render_generic_json(self, parent, data):
        import json as _json
        text = ctk.CTkTextbox(
            parent, font=th.FONT_MONO, wrap="word", state="normal",
            fg_color=th.SURFACE, text_color=th.TEXT,
            border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_MD
        )
        text.grid(row=0, column=0, sticky="nsew")
        text.insert("end", _json.dumps(data, ensure_ascii=False, indent=2))
        text.configure(state="disabled")

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
                content = f.read()
            text.insert("end", content)
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

    # --- Helpers ---

    def _set_busy(self, busy: bool, status: str = ""):
        self._agent_running = busy
        self.status_label.configure(text=status)
        state = "disabled" if busy else "normal"
        self.inbox_btn.configure(state=state)
        if self.stage == "chatting":
            self.coord_done_btn.configure(state=state)
        if self.stage == "summary_ready" and not busy:
            self.confirm_gen_btn.configure(state="normal")

    def _auto_save_draft(self, stage: str, editor_output: str = "", recorder_draft=None):
        data = {
            "room": "init",
            "stage": stage,
            "chapter_number": None,
            "active_episode_id": None,
            "user_input": self.chat_history[-1]["content"] if self.chat_history else "",
            "writer_output": None,
            "editor_output": editor_output,
            "recorder_draft": recorder_draft,
        }
        try:
            self.pm.save_temp_draft(self.project_folder, data)
        except Exception:
            pass

    def _save_chat_history(self):
        try:
            self.pm.save_chat_history(self.project_folder, "chat_history_init.json", self.chat_history)
        except Exception:
            pass

    def _restore_chat_history(self):
        """Load chat history from file and restore UI. Also check temp_draft for stage state."""
        history = self.pm.load_chat_history(self.project_folder, "chat_history_init.json")
        if not history:
            return

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self._post_message(role, content)
        self.chat_history = history

        draft = self.pm.load_temp_draft(self.project_folder)
        if not draft or draft.get("room") != "init":
            return

        stage = draft.get("stage", "chatting")
        if stage == "editor_done":
            self.editor_summary = draft.get("editor_output", "")
            self.stage = "summary_ready"
            self.confirm_gen_btn.configure(state="normal")
            self.coord_done_btn.configure(state="disabled")
        elif stage == "recorder_drafted" and draft.get("recorder_draft"):
            self.editor_summary = draft.get("editor_output", "")
            self.recorder_draft = draft["recorder_draft"]
            self.stage = "recorder_done"
