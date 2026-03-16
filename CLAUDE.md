# CLAUDE.md

## ⚠️ Must Read First When Starting a New Conversation

**This project is an ongoing design and development effort.**
When a new conversation begins, you must read the file below **before writing any code** to understand the current design intentions and project status.

```
E:\novel_AI_python\PROJECT_DESIGN.md
```

- This file contains the project goals, agent roles, pipeline structure, and UI architecture.
- The file is continuously updated, so **always refer to the latest version**.
- Treat this design document as the **primary source of truth**, even over existing code.

---

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## 5. Git Workflow

This project uses **Git and GitHub for version control**.  
All implementation work must follow the rules below.

### Commit Policy

- Commit after completing each **logical implementation step**.
- Do not accumulate large amounts of changes without committing.
- Each commit should represent **one clear change or feature**.
- Ensure the code runs without obvious errors before committing.

### Commit Message Rules

Commit messages must be written **in Korean**.

Use simple structured prefixes:

```

feat: 새로운 기능 구현
fix: 버그 수정
refactor: 구조 개선 (기능 변화 없음)
docs: 문서 수정
test: 테스트 추가/수정
chore: 기타 작업 (설정, 의존성 등)

```

Examples:

```

feat: 에피소드 데이터 구조 구현
fix: 챕터 번호 계산 오류 수정
refactor: 루프 컨트롤러 단순화
docs: PROJECT_DESIGN.md 업데이트

```

### Commit Timing

After finishing a development step:

1. Verify the code runs.
2. Stage modified files.
3. Create a git commit with a clear message.

Avoid committing incomplete or broken states unless explicitly necessary.

### Scope Discipline

- Do not mix unrelated changes in a single commit.
- If two features are implemented, create **two commits**.
- If documentation changes are separate from code changes, commit them separately.

### Branch Strategy

```
main
└── dev
    ├── feat/episode-management-room
    ├── feat/settings-organization-room
    ├── fix/revision-count-bug
    └── ...
```

- **`main`** — stable only. Receives merges from `dev` when a milestone is complete.
- **`dev`** — integration branch. All work branches are created from and merged back into `dev`.
- **Work branches** — named after the type and scope of work, e.g. `feat/episode-management-room`, `fix/revision-count-bug`, `refactor/common-sidebar`. Use the same prefixes as commit messages (`feat/fix/refactor/docs/chore`).

### GitHub Usage

The repository will be synchronized with **GitHub**.

Work branch workflow:

```
git checkout dev
git pull origin dev
git checkout -b feat/your-feature

... implement & commit ...

git pull origin dev        ← sync before PR
git push origin feat/your-feature
→ open PR into dev
→ merge
```

Frequent small commits are preferred over large commits.

### Safety Rule

If a change significantly modifies multiple files or core logic:

- Commit the current stable state **before starting the change**.

This ensures that the project can be rolled back easily if something breaks.