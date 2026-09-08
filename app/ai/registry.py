from __future__ import annotations

from typing import Dict, List, Optional

from app.ai.base import AIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.kimi import KimiProvider
from app.ai.providers.opencode import OpenCodeProvider
from app.ai.providers.qwen import QwenProvider


class ProviderRegistry:
    def __init__(
        self,
        order: Optional[List[str]] = None,
        register_defaults: bool = True,
    ):
        self._providers: Dict[str, AIProvider] = {}
        self._order: List[str] = []
        self._register_defaults_called = False
        if register_defaults:
            self._register_defaults()
            self._register_defaults_called = True
        if order:
            self._order = [name for name in order if name in self._providers]

    def _register_defaults(self) -> None:
        self.register(KimiProvider())
        self.register(QwenProvider())
        self.register(OpenCodeProvider())
        self.register(GeminiProvider())

    def register(self, provider: AIProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[AIProvider]:
        return self._providers.get(name)

    def by_name(self) -> Dict[str, AIProvider]:
        return dict(self._providers)

    def ordered_names(self) -> List[str]:
        # Include names not explicitly ordered at the end
        ordered = [n for n in self._order if n in self._providers]
        for name in self._providers:
            if name not in ordered:
                ordered.append(name)
        return ordered

    def names(self) -> List[str]:
        return list(self._providers.keys())


def build_registry(order: Optional[List[str]] = None) -> ProviderRegistry:
    return ProviderRegistry(order=order if order is not None else [])
