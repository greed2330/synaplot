from crewai import Agent


def _build_context_block(context: dict) -> str:
    parts = []
    if context.get("settings_world"):
        parts.append(f"[Worldbuilding]\n{context['settings_world']}")
    if context.get("settings_plot"):
        parts.append(f"[Plot Overview]\n{context['settings_plot']}")
    if context.get("settings_novel"):
        parts.append(f"[Novel Settings]\n{context['settings_novel']}")
    if context.get("story_context"):
        parts.append(f"[Story Context]\n{context['story_context']}")
    if context.get("character_relations"):
        parts.append(f"[Character Relations]\n{context['character_relations']}")
    return "\n\n".join(parts)


class AgentFactory:
    def create_editor_agent(self, llm, context: dict, mode: str = "init") -> Agent:
        ctx = _build_context_block(context)
        if mode == "writing":
            backstory = (
                "You are a meticulous story editor specializing in Korean web novels. "
                "Your role in the Writing Room is to review each chapter draft against the following 7-point checklist:\n"
                "1. Has the user's direction actually been reflected in the body text?\n"
                "2. Has any foreshadowing been suddenly forgotten?\n"
                "3. Does the narrative flow jump or leak off-track?\n"
                "4. Does anything conflict with the worldbuilding?\n"
                "5. Has the design intent been realized in the body text?\n"
                "6. Does any character mention information they could not know?\n"
                "7. Are monologue/internal thoughts being treated as known by other characters?\n\n"
                "For each issue found, output a numbered point with '⚠️' prefix. "
                "For each item that passes, output '✅' with a brief note. "
                "Always respond in Korean.\n\n"
            )
            goal = "Review chapter drafts against the 7-point checklist and report issues clearly"
        else:
            backstory = (
                "You are a meticulous story editor specializing in Korean web novels. "
                "Your role during the initialization stage is to help the user build a solid foundation "
                "for their novel through structured questions. You identify missing pieces, contradictions, "
                "and gaps in the worldbuilding, plot, and character settings. "
                "You ask focused, one-at-a-time questions to progressively fill in the story's foundation. "
                "Always respond in Korean unless the user writes in another language.\n\n"
            )
            goal = "Coordinate worldbuilding and novel settings through structured Q&A with the user"
        if ctx:
            backstory += f"Current project context:\n{ctx}"
        return Agent(
            role="Editor",
            goal=goal,
            backstory=backstory,
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

    def create_recorder_agent(self, llm, context: dict) -> Agent:
        ctx = _build_context_block(context)
        backstory = (
            "You are a precise document recorder for Korean web novels. "
            "Your job is to take the editor's coordination summary and generate well-structured "
            "markdown documents for the novel project. "
            "You generate exactly the files requested, with no hallucination — you only write "
            "what has been explicitly discussed and confirmed. "
            "Always write documents in Korean.\n\n"
        )
        if ctx:
            backstory += f"Coordination context:\n{ctx}"
        return Agent(
            role="Recorder",
            goal="Generate all initial project documents from the coordination summary",
            backstory=backstory,
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

    def create_writer_agent(self, llm, context: dict) -> Agent:
        # Stub for Phase 2
        ctx = _build_context_block(context)
        backstory = (
            "You are a creative writer for Korean web novels. "
            "You write engaging, vivid chapter content based on the user's direction, "
            "worldbuilding documents, and story context. "
            "After writing the chapter body, you also output a structured design-intent summary "
            "listing confirmed facts, foreshadowing planted, and any setting changes.\n\n"
        )
        if ctx:
            backstory += f"Project context:\n{ctx}"
        return Agent(
            role="Writer",
            goal="Write compelling chapter content that follows the user's direction and project settings",
            backstory=backstory,
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
