from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InputEvent:
    source: str
    command: str
    payload: str | None = None


class InputProvider(Protocol):
    name: str

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...


class InputManager:
    def __init__(self) -> None:
        self._providers: list[InputProvider] = []

    def register(self, provider: InputProvider) -> None:
        self._providers.append(provider)

    def start_all(self) -> None:
        for provider in self._providers:
            provider.start()

    def stop_all(self) -> None:
        for provider in self._providers:
            provider.stop()
