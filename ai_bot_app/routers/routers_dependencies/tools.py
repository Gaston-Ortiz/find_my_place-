# Standard library imports
import json

# Third party imports
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain.docstore.document import Document

# Internal dependencies
from ai_bot_app import settings
from ai_bot_app.routers.routers_dependencies.embeddings import get_retrieval


@tool(response_format="content_and_artifact")
def retrieve_docs(
    question: str,
    config: RunnableConfig,
) -> list[Document]:
    "Search and return information about the pdf"

    # Get retriever
    retriever = get_retrieval(
        index_name=settings.ELASTIC_INDEX_NAME,
        strategy="semantic",
        embedding_model=settings.EMBEDDING_MODEL,
    )

    # Do similarity search
    retrieved_docs = retriever.similarity_search(query=question, k=5)

    serialized = "\n\n".join(
        (
            f"Name: {doc.metadata['name']}\n"
            f"Source: {doc.metadata}\n"
            f"Content: {doc.page_content}"
        )
        for doc in retrieved_docs
    )

    return serialized, retrieved_docs


@tool
def save_data(data_dict: dict) -> str:
    """Save data as a json file"""

    # Save data_dict as JSON in current directory
    with open("data.json", "w") as f:
        json.dump(data_dict, f, indent=4)

    return "Data saved successfully"
