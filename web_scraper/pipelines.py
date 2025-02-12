from web_scraper.dependencies.embedding import get_embedding_model
import elasticsearch
from langchain_core.documents import Document
from web_scraper.dependencies import items
from web_scraper import settings


class ElasticSearchPipeline:
    collection_name = "scrapy_items"

    # def __init__(self, mongo_uri, mongo_db, embedding_model, index_name, strategy):
    #     self.elas = mongo_uri
    #     self.mongo_db = mongo_db
    #     self.embedding_model = embedding_model
    #     self.index_name = index_name
    #     self.strategy = strategy

    def open_spider(self, spider):
        es_client = elasticsearch.Elasticsearch(
            hosts=[f"http://{settings.ELASTIC_URL}"],
            max_retries=10,
        )

        embeddings = get_embedding_model(
            model=settings.EMBEDDING_MODEL, dimension=settings.EMBEDDING_DIMENSION
        )

        print(f"Embedding model: {settings.EMBEDDING_MODEL}")

        self.vector_store = ElasticsearchStore(
            es_connection=es_client,
            index_name=settings.ELASTIC_INDEX_NAME,
            embedding=embeddings,
            strategy=retrieval_strategies["semantic"],
        )

    def process_item(self, house_item: items.HouseAdvertisement, spider):
        # house_item = items.HouseAdvertisement(**house_item)

        document = Document(
            page_content=house_item.description,
            metadata=house_item.model_dump(exclude={"description", "code_number"}),
        )

        self.vector_store.add_documents([document], ids=[house_item.code_number])

        return house_item.model_dump()

    def close_spider(self, spider):
        self.es_client.close()
        self.vector_store.close()
