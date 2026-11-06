from app.contracts.prompt_builder import PromptBuilder
from app.domain.conversations import ConversationContext, ConversationMessage
from app.domain.messages import Message
from app.domain.prompt_context import PromptContext
from app.domain.prompts import PromptMetadata
from app.domain.sessions import SessionContext
from app.domain.sources import VerifiedSource
from app.domain.tools import ToolDescription
from app.prompt_builder.policies import DEFAULT_RESPONSE_CONSTRAINTS, DEFAULT_SAFETY_RULES
from app.prompt_builder.templates import SYSTEM_PROMPT_TEMPLATE, format_verified_sources


class DefaultPromptBuilder(PromptBuilder):
    """Builds PromptContext from already prepared session, conversation and sources."""

    async def build(
        self,
        message: Message,
        session: SessionContext,
        conversation: ConversationContext,
        verified_sources: list[VerifiedSource],
        available_tools: list[ToolDescription],
    ) -> PromptContext:
        sources_block = self._format_sources(verified_sources)
        history_block = self._format_history(conversation.recent_messages, current_text=message.text)
        system_prompt = f"{SYSTEM_PROMPT_TEMPLATE}\n\n{format_verified_sources(sources_block)}"
        if history_block:
            system_prompt = f"{system_prompt}\n\n{history_block}"

        return PromptContext(
            system_prompt=system_prompt,
            user_message=message.text,
            conversation_summary=conversation.conversation_summary,
            recent_messages=list(conversation.recent_messages),
            active_topic=conversation.active_topic,
            active_product=conversation.active_product,
            verified_sources=list(verified_sources),
            available_tools=list(available_tools),
            safety_rules=list(DEFAULT_SAFETY_RULES),
            response_constraints=list(DEFAULT_RESPONSE_CONSTRAINTS),
            metadata=PromptMetadata(
                prompt_type="sales_default",
                language="ru",
                values={
                    "session_id": session.session_id,
                    "dialog_id": session.dialog_id,
                    "channel": session.channel.value,
                },
            ),
        )

    def _format_sources(self, verified_sources: list[VerifiedSource]) -> str:
        if not verified_sources:
            return ""

        lines: list[str] = []
        for source in verified_sources:
            confirmed = source.metadata.get("confirmed_fields", "")
            lines.append(
                f"- [{source.source_type}/{source.source_id}] {source.title}: "
                f"{source.content} (confirmed_fields={confirmed or 'none'})"
            )
        return "\n".join(lines)

    def _format_history(
        self,
        recent_messages: list[ConversationMessage],
        *,
        current_text: str,
    ) -> str:
        filtered = [
            item
            for item in recent_messages
            if not (
                item.role in {"user", "customer", "client"}
                and item.text.strip() == current_text.strip()
            )
        ]
        recent = filtered[-6:]
        if not recent:
            return ""
        lines = ["Recent conversation:"]
        for item in recent:
            role = "client" if item.role in {"user", "customer", "client"} else "assistant"
            lines.append(f"- {role}: {item.text}")
        return "\n".join(lines)
