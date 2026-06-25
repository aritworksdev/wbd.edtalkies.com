from __future__ import annotations


class PromptBuilder:
    def build_teacher_prompt(self, recognized_text: str) -> str:
        return recognized_text.strip()
