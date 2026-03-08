from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, TypedDict

from ..contracts.dtos import AnswerResponse, ChatMessage, DocumentChunk
from ..contracts.interfaces import (
    IAIProviderAccess,
    IGenerationEngine,
    IKnowledgeStoreAccess,
    IQueryManager,
)


def _format_messages_for_prompt(messages: Sequence[BaseMessage]) -> str:
    """Format message history for the completion prompt."""
    if not messages:
        return ""
    parts: list[str] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            role = "User"
        elif isinstance(m, AIMessage):
            role = "Assistant"
        else:
            role = "User"  # Default fallback
        
        content = m.content
        if isinstance(content, list):
            # Handle complex content (list of blocks)
            content = " ".join(
                str(b.get("text", "")) if isinstance(b, dict) else str(b) 
                for b in content
            )
        parts.append(f"{role}: {content}")
        
    return "Conversation:\n" + "\n".join(parts) + "\n\nAnswer the last user question using the context above."


class QueryState(TypedDict):
    document_id: str
    messages: Annotated[list[BaseMessage], add_messages]
    answer: NotRequired[AnswerResponse | None]
    query_vector: NotRequired[list[float]]
    chunks: NotRequired[list[DocumentChunk]]
    raw_response: NotRequired[str]


class QueryManager(IQueryManager):
    """Orchestrates the conversational RAG pipeline using LangGraph with Checkpointing.

    State stores messages as BaseMessage objects. 
    Graph: validate → embed → search → generate → extract → append_assistant.
    The new user message is passed in initial state; add_messages merges it with checkpoint.
    """

    def __init__(
        self,
        generation_engine: IGenerationEngine,
        ai_provider: IAIProviderAccess,
        knowledge_store: IKnowledgeStoreAccess,
    ) -> None:
        self._generation = generation_engine
        self._ai = ai_provider
        self._store = knowledge_store
        self._checkpointer = MemorySaver()
        self._graph = self._build_graph()

    def get_graph_png(self) -> bytes:
        """Generate a PNG visualization of the LangGraph (nodes and routes)."""
        return self._graph.get_graph().draw_mermaid_png()

    def _build_graph(self) -> Any:
        builder = StateGraph(QueryState)

        builder.add_node("validate", self._node_validate)
        builder.add_node("embed", self._node_embed)
        builder.add_node("search", self._node_search)
        builder.add_node("generate", self._node_generate)
        builder.add_node("extract", self._node_extract)
        builder.add_node("append_assistant", self._node_append_assistant)

        builder.add_edge(START, "validate")
        builder.add_conditional_edges(
            "validate",
            self._route_after_validate,
            {"continue": "embed", "append": "append_assistant"},
        )
        builder.add_edge("embed", "search")
        builder.add_conditional_edges(
            "search",
            self._route_after_search,
            {"continue": "generate", "append": "append_assistant"},
        )
        builder.add_edge("generate", "extract")
        builder.add_edge("extract", "append_assistant")
        builder.add_edge("append_assistant", END)

        return builder.compile(checkpointer=self._checkpointer)

    async def _node_validate(self, state: QueryState) -> dict:
        document_id = state["document_id"]
        exists = await self._store.exists(document_id)
        if not exists:
            return {
                "answer": AnswerResponse(
                    document_id=document_id,
                    answer_text="Document not found. Please ingest it first.",
                )
            }
        return {}

    def _route_after_validate(
        self, state: QueryState
    ) -> Literal["continue", "append"]:
        return "append" if state.get("answer") is not None else "continue"

    async def _node_embed(self, state: QueryState) -> dict:
        messages = state.get("messages") or []
        last_user = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                content = m.content
                if isinstance(content, str):
                    last_user = content
                elif isinstance(content, list):
                    last_user = " ".join(str(x) for x in content)
                break
        embed_req = self._generation.create_embedding_request(last_user)
        query_vector = await self._ai.fetch_vector(embed_req)
        return {"query_vector": query_vector}

    async def _node_search(self, state: QueryState) -> dict:
        document_id = state["document_id"]
        query_vector = state.get("query_vector") or []
        results = await self._store.search_similar(
            document_id, query_vector, top_k=5
        )
        if not results:
            return {
                "answer": AnswerResponse(
                    document_id=document_id,
                    answer_text="No relevant content found for this question.",
                )
            }
        return {"chunks": [r.chunk for r in results]}

    def _route_after_search(
        self, state: QueryState
    ) -> Literal["continue", "append"]:
        return "append" if state.get("answer") is not None else "continue"

    async def _node_generate(self, state: QueryState) -> dict:
        chunks = state.get("chunks") or []
        messages = state.get("messages") or []
        conversation_prompt = _format_messages_for_prompt(messages)
        completion_req = self._generation.create_completion_request(
            conversation_prompt, chunks
        )
        raw_response = await self._ai.fetch_completion(completion_req)
        return {"raw_response": raw_response}

    async def _node_extract(self, state: QueryState) -> dict:
        raw_response = state.get("raw_response") or ""
        chunks = state.get("chunks") or []
        answer = self._generation.extract_citations(
            raw_response, chunks, state["document_id"]
        )
        return {"answer": answer}

    async def _node_append_assistant(self, state: QueryState) -> dict:
        """Append the assistant response to messages."""
        answer = state.get("answer")
        if answer is not None:
            return {
                "messages": [AIMessage(content=answer.answer_text)],
            }
        return {}

    async def query_document(
        self,
        document_id: str,
        question: str,
    ) -> AnswerResponse:
        # Use document_id as thread_id as requested
        actual_thread_id = document_id
        config = {"configurable": {"thread_id": actual_thread_id}}
        
        initial: dict[str, Any] = {
            "document_id": document_id,
            "messages": [HumanMessage(content=question)],
        }
        
        result = await self._graph.ainvoke(initial, config=config)

        answer = result.get("answer")
        state_messages = result.get("messages") or []
        
        chat_messages: list[ChatMessage] = []
        for m in state_messages:
            role = "user"
            if isinstance(m, AIMessage):
                role = "assistant"
            
            content = m.content
            if isinstance(content, list):
                 content = " ".join(str(x) for x in content)
            
            chat_messages.append(ChatMessage(role=role, content=str(content)))

        if answer is None:
            return AnswerResponse(
                document_id=document_id,
                thread_id=actual_thread_id,
                answer_text="An error occurred while processing your question.",
                messages=chat_messages,
            )
        
        return AnswerResponse(
            document_id=answer.document_id,
            thread_id=actual_thread_id,
            answer_text=answer.answer_text,
            messages=chat_messages,
        )
