# Third party imports
from fastapi import APIRouter, HTTPException, Query

# Internal dependencies
from ai_bot_app import settings
from ai_bot_app.routers.routers_dependencies.react_agent import get_react_agent


router = APIRouter(prefix="/bot", tags=["Bot"])

agent_executor = get_react_agent()


@router.post("/")
async def get_bot_response(question: str, thread_id: str):
    """
    Get a response from the bot

    Parameters
    ----------
    question: str
        The question to ask the bot
    thread_id: str
        The thread id

    Returns
    -------
    response: str
        The response from the bot
    """
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    response = agent_executor.invoke({"messages": [("human", question)]}, config=config)

    return response
