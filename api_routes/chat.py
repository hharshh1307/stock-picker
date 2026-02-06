"""Chat API endpoint with SSE streaming."""

import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request body."""
    message: str
    conversation_id: str | None = None


class ChatSuggestion(BaseModel):
    """Suggested question."""
    question: str
    category: str


SUGGESTED_QUESTIONS = [
    ChatSuggestion(question="Should I invest in RELIANCE?", category="stock_analysis"),
    ChatSuggestion(question="Compare TCS vs INFY", category="comparison"),
    ChatSuggestion(question="Which sectors are trending?", category="market"),
    ChatSuggestion(question="What are the top gaining stocks?", category="market"),
    ChatSuggestion(question="Which IT stocks are undervalued?", category="sector"),
    ChatSuggestion(question="Why is Adani falling?", category="news"),
    ChatSuggestion(question="Where should I invest 5 lakhs?", category="advice"),
    ChatSuggestion(question="What's happening in the banking sector?", category="sector"),
]


@router.get("/suggestions")
async def get_suggestions() -> list[dict[str, str]]:
    """Get suggested questions for the chat."""
    return [{"question": s.question, "category": s.category} for s in SUGGESTED_QUESTIONS]


async def generate_response(message: str, conversation_id: str | None) -> AsyncGenerator[str, None]:
    """Generate SSE events for the chat response.

    This is a placeholder that will be replaced with the actual agent implementation.
    """
    try:
        # Import the agent (will be created later)
        from agent import FinancialExpertAgent
        from api_server import get_store

        store = get_store()
        agent = FinancialExpertAgent(store)

        # Stream the response
        async for chunk in agent.stream_response(message, conversation_id):
            yield f"data: {json.dumps(chunk)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except ImportError:
        # Agent not yet implemented - return a placeholder response
        yield f"data: {json.dumps({'type': 'text', 'content': 'The AI agent is not yet configured. '})}\n\n"
        yield f"data: {json.dumps({'type': 'text', 'content': 'Please ensure OPENAI_API_KEY is set in your .env file '})}\n\n"
        yield f"data: {json.dumps({'type': 'text', 'content': 'and the agent module is properly installed.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Chat endpoint with SSE streaming."""
    return StreamingResponse(
        generate_response(request.message, request.conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sync")
async def chat_sync(request: ChatRequest) -> dict[str, Any]:
    """Synchronous chat endpoint (non-streaming) for testing."""
    try:
        from agent import FinancialExpertAgent
        from api_server import get_store

        store = get_store()
        agent = FinancialExpertAgent(store)
        response = agent.get_response(request.message, request.conversation_id)

        return {
            "success": True,
            "response": response,
            "conversation_id": request.conversation_id,
        }

    except ImportError:
        return {
            "success": False,
            "error": "Agent not configured. Set OPENAI_API_KEY in .env file.",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
