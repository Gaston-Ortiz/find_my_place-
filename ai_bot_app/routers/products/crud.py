from fastapi import APIRouter, HTTPException, Query
from elasticsearch import Elasticsearch, NotFoundError
from typing import List, Optional, Dict, Any
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.documents import Document

# Internal dependencies
from ai_bot_app import settings
from ai_bot_app.routers.routers_dependencies import models
from ai_bot_app.routers.routers_dependencies.embeddings import (
    get_embedding_model,
    retrieval_strategies,
)


router = APIRouter(prefix="/products", tags=["Manage products"])

# Initialize Elasticsearch client and vector store
es_client = Elasticsearch(
    hosts=[f"http://{settings.ELASTIC_URL}"],
    max_retries=10,
)

embeddings = get_embedding_model(
    model=settings.EMBEDDING_MODEL, dimension=settings.EMBEDDING_DIMENSION
)
vector_store = ElasticsearchStore(
    es_connection=es_client,
    index_name=settings.ELASTIC_INDEX_NAME,
    embedding=embeddings,
    strategy=retrieval_strategies["semantic"],
)


@router.get("/", response_model=List[Dict[str, Any]])
async def get_houses(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search_query: Optional[str] = None,
):
    """
    Retrieve houses with optional semantic search
    """
    try:
        if search_query:
            # Perform semantic search
            results = vector_store.similarity_search(search_query, k=limit)
            return [doc.model_dump(exclude={"id", "type"}) for doc in results]
        else:
            # Regular pagination
            response = es_client.search(
                index=settings.ELASTIC_INDEX_NAME,
                body={"from": skip, "size": limit, "query": {"match_all": {}}, "_source": ["text", "metadata"]},
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_house(house: models.HouseAdvertisementCreate):
    """
    Create a new house document
    """
    try:
        document = Document(
            page_content=house.description,
            metadata=house.model_dump(exclude={"description"}),
        )
        vector_store.add_documents([document], ids=[house.code_number])
        return {"message": "House created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{code_number}")
async def get_house(code_number: int):
    """
    Retrieve a specific house by ID
    """
    try:
        response = es_client.get(
            index=settings.ELASTIC_INDEX_NAME,
            id=code_number,
            _source=["text", "metadata"]
        )
        return response["_source"]
    except NotFoundError:
        raise HTTPException(status_code=404, detail="House not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{code_number}")
async def update_house(code_number: int, house: models.HouseAdvertisementUpdate):
    """
    Update an existing house document
    """
    try:
        # Check if document exists
        current_document = es_client.get(index=settings.ELASTIC_INDEX_NAME, id=code_number, _source=["text", "metadata"])["_source"]

        # Extract only the fields provided in the update.
        update_data = house.model_dump(exclude_unset=True)

        # If the user provided an updated description, use it. Otherwise, use the existing 'text' field from the document.
        new_description = update_data.get("description", current_document.get("text"))
        # Remove 'description' from the update data so it doesn't interfere with metadata.
        update_data.pop("description", None)

        # Merge metadata: start with the existing metadata and update only the keys provided.
        new_metadata = current_document.get("metadata", {}).copy()
        new_metadata.update(update_data)

        # Create a new document instance.
        document = Document(
            page_content=new_description,
            metadata=new_metadata,
        )

        vector_store.add_documents([document], ids=[code_number])
        return {"message": "House updated successfully"}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="House not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{code_number}")
async def delete_house(code_number: int):
    """
    Delete a house document
    """
    try:
        es_client.delete(index=settings.ELASTIC_INDEX_NAME, id=code_number)
        return {"message": "House deleted successfully"}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="House not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
