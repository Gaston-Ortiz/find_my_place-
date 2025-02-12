# Third party dependencies
from fastapi import FastAPI

# Internal dependencies
from ai_bot_app.routers.products import crud
from ai_bot_app.routers.bot import ai_bot

app = FastAPI(
    title="APIs for AI Bot App",
    description="These APIs are used in AI Bot App. You can use them to manage the products in the database and chat with the AI to get information about the products.",
    version="1.0.0",
)

app.include_router(crud.router, prefix="/api/v1")
app.include_router(ai_bot.router, prefix="/api/v1")
