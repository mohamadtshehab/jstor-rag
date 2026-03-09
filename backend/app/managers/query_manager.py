from __future__ import annotations

from typing import Annotated, Any, Literal
from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired, TypedDict

from ..contracts.dtos import AnswerResponse, ChatMessage, DocumentChunk
from ..contracts.interfaces import (
    IAIProviderAccess,
    IGeneratingEngine,
    IKnowledgeStoreAccess,
    IQueryManager,
)


class QueryState(TypedDict):
    document_id: str
    messages: Annotated[list[BaseMessage], add_messages]
    answer: NotRequired[AnswerResponse | None]
    query_vector: NotRequired[list[float]]
    chunks: NotRequired[list[DocumentChunk]]
    raw_response: NotRequired[str]


class SearchToolInput(BaseModel):
    query: str = Field(description="The query string to search for in the document.")

class QueryManager(IQueryManager):
    """Orchestrates the conversational RAG pipeline using LangGraph with Checkpointing.

    Implements the agentic pattern: LLM -> Conditional -> Tool -> LLM.
    """

    def __init__(
        self,
        generation_engine: IGeneratingEngine,
        ai_provider: IAIProviderAccess,
        knowledge_store: IKnowledgeStoreAccess,
    ) -> None:
        self._generation = generation_engine
        self._ai = ai_provider
        self._store = knowledge_store

        @tool(args_schema=SearchToolInput)
        async def search_tool(query: str, config: RunnableConfig) -> str:
            """Search the document for relevant context and information.

            Args:
                query: The query string to search for in the document.
            """
            doc_id = config.get("configurable", {}).get("document_id")
            if not doc_id:
                return "Error: Document ID context missing."

            embed_req = self._generation.create_embedding_request(query)
            query_vector = await self._ai.fetch_vector(embed_req)

            results = await self._store.search_similar(
                doc_id, query_vector, top_k=5
            )

            if not results:
                return "No relevant information found in the document."

            context_text = "\n\n".join(
                f"[Chunk {i+1}]: {r.chunk.text}"
                for i, r in enumerate(results)
            )
            return context_text

        self.tools = [search_tool]
        self.tools_by_name = {t.name: t for t in self.tools}

        self.model = self._ai.get_chat_model()
        self.model_with_tools = self.model.bind_tools(self.tools, tool_choice="auto")

        self._checkpointer = MemorySaver()
        self._graph = self._build_graph()

    def get_graph_png(self) -> bytes:
        """Generate a PNG visualization of the LangGraph (nodes and routes)."""
        return self._graph.get_graph().draw_mermaid_png()

    def _build_graph(self) -> Any:
        builder = StateGraph(QueryState)

        builder.add_node("llm_call", self.llm_call)
        builder.add_node("tool_node", self.tool_node)

        builder.add_edge(START, "llm_call")
        builder.add_conditional_edges(
            "llm_call",
            self.should_continue,
            ["tool_node", END]
        )
        builder.add_edge("tool_node", "llm_call")

        return builder.compile(checkpointer=self._checkpointer)

    async def llm_call(self, state: QueryState, config: RunnableConfig) -> dict:
        """LLM decides whether to call a tool or not."""
        messages = state["messages"]
        sys_msg = SystemMessage(content=self._generation.create_rag_system_prompt())
        response = await self.model_with_tools.ainvoke([sys_msg] + messages, config)
        return {"messages": [response]}

    async def tool_node(self, state: QueryState, config: RunnableConfig) -> dict:
        """Performs the tool call."""
        result = []
        last_message = state["messages"][-1]

        if not isinstance(last_message, AIMessage):
            raise ValueError("Last message must be an AI message to contain tool calls.")

        for tool_call in last_message.tool_calls:
            tool = self.tools_by_name[tool_call["name"]]
            observation = await tool.ainvoke(tool_call["args"], config=config)
            result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))

        return {"messages": result}

    def should_continue(self, state: QueryState) -> Literal["tool_node", "__end__"]:
        """Decide whether to loop through the tool or stop."""
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tool_node"
        return "__end__"

    async def clear_conversation(self, document_id: str) -> None:
        """Discard all checkpointed state for the given document thread."""
        thread_id = document_id
        keys_to_delete = [
            key for key in self._checkpointer.storage
            if key[0] == thread_id
        ]
        for key in keys_to_delete:
            del self._checkpointer.storage[key]

    async def query_document(
        self,
        document_id: str,
        question: str,
    ) -> AnswerResponse:
        actual_thread_id = document_id

        config = {
            "configurable": {
                "thread_id": actual_thread_id,
                "document_id": document_id,
            }
        }

        initial: dict[str, Any] = {
            "document_id": document_id,
            "messages": [HumanMessage(content=question)],
        }

        result = await self._graph.ainvoke(initial, config=config)

        state_messages = result.get("messages") or []

        chat_messages: list[ChatMessage] = []
        last_answer_text = ""

        for m in state_messages:
            role = "user"
            if isinstance(m, AIMessage):
                role = "assistant"
                if m.content:
                    last_answer_text = str(m.content)
            elif isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, ToolMessage):
                continue

            content = m.content
            if isinstance(content, list):
                content = " ".join(str(x) for x in content)

            chat_messages.append(ChatMessage(role=role, content=str(content)))

        return AnswerResponse(
            document_id=document_id,
            thread_id=actual_thread_id,
            answer_text=last_answer_text or "No answer generated.",
            messages=chat_messages,
        )
