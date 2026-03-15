import os
import queue
import threading
import customtkinter as ctk
from tkinter import messagebox, simpledialog

from src import i18n
from src.loop_controller import ManualLoopController
from src.project_manager import ProjectManager


CHAT_ROLES = {
    "user": ("You", "gray70"),
    "editor": ("Editor", "#4A90D9"),
    "recorder": ("Recorder", "#7B68EE"),
    "system": ("System", "gray50"),
}


class InitializationScreen(ctk.CTkFrame):
    def __init__(self, master, project_folder: str, result_queue: queue.Queue,
                 on_init_complete=None, **kwargs):
        super().__init__(master, **kwargs)
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

        # Left sidebar
        self._build_left_sidebar()
        # Center chat area
        self._build_chat_area()
        # Right sidebar
        self._build_right_sidebar()

    def _build_left_sidebar(self):
        frame = ctk.CTkFrame(self, width=200)
        frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        frame.grid_propagate(False)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text=i18n.t("settings_files"), font=ctk.CTkFont(family="Malgun Gothic", size=13, weight="bold")).grid(
            row=0, column=0, pady=(12, 4), padx=8
        )
        self.left_file_list = ctk.CTkScrollableFrame(frame)
        self.left_file_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))
        self.left_file_list.grid_columnconfigure(0, weight=1)

        project_name = self.pm.get_project_name(self.project_folder)
        ctk.CTkLabel(frame, text=i18n.t("project_label") + ":\n" + project_name, text_color="gray", wraplength=180,
                     font=ctk.CTkFont(family="Malgun Gothic", size=13)).grid(
            row=2, column=0, pady=(0, 12), padx=8
        )

    def _build_chat_area(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=8)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Chat display
        self.chat_display = ctk.CTkTextbox(frame, state="disabled", wrap="word",
                                           font=ctk.CTkFont(family="Malgun Gothic", size=13))
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))

        # Input area
        input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        input_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        input_frame.grid_columnconfigure(0, weight=1)

        self.user_input = ctk.CTkTextbox(input_frame, height=80, wrap="word",
                                         font=ctk.CTkFont(family="Malgun Gothic", size=13))
        self.user_input.grid(row=0, column=0, sticky="ew", columnspan=2)
        self.user_input.bind("<Control-Return>", self._on_send)

        send_btn = ctk.CTkButton(input_frame, text=i18n.t("send_btn"), width=140, command=self._on_send)
        send_btn.grid(row=1, column=0, sticky="e", pady=(4, 0))

        # Action buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

        self.inbox_btn = ctk.CTkButton(btn_frame, text=i18n.t("check_inbox"), command=self._on_check_inbox)
        self.inbox_btn.pack(side="left", padx=(0, 8))

        self.coord_done_btn = ctk.CTkButton(
            btn_frame, text=i18n.t("coord_done"),
            fg_color="#E67E22", hover_color="#CA6F1E",
            command=self._on_coordination_done
        )
        self.coord_done_btn.pack(side="left", padx=(0, 8))

        self.confirm_gen_btn = ctk.CTkButton(
            btn_frame, text=i18n.t("confirm_gen"),
            fg_color="#27AE60", hover_color="#1E8449",
            command=self._on_confirm_generation,
            state="disabled"
        )
        self.confirm_gen_btn.pack(side="left")

        self.status_label = ctk.CTkLabel(btn_frame, text="", text_color="gray")
        self.status_label.pack(side="right", padx=(8, 0))

    def _build_right_sidebar(self):
        frame = ctk.CTkFrame(self, width=220)
        frame.grid(row=0, column=2, sticky="nsew", padx=(4, 8), pady=8)
        frame.grid_propagate(False)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text=i18n.t("project_files"), font=ctk.CTkFont(family="Malgun Gothic", size=13, weight="bold")).grid(
            row=0, column=0, pady=(12, 4), padx=8
        )
        self.right_file_list = ctk.CTkScrollableFrame(frame)
        self.right_file_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.right_file_list.grid_columnconfigure(0, weight=1)

        new_file_btn = ctk.CTkButton(frame, text=i18n.t("new_file"), command=self._on_new_file)
        new_file_btn.grid(row=2, column=0, pady=(0, 12), padx=8, sticky="ew")

    def _refresh_right_sidebar(self):
        for w in self.right_file_list.winfo_children():
            w.destroy()
        files = self._get_all_project_files()
        for i, fpath in enumerate(files):
            rel = os.path.relpath(fpath, self.project_folder)
            row_frame = ctk.CTkFrame(self.right_file_list, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", pady=1)
            row_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(row_frame, text=rel, anchor="w", wraplength=140).grid(row=0, column=0, sticky="w")
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.grid(row=1, column=0, sticky="w")

            ctk.CTkButton(btn_frame, text=i18n.t("view"), width=40, height=20,
                          command=lambda p=fpath: self._view_file(p)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text=i18n.t("edit"), width=40, height=20,
                          command=lambda p=fpath: self._edit_file(p)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text=i18n.t("delete"), width=40, height=20,
                          fg_color="#E74C3C", hover_color="#C0392B",
                          command=lambda p=fpath: self._delete_file(p)).pack(side="left", padx=2)

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
            rel = os.path.relpath(fpath, self.project_folder)
            btn = ctk.CTkButton(
                self.left_file_list, text=rel, anchor="w",
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
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
        label, color = CHAT_ROLES.get(role, ("Unknown", "white"))
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\n[{label}]\n", f"role_{role}")
        self.chat_display.insert("end", content + "\n", "content")
        self.chat_display.tag_config(f"role_{role}", foreground=color)
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
        win.geometry("500x400")
        win.grab_set()

        ctk.CTkLabel(win, text="Recorder가 문서를 생성했습니다.", font=ctk.CTkFont(size=14)).pack(pady=16)
        ctk.CTkLabel(win, text="저장하시겠습니까?", text_color="gray").pack()

        def _approve():
            win.destroy()
            self._save_recorder_draft()

        def _reject():
            win.destroy()
            self._post_system_message("저장이 취소되었습니다. 문서를 수동으로 검토한 후 다시 시도하세요.")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=24)
        ctk.CTkButton(btn_frame, text="Approve & Save", fg_color="#27AE60",
                      command=_approve).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Reject", fg_color="#E74C3C",
                      command=_reject).pack(side="left", padx=8)

        # Preview text
        text = ctk.CTkTextbox(win, state="normal")
        text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        for key, content in draft.items():
            text.insert("end", f"\n=== {key} ===\n{content}\n")
        text.configure(state="disabled")

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
        win = ctk.CTkToplevel(self)
        win.title(os.path.basename(path))
        win.geometry("600x500")
        text = ctk.CTkTextbox(win, state="normal")
        text.pack(fill="both", expand=True, padx=8, pady=8)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            text.insert("end", content)
        except Exception as e:
            text.insert("end", f"Could not read file: {e}")
        text.configure(state="disabled")

    def _edit_file(self, path: str):
        win = ctk.CTkToplevel(self)
        win.title(f"Edit: {os.path.basename(path)}")
        win.geometry("600x500")
        text = ctk.CTkTextbox(win, state="normal")
        text.pack(fill="both", expand=True, padx=8, pady=(8, 0))
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

        ctk.CTkButton(win, text="Save", command=_save).pack(pady=8)

    def _delete_file(self, path: str):
        rel = os.path.relpath(path, self.project_folder)
        in_chapters = path.startswith(os.path.join(self.project_folder, "chapters"))
        msg = f"Delete '{rel}'?"
        if in_chapters:
            msg += "\n\n⚠️ Deleting a chapter file may make context files inconsistent."
        if not messagebox.askyesno("Delete File", msg):
            return
        try:
            os.remove(path)
            self._refresh_right_sidebar()
            self._refresh_left_sidebar()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_new_file(self):
        name = simpledialog.askstring("New File", "File name (relative to project folder):")
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

        # Restore chat display
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self._post_message(role, content)
        self.chat_history = history

        # Check temp_draft for stage (summary_ready / recorder_drafted)
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
