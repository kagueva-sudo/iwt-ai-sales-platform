from app.contracts.knowledge_provider import KnowledgeProvider
from app.domain.sources import SourceSelectionResult, VerifiedSource


class SourceSelector:
    def __init__(self, providers: list[KnowledgeProvider]) -> None:
        self.providers = providers

    async def select_sources(self, query: str) -> SourceSelectionResult:
        selected_sources: list[VerifiedSource] = []
        for provider in self.providers:
            result = await provider.search(query)
            selected_sources.extend(result.sources)

        return SourceSelectionResult(query=query, sources=selected_sources)
