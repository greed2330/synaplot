# Web Novel AI Writer Team — Project Design Document

> ⚠️ This document is continuously updated. Always interpret it based on the latest version.
> Last updated: 2026-03-16 (all gaps resolved — temp_draft schema, inbox UX, episode optionality, model UI location, chapter uniqueness, settings backup, project name validation)

---

## 1. Final Project Goal

A **desktop GUI application for collaborative web novel writing** that uses a local Ollama model and CrewAI multi-agent orchestration.

- UI: local desktop app built with CustomTkinter
- LLM: local Ollama (currently based on gemma2:9b, replaceable later)
- Distribution: PyInstaller EXE
- Core value: the user sets the direction, and the AI agent team collaborates to write

---

## 2. Overall User Flow

```
[Launch App]
    ↓
[Project Selection Screen]
  ├─ Select Existing Project → Load that working folder
  └─ Create New Project → Auto-create working folder → Enter initialization stage
    ↓
[Initialization Stage] ← Only for new projects
    ↓
[Room Selection]
  ├─ 📝 Novel Writing Room
  ├─ ⚙️  Settings Organization Room
  └─ 🗂️  Episode Management Room   ← A fully separate screen from the writing room
```

---

## 3. Initialization Stage (When Starting a New Project)

### Purpose
Create the working folder structure + produce the novel’s foundation documents (worldbuilding, plot, settings, etc.)

### Active Agent
**Only the Editor Agent** is active.
- The Writer may drift off-course due to creative impulse.
- The Editor is better suited to identify missing pieces and contradictions through structured questioning.
- The Recorder appears only when documents need to be generated.

### Flow
```
[App automatically creates working folder]
              ↓
[Editor] Receives and begins coordinating the user’s ideas
  - If the user places idea notes (txt/md) into the designated folder, the app reads and forwards them
  - If a file exceeds the size limit, it is automatically split into chunks and processed sequentially / an overflow warning is shown
  - The Editor fills gaps through structured questions
              ↓
[User] Clicks [Coordination Complete]
              ↓
[Editor] Outputs a full summary of the discussion
              ↓
[Recorder] Called → Generates all initial documents in one batch
              ↓
[Writing Room becomes accessible]
```

### Documents Generated During Initialization
- `settings/세계관.md` — worldbuilding settings
- `settings/줄거리.md` — overall big-picture plot
- `settings/소설설정.md` — characters, abilities, rules, etc.
- `context/story_context.md` — initially empty file (filled later by the Recorder after writing begins)
- `context/character_relations.md` — initial character knowledge state (based on the Editor’s coordination)

---

## 4. Agent Structure and Roles

### ✍️ Writer Agent
- Active in: Writing Room
- Writes the novel body based on the user’s repertoire, worldbuilding documents, and context summary
- After writing, also outputs a **structured design-intent summary** so the Recorder and Editor can reference it without inference
  ```
  Confirmed facts:
  - Character A learns B’s true identity
  - Location X is destroyed

  Foreshadowing planted:
  - Hint about C’s past (optionally specifying the planned payoff chapter)

  Changes to existing settings:
  - None
  ```

### 🔍 Editor Agent
- Active in: Initialization Stage (solo) / Writing Room / Settings Organization Room
- **Initialization Stage**: coordinates worldbuilding/settings through structured questions
- **Writing Room**: cross-checks the body text + design intent + `story_context.md` + `character_relations.md`, then reviews rigorously
  - Whether foreshadowing has been suddenly forgotten
  - Whether the narrative flow jumps or leaks off-track
  - Whether anything conflicts with the worldbuilding
  - Whether the design intent was actually realized in the text
  - Whether a character mentions information they could not know
  - Whether monologue/internal thoughts are being treated as known by other characters
- Presents review results as numbered points
  - Example: "✅ Foreshadowing A from Chapter 3 is paid off in this chapter."
  - Example: "⚠️ This part conflicts with worldbuilding setting X."
  - Example: "⚠️ A is not yet in a position to know B’s ability."
- **Settings Organization Room**: checks new ideas against existing settings for conflicts

### 📦 Recorder Agent
- Active in: after initialization is completed / after a chapter is approved in the Writing Room
- Manages three file categories (one file each is kept, and the whole file is rewritten each time without append)
- **Requires user review before saving** (approve/reject; if rejected, the user edits manually and then saves)
- Hallucination prevention: does not directly analyze the body text; references only the Writer’s structured fact list

  **① Main chapter file** (`chapters/n화.txt`)
  - Stores the finalized chapter body text (a new file is created for each chapter)

  **② Context summary file** (`context/story_context.md`)
  - One file is maintained and fully rewritten whenever a chapter is completed
  ```
  [Foreshadowing List]
  - Chapter n: foreshadowing content (unresolved/resolved)

  [Story Flow]
  - Chapter 1: summary of key events
  - Chapter 2: ...

  [Confirmed Setting Changes]
  - Changed/added worldbuilding settings
  ```

  **③ Character relationships and knowledge-state file** (`context/character_relations.md`)
  - One file is maintained and fully rewritten whenever a chapter is completed
  ```
  [Character A] (as of Chapter n)
  ✅ Knows: B’s name (Chapter 1), that C belongs to the organization (Chapter 3)
  ❌ Does not know: B’s ability, B’s past
  🤔 Suspects / is guessing: a sense that B is hiding something (Chapter 4~)
  ```

---

## 5. Writing Pipeline

```
[User] Inputs direction / ideas / repertoire for this chapter
              ↓
[Writer] Outputs novel body text + structured design intent → displayed in the chat area
              ↓
[Editor] Cross-checks the body text + design intent + all context files
        → presents issues as numbered points → displayed in the chat area
              ↓
[User] Reviews item by item and gives final instructions
    ✅ Keep this  🔧 Fix this + my opinion
              ↓
    ├─ If revisions exist → [Writer] receives only the finalized instructions and rewrites (context reset)
    │                    → [Editor] judges pass/fail only
    │                    → If fail, asks the user for another judgment (maximum 2 rounds)
    │
    └─ If everything is approved → [Recorder] outputs draft → user reviews → save confirmed
```

### Loop Design Principles
- Context reset every round: the Writer always receives only (settings + context summary + repertoire + latest draft + latest instructions)
- 2-round limit: if it still fails after 2 revisions, the user intervenes directly
- Feedback owners are the Editor + the user: the Editor finds issues, and the user finalizes the direction before passing it to the Writer

---

## 6. Settings Organization Room Pipeline

```
[User] Inputs a batch of ideas or drops in a file
              ↓
[Step 1 - Compression]
  The Editor Agent breaks the original input into structured setting items
  (If a file is provided, the app checks its size → if too large, it splits it into chunks and processes them sequentially)
              ↓
[Step 2 - Conflict Review]
  Compare organized items vs existing settings files
  If a conflict is found, present each case to the user one by one:
  "⚠️ [New Idea] conflicts with existing setting [X].
   → [Adopt New Idea] [Keep Existing Setting] [Edit Manually]"
              ↓
[User] Makes item-by-item decisions
              ↓
[Step 3 - Apply to Settings Files]
  Apply the chosen decisions to the existing settings files
```

---

## 7. UI Architecture

### 7-1. Overall Screen Structure

```
[Project Selection Screen]
    ↓
[Initialization Stage] (new projects only)
    ↓
┌──────────────────────────────────────────────┐
│  [Room Selection]  📝 Writing Room   ⚙️ Settings Room │
├───────────┬──────────────────┬───────────────┤
│  Left Side │    Chat Area      │  File Mgmt    │
│ (Settings) │   (Main Area)     │   Sidebar     │
└───────────┴──────────────────┴───────────────┘
```

### 7-2. Left Sidebar — Settings Management
- Select worldbuilding/settings documents
- Episode arc list and current active episode (Writing Room only)

### 7-3. Main Area — Chat Area
- Displays agent messages with clear speaker separation
- Shows the current episode/chapter at the top (Writing Room only)
- User input field
- Context-sensitive action buttons (enabled depending on pipeline stage):
  - Writing Room: [Approve] [Request Revision]
  - Settings Organization Room: [Adopt] [Keep] [Edit Manually]
  - Recorder review: [Confirm Save] [Edit Manually Then Save]
  - Initialization Stage: [Coordination Complete]

### 7-4. Right Sidebar — File Management
- Shows the full file list of the current project folder
- Per-file actions: [View] [Edit] [Delete]
- [+ Create New File] button
- Also serves as a direct manual-edit path for settings files (accessible even without entering the Settings Organization Room)

---

## 8. Project File Structure

```
projects/
└── {project_name}/              # New conversation room = new project folder
    ├── settings/                # Worldbuilding/settings documents
    │   ├── 세계관.md
    │   ├── 줄거리.md
    │   └── 소설설정.md
    ├── chapters/                # Finalized chapter files (managed by Recorder)
    │   ├── 1화.txt
    │   └── 2화.txt
    ├── context/                 # Context files for agents (managed by Recorder, one file each)
    │   ├── story_context.md
    │   └── character_relations.md
    ├── inbox/                   # Folder where the user places idea files
    │   └── 아이디어노트.txt
    ├── backup/                  # Automatic backups (snapshot created whenever Recorder finishes work)
    │   ├── 001_20260316_143022/
    │   ├── 002_20260316_151045/
    │   └── 003_20260316_163312/
    ├── temp_draft.json            # Automatic temporary save in case the app is forcibly closed
    ├── project_config.json        # Stores app/LLM settings and project state
    ├── episodes.json              # Episode and chapter structure data
    ├── chat_history_write.json    # Writing Room conversation history
    └── chat_history_setting.json  # Settings Organization Room conversation history
```

---

## 9. Technical Considerations and Safeguards

### Handling gemma2:9b limitations
- Always pass the following to agents: settings files (required sections) + `story_context.md` + `character_relations.md`
- Split settings files into [Required Items] / [Detailed Items] sections → always include required items; include only the current episode’s detailed items
- Do not pass the full novel text to agents → `story_context.md` replaces it
- Control context file size by fully rewriting instead of append
- The Writer explicitly outputs design intent as a structured list → minimizes inference burden on the Recorder and Editor

### Hallucination safeguards
- The Recorder does not directly analyze the body text and uses only the Writer’s fact list
- Recorder output must always be user-reviewed before saving

### Initialization contamination prevention (Scenario 2)
- When [Coordination Complete] is clicked, the Editor outputs a summary of finalized contents
- The Recorder is called only after the user reviews that summary and clicks [Confirm Document Generation]
- This adds one more user confirmation step to prevent contamination

### Automatic backup system (Scenario 8)
- Trigger: whenever the Recorder finishes work (chapter save, context file update, initialization completion, etc.)
- Method: create a full project-folder snapshot via Python `shutil.copytree()` or `zipfile` (no AI needed)
- Save location: `backup/001_20260316_143022/` format (work number + timestamp)
- The file-management sidebar can display backup history and allow rollback to a specific point

### Safeguard when deleting chapters (Scenario 5)
- Show a warning popup when deletion of files inside `chapters/` is detected
- Integrate with backup system to suggest rolling back context files to a backup from before that point
  ```
  "Deleting Chapter n will make the context files inconsistent. Restore from backup?"
  → [Restore from Backup] [Delete Anyway]
  ```

### Handling forced app termination (Scenario 9)
- As soon as agent output appears in the chat area, auto-save it into `temp_draft.json`
- On app relaunch, detect the temp file → offer: "Would you like to continue your previous work?"

### Handling Ollama server downtime (Scenario 10)
- 3 retry attempts (exponential backoff)
- After 3 failures, show: "Please check the Ollama server"
- After reconnection, continue from `temp_draft`

### Editor checklist (prompt)
```
Writing Room review checklist:
1. Has the user’s repertoire actually been reflected in the body text? (Scenario 3)
2. Has any foreshadowing been suddenly forgotten?
3. Does the narrative flow jump or leak off-track?
4. Does anything conflict with the worldbuilding?
5. Has the design intent been realized in the body text?
6. Does any character mention information they could not know?
7. Are monologue/internal thoughts being treated as known by other characters?
```

### Guidance after 2 failed rounds (Scenario 4)
```
"Even after 2 revisions, [the cited issue] has not been resolved."
→ [Ignore This Issue and Continue] [Edit Manually]
```

### Detecting inconsistencies between context files (Scenario 6)
- If the user manually edits and saves context files, ask the Editor to cross-check the two files once with a short call

### Detecting cascading conflicts in the Settings Organization Room (Scenario 7)
- After resolving a conflict, rerun conflict checking based on the updated settings
- Loop until there are no conflicts left (maximum 3 rounds)

### Processing order for multiple inbox files (Scenario 1)
- Sort by filename or creation date, then process sequentially
- Before processing, show the user the list and order for confirmation

### Major problems in the current codebase (needs improvement)
- Simple one-time sequential execution of Writer → Editor → Recorder (no loop)
- Infinite append accumulation in `lore.txt`
- Deprecated use of `langchain_community.llms.Ollama`
- Missing `context` parameter passing between Tasks

---

## 10. Episode & Chapter Structure

- **Episode** = a story-arc container (e.g. "The protagonist dies," Chapters 1–10) — defined directly by the user
- **Chapter** = the actual writing unit — agents write at the chapter level

### Episode Management Room Layout
A fully separate screen from the Writing Room. It does not alter the existing 3-panel Writing Room layout.

```
┌──────────────┬─────────────────────┬──────────────────┐
│ Episode List │ Selected Episode    │ Chapters in This │
│              │ Details             │ Episode          │
└──────────────┴─────────────────────┴──────────────────┘
```

**Episode List Panel**
- Shows episode title, status, and order within the story

**Episode Detail Panel**
- Title, short description, episode goal, key events (3–5 bullets), and status display
- Status values: `planned` / `in_progress` / `completed` / `on_hold`

**Chapter List Panel**
- Shows chapter number, title, and completion state
- Chapters are the actual units written in the Writing Room

### Episode Feature Scope for v1
Included:
- create episode / rename episode / change status / reorder / assign active episode / edit description and goal

Excluded from v1 (to avoid excessive complexity):
- kanban boards, timeline editors, drag-and-drop plot structures, complex story planners

---

## 11. Software Architecture Layers

### Overall Layer Structure
```
GUI
 ↓
LoopController
 ↓
AgentFactory
 ↓
LLM Provider  (returns a CrewAI-compatible LLM object)
 ↓
CrewAI Agents
 ↓
Model (Ollama, etc.)
```

### LoopController
- Separated so that the GUI does not directly contain agent-loop logic
- Responsibilities: call Writer → call Editor → determine whether revision is needed → enforce maximum 2 rounds → return result status
- v1: `ManualLoopController` (manual `while` loop)
- Future: interface separation so it can be replaced with `CrewFlowLoopController`

```
LoopController (interface)
  ├─ ManualLoopController   ← v1 implementation
  └─ CrewFlowLoopController ← replaceable later
```

### AgentFactory
- Receives context from the LoopController and creates CrewAI agents
- Injected inputs:
  - a CrewAI-compatible LLM object returned by the LLM Provider
  - current context files (`settings`, `story_context.md`, `character_relations.md`)
- Creates agents by injecting context into agent backstories
- Creates fresh agent instances every loop round (to preserve the context-reset principle)

### LLM Provider
- Role: manages model settings and acts as a factory that returns LLM objects accepted by CrewAI / LangChain
- v1: `OllamaProvider` → internally creates and returns `langchain_ollama.OllamaLLM(...)`
- Future: `OpenAIProvider`, `AnthropicProvider` can be added

```
BaseLLMProvider (interface)
  ├─ OllamaProvider    ← v1 implementation, returns OllamaLLM
  ├─ OpenAIProvider    ← future
  └─ AnthropicProvider ← future
```

### Model Selection UI
- Check Ollama availability: run `ollama list` → if it fails, show an error message
- Auto-detect installed models: parse `ollama list` → populate a dropdown list
- Store model settings in `project_config.json`

```json
{
  "llm_provider": "ollama",
  "llm_model": "gemma2:9b",
  "initialized": false,
  "current_chapter": 1,
  "active_episode_id": null
}
```
- `initialized`: false until the Initialization Stage is completed; gates access to the Writing Room
- `current_chapter`: the next chapter number to be written; determined by `max(existing chapter numbers) + 1` on load, falling back to 1 if `chapters/` is empty
- `active_episode_id`: references an episode `id` in `episodes.json`; used by the Writing Room left sidebar
- `project_name` is intentionally omitted — it is always derived from `os.path.basename(project_folder)` to prevent config/folder name desync
- If a previously selected model no longer exists, show a warning in the UI

---

## 12. Data Schemas

### episodes.json

Stores all episode and chapter-assignment data. Kept separate from `project_config.json` because it is story data, not app configuration.

```json
{
  "episodes": [
    {
      "id": "ep1",
      "title": "Prologue",
      "status": "completed",
      "description": "Introduction to the world and the protagonist",
      "goal": "Let the reader understand the setting and protagonist before the main conflict begins",
      "key_events": [
        "Protagonist's first appearance",
        "First manifestation of the ability"
      ],
      "chapters": [1, 2]
    },
    {
      "id": "ep2",
      "title": "Growth Arc",
      "status": "in_progress",
      "description": "",
      "goal": "",
      "key_events": [],
      "chapters": [3, 4, 5]
    }
  ]
}
```

- `status` values: `planned` / `in_progress` / `completed` / `on_hold`
- `chapters` contains chapter numbers (integers) matching the filenames in `chapters/`
- Episode order in the array is the display order; reordering = reordering the array

### Chapter numbering rule

- On project load: scan `chapters/` → `current_chapter = max(existing numbers) + 1`; if folder is empty, `current_chapter = 1`
- Deleting a chapter does not reuse that number — the next chapter always gets `max + 1`
- This prevents filename collisions when a chapter is deleted and then recreated

---

## 13. GUI Threading Model

All LLM calls (CrewAI agent execution) must run on a background thread. CustomTkinter (Tkinter-based) crashes if its widgets are updated from a non-main thread.

### Pattern

```
Main UI thread
    │
    ├─ spawns ──► Worker Thread  (runs CrewAI agent, blocks here for seconds/minutes)
    │                │
    │                └─ puts result into queue.Queue()
    │
    └─ root.after(100, poll_queue)  ◄─ polls queue every 100ms, updates UI safely
```

### Implementation sketch

```python
import threading, queue

result_queue = queue.Queue()

def run_agent_thread(agent_fn, *args):
    result = agent_fn(*args)
    result_queue.put(result)

def poll_queue():
    try:
        result = result_queue.get_nowait()
        update_chat_area(result)   # safe: runs on main thread
    except queue.Empty:
        pass
    root.after(100, poll_queue)   # reschedule

# To start an agent call:
threading.Thread(target=run_agent_thread, args=(writer_agent.run, inputs), daemon=True).start()
poll_queue()
```

- Worker threads are daemon threads (they die with the app)
- All widget updates happen exclusively through `root.after()` callbacks on the main thread
- Agent cancellation: pass a `threading.Event` stop flag into the worker; check it between pipeline steps

---

## 14. Settings Organization Room — File Routing

When the Editor has compressed user input into structured setting items (Step 1), each item must be assigned to one of the existing settings files before being written.

### Routing UX

The Editor auto-classifies each item and presents its suggestion. The user confirms or overrides via a dropdown — they do not need to classify from scratch:

```
Apply this item to which file?

  Editor's suggestion: [ 소설설정.md ▼ ]   ← user can change
  [ Confirm ]
```

This keeps hallucination risk low (human has final say) while reducing user cognitive load (Editor does the first-pass classification).

### Routing order

1. Editor classifies all items in one pass
2. User confirms/changes file assignment for each item
3. Only after all assignments are confirmed does Step 3 (actual file write) begin

---

## 15. Remaining Design Decisions (Finalized)

### temp_draft.json schema

Auto-saved whenever an agent output appears in the chat area. Used to offer session recovery on next launch.

```json
{
  "room": "writing",
  "stage": "editor_reviewed",
  "chapter_number": 12,
  "active_episode_id": "ep3",
  "user_input": "I want the protagonist to start suspecting the other character's identity in this chapter",
  "writer_output": "...",
  "editor_output": "...",
  "recorder_draft": null,
  "updated_at": "2026-03-16T15:42:10"
}
```

- `stage` values: `writer_done` / `editor_reviewed` / `recorder_drafted`
- `recorder_draft`: null until the Recorder produces output; contains the 3-file draft object once it does
- `updated_at`: ISO 8601 timestamp; used to determine whether the temp file is stale
- On launch: if temp_draft.json exists → offer "Resume previous session?"; if declined, delete the file

### inbox/ file detection

v1 uses a **manual button** approach — no polling or file watcher.

UX flow:
1. User places files into `inbox/`
2. User clicks **[Check Inbox]** button
3. App scans `inbox/` → displays file list with processing order
4. User clicks **[Load]** to confirm → files are passed to the Editor sequentially

Rationale: simpler, fewer bugs, and the user controls exactly when files are processed.

### Episode requirement for writing

Episodes are **optional**. The user can start writing Chapter 1 without creating any episodes.

- If no active episode is set, the left sidebar displays: `Current Episode: (none)`
- Writing proceeds normally regardless
- After episodes are created, existing chapters can be manually assigned to them in the Episode Management Room

### Model selection UI

Model is a **project-wide setting**, not per-room. Two entry points:

1. **Project Selection Screen** — model can be checked/changed before opening or creating a project
2. **In-project: shared settings button** in the top bar (accessible from all rooms) — opens a project settings panel where the model can be changed

No per-room model dropdowns. All rooms use the same model stored in `project_config.json`.

### Additional: chapter-to-episode uniqueness

A chapter number may only appear in one episode's `chapters` array. When assigning a chapter in the Episode Management Room, if that chapter is already assigned to another episode, show a warning:
```
Chapter 3 is already assigned to "Episode 1: Prologue".
Move it to this episode?  [Move]  [Cancel]
```

### Additional: settings file backup on Settings Organization Room write

The backup system (Section 9) triggers on Recorder completion. Settings Organization Room writes (Step 3) also trigger a backup snapshot, since settings changes are irreversible without one.

### Additional: project name input validation

When creating a new project, the name field rejects characters that are invalid in Windows filesystem paths: `\ / : * ? " < > |`
Show an inline error: `"Project name cannot contain: \ / : * ? " < > |"`

---

## 16. Undecided Items

None. All design items have been finalized.
