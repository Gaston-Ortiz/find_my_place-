import os

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
)
# Delay requests to avoid bot detection
DOWNLOAD_DELAY = 1  # Wait 2 seconds between requests
RANDOMIZE_DOWNLOAD_DELAY = True  # Randomize delay slightly
CONCURRENT_REQUESTS_PER_DOMAIN = 1  # Only 1 request at a time

SPIDER_MODULES = ["web_scraper.spiders"]
NEWSPIDER_MODULE = "web_scraper.spiders"

# Pipelines are set per spider: `listings` stores in Postgres (custom_settings).
# Elasticsearch is paused (see PLAN.md); it was fed by `house_spider` with
# {"web_scraper.pipelines.ElasticSearchPipeline": 300}
ITEM_PIPELINES = {}

# Postgres settings (docker-compose sets DATABASE_URL; the default targets the
# compose service from the host, on POSTGRES_PORT)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://find_my_place:find_my_place@localhost:5433/find_my_place",
)

# Elasticsearch settings (overridable from the environment, e.g. docker-compose)
ELASTIC_URL = os.getenv("ELASTIC_URL", "elasticsearch:9200")
ELASTIC_INDEX_NAME = os.getenv("ELASTIC_INDEX_NAME", "scrapy_items")

# Embedding settings
EMBEDDING_MODEL = "avsolatorio/GIST-small-Embedding-v0"
EMBEDDING_DIMENSION = 384

# Chat settings
CHAT_MODEL = "gpt-4o-mini"
