# Implementation Checklist

> Tracks progress against PROJECT_DESIGN.md. Updated after each work session.
> Last updated: 2026-03-16

---

## Overall Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Project foundation + Initialization Stage | ✅ Complete |
| Phase 1.5 | UI 개선 (디자인, 내비게이션, i18n, 프로젝트 삭제) | ✅ Complete |
| Phase 2 | Writing Room | ✅ Complete |
| Phase 3 | Settings Organization Room | ⬜ Not Started |
| Phase 4 | Episode Management Room | ⬜ Not Started |
| Phase 5 | Polish + PyInstaller build | ⬜ Not Started |

---

## Phase 1 — Foundation & Initialization Stage

### Infrastructure
- [x] Project folder structure creation (`settings/`, `chapters/`, `context/`, `inbox/`, `backup/`)
- [x] `project_config.json` schema + read/write
- [x] `episodes.json` default scaffold
- [x] `chat_history_write.json` / `chat_history_setting.json` init
- [x] `ProjectManager` class (create, load, list, backup, temp_draft, scan_inbox)
- [x] `chapters/` scan → `current_chapter` auto-calculation on load
- [x] `create_backup()` via `shutil.copytree` (excludes `backup/` recursion)
- [x] Project name validation (Windows invalid chars `\ / : * ? " < > |`)
- [x] `temp_draft.json` auto-save + session recovery on relaunch

### LLM Layer
- [x] `BaseLLMProvider` interface
- [x] `OllamaProvider` → `crewai.LLM(model="ollama/{model}")` (LiteLLM routing)
- [x] `get_available_models()` via `ollama list` parsing
- [x] `OPENAI_API_KEY=NA` dummy injection (CrewAI compatibility)
- [x] Model-not-found warning on project load (model in config no longer installed)

### Agent Layer
- [x] `AgentFactory` class
- [x] `create_editor_agent(llm, context)` — Korean web novel editor
- [x] `create_recorder_agent(llm, context)` — document generator
- [x] `create_writer_agent(llm, context)` — stub (Phase 2)
- [x] Context injection into agent `backstory`

### Loop Controller
- [x] `ManualLoopController` skeleton
- [x] `run_init_editor()` — Editor Q&A during initialization
- [x] `run_init_editor_summary()` — full summary on [Coordination Complete]
- [x] `run_init_recorder()` — 5-file document generation
- [x] `run_inbox_file()` — inbox file processing with chunk splitting (>10,000 chars)
- [x] 3-retry exponential backoff on Ollama connection failure
- [x] `_parse_recorder_output()` — section marker parsing
- [ ] `run_writing_loop()` — full implementation (Phase 2)

### GUI — Project Selection Screen
- [x] Existing project list with selection highlight
- [x] Create new project (name validation, inline error label)
- [x] Ollama model dropdown (async load via background thread)
- [x] Model saved to `project_config.json` on open/create
- [x] Model-not-found warning display

### GUI — Initialization Stage (3-panel layout)
- [x] Left sidebar: settings/context file list (populated after Recorder finishes)
- [x] Center: chat area with role-colored speaker labels
- [x] Center: user input field (Ctrl+Enter to send)
- [x] Center: [Check Inbox] button → file list dialog → Editor processes sequentially
- [x] Center: [Coordination Complete] button → Editor summary
- [x] Center: [Confirm Document Generation] button (enabled after summary)
- [x] Right sidebar: full project file list (View / Edit / Delete)
- [x] Right sidebar: [+ New File] button
- [x] Recorder draft preview dialog (Approve / Reject)
- [x] Save on approve → `mark_initialized()` → `create_backup()` → delete temp_draft
- [x] Chapter delete warning popup
- [x] Background thread + `queue.Queue` + `root.after(100)` polling (no UI blocking)
- [x] `temp_draft.json` auto-save after each agent response
- [x] Session resume offer on relaunch (temp_draft detection)
- [ ] Inbox overflow warning display (was_split flag is passed but UI message is basic)
- [ ] Editor context cross-check after manual context file edit (Scenario 6) → **moved to Phase 2**

### Logging
- [x] `src/logger.py` — RotatingFileHandler (`logs/app.log`) + console handler
- [x] `llm_provider`: model creation, ollama list result
- [x] `loop_controller`: agent call start/end, retry warnings, errors
- [x] `project_manager`: project create/load, backup
- [x] `main.py`: app start/stop

---

## Phase 2 — Writing Room

### Loop Controller
- [x] `run_writer()` — Writer agent: body text + structured design-intent output
- [x] `run_editor_review()` — Editor: 7-point checklist (first pass) / pass-fail (revision)
- [x] `run_writer_revision()` — Writer revision with editor + user feedback
- [x] `run_writing_recorder()` — Recorder: story_context.md + character_relations.md rewrite
- [x] Max 2 revision rounds enforcement + "무시하고 승인" guidance (Scenario 4)
- [x] `_parse_writer_output()` — section marker parsing
- [x] `_parse_writing_recorder_output()` — section marker parsing

### GUI — Writing Room (3-panel layout)
- [x] Left sidebar: settings/context file list + current chapter/episode display
- [x] Center: chat area (Writer / Editor / System messages with role colors)
- [x] Center: user input (Ctrl+Enter to send)
- [x] Center: [Approve] / [Request Revision] / [무시하고 승인] buttons
- [x] Center: Recorder review dialog ([저장] / [취소])
- [x] Right sidebar: file management (View / Edit / Delete — same as init screen)
- [x] Chapter file save (`chapters/N화.txt`)
- [x] `story_context.md` full rewrite after chapter approval
- [x] `character_relations.md` full rewrite after chapter approval
- [x] `chat_history_write.json` persistence
- [x] `temp_draft.json` auto-save during writing pipeline
- [x] Session restore from temp_draft on relaunch
- [ ] Room selector tabs: [집필실] / [설정실] / [에피소드 관리] — Phase 3/4에서 추가

---

## Phase 3 — Settings Organization Room

- [ ] Step 1: Editor compresses user input into structured setting items
- [ ] Step 2: conflict check vs existing settings files
- [ ] Conflict resolution UI (Adopt / Keep / Edit Manually) per item
- [ ] File routing UX (Editor suggests target file, user confirms/overrides)
- [ ] Step 3: write decisions to settings files
- [ ] Cascading conflict re-check after each resolution (max 3 rounds, Scenario 7)
- [ ] Backup trigger on settings write
- [ ] `chat_history_setting.json` persistence

---

## Phase 4 — Episode Management Room

- [ ] `episodes.json` read/write
- [ ] Episode list panel (title, status, order)
- [ ] Episode detail panel (title, description, goal, key_events, status)
- [ ] Chapter list panel (chapters assigned to selected episode)
- [ ] Create / rename / reorder episodes
- [ ] Status change (`planned` / `in_progress` / `completed` / `on_hold`)
- [ ] Assign active episode → saved to `project_config.json`
- [ ] Chapter-to-episode assignment (uniqueness warning, Scenario: move chapter)
- [ ] Chapter delete → context inconsistency warning + backup restore suggestion
- [ ] 우측 사이드바에서 `episodes.json` Edit 버튼 제거 → 에피소드 관리 화면에서만 편집 가능하도록

---

## Phase 5 — Polish & Build

- [ ] PyInstaller `.spec` file
- [ ] Single-file EXE build test (Windows)
- [ ] App icon
- [ ] Ollama server down → reconnect flow from `temp_draft` (Scenario 10)
- [ ] Settings backup restore UI in file management sidebar
- [ ] End-to-end test: new project → init → write chapter 1 → save

---

## Known Issues / TODO

- CrewAI `verbose=False` still prints execution trace prompt to stdout (cosmetic)
- `run_writing_loop()` is a stub (raises NotImplementedError)

---

## Git Log Summary

| Commit | Message |
|--------|---------|
| `2c6671f` | feat: 단계별 로깅 추가 |
| `2aa4b16` | fix: LLM 프로바이더 crewai.LLM으로 교체 |
| `e1fbcdf` | fix: CrewAI OPENAI_API_KEY 더미값 주입 |
| `478fe8b` | fix: CTkTextbox tag_config font 옵션 제거 |
| `c0cb0cb` | feat: 1단계 구현 |
| `3eddb48` | chore: 프로젝트 초기 설정 |
