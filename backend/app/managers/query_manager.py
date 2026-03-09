from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from typing import Annotated, Any, Literal

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
    IGenerationEngine,
    IKnowledgeStoreAccess,
    IQueryManager,
)


class QueryState(TypedDict):
    document_id: str
    messages: Annotated[list[BaseMessage], add_messages]
    # Legacy fields (optional)
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
        generation_engine: IGenerationEngine,
        ai_provider: IAIProviderAccess,
        knowledge_store: IKnowledgeStoreAccess,
    ) -> None:
        self._generation = generation_engine
        self._ai = ai_provider
        self._store = knowledge_store
        
        # Define tools
        @tool(args_schema=SearchToolInput)
        async def search_tool(query: str, config: RunnableConfig) -> str:
            """Search the document for relevant context and information.
            
            Args:
                query: The query string to search for in the document.
            """
            doc_id = config.get("configurable", {}).get("document_id")
            if not doc_id:
                return "Error: Document ID context missing."
                
            # Embed query
            embed_req = self._generation.create_embedding_request(query)
            query_vector = await self._ai.fetch_vector(embed_req)
            
            # Search knowledge base
            results = await self._store.search_similar(
                doc_id, query_vector, top_k=5
            )
            
            if not results:
                return "No relevant information found in the document."
                
            # Format results
            context_text = "\n\n".join(
                f"[Chunk {i+1}]: {r.chunk.text}" 
                for i, r in enumerate(results)
            )
            return context_text

        self.tools = [search_tool]
        self.tools_by_name = {t.name: t for t in self.tools}
        
        # Bind tools to model
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
        """LLM decides whether to call a tool or not"""
        messages = state["messages"]
        
        # Prepend system message
        sys_msg = SystemMessage(
            content="You are a helpful assistant. You are answering questions about a specific document. "
                    "You have access to a 'search_tool' that allows you to search for relevant sections in the document. "
                    "Use this tool to find information before answering user questions. "
        )
        
        # Invoke model
        response = await self.model_with_tools.ainvoke([sys_msg] + messages, config)
        return {"messages": [response]}

    async def tool_node(self, state: QueryState, config: RunnableConfig) -> dict:
        """Performs the tool call"""
        result = []
        last_message = state["messages"][-1]
        
        if not isinstance(last_message, AIMessage):
             raise ValueError("Last message must be an AI message to contain tool calls.")
        
        for tool_call in last_message.tool_calls:
            tool = self.tools_by_name[tool_call["name"]]
            # Pass config to tool execution so it can access document_id
            observation = await tool.ainvoke(tool_call["args"], config=config)
            result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
            
        return {"messages": result}

    def should_continue(self, state: QueryState) -> Literal["tool_node", "__end__"]:
        """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""
        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM makes a tool call, then perform an action
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tool_node"

        # Otherwise, we stop (reply to the user)
        return "__end__"

    async def query_document(
        self,
        document_id: str,
        question: str,
    ) -> AnswerResponse:
        # Use document_id as thread_id
        actual_thread_id = document_id
        
        # Config including document_id for tools
        config = {
            "configurable": {
                "thread_id": actual_thread_id,
                "document_id": document_id
            }
        }
        
        initial: dict[str, Any] = {
            "document_id": document_id,
            "messages": [HumanMessage(content=question)],
        }
        
        result = await self._graph.ainvoke(initial, config=config)

        state_messages = result.get("messages") or []
        
        # Convert to ChatMessage list for DTO
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
                continue # Skip tool messages in final output if desired, or map to 'system'
            
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
