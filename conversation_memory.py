from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class MemoryTurn:
    role: str
    content: str


class SimpleConversationBufferMemory:
    """
    Lightweight fallback implementation compatible with the idea of
    ConversationBufferMemory.

    It stores a rolling conversation history for data analysis agent runs.
    The goal is to make multi-turn analysis traceable even when the full
    LangChain package is not installed in the runtime environment.
    """

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self.chat_memory: List[MemoryTurn] = []

    def save_context(self, inputs: Dict[str, str], outputs: Dict[str, str]) -> None:
        user_input = inputs.get("input", "")
        agent_output = outputs.get("output", "")

        if user_input:
            self.chat_memory.append(MemoryTurn(role="user", content=user_input))

        if agent_output:
            self.chat_memory.append(MemoryTurn(role="assistant", content=agent_output))

        if len(self.chat_memory) > self.max_turns:
            self.chat_memory = self.chat_memory[-self.max_turns :]

    def load_memory_variables(self, _: Dict[str, str] | None = None) -> Dict[str, str]:
        history = "\n".join(
            f"{turn.role}: {turn.content}" for turn in self.chat_memory
        )
        return {"chat_history": history}

    def clear(self) -> None:
        self.chat_memory.clear()
